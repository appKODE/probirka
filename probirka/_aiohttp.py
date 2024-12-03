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
    async def endpoint(
        _: web.Request,
    ) -> web.Response:
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
