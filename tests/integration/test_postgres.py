from datetime import timedelta

import pytest

pytest.importorskip('asyncpg')

import asyncpg

from probirka import PostgresAsyncpgProbe


@pytest.mark.asyncio
async def test_dsn(postgres_dsn: str) -> None:
    result = await PostgresAsyncpgProbe(dsn=postgres_dsn).run_check()

    assert result.ok is True
    assert result.error is None
    assert result.elapsed > timedelta(0)


@pytest.mark.asyncio
async def test_connection_client(postgres_dsn: str) -> None:
    conn = await asyncpg.connect(postgres_dsn)
    try:
        result = await PostgresAsyncpgProbe(conn).run_check()
        factory_result = await PostgresAsyncpgProbe(lambda: conn).run_check()
        # an existing client is never closed by the probe
        assert conn.is_closed() is False
    finally:
        await conn.close()

    assert result.ok is True
    assert factory_result.ok is True


@pytest.mark.asyncio
async def test_pool_client(postgres_dsn: str) -> None:
    pool = await asyncpg.create_pool(postgres_dsn, min_size=1, max_size=2)
    try:
        result = await PostgresAsyncpgProbe(pool).run_check()
    finally:
        await pool.close()

    assert result.ok is True


@pytest.mark.asyncio
async def test_wrong_password(postgres_dsn: str) -> None:
    dsn = postgres_dsn.replace('probirka:probirka@', 'probirka:wrong@', 1)
    assert dsn != postgres_dsn

    result = await PostgresAsyncpgProbe(dsn=dsn, timeout=5).run_check()

    assert result.ok is False
    assert result.error is not None
    assert result.error.startswith('InvalidPasswordError')


@pytest.mark.asyncio
async def test_connection_refused(unreachable_port: int) -> None:
    dsn = f'postgresql://probirka:probirka@127.0.0.1:{unreachable_port}/probirka'

    result = await PostgresAsyncpgProbe(dsn=dsn, timeout=5).run_check()

    assert result.ok is False
    assert result.error is not None
    assert 'ConnectionRefusedError' in result.error or 'OSError' in result.error
