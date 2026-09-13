import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from probirka import CallableProbe, Probe, ProbeBase, ProbeResult


@pytest.mark.parametrize(
    ('probe_result', 'is_ok'),
    [
        pytest.param(True, True),
        pytest.param(False, False),
        pytest.param(None, True),
        pytest.param(MagicMock(side_effect=ValueError('test error')), False),
    ],
)
@pytest.mark.asyncio
async def test_run_check(
    probe_result: MagicMock | bool | None,
    is_ok: bool,
    make_testing_probe: Callable[[MagicMock | bool | None], Probe],
) -> None:
    probe = make_testing_probe(probe_result)
    results = await probe.run_check()
    assert results.ok == is_ok, results


class TestProbeBase:
    class ConcreteProbe(ProbeBase):
        async def _check(self) -> bool:
            return True

    def test_init_with_default_values(self) -> None:
        probe = self.ConcreteProbe()
        assert probe._name == 'ConcreteProbe'
        assert probe._timeout is None

    def test_init_with_custom_values(self) -> None:
        probe = self.ConcreteProbe(name='CustomProbe', timeout=5)
        assert probe._name == 'CustomProbe'
        assert probe._timeout == 5

    @pytest.mark.asyncio
    async def test_run_check_success(self) -> None:
        probe = self.ConcreteProbe()
        result = await probe.run_check()

        assert isinstance(result, ProbeResult)
        assert result.ok is True
        assert isinstance(result.started_at, datetime)
        assert isinstance(result.elapsed, timedelta)
        assert result.name == 'ConcreteProbe'
        assert result.error is None

    @pytest.mark.asyncio
    async def test_run_check_with_timeout(self) -> None:
        class SlowProbe(ProbeBase):
            async def _check(self) -> bool:
                await asyncio.sleep(0.5)
                return True

        probe = SlowProbe(timeout=0.1)  # type: ignore[arg-type]
        result = await probe.run_check()

        assert result.ok is False
        assert result.error == 'TimeoutError: probe timed out after 0.1s'
        assert result.elapsed < timedelta(seconds=0.4)

    @pytest.mark.asyncio
    async def test_run_check_with_exception(self) -> None:
        class FailingProbe(ProbeBase):
            async def _check(self) -> bool:
                raise ValueError('Test error')

        probe = FailingProbe()
        result = await probe.run_check()

        assert result.ok is False
        assert result.error == 'ValueError: Test error'

    @pytest.mark.asyncio
    async def test_run_check_with_exception_without_message(self) -> None:
        class FailingProbe(ProbeBase):
            async def _check(self) -> bool:
                raise RuntimeError

        result = await FailingProbe().run_check()

        assert result.ok is False
        assert result.error == 'RuntimeError'

    @pytest.mark.asyncio
    async def test_run_check_result_is_always_bool(self) -> None:
        class TruthyProbe(ProbeBase):
            async def _check(self) -> Any:
                return 'yes'

        result = await TruthyProbe().run_check()

        assert result.ok is True

    def test_probe_without_check_is_abstract(self) -> None:
        class IncompleteProbe(ProbeBase):
            pass

        with pytest.raises(TypeError):
            IncompleteProbe()  # type: ignore[abstract]

    def test_name_property(self) -> None:
        assert self.ConcreteProbe().name == 'ConcreteProbe'
        assert self.ConcreteProbe(name='custom').name == 'custom'


class TestCallableProbe:
    def test_init_with_sync_function(self) -> None:
        def test_func() -> bool:
            return True

        probe = CallableProbe(test_func)
        assert probe._name == 'test_func'
        assert probe._func == test_func

    def test_init_with_async_function(self) -> None:
        async def test_func() -> bool:
            return True

        probe = CallableProbe(test_func)
        assert probe._name == 'test_func'
        assert probe._func == test_func

    @pytest.mark.asyncio
    async def test_check_with_sync_function(self) -> None:
        def test_func() -> bool:
            return True

        probe = CallableProbe(test_func)
        result = await probe._check()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_with_async_function(self) -> None:
        async def test_func() -> bool:
            return True

        probe = CallableProbe(test_func)
        result = await probe._check()
        assert result is True

    @pytest.mark.asyncio
    async def test_run_check_with_sync_function(self) -> None:
        def test_func() -> bool:
            return True

        probe = CallableProbe(test_func)
        result = await probe.run_check()

        assert isinstance(result, ProbeResult)
        assert result.ok is True
        assert result.name == 'test_func'

    @pytest.mark.asyncio
    async def test_sync_function_respects_timeout(self) -> None:
        def test_func() -> bool:
            time.sleep(0.5)
            return True

        probe = CallableProbe(test_func, timeout=0.1)  # type: ignore[arg-type]
        started = time.monotonic()
        result = await probe.run_check()

        assert result.ok is False
        assert result.error == 'TimeoutError: probe timed out after 0.1s'
        assert time.monotonic() - started < 0.4

    @pytest.mark.asyncio
    async def test_sync_function_does_not_block_event_loop(self) -> None:
        def test_func() -> bool:
            time.sleep(0.3)
            return True

        probe = CallableProbe(test_func)
        ticks = 0

        async def ticker() -> None:
            nonlocal ticks
            for _ in range(5):
                await asyncio.sleep(0.05)
                ticks += 1

        result, _ = await asyncio.gather(probe.run_check(), ticker())

        assert result.ok is True
        assert ticks == 5

    @pytest.mark.asyncio
    async def test_run_check_with_async_function(self) -> None:
        async def test_func() -> bool:
            return True

        probe = CallableProbe(test_func)
        result = await probe.run_check()

        assert isinstance(result, ProbeResult)
        assert result.ok is True
        assert result.name == 'test_func'


