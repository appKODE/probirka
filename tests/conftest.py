from typing import Callable, Optional, Union
from unittest.mock import MagicMock

from pytest import fixture

from probirka import Probe, ProbeBase


@fixture
def make_testing_probe() -> Callable[[Union[MagicMock, Optional[bool]]], Probe]:
    def _inner(probe_result: Union[MagicMock, Optional[bool]]) -> Probe:
        class _Probe(ProbeBase):
            async def _check(self) -> Optional[bool]:
                if isinstance(probe_result, MagicMock):
                    return probe_result()
                return probe_result

        return _Probe()

    return _inner
