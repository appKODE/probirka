from typing import Callable, Optional, Union
from unittest.mock import MagicMock

import pytest

from probirka import Probe


@pytest.mark.parametrize(
    ['probe_result', 'is_ok'],
    [
        pytest.param(True, True),
        pytest.param(False, False),
        pytest.param(None, True),
        pytest.param(MagicMock(side_effect=ValueError('test error')), False),
    ],
)
@pytest.mark.asyncio
async def test_run_check(
    probe_result: Union[MagicMock, Optional[bool]],
    is_ok: bool,
    make_testing_probe: Callable[[Union[MagicMock, Optional[bool]]], Probe],
) -> None:
    probe = make_testing_probe(probe_result)
    results = await probe.run_check()
    assert results.ok == is_ok, results