@pytest.mark.asyncio
async def test_probe_caching() -> None:
    class TestProbe(ProbeBase):
        def __init__(self, success_ttl: int | None = None, failed_ttl: int | None = None) -> None:
            super().__init__(success_ttl=success_ttl, failed_ttl=failed_ttl)
            self._counter = 0

        async def _check(self) -> bool:
            self._counter += 1
            return True

    # no caching
    probe = TestProbe()
    result1 = await probe.run_check()
    result2 = await probe.run_check()
    assert result1.ok is True
    assert result2.ok is True
    assert result1.cached is None
    assert result2.cached is None  # cached is always None when caching is off
    assert probe._counter == 2

    # caching of a successful result
    probe = TestProbe(success_ttl=1)
    result1 = await probe.run_check()
    await asyncio.sleep(0.1)  # a short delay, below the TTL
    result2 = await probe.run_check()
    assert result1.ok is True
    assert result2.ok is True
    assert result1.cached is False
    assert result2.cached is True
    assert probe._counter == 1

    # cache expiry
    await asyncio.sleep(1.1)  # wait for the TTL to expire
    result3 = await probe.run_check()
    assert result3.ok is True
    assert result3.cached is False
    assert probe._counter == 2

    # caching of a failed result
    class FailingProbe(ProbeBase):
        def __init__(self, failed_ttl: int | None = None) -> None:
            super().__init__(failed_ttl=failed_ttl)
            self._counter = 0

        async def _check(self) -> bool:
            self._counter += 1
            return False

    probe = FailingProbe(failed_ttl=1)
    result1 = await probe.run_check()
    await asyncio.sleep(0.1)  # a short delay, below the TTL
    result2 = await probe.run_check()
    assert result1.ok is False
    assert result2.ok is False
    assert result1.cached is False
    assert result2.cached is True
    assert probe._counter == 1

    # cache expiry of a failed result
    await asyncio.sleep(1.1)  # wait for the TTL to expire
    result3 = await probe.run_check()
    assert result3.ok is False
    assert result3.cached is False
    assert probe._counter == 2


@pytest.mark.asyncio
async def test_probe_info() -> None:
    class TestProbe(ProbeBase):
        async def _check(self) -> bool:
            self.add_info('test_key', 'test_value')
            return True

    probe = TestProbe()
    result = await probe.run_check()

    assert result.ok is True
    assert result.info == {'test_key': 'test_value'}


@pytest.mark.asyncio
async def test_probe_info_caching() -> None:
    class TestProbe(ProbeBase):
        def __init__(self, success_ttl: int | None = None) -> None:
            super().__init__(success_ttl=success_ttl)
            self._counter = 0

        async def _check(self) -> bool:
            self._counter += 1
            self.add_info('counter', self._counter)
            return True

    # with caching
    probe = TestProbe(success_ttl=1)
    result1 = await probe.run_check()
    result2 = await probe.run_check()

    assert result1.ok is True
    assert result2.ok is True
    assert result1.cached is False
    assert result2.cached is True
    assert result1.info == {'counter': 1}
    assert result2.info == {'counter': 1}
    assert probe._counter == 1


@pytest.mark.asyncio
async def test_probe_info_empty() -> None:
    class TestProbe(ProbeBase):
        async def _check(self) -> bool:
            return True

    probe = TestProbe()
    result = await probe.run_check()

    assert result.ok is True
    assert result.info is None


@pytest.mark.asyncio
async def test_callable_probe_async_call_object() -> None:
    class _AsyncCallable:
        async def __call__(self) -> bool:
            return False

    probe = CallableProbe(_AsyncCallable(), name='async_call')
    result = await probe.run_check()
    assert result.ok is False


