import asyncio
import json
from datetime import datetime

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


@pytest.mark.asyncio
async def test_run_timeout_returns_failed_result() -> None:
    checks = Probirka()

    @checks.add()
    async def _fast() -> bool:
        return True

    @checks.add()
    async def _slow() -> bool:
        await asyncio.sleep(1)
        return True

    results = await checks.run(timeout=0.1)  # type: ignore[arg-type]

    assert results.ok is False
    assert results.error == 'TimeoutError: probirka run timed out after 0.1s'
    assert [check.name for check in results.checks] == ['_fast', '_slow']
    assert results.checks[0].ok is True
    assert results.checks[0].error is None
    assert results.checks[1].ok is False
    assert results.checks[1].error == 'TimeoutError: probirka run timed out after 0.1s'
    assert results.elapsed.total_seconds() < 0.5


@pytest.mark.asyncio
async def test_run_without_timeout_has_no_error() -> None:
    checks = Probirka()

    @checks.add()
    async def _fast() -> bool:
        return True

    results = await checks.run(timeout=1)

    assert results.ok is True
    assert results.error is None


@pytest.mark.asyncio
async def test_unknown_group_is_ignored() -> None:
    checks = Probirka()
    results = await checks.run(with_groups='missing', skip_required=True)

    assert results.ok is True
    assert not results.checks
    assert 'missing' not in checks._optional_probes


@pytest.mark.asyncio
async def test_to_dict_is_json_compatible() -> None:
    checks = Probirka()
    checks.add_info('version', '1.0')

    @checks.add(name='ok_check')
    async def _ok() -> bool:
        return True

    results = await checks.run()
    data = results.to_dict()

    assert data['ok'] is True
    assert data['error'] is None
    assert data['info'] == {'version': '1.0'}
    assert isinstance(data['elapsed'], float)
    assert datetime.fromisoformat(data['started_at']) == results.started_at
    assert isinstance(data['checks'], list)
    assert data['checks'][0]['name'] == 'ok_check'
    assert isinstance(data['checks'][0]['elapsed'], float)
    assert data['checks'][0]['started_at'] == results.checks[0].started_at.isoformat()
    assert json.loads(json.dumps(data)) == data


@pytest.mark.asyncio
async def test_probe_ttl_zero_overrides_global_ttl() -> None:
    checks = Probirka(success_ttl=100, failed_ttl=100)
    counter = 0

    @checks.add(success_ttl=0, failed_ttl=0)
    def _check() -> bool:
        nonlocal counter
        counter += 1
        return True

    await checks.run()
    results = await checks.run()
    assert counter == 2
    assert results.checks[0].cached is not True
