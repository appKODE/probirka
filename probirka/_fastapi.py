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
    async def endpoint() -> Response:
        res = await probirka.run(
            timeout=timeout,
            with_groups=with_groups,
            skip_required=skip_required,
        )
        resp = JSONResponse(jsonable_encoder(res)) if return_results else Response()
        resp.status_code = success_code if res.ok else error_code
        return resp

    return endpoint
