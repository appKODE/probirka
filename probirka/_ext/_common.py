from __future__ import annotations

import json

from collections.abc import Sequence

from probirka._probirka import Probirka

JSON_CONTENT_TYPE = 'application/json'
"""Content type of a rendered body, spelled the same way by every adapter."""


async def run_and_render(
    probirka: Probirka,
    timeout: int | None,
    with_groups: str | Sequence[str],
    skip_required: bool,
    return_results: bool,
    success_code: int,
    error_code: int,
) -> tuple[int, bytes | None]:
    """
    Run the probes and turn the outcome into a status code and a response body.

    The single place where the JSON contract shared by the adapters lives. ``info`` may hold
    arbitrary objects, so the dump falls back to ``str`` instead of raising.

    :param probirka: The Probirka instance to run.
    :param timeout: The timeout for the Probirka run.
    :param with_groups: Groups to include in the Probirka run.
    :param skip_required: Whether to skip required checks.
    :param return_results: Whether to render the results at all. When false nothing is serialized:
        neither :meth:`ProbirkaResult.to_dict` nor ``json.dumps`` is called.
    :param success_code: The HTTP status code for a successful response.
    :param error_code: The HTTP status code for an error response.
    :return: The status code, and the UTF-8 JSON body or ``None`` for a response without a body.
    """
    res = await probirka.run(
        timeout=timeout,
        with_groups=with_groups,
        skip_required=skip_required,
    )
    status_code = success_code if res.ok else error_code
    if not return_results:
        return status_code, None
    return status_code, json.dumps(obj=res.to_dict(), default=str).encode()
