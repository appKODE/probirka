from functools import partial
from inspect import isroutine
from typing import Any, Callable, TypeVar, Union

T = TypeVar('T')

ClientOrFactory = Union[T, Callable[[], T]]
"""Either a ready client instance or a zero-argument function (lambda, ``functools.partial``) returning one."""


class ProbeFailure(Exception):
    """
    Raised by a probe when the dependency answered, but not the way a healthy one should.

    Examples: Redis replied to ``PING`` with something other than ``True``, an HTTP endpoint
    returned an unexpected status code. The message ends up in :attr:`ProbeResult.error`.
    """


def resolve(client_or_factory: ClientOrFactory[T]) -> T:
    """
    Return the client itself, or call the factory to obtain it.

    Lets a probe be constructed before the connection pool exists (for example in a
    FastAPI lifespan): pass ``lambda: app.state.pool`` instead of the pool.

    Only plain functions, methods, lambdas and ``functools.partial`` objects are treated as
    factories; a client object that happens to define ``__call__`` is returned as is.

    :param client_or_factory: A client instance or a zero-argument function returning one.
    :return: The client instance.
    """
    if isroutine(client_or_factory) or isinstance(client_or_factory, partial):
        return client_or_factory()
    return client_or_factory  # type: ignore[return-value]


def require_exactly_one(**kwargs: Any) -> None:
    """
    Ensure exactly one of the given keyword arguments is not ``None``.

    :param kwargs: Mutually exclusive constructor arguments (``client=..., dsn=...``).
    :raises ValueError: If none or more than one of them is set.
    """
    provided = [name for name, value in kwargs.items() if value is not None]
    names = ', '.join(kwargs)
    if not provided:
        raise ValueError(f'one of {names} is required')
    if len(provided) > 1:
        raise ValueError(f'{names} are mutually exclusive, got {", ".join(provided)}')
