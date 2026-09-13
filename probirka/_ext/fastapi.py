from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import status
from fastapi.responses import Response

from probirka._ext._common import JSON_CONTENT_TYPE, run_and_render

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Sequence

    from probirka._probirka import Probirka


def make_fastapi_endpoint(
    probirka: Probirka,
    timeout: int | None = None,
    with_groups: str | Sequence[str] = '',
    skip_required: bool = False,
    return_results: bool = True,
    success_code: int = status.HTTP_200_OK,
    error_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> Callable[[], Coroutine[Any, Any, Response]]:
    """
    Create a FastAPI endpoint for a given Probirka instance.

    Args:
        probirka (Probirka): The Probirka instance to run.
        timeout (int | None): The timeout for the Probirka run.
        with_groups (str | Sequence[str]): Groups to include in the Probirka run.
        skip_required (bool): Whether to skip required checks.
        return_results (bool): Whether to return the results in the response.
        success_code (int): The HTTP status code for a successful response.
        error_code (int): The HTTP status code for an error response.

    Returns:
        Callable[[], Coroutine[Any, Any, Response]]: The FastAPI endpoint.
    """

    async def endpoint() -> Response:
        """
        Run the Probirka instance and return the FastAPI response.

        Returns:
            Response: The HTTP response with the Probirka results.
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
            return Response(status_code=status_code)
        return Response(content=body, status_code=status_code, media_type=JSON_CONTENT_TYPE)

    return endpoint
