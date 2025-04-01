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

    # Проверяем, что при запуске только опциональных проверок запускается только одна проверка
    results = await checks.run(with_groups='optional', skip_required=True)
    assert len(results.checks) == 1
    assert results.checks[0].ok is False

    # Проверяем, что при запуске всех проверок запускается только обязательная проверка
    results = await checks.run()
    assert len(results.checks) == 1
    assert results.checks[0].ok is True


@pytest.mark.asyncio
async def test_probirka_caching() -> None:
    checks = Probirka()
    counter = 0

    @checks.add(success_ttl=1)
    def _check_1() -> bool:
        nonlocal counter
        counter += 1
        return True

    # Первый запуск
    results = await checks.run()
    assert results.checks[0].ok is True
    assert counter == 1

    # Второй запуск (должен использовать кэш)
    results = await checks.run()
    assert results.checks[0].ok is True
    assert counter == 1

    # Проверка глобальных настроек кэширования
    checks2 = Probirka(success_ttl=1, failed_ttl=1)
    counter2 = 0

    @checks2.add()
    def _check_2() -> bool:
        nonlocal counter2
        counter2 += 1
        return True

    # Первый запуск
    results = await checks2.run()
    assert results.checks[0].ok is True
    assert counter2 == 1

    # Второй запуск (должен использовать кэш)
    results = await checks2.run()
    assert results.checks[0].ok is True
    assert counter2 == 1