@pytest.mark.asyncio
async def test_callable_probe_sync_returning_awaitable() -> None:
    async def _inner() -> bool:
        return False

    def _func() -> Awaitable[bool]:
        return _inner()

    probe = CallableProbe(_func)
    result = await probe.run_check()
    assert result.ok is False


@pytest.mark.asyncio
async def test_started_at_is_timezone_aware() -> None:
    class _Probe(ProbeBase):
        async def _check(self) -> bool:
            return True

    result = await _Probe().run_check()
    assert result.started_at.tzinfo is not None
    assert result.started_at.utcoffset() is not None
    assert datetime.fromisoformat(result.to_dict()['started_at']) == result.started_at


@pytest.mark.asyncio
async def test_cache_ttl_survives_wall_clock_jumps() -> None:
    class _Probe(ProbeBase):
        def __init__(self) -> None:
            super().__init__(success_ttl=100)
            self.calls = 0

        async def _check(self) -> bool:
            self.calls += 1
            return True

    probe = _Probe()
    first = await probe.run_check()

    # The wall clock jumps a year ahead; the monotonic deadline must still hold the cache.
    with patch('probirka._probes._base.datetime') as mock_datetime:
        mock_datetime.now.return_value = first.started_at + timedelta(days=365)
        second = await probe.run_check()

    assert second.cached is True
    assert probe.calls == 1


@pytest.mark.asyncio
async def test_elapsed_is_monotonic() -> None:
    class _Probe(ProbeBase):
        async def _check(self) -> bool:
            await asyncio.sleep(0.3)
            return True

    result = await _Probe().run_check()
    assert result.elapsed >= timedelta(seconds=0.3)
    assert result.elapsed < timedelta(seconds=2)


@pytest.mark.asyncio
async def test_callable_probe_names_callables_without_dunder_name() -> None:
    class _AsyncCallable:
        async def __call__(self) -> bool:
            return True

    probe = CallableProbe(_AsyncCallable())
    assert probe.name == '_AsyncCallable'

    result = await probe.run_check()
    assert result.name == '_AsyncCallable'


@pytest.mark.asyncio
async def test_probe_allow_failure_flag() -> None:
    class FailingProbe(ProbeBase):
        async def _check(self) -> bool:
            return False

    strict = await FailingProbe().run_check()
    assert strict.allow_failure is False
    assert FailingProbe().allow_failure is False

    probe = FailingProbe(allow_failure=True, failed_ttl=1)
    assert probe.allow_failure is True
    fresh = await probe.run_check()
    cached = await probe.run_check()
    assert fresh.ok is False
    assert fresh.allow_failure is True
    assert cached.cached is True
    assert cached.allow_failure is True


@pytest.mark.asyncio
async def test_callable_probe_allow_failure() -> None:
    probe = CallableProbe(lambda: False, allow_failure=True)
    result = await probe.run_check()
    assert result.ok is False
    assert result.allow_failure is True
    assert result.to_dict()['allow_failure'] is True


@pytest.mark.asyncio
async def test_registered_secrets_are_masked_in_error() -> None:
    class _Probe(ProbeBase):
        def __init__(self) -> None:
            super().__init__()
            self._register_secrets('hunter2', 'p%40ss', 'p@ss')

        async def _check(self) -> bool:
            raise RuntimeError('postgresql://app:hunter2@db/app rejected p%40ss (p@ss)')

    result = await _Probe().run_check()

    assert result.error == 'RuntimeError: postgresql://app:***@db/app rejected *** (***)'


@pytest.mark.asyncio
async def test_secrets_are_not_touched_in_info_of_the_probe_itself() -> None:
    class _Probe(ProbeBase):
        def __init__(self) -> None:
            super().__init__()
            self._register_secrets('hunter2')

        async def _check(self) -> bool:
            self.add_info('password', 'hunter2')
            self.add_info('dsn', 'postgresql://app:hunter2@db/app')
            return True

    result = await _Probe().run_check()

    # the dataclass keeps what the probe produced, ``to_dict`` is where masking happens
    assert result.info == {'password': 'hunter2', 'dsn': 'postgresql://app:hunter2@db/app'}
    assert result.to_dict()['info'] == {'password': '***', 'dsn': 'postgresql://app:***@db/app'}
    assert result.to_dict(redact=False)['info'] == result.info


@pytest.mark.asyncio
async def test_to_dict_masks_url_password_in_error() -> None:
    class _Probe(ProbeBase):
        async def _check(self) -> bool:
            raise RuntimeError('cannot reach amqp://guest:guest@mq/')

    result = await _Probe().run_check()

    assert result.error == 'RuntimeError: cannot reach amqp://guest:guest@mq/'
    assert result.to_dict()['error'] == 'RuntimeError: cannot reach amqp://guest:***@mq/'
    assert result.to_dict(redact=False)['error'] == result.error
