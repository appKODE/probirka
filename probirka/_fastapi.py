from typing import Any, Callable, Coroutine, List, Optional, Union

from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response

from probirka import Probirka


def make_fastapi_endpoint(
    probirka: Probirka,
    timeout: Optional[int] = None,
    with_groups: Union[str, List[str]] = '',
    skip_required: bool = False,
    return_results: bool = True,
    success_code: int = status.HTTP_200_OK,
    error_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> Callable[[], Coroutine[Any, Any, Response]]:
    """
    Create a FastAPI endpoint for a given Probirka instance.

    Args:
        probirka (Probirka): The Probirka instance to run.
        timeout (Optional[int]): The timeout for the Probirka run.
        with_groups (Union[str, List[str]]): Groups to include in the Probirka run.
        skip_required (bool): Whether to skip required checks.
        return_results (bool): Whether to return the results in the response.
        success_code (int): The HTTP status code for a successful response.
        error_code (int): The HTTP status code for an error response.

    Returns:
        Callable[[], Coroutine[Any, Any, Response]]: The FastAPI endpoint.
    """

    async def endpoint() -> Response:
        """
        The FastAPI endpoint that runs the Probirka instance.

        Returns:
            Response: The HTTP response with the Probirka results.
        """
        res = await probirka.run(
            timeout=timeout,
            with_groups=with_groups,
            skip_required=skip_required,
        )
        resp = JSONResponse(jsonable_encoder(res)) if return_results else Response()
        resp.status_code = success_code if res.ok else error_code
        return resp

    return endpoint
