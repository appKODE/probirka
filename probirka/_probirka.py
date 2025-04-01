from asyncio import gather, wait_for
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from probirka._probes import CallableProbe, Probe
from probirka._results import HealthCheckResult, ProbeResult


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
        :param failed_ttl: Cache duration for failed results. If None, uses the global failed_ttl setting.
        :return: Decorated function
        """

        def _wrapper(func: Callable) -> Any:
            self.add_probes(
                CallableProbe(
                    func=func,
                    name=name,
                    timeout=timeout,
                    success_ttl=success_ttl or self._success_ttl,
                    failed_ttl=failed_ttl or self._failed_ttl,
                ),
                groups=groups,
            )
            return func

        return _wrapper

    async def _inner_run(
        self,
        with_groups: List[str],
        skip_required: bool,
    ) -> Sequence[ProbeResult]:
        """
        Run probes and gather results.

        :param with_groups: Groups to run. Required probes run unless skip_required=True
        :param skip_required: Skip probes without groups
        :return: Sequence of probe results
        """
        tasks = [] if skip_required else [probe.run_check() for probe in self._required_probes]
        for group in with_groups:
            tasks += [probe.run_check() for probe in self._optional_probes[group]]
        results = await gather(*tasks)
        for coro in tasks:
            coro.close()
        return results

    async def run(
        self,
        timeout: Optional[int] = None,
        with_groups: Union[str, List[str]] = '',
        skip_required: bool = False,
    ) -> HealthCheckResult:
        """
        Run health check and return results.

        :param timeout: Overall timeout in seconds
        :param with_groups: Groups to run. Required probes run unless skip_required=True
        :param skip_required: Skip probes without groups
        :return: Health check result
        """
        if with_groups and isinstance(with_groups, str):
            with_groups = [with_groups]
        started_at = datetime.now()
        fut = self._inner_run(
            with_groups=with_groups,  # type: ignore
            skip_required=skip_required,
        )
        results = (
            await wait_for(
                fut=fut,
                timeout=timeout,
            )
            if timeout
            else await fut
        )
        ok = True
        for result in results:
            if result.ok is False:
                ok = False
                break
        return HealthCheckResult(
            ok=ok,
            info=self._info,
            started_at=started_at,
            total_elapsed=datetime.now() - started_at,
            checks=results,
        )
