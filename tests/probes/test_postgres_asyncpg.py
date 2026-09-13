from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip('asyncpg')

import asyncpg

from probirka import PostgresAsyncpgProbe


def test_requires_client_or_dsn() -> None:
    with pytest.raises(ValueError):
        PostgresAsyncpgProbe()
    with pytest.raises(ValueError):
        PostgresAsyncpgProbe(client=MagicMock(), dsn='postgresql://x')


@pytest.mark.asyncio
async def test_pool_success() -> None:
    pool = MagicMock()
    pool.fetchval = AsyncMock(return_value=1)

    result = await PostgresAsyncpgProbe(pool).run_check()

    assert result.ok is True
    assert result.name == 'PostgresAsyncpgProbe'
    pool.fetchval.assert_awaited_once_with('SELECT 1')


@pytest.mark.asyncio
async def test_factory_is_called_on_each_check() -> None:
    pool = MagicMock()
    pool.fetchval = AsyncMock(return_value=1)
    calls = []

    def factory() -> MagicMock:
        calls.append(1)
        return pool

    probe = PostgresAsyncpgProbe(factory)
    await probe.run_check()
    await probe.run_check()

    assert len(calls) == 2
    assert pool.fetchval.await_count == 2


@pytest.mark.asyncio
async def test_pool_error_is_reported() -> None:
    pool = MagicMock()
    pool.fetchval = AsyncMock(side_effect=asyncpg.PostgresError('boom'))

    result = await PostgresAsyncpgProbe(pool, name='db').run_check()

    assert result.ok is False
    assert result.error == 'PostgresError: boom'


@pytest.mark.asyncio
async def test_dsn_opens_and_closes_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=1)
    conn.close = AsyncMock()
    connect = AsyncMock(return_value=conn)
    monkeypatch.setattr(asyncpg, 'connect', connect)

    result = await PostgresAsyncpgProbe(dsn='postgresql://localhost/db').run_check()

    assert result.ok is True
    connect.assert_awaited_once_with('postgresql://localhost/db')
    conn.fetchval.assert_awaited_once_with('SELECT 1')
    conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_dsn_closes_connection_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = MagicMock()
    conn.fetchval = AsyncMock(side_effect=RuntimeError('query failed'))
    conn.close = AsyncMock()
    monkeypatch.setattr(asyncpg, 'connect', AsyncMock(return_value=conn))

    result = await PostgresAsyncpgProbe(dsn='postgresql://localhost/db').run_check()

    assert result.ok is False
    assert result.error == 'RuntimeError: query failed'
    conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_dsn_connect_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _refuse(*_: Any, **__: Any) -> Any:
        raise ConnectionRefusedError('refused')

    monkeypatch.setattr(asyncpg, 'connect', AsyncMock(side_effect=_refuse))

    result = await PostgresAsyncpgProbe(dsn='postgresql://localhost/db').run_check()

    assert result.ok is False
    assert result.error == 'ConnectionRefusedError: refused'


@pytest.mark.asyncio
async def test_dsn_password_is_masked_in_error(monkeypatch: pytest.MonkeyPatch) -> None:
    dsn = 'postgresql://app:hunter2@localhost/db'

    async def _connect(given: str) -> None:
        raise asyncpg.InvalidPasswordError(f'password authentication failed for {given} with "hunter2"')

    monkeypatch.setattr(asyncpg, 'connect', _connect)

    result = await PostgresAsyncpgProbe(dsn=dsn).run_check()

    assert result.ok is False
    assert result.error == 'InvalidPasswordError: password authentication failed for postgresql://app:***@localhost/db with "***"'
