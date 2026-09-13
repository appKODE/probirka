import asyncio
import json
from datetime import datetime, timedelta

import pytest

from probirka import ProbeBase, Probirka
from tests.helpers import FailureProbe, SlowProbe


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

    # running only the optional probes runs exactly one probe
    results = await checks.run(with_groups='optional', skip_required=True)
    assert len(results.checks) == 1
    assert results.checks[0].ok is False

    # running everything runs only the required probe
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

    # first run
    results = await checks.run()
    assert results.checks[0].ok is True
    assert counter == 1

    # second run (must hit the cache)
    results = await checks.run()
    assert results.checks[0].ok is True
    assert counter == 1

    # global cache settings
    checks2 = Probirka(success_ttl=1, failed_ttl=1)
    counter2 = 0

    @checks2.add()
    def _check_2() -> bool:
        nonlocal counter2
        counter2 += 1
        return True

    # first run
    results = await checks2.run()
    assert results.checks[0].ok is True
    assert counter2 == 1

    # second run (must hit the cache)
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
    assert data['checks'][0]['allow_failure'] is False
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


@pytest.mark.asyncio
async def test_timestamps_are_timezone_aware() -> None:
    checks = Probirka()

    @checks.add()
    def _check() -> bool:
        return True

    results = await checks.run()

    assert results.started_at.tzinfo is not None
    assert results.started_at.utcoffset() is not None
    assert results.checks[0].started_at.tzinfo is not None
    assert results.checks[0].started_at.utcoffset() is not None

    data = results.to_dict()
    assert datetime.fromisoformat(data['started_at']) == results.started_at
    assert datetime.fromisoformat(data['started_at']).utcoffset() is not None
    assert datetime.fromisoformat(data['checks'][0]['started_at']) == results.checks[0].started_at


@pytest.mark.asyncio
async def test_elapsed_is_measured_monotonically() -> None:
    checks = Probirka()

    @checks.add()
    async def _slow() -> bool:
        await asyncio.sleep(0.3)
        return True

    results = await checks.run()

    assert results.elapsed >= timedelta(seconds=0.3)
    assert results.elapsed < timedelta(seconds=2)
    assert results.checks[0].elapsed >= timedelta(seconds=0.3)
    assert results.checks[0].elapsed <= results.elapsed


@pytest.mark.asyncio
async def test_elapsed_excludes_cache_lookup() -> None:
    checks = Probirka(success_ttl=100)

    @checks.add()
    def _check() -> bool:
        return True

    first = await checks.run()
    second = await checks.run()

    assert second.checks[0].cached is True
    assert second.checks[0].elapsed == first.checks[0].elapsed
    assert second.checks[0].elapsed >= timedelta(0)


@pytest.mark.asyncio
async def test_run_accepts_any_sequence_of_groups() -> None:
    checks = Probirka()

    @checks.add(groups=('db', 'cache'))
    def _check() -> bool:
        return True

    results = await checks.run(with_groups=('db',), skip_required=True)
    assert len(results.checks) == 1
    assert results.checks[0].name == '_check'


@pytest.mark.asyncio
async def test_allow_failure_probe_does_not_affect_ok() -> None:
    checks = Probirka()

    @checks.add(name='db')
    async def _db() -> bool:
        return True

    @checks.add(name='cache', allow_failure=True)
    async def _cache() -> bool:
        return False

    results = await checks.run()

    assert results.ok is True
    assert results.error is None
    assert [(c.name, c.ok, c.allow_failure) for c in results.checks] == [
        ('db', True, False),
        ('cache', False, True),
    ]


@pytest.mark.asyncio
async def test_strict_probe_failure_still_fails_next_to_allowed() -> None:
    checks = Probirka()

    @checks.add(name='db')
    async def _db() -> bool:
        return False

    @checks.add(name='cache', allow_failure=True)
    async def _cache() -> bool:
        return False

    results = await checks.run()

    assert results.ok is False


@pytest.mark.asyncio
async def test_group_allow_failure_relaxes_probes() -> None:
    checks = Probirka()
    checks.add_probes(FailureProbe(name='http'), FailureProbe(name='smtp'), groups='external', allow_failure=True)

    results = await checks.run(with_groups='external')

    assert results.ok is True
    assert all(c.ok is False and c.allow_failure is True for c in results.checks)


@pytest.mark.asyncio
async def test_group_allow_failure_false_overrides_probe() -> None:
    checks = Probirka()
    checks.add_probes(FailureProbe(name='x', allow_failure=True), groups='core', allow_failure=False)

    results = await checks.run(with_groups='core', skip_required=True)

    assert results.ok is False
    assert results.checks[0].allow_failure is False


