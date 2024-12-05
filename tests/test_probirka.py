import pytest
from probirka import Probirka


@pytest.mark.asyncio
async def test_decorator() -> None:
    checks = Probirka()
    results = await checks.run()
    assert not results.checks

    @checks.add()
    def ok_check() -> bool:
        return False

    results = await checks.run()
    assert results.checks


@pytest.mark.asyncio
async def test_optional_probe() -> None:
    checks = Probirka()

    @checks.add()
    def _check_1() -> bool:
        return True

    @checks.add(groups='optional')
    def _check_2() -> bool:
        return False

    results = await checks.run(with_groups='optional')
    assert len(results.checks) == 2  # noqa

    results = await checks.run()
    assert len(results.checks) == 1
    assert results.checks[0].ok is True
