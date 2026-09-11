from typing import Any, Callable, Coroutine, List, Optional, Union

from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, JsonResponse

from probirka import Probirka

_ALLOWED_METHODS = ('GET', 'HEAD')


def make_django_view(
    probirka: Probirka,
    timeout: Optional[int] = None,
    with_groups: Union[str, List[str]] = '',
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
        timeout (Optional[int]): The timeout for the Probirka run.
        with_groups (Union[str, List[str]]): Groups to include in the Probirka run.
        skip_required (bool): Whether to skip required checks.
        return_results (bool): Whether to return the results in the response.
        success_code (int): The HTTP status code for a successful response.
        error_code (int): The HTTP status code for an error response.

    Returns:
        Callable[[HttpRequest], Coroutine[Any, Any, HttpResponse]]: The Django async view.
    """

    async def view(request: HttpRequest) -> HttpResponse:
        """
        The Django view that runs the Probirka instance.

        Args:
            request: The Django request object.

        Returns:
            HttpResponse: The HTTP response with the Probirka results.
        """
        if request.method not in _ALLOWED_METHODS:
            return HttpResponseNotAllowed(_ALLOWED_METHODS)
        res = await probirka.run(
            timeout=timeout,
            with_groups=with_groups,
            skip_required=skip_required,
        )
        status_code = success_code if res.ok else error_code
        if return_results:
            return JsonResponse(res.to_dict(), status=status_code, json_dumps_params={'default': str})
        return HttpResponse(status=status_code)

    return view
