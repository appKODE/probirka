from asyncio import gather, wait_for
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from probirka._probes import CallableProbe, Probe
from probirka._results import HealthCheckResult, ProbeResult


class Probirka:
    """
    Probirka is a health check manager that allows adding and running probes.
    """

    def __init__(
        self,
    ) -> None:
        """
        Initialize the Probirka instance.
        """
        self._required_probes: List[Probe] = []
        self._optional_probes: Dict[str, List[Probe]] = defaultdict(list)
        self._info: Dict[str, Any] = {}

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
        self._info[name] = value

    @property
    def info(
        self,
    ) -> Dict[str, Any]:
        """
        Get the information added to the health check result.

        :return: A dictionary containing the information.
        """
        return self._info

    def add_probes(
        self,
        *probes: Probe,
        groups: Union[str, List[str]] = '',
    ) -> None:
        """
        Add probes to the health check.

        :param probes: The probes to add.
        :param groups: The groups to which the probes belong.
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
    ) -> Callable:
        """
        Decorator to add a callable as a probe.

        :param name: The name of the probe.
        :param timeout: The timeout for the probe.
        :param groups: The groups to which the probe belongs.
        :return: The decorated function.
        """

        def _wrapper(func: Callable) -> Any:
            self.add_probes(
                CallableProbe(
                    func=func,
                    name=name,
                    timeout=timeout,
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
        Run the probes and gather the results.

        :param with_groups: The groups of probes to run.
        :param skip_required: Whether to skip the required probes.
        :return: A sequence of probe results.
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
        Run the health check and return the result.

        :param timeout: The timeout for the health check.
        :param with_groups: The groups of probes to run.
        :param skip_required: Whether to skip the required probes.
        :return: The health check result.
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
