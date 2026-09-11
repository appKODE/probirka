from asyncio import ensure_future, gather, wait
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from probirka._probes import CallableProbe, Probe
from probirka._results import ProbirkaResult, ProbeResult


class Probirka:
    """
    Probirka is a health check manager that allows adding and running probes.
    """

    def __init__(
        self,
        success_ttl: Optional[Union[int, timedelta]] = None,
        failed_ttl: Optional[Union[int, timedelta]] = None,
    ) -> None:
        """
        Initialize the Probirka instance.

        :param success_ttl: Default cache duration for successful results. If None, successful results are not cached.
        :param failed_ttl: Default cache duration for failed results. If None, failed results are not cached.
        """
        self._required_probes: List[Probe] = []
        self._optional_probes: Dict[str, List[Probe]] = defaultdict(list)
        self._info: Optional[Dict[str, Any]] = None
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
    ) -> Optional[Dict[str, Any]]:
        """
        Get the information added to the health check result.

        :return: The information added to the health check result.
        """
        return self._info

    def add_probes(
        self,
        *probes: Probe,
        groups: Union[str, List[str]] = '',
    ) -> None:
        """
        Add probes to the health check.

        :param probes: Probes to add
        :param groups: Groups for optional probes. Probes without groups are required.
        """
        if groups:
            if isinstance(groups, str):
                groups = [groups]
            for group in groups:
                self._optional_probes[group].extend(probes)
            return
        self._required_probes.extend(probes)

    def add(
        self,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        groups: Union[str, List[str]] = '',
        success_ttl: Optional[Union[int, timedelta]] = None,
        failed_ttl: Optional[Union[int, timedelta]] = None,
    ) -> Callable:
        """
        Decorator to add a callable as a probe.

        :param name: Probe name
        :param timeout: Probe timeout in seconds
        :param groups: Groups for optional probes. Probes without groups are required.
        :param success_ttl: Cache duration for successful results. If None, uses the global success_ttl setting.
            Pass ``0`` to disable caching of successful results for this probe.
        :param failed_ttl: Cache duration for failed results. If None, uses the global failed_ttl setting.
            Pass ``0`` to disable caching of failed results for this probe.
        :return: Decorated function
        """

        def _wrapper(func: Callable) -> Any:
            self.add_probes(
                CallableProbe(
                    func=func,
                    name=name,
                    timeout=timeout,
                    success_ttl=success_ttl if success_ttl is not None else self._success_ttl,
                    failed_ttl=failed_ttl if failed_ttl is not None else self._failed_ttl,
                ),
                groups=groups,
            )
            return func

        return _wrapper

    async def _inner_run(
        self,
        with_groups: List[str],
        skip_required: bool,
        timeout: Optional[int],
        started_at: datetime,
    ) -> Tuple[List[ProbeResult], bool]:
        """
        Run probes concurrently and gather results in registration order.

        Probes that do not finish within ``timeout`` are cancelled and reported
        as failed with a ``TimeoutError`` message, so partial results survive.

        :param with_groups: Groups to run. Required probes run unless skip_required=True
        :param skip_required: Skip probes without groups
        :param timeout: Overall timeout in seconds, ``None`` to wait indefinitely
        :param started_at: Start time of the whole run
        :return: Probe results and whether the overall timeout was hit
        """
        probes: List[Probe] = [] if skip_required else list(self._required_probes)
        for group in with_groups:
            probes.extend(self._optional_probes.get(group, ()))
        if not probes:
            return [], False

        tasks = [ensure_future(probe.run_check()) for probe in probes]
        _, pending = await wait(tasks, timeout=timeout)
        if pending:
            for task in pending:
                task.cancel()
            await gather(*pending, return_exceptions=True)

        timeout_error = f'TimeoutError: probirka run timed out after {timeout}s'
        results: List[ProbeResult] = []
        for probe, task in zip(probes, tasks):
            if task in pending:
                results.append(
                    ProbeResult(
                        name=probe.name,
                        ok=False,
                        cached=None,
                        started_at=started_at,
                        elapsed=datetime.now() - started_at,
                        info=probe.info,
                        error=timeout_error,
                    )
                )
            else:
                results.append(task.result())
        return results, bool(pending)

    async def run(
        self,
        timeout: Optional[int] = None,
        with_groups: Union[str, List[str]] = '',
        skip_required: bool = False,
    ) -> ProbirkaResult:
        """
        Run health check and return results.

        The overall timeout never raises: probes that did not finish in time are
        reported as failed and the whole result gets ``ok=False`` with ``error`` set.

        :param timeout: Overall timeout in seconds
        :param with_groups: Groups to run. Required probes run unless skip_required=True
        :param skip_required: Skip probes without groups
        :return: Health check result
        """
        if isinstance(with_groups, str):
            with_groups = [with_groups] if with_groups else []
        started_at = datetime.now()
        results, timed_out = await self._inner_run(
            with_groups=with_groups,
            skip_required=skip_required,
            timeout=timeout or None,
            started_at=started_at,
        )
        return ProbirkaResult(
            ok=not timed_out and all(result.ok for result in results),
            info=self._info,
            started_at=started_at,
            elapsed=datetime.now() - started_at,
            checks=results,
            error=f'TimeoutError: probirka run timed out after {timeout}s' if timed_out else None,
        )
