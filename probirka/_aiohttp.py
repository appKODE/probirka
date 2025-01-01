import json

from dataclasses import asdict
from typing import Any, Callable, Coroutine, List, Optional, Union

from aiohttp import web

from probirka import Probirka


def make_aiohttp_endpoint(
    probirka: Probirka,
    timeout: Optional[int] = None,
    with_groups: Union[str, List[str]] = '',
    skip_required: bool = False,
    return_results: bool = True,
    success_code: int = 200,
    error_code: int = 500,
) -> Callable[[web.Request], Coroutine[Any, Any, web.Response]]:
    """
    Create an aiohttp endpoint for a given Probirka instance.

    Args:
        probirka (Probirka): The Probirka instance to run.
        timeout (Optional[int]): The timeout for the Probirka run.
        with_groups (Union[str, List[str]]): Groups to include in the Probirka run.
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
        res = await probirka.run(
            timeout=timeout,
            with_groups=with_groups,
            skip_required=skip_required,
        )
        status_code = success_code if res.ok else error_code
        return (
            web.json_response(
                text=json.dumps(obj=asdict(res), default=str),
                status=status_code,
            )
            if return_results
            else web.Response(
                body='',
                status=status_code,
            )
        )

    return endpoint
