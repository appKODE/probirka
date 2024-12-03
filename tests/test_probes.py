from typing import Callable, Optional, Union
from unittest.mock import MagicMock

from pytest import mark, param

from probirka import Probe


@mark.parametrize(
    ['probe_result', 'is_ok'],
    [
        param(True, True),
        param(False, False),
        param(None, True),
        param(MagicMock(side_effect=ValueError('test error')), False),
    ],
)
async def test_run_check(
    probe_result: [Union[MagicMock, Optional[bool]]],
    is_ok: bool,
    make_testing_probe: Callable[[Union[MagicMock, Optional[bool]]], Probe],
):
    probe = make_testing_probe(probe_result)
    results = await probe.run_check()
    assert results.ok == is_ok, results