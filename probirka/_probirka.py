from __future__ import annotations

from asyncio import ensure_future, gather, wait
from collections import defaultdict
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from time import monotonic
from typing import TYPE_CHECKING, Any, TypeVar

from probirka._probe import CallableProbe, Probe, ProbeCallable
from probirka._results import ProbeResult, ProbirkaResult

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

ProbeFuncT = TypeVar('ProbeFuncT', bound=ProbeCallable)


class Probirka:
    """Probirka is a health check manager that allows adding and running probes."""

    def __init__(
        self,
        success_ttl: int | timedelta | None = None,
        failed_ttl: int | timedelta | None = None,
    ) -> None:
        """
        Initialize the Probirka instance.

        :param success_ttl: Default cache duration for successful results. If None, successful results are not cached.
        :param failed_ttl: Default cache duration for failed results. If None, failed results are not cached.
        """
        self._required_probes: list[Probe] = []
        self._optional_probes: dict[str, list[Probe]] = defaultdict(list)
        self._group_allow_failure: dict[str, bool] = {}
        self._info: dict[str, Any] | None = None
        self._success_ttl = timedelta(seconds=success_ttl) if isinstance(success_ttl, int) else success_ttl
        self._failed_ttl = timedelta(seconds=failed_ttl) if isinstance(failed_ttl, int) else failed_ttl

    def add_info(
        self,
        name: str,
        value: Any,
    ) -> None:
        """
        Add information to the health check result.

        :param name: The name of the information.
        :param value: The value of the information.
        """
        if self._info is None:
            self._info = {}
        self._info[name] = value

    @property
    def info(
        self,
    ) -> dict[str, Any] | None:
        """
        Get the information added to the health check result.

        :return: The information added to the health check result.
        """
        return self._info

    def add_probes(
        self,
        *probes: Probe,
        groups: str | Sequence[str] = '',
        allow_failure: bool | None = None,
    ) -> None:
        """
        Add probes to the health check.

        :param probes: Probes to add
        :param groups: Groups for optional probes. Probes without groups are required.
        :param allow_failure: Group-level override of the probes' own ``allow_failure``.
            ``None`` (default) leaves the group as is, so every probe keeps its own setting.
            ``True``/``False`` applies to all probes of the given groups, including ones
            added earlier, and replaces a value set by a previous call. A probe that is run
            through several sources (required list, several groups) is allowed to fail only
            if every source allows it. Requires ``groups``.
        :raises ValueError: if ``allow_failure`` is given without ``groups``
        """
        if groups:
            names = [groups] if isinstance(groups, str) else groups
            for group in names:
                self._optional_probes[group].extend(probes)
                if allow_failure is not None:
                    self._group_allow_failure[group] = allow_failure
            return
        if allow_failure is not None:
            msg = 'allow_failure applies to groups; set it on the probe itself'
            raise ValueError(msg)
        self._required_probes.extend(probes)

    def add(
        self,
        name: str | None = None,
        timeout: int | None = None,
        groups: str | Sequence[str] = '',
        success_ttl: int | timedelta | None = None,
        failed_ttl: int | timedelta | None = None,
        allow_failure: bool = False,
    ) -> Callable[[ProbeFuncT], ProbeFuncT]:
        """
        Register the decorated callable as a probe.

        :param name: Probe name
        :param timeout: Probe timeout in seconds
        :param groups: Groups for optional probes. Probes without groups are required.
        :param success_ttl: Cache duration for successful results. If None, uses the global success_ttl setting.
            Pass ``0`` to disable caching of successful results for this probe.
        :param failed_ttl: Cache duration for failed results. If None, uses the global failed_ttl setting.
            Pass ``0`` to disable caching of failed results for this probe.
        :param allow_failure: If True, a failure of this probe does not affect the overall ``ok``.
            A group-level ``allow_failure`` passed to :meth:`add_probes` overrides this.
        :return: Decorated function
        """

        def _wrapper(func: ProbeFuncT) -> ProbeFuncT:
            self.add_probes(
                CallableProbe(
                    func=func,
                    name=name,
                    timeout=timeout,
                    success_ttl=success_ttl if success_ttl is not None else self._success_ttl,
                    failed_ttl=failed_ttl if failed_ttl is not None else self._failed_ttl,
                    allow_failure=allow_failure,
                ),
                groups=groups,
            )
            return func

        return _wrapper

    def _collect(
        self,
        with_groups: Sequence[str],
        skip_required: bool,
    ) -> tuple[list[Probe], dict[int, list[bool | None]]]:
        """
        Build the list of probes to run and, per probe, the ``allow_failure`` value of its sources.

        A source is the required list or a group the probe is run through; it contributes ``None``
        when it does not override the probe's own setting.
        The same probe object may appear more than once in the list; its sources are
        merged by identity so the effective flag is the same for every occurrence.

        :param with_groups: Groups to run
        :param skip_required: Skip probes without groups
        :return: Probes in registration order and their sources keyed by ``id(probe)``
        """
        probes: list[Probe] = []
        sources: dict[int, list[bool | None]] = defaultdict(list)
        if not skip_required:
            for probe in self._required_probes:
                probes.append(probe)
                sources[id(probe)].append(None)
        for group in with_groups:
            group_flag = self._group_allow_failure.get(group)
            for probe in self._optional_probes.get(group, ()):
                probes.append(probe)
                sources[id(probe)].append(group_flag)
        return probes, sources

    @staticmethod
    def _effective_allow_failure(
        own: bool,
        sources: Sequence[bool | None],
    ) -> bool:
        """
        Combine the probe's own ``allow_failure`` with the overrides of the sources it ran through.

        Every source must allow the failure: a strict source always wins.
        """
        return all(own if flag is None else flag for flag in sources)

    async def _inner_run(
        self,
        with_groups: Sequence[str],
        skip_required: bool,
        timeout: int | None,
        started_at: datetime,
        start: float,
    ) -> tuple[list[ProbeResult], bool]:
        """
        Run probes concurrently and gather results in registration order.

        Probes that do not finish within ``timeout`` are cancelled and reported
        as failed with a ``TimeoutError`` message, so partial results survive.
        Each result carries the effective ``allow_failure`` for this run: the probe's
        own setting unless a group it ran in overrides it.

        :param with_groups: Groups to run. Required probes run unless skip_required=True
        :param skip_required: Skip probes without groups
        :param timeout: Overall timeout in seconds, ``None`` to wait indefinitely
        :param started_at: Wall-clock start of the whole run, reported in results
        :param start: ``time.monotonic()`` reading taken at the same moment, used to measure durations
        :return: Probe results and whether the overall timeout was hit
        """
        probes, sources = self._collect(with_groups, skip_required)
        if not probes:
            return [], False

        tasks = [ensure_future(probe.run_check()) for probe in probes]
        _, pending = await wait(tasks, timeout=timeout)
        if pending:
            for task in pending:
                task.cancel()
            await gather(*pending, return_exceptions=True)

        timeout_error = f'TimeoutError: probirka run timed out after {timeout}s'
        results: list[ProbeResult] = []
        for probe, task in zip(probes, tasks, strict=True):
            if task in pending:
                own = bool(getattr(probe, 'allow_failure', False))
                results.append(
                    ProbeResult(
                        name=probe.name,
                        ok=False,
                        cached=None,
                        started_at=started_at,
                        elapsed=timedelta(seconds=monotonic() - start),
                        info=probe.info,
                        error=timeout_error,
                        allow_failure=self._effective_allow_failure(own, sources[id(probe)]),
                    )
                )
                continue
            result = task.result()
            effective = self._effective_allow_failure(result.allow_failure, sources[id(probe)])
            if effective != result.allow_failure:
                result = replace(result, allow_failure=effective)
            results.append(result)
        return results, bool(pending)

    async def run(
        self,
        timeout: int | None = None,
        with_groups: str | Sequence[str] = '',
        skip_required: bool = False,
    ) -> ProbirkaResult:
        """
        Run health check and return results.

        The overall timeout never raises: probes that did not finish in time are
        reported as failed and ``error`` is set. ``ok`` is ``False`` only if a probe
        without ``allow_failure`` failed or did not finish in time.

        :param timeout: Overall timeout in seconds
        :param with_groups: Groups to run. Required probes run unless skip_required=True
        :param skip_required: Skip probes without groups
        :return: Health check result
        """
        groups = ([with_groups] if with_groups else []) if isinstance(with_groups, str) else list(with_groups)
        started_at = datetime.now(UTC).astimezone()
        start = monotonic()
        results, timed_out = await self._inner_run(
            with_groups=groups,
            skip_required=skip_required,
            timeout=timeout or None,
            started_at=started_at,
            start=start,
        )
        return ProbirkaResult(
            ok=all(result.ok or result.allow_failure for result in results),
            info=self._info,
            started_at=started_at,
            elapsed=timedelta(seconds=monotonic() - start),
            checks=results,
            error=f'TimeoutError: probirka run timed out after {timeout}s' if timed_out else None,
        )