@pytest.mark.asyncio
async def test_group_without_allow_failure_keeps_probe_setting() -> None:
    checks = Probirka()
    checks.add_probes(FailureProbe(name='soft', allow_failure=True), FailureProbe(name='hard'), groups='g')

    results = await checks.run(with_groups='g')

    assert results.ok is False
    assert [c.allow_failure for c in results.checks] == [True, False]

    results = await checks.run(with_groups='g', skip_required=True)
    assert results.ok is False


@pytest.mark.asyncio
async def test_strict_source_wins_when_probe_in_several_groups() -> None:
    checks = Probirka()
    probe = FailureProbe(name='pg')
    checks.add_probes(probe, groups='readiness')
    checks.add_probes(probe, groups='deep', allow_failure=True)

    soft = await checks.run(with_groups='deep')
    assert soft.ok is True
    assert soft.checks[0].allow_failure is True

    both = await checks.run(with_groups=['readiness', 'deep'])
    assert both.ok is False
    assert [c.allow_failure for c in both.checks] == [False, False]


@pytest.mark.asyncio
async def test_required_probe_in_soft_group_stays_strict() -> None:
    checks = Probirka()
    probe = FailureProbe(name='pg')
    checks.add_probes(probe)
    checks.add_probes(probe, groups='deep', allow_failure=True)

    results = await checks.run(with_groups='deep')

    assert results.ok is False
    assert [c.allow_failure for c in results.checks] == [False, False]


def test_group_allow_failure_last_explicit_value_wins() -> None:
    checks = Probirka()
    checks.add_probes(FailureProbe(), groups='g', allow_failure=True)
    checks.add_probes(FailureProbe(), groups='g')
    assert checks._group_allow_failure == {'g': True}

    checks.add_probes(FailureProbe(), groups='g', allow_failure=False)
    assert checks._group_allow_failure == {'g': False}


def test_allow_failure_without_groups_raises() -> None:
    checks = Probirka()

    with pytest.raises(ValueError, match='allow_failure applies to groups'):
        checks.add_probes(FailureProbe(), allow_failure=True)
    with pytest.raises(ValueError, match='allow_failure applies to groups'):
        checks.add_probes(FailureProbe(), allow_failure=False)
    assert not checks._required_probes


@pytest.mark.asyncio
async def test_run_timeout_of_allowed_probe_keeps_ok() -> None:
    checks = Probirka()

    @checks.add(name='fast')
    async def _fast() -> bool:
        return True

    @checks.add(name='slow', allow_failure=True)
    async def _slow() -> bool:
        await asyncio.sleep(1)
        return True

    results = await checks.run(timeout=0.1)  # type: ignore[arg-type]

    assert results.ok is True
    assert results.error == 'TimeoutError: probirka run timed out after 0.1s'
    assert results.checks[1].ok is False
    assert results.checks[1].allow_failure is True
    assert results.checks[1].error == 'TimeoutError: probirka run timed out after 0.1s'


@pytest.mark.asyncio
async def test_run_timeout_of_probe_in_soft_group_keeps_ok() -> None:
    checks = Probirka()
    checks.add_probes(SlowProbe(name='slow'), groups='ext', allow_failure=True)

    results = await checks.run(timeout=0.1, with_groups='ext')  # type: ignore[arg-type]

    assert results.ok is True
    assert results.error is not None
    assert results.checks[0].allow_failure is True


@pytest.mark.asyncio
async def test_to_dict_contains_allow_failure() -> None:
    checks = Probirka()
    checks.add_probes(FailureProbe(name='soft', allow_failure=True))

    data = (await checks.run()).to_dict()

    assert data['ok'] is True
    assert data['checks'][0]['allow_failure'] is True
    assert json.loads(json.dumps(data)) == data


@pytest.mark.asyncio
async def test_to_dict_masks_secrets_by_default() -> None:
    checks = Probirka()
    checks.add_info('version', '1.0')
    checks.add_info('api_key', 'abc')
    checks.add_info('broker', 'amqp://guest:guest@mq/')

    class _Probe(ProbeBase):
        async def _check(self) -> bool:
            self.add_info('password', 'hunter2')
            return True

    checks.add_probes(_Probe())

    data = (await checks.run()).to_dict()
    raw = (await checks.run()).to_dict(redact=False)

    assert data['info'] == {'version': '1.0', 'api_key': '***', 'broker': 'amqp://guest:***@mq/'}
    assert data['checks'][0]['info'] == {'password': '***'}
    assert raw['info'] == {'version': '1.0', 'api_key': 'abc', 'broker': 'amqp://guest:guest@mq/'}
    assert raw['checks'][0]['info'] == {'password': 'hunter2'}
