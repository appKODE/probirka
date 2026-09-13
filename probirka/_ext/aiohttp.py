from __future__ import annotations

from collections.abc import Callable, Coroutine, Sequence
from typing import Any

from aiohttp import web

from probirka._ext._common import JSON_CONTENT_TYPE, run_and_render
from probirka._probirka import Probirka


def make_aiohttp_endpoint(
    probirka: Probirka,
    timeout: int | None = None,
    with_groups: str | Sequence[str] = '',
    skip_required: bool = False,
    return_results: bool = True,
    success_code: int = 200,
    error_code: int = 500,
) -> Callable[[web.Request], Coroutine[Any, Any, web.Response]]:
    """
    Create an aiohttp endpoint for a given Probirka instance.

    Args:
        probirka (Probirka): The Probirka instance to run.
        timeout (int | None): The timeout for the Probirka run.
        with_groups (str | Sequence[str]): Groups to include in the Probirka run.
        skip_required (bool): Whether to skip required checks.
        return_results (bool): Whether to return the results in the response.
        success_code (int): The HTTP status code for a successful response.
        error_code (int): The HTTP status code for an error response.

    Returns:
        Callable[[web.Request], Coroutine[Any, Any, web.Response]]: The aiohttp endpoint.
    """

    async def endpoint(
        _: web.Request,
    ) -> web.Response:
        """
        The aiohttp endpoint that runs the Probirka instance.

        Args:
            _: The aiohttp request object.

        Returns:
            web.Response: The HTTP response with the Probirka results.
        """
        status_code, body = await run_and_render(
            probirka=probirka,
            timeout=timeout,
            with_groups=with_groups,
            skip_required=skip_required,
            return_results=return_results,
            success_code=success_code,
            error_code=error_code,
        )
        if body is None:
            return web.Response(body='', status=status_code)
        return web.Response(body=body, status=status_code, content_type=JSON_CONTENT_TYPE)

    return endpoint
