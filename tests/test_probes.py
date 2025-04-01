from typing import Callable, Optional, Union, Any
from unittest.mock import MagicMock

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from probirka import Probe
from probirka._probes import ProbeBase, CallableProbe
from probirka._results import ProbeResult


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


class TestProbeBase:
    class ConcreteProbe(ProbeBase):
        async def _check(self) -> bool:
            return True

    def test_init_with_default_values(self) -> None:
        probe = self.ConcreteProbe()
        assert probe._name == "ConcreteProbe"
        assert probe._timeout is None

    def test_init_with_custom_values(self) -> None:
        probe = self.ConcreteProbe(name="CustomProbe", timeout=5)
        assert probe._name == "CustomProbe"
        assert probe._timeout == 5

    @pytest.mark.asyncio
    async def test_run_check_success(self) -> None:
        probe = self.ConcreteProbe()
        result = await probe.run_check()

        assert isinstance(result, ProbeResult)
        assert result.ok is True
        assert isinstance(result.started_at, datetime)
        assert isinstance(result.elapsed, timedelta)
        assert result.name == "ConcreteProbe"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_run_check_with_timeout(self) -> None:
        class SlowProbe(ProbeBase):
            async def _check(self) -> bool:
                await asyncio.sleep(2)
                return True

        probe = SlowProbe(timeout=1)
        result = await probe.run_check()

        assert result.ok is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_run_check_with_exception(self) -> None:
        class FailingProbe(ProbeBase):
            async def _check(self) -> bool:
                raise ValueError("Test error")

        probe = FailingProbe()
        result = await probe.run_check()

        assert result.ok is False
        assert result.error == "Test error"


class TestCallableProbe:
    def test_init_with_sync_function(self) -> None:
        def test_func() -> bool:
            return True

        probe = CallableProbe(test_func)
        assert probe._name == "test_func"
        assert probe._func == test_func

    def test_init_with_async_function(self) -> None:
        async def test_func() -> bool:
            return True

        probe = CallableProbe(test_func)
        assert probe._name == "test_func"
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
        assert result.name == "test_func"

    @pytest.mark.asyncio
    async def test_run_check_with_async_function(self) -> None:
        async def test_func() -> bool:
            return True

        probe = CallableProbe(test_func)
        result = await probe.run_check()

        assert isinstance(result, ProbeResult)
        assert result.ok is True
        assert result.name == "test_func"


@pytest.mark.asyncio
async def test_probe_caching() -> None:
    class TestProbe(ProbeBase):
        def __init__(self, success_ttl: Optional[int] = None, failed_ttl: Optional[int] = None):
            super().__init__(success_ttl=success_ttl, failed_ttl=failed_ttl)
            self._counter = 0

        async def _check(self) -> bool:
            self._counter += 1
            return True

    # Тест без кэширования
    probe = TestProbe()
    result1 = await probe.run_check()
    result2 = await probe.run_check()
    assert result1.ok is True
    assert result2.ok is True
    assert result1.cached is False
    assert result2.cached is False
    assert probe._counter == 2

    # Тест с кэшированием успешного результата
    probe = TestProbe(success_ttl=1)
    result1 = await probe.run_check()
    result2 = await probe.run_check()
    assert result1.ok is True
    assert result2.ok is True
    assert result1.cached is False
    assert result2.cached is True
    assert probe._counter == 1

    # Тест с кэшированием неуспешного результата
    class FailingProbe(ProbeBase):
        def __init__(self, failed_ttl: Optional[int] = None):
            super().__init__(failed_ttl=failed_ttl)
            self._counter = 0

        async def _check(self) -> bool:
            self._counter += 1
            return False

    probe = FailingProbe(failed_ttl=1)
    result1 = await probe.run_check()
    result2 = await probe.run_check()
    assert result1.ok is False
    assert result2.ok is False
    assert result1.cached is False
    assert result2.cached is True
    assert probe._counter == 1


@pytest.mark.asyncio
async def test_probe_info() -> None:
    class TestProbe(ProbeBase):
        async def _check(self) -> bool:
            self.add_info("test_key", "test_value")
            return True

    probe = TestProbe()
    result = await probe.run_check()

    assert result.ok is True
    assert result.info == {"test_key": "test_value"}


@pytest.mark.asyncio
async def test_probe_info_caching() -> None:
    class TestProbe(ProbeBase):
        def __init__(self, success_ttl: Optional[int] = None):
            super().__init__(success_ttl=success_ttl)
            self._counter = 0

        async def _check(self) -> bool:
            self._counter += 1
            self.add_info("counter", self._counter)
            return True

    # Тест с кэшированием
    probe = TestProbe(success_ttl=1)
    result1 = await probe.run_check()
    result2 = await probe.run_check()

    assert result1.ok is True
    assert result2.ok is True
    assert result1.cached is False
    assert result2.cached is True
    assert result1.info == {"counter": 1}
    assert result2.info == {"counter": 1}
    assert probe._counter == 1


@pytest.mark.asyncio
async def test_probe_info_empty() -> None:
    class TestProbe(ProbeBase):
        async def _check(self) -> bool:
            return True

    probe = TestProbe()
    result = await probe.run_check()

    assert result.ok is True
    assert result.info == {}
