from dataclasses import asdict
from typing import Any, Callable, Coroutine, List, Optional, Union

from django.http import HttpRequest, HttpResponse, JsonResponse

from probirka import Probirka


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

    async def view(_: HttpRequest) -> HttpResponse:
        """
        The Django view that runs the Probirka instance.

        Args:
            _: The Django request object.

        Returns:
            HttpResponse: The HTTP response with the Probirka results.
        """
        res = await probirka.run(
            timeout=timeout,
            with_groups=with_groups,
            skip_required=skip_required,
        )
        status_code = success_code if res.ok else error_code
        if return_results:
            return JsonResponse(asdict(res), status=status_code, safe=False)
        return HttpResponse(status=status_code)

    return view
