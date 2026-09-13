from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed

from probirka._ext._common import JSON_CONTENT_TYPE, run_and_render

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Sequence

    from probirka._probirka import Probirka

_ALLOWED_METHODS = ('GET', 'HEAD')


def make_django_view(
    probirka: Probirka,
    timeout: int | None = None,
    with_groups: str | Sequence[str] = '',
    skip_required: bool = False,
    return_results: bool = True,
    success_code: int = 200,
    error_code: int = 500,
) -> Callable[[HttpRequest], Coroutine[Any, Any, HttpResponse]]:
    """
    Create a Django async view for a given Probirka instance.

    The view accepts ``GET`` (and ``HEAD``) requests only; other methods get ``405``.
    The JSON body is :meth:`ProbirkaResult.to_dict`, the same format as the other integrations.

    Args:
        probirka (Probirka): The Probirka instance to run.
        timeout (int | None): The timeout for the Probirka run.
        with_groups (str | Sequence[str]): Groups to include in the Probirka run.
        skip_required (bool): Whether to skip required checks.
        return_results (bool): Whether to return the results in the response.
        success_code (int): The HTTP status code for a successful response.
        error_code (int): The HTTP status code for an error response.

    Returns:
        Callable[[HttpRequest], Coroutine[Any, Any, HttpResponse]]: The Django async view.
    """

    async def view(request: HttpRequest) -> HttpResponse:
        """
        Run the Probirka instance and return the Django response.

        Args:
            request: The Django request object.

        Returns:
            HttpResponse: The HTTP response with the Probirka results.
        """
        if request.method not in _ALLOWED_METHODS:
            return HttpResponseNotAllowed(_ALLOWED_METHODS)
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
            return HttpResponse(status=status_code)
        return HttpResponse(body, status=status_code, content_type=JSON_CONTENT_TYPE)

    return view
