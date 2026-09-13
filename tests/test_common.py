from functools import partial

import pytest

from probirka._probes._common import require_exactly_one, resolve


def test_resolve_returns_instance_as_is() -> None:
    client = object()
    assert resolve(client) is client


def test_resolve_calls_factory() -> None:
    client = object()
    assert resolve(lambda: client) is client


def test_resolve_calls_partial_and_method() -> None:
    client = object()

    class Holder:
        def get(self) -> object:
            return client

    assert resolve(partial(lambda c: c, client)) is client
    assert resolve(Holder().get) is client


def test_resolve_keeps_callable_client_instance() -> None:
    class CallableClient:
        def __call__(self) -> None:
            raise AssertionError('must not be called')

    client = CallableClient()
    assert resolve(client) is client


def test_require_exactly_one_accepts_single_argument() -> None:
    require_exactly_one(client=object(), dsn=None)
    require_exactly_one(client=None, dsn='postgresql://')


def test_require_exactly_one_rejects_nothing() -> None:
    with pytest.raises(ValueError, match='one of client, dsn is required'):
        require_exactly_one(client=None, dsn=None)


def test_require_exactly_one_rejects_both() -> None:
    with pytest.raises(ValueError, match='mutually exclusive'):
        require_exactly_one(client=object(), dsn='postgresql://')
