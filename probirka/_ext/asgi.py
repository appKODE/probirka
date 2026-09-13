from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping, Sequence
from typing import TYPE_CHECKING, Any, TypeAlias

from probirka._ext._common import JSON_CONTENT_TYPE, run_and_render

if TYPE_CHECKING:
    from probirka._probirka import Probirka

Scope: TypeAlias = MutableMapping[str, Any]
"""ASGI connection scope."""

Message: TypeAlias = MutableMapping[str, Any]
"""A single ASGI protocol message."""

Receive: TypeAlias = Callable[[], Awaitable[Message]]
"""Awaitable returning the next message from the server."""

Send: TypeAlias = Callable[[Message], Awaitable[None]]
"""Coroutine function sending a message to the server."""

ASGIApp: TypeAlias = Callable[[Scope, Receive, Send], Awaitable[None]]
"""An ASGI 3 application."""

_ALLOWED_METHODS = ('GET', 'HEAD')
_ALLOW_HEADER = ', '.join(_ALLOWED_METHODS).encode()
_JSON_CONTENT_TYPE = JSON_CONTENT_TYPE.encode()


async def _send_response(
    send: Send,
    status_code: int,
    body: bytes | None,
    with_body: bool = True,
    extra_headers: Sequence[tuple[bytes, bytes]] = (),
) -> None:
    """
    Send a complete HTTP response as ASGI messages.

    Args:
        send: The ASGI send callable.
        status_code: The HTTP status code.
        body: The response body, or None for a response without one.
        with_body: Whether to actually send the body. False for HEAD, which keeps the headers
            a GET would have returned but carries no content.
        extra_headers: Headers to send in front of the content ones.
    """
    headers = list(extra_headers)
    if body is None:
        headers.append((b'content-length', b'0'))
    else:
        headers.append((b'content-type', _JSON_CONTENT_TYPE))
        headers.append((b'content-length', str(len(body)).encode()))
    await send(
        {
            'type': 'http.response.start',
            'status': status_code,
            'headers': headers,
        }
    )
    await send(
        {
            'type': 'http.response.body',
            'body': body if body is not None and with_body else b'',
        }
    )


async def _handle_lifespan(
    receive: Receive,
    send: Send,
) -> None:
    """
    Acknowledge the lifespan protocol so that standalone servers start without warnings.

    The application holds no state of its own, so there is nothing to set up or tear down.

    Args:
        receive: The ASGI receive callable.
        send: The ASGI send callable.
    """
    while True:
        message = await receive()
        if message['type'] == 'lifespan.startup':
            await send({'type': 'lifespan.startup.complete'})
        elif message['type'] == 'lifespan.shutdown':
            await send({'type': 'lifespan.shutdown.complete'})
            return


class _ProbirkaAsgiApp:
    """
    The ASGI application returned by :func:`make_asgi_app`.

    A callable object rather than a closure on purpose: Starlette treats a plain function passed
    to ``Route`` as a request/response endpoint and calls it with a single argument, while an
    instance is recognised as the ASGI application it is.
    """

    def __init__(
        self,
        probirka: Probirka,
        timeout: int | None,
        with_groups: str | Sequence[str],
        skip_required: bool,
        return_results: bool,
        success_code: int,
        error_code: int,
    ) -> None:
        self._probirka = probirka
        self._timeout = timeout
        self._with_groups = with_groups
        self._skip_required = skip_required
        self._return_results = return_results
        self._success_code = success_code
        self._error_code = error_code

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """
        Run the Probirka instance and answer the request.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.

        Raises:
            RuntimeError: If the server opens a connection that is neither HTTP nor lifespan.
        """
        scope_type = scope['type']
        if scope_type == 'lifespan':
            await _handle_lifespan(receive, send)
            return
        if scope_type != 'http':
            msg = f'probirka serves the http and lifespan scopes only, got {scope_type!r}'
            raise RuntimeError(msg)
        method = scope['method']
        if method not in _ALLOWED_METHODS:
            await _send_response(send, 405, None, extra_headers=((b'allow', _ALLOW_HEADER),))
            return
        status_code, body = await run_and_render(
            probirka=self._probirka,
            timeout=self._timeout,
            with_groups=self._with_groups,
            skip_required=self._skip_required,
            return_results=self._return_results,
            success_code=self._success_code,
            error_code=self._error_code,
        )
        await _send_response(send, status_code, body, with_body=method != 'HEAD')


def make_asgi_app(
    probirka: Probirka,
    timeout: int | None = None,
    with_groups: str | Sequence[str] = '',
    skip_required: bool = False,
    return_results: bool = True,
    success_code: int = 200,
    error_code: int = 500,
) -> ASGIApp:
    """
    Create a framework-independent ASGI application for a given Probirka instance.

    The application is a plain ASGI 3 callable with no third-party dependencies. Register it as a
    route (``Route('/health', app, methods=['GET', 'HEAD'])`` in Starlette), mount it
    (``app.mount('/health', health_app)`` in FastAPI, ``asgi('/health', is_mount=True)`` in
    Litestar), or serve it on its own port with ``uvicorn module:health_app``.

    Two behaviours differ from the framework-specific adapters, because a mounted application
    gets no help from the host router:

    * The request path is ignored. Whatever reaches the application is answered, so an app
      mounted at ``/health`` also answers ``/health/anything``.
    * Only ``GET`` and ``HEAD`` are served; every other method gets ``405`` with an ``allow``
      header. ``HEAD`` returns the headers a ``GET`` would have returned, with an empty body.

    Args:
        probirka (Probirka): The Probirka instance to run.
        timeout (int | None): The timeout for the Probirka run.
        with_groups (str | Sequence[str]): Groups to include in the Probirka run.
        skip_required (bool): Whether to skip required checks.
        return_results (bool): Whether to return the results in the response.
        success_code (int): The HTTP status code for a successful response.
        error_code (int): The HTTP status code for an error response.

    Returns:
        ASGIApp: The ASGI application.
    """
    return _ProbirkaAsgiApp(
        probirka=probirka,
        timeout=timeout,
        with_groups=with_groups,
        skip_required=skip_required,
        return_results=return_results,
        success_code=success_code,
        error_code=error_code,
    )
