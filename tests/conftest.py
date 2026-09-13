pytest_plugins = ('pytest_asyncio',)

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

from probirka import Probe, ProbeBase


@pytest.fixture
def make_testing_probe() -> Callable[[MagicMock | bool | None], Probe]:
    def _inner(probe_result: MagicMock | bool | None) -> Probe:
        class _Probe(ProbeBase):
            async def _check(self) -> bool | None:
                if isinstance(probe_result, MagicMock):
                    return probe_result()
                return probe_result

        return _Probe()

    return _inner
