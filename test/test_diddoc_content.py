"""Test working with diddocs."""

from contextlib import contextmanager
from inspect import iscoroutine
import json
import os
from typing import Any, Callable, ParamSpec, Tuple, TypeVar, cast

from aries_askar.key import Key
import colored
from colored import stylize
from indy_vdr.ledger import build_get_nym_request, build_nym_request
from indy_vdr.pool import Pool
from indy_vdr.request import Request
import pytest

DIDGen = Tuple[Key, str, str, str]
P = ParamSpec("P")
R = TypeVar("R")


@contextmanager
def section(title: str):
    size = os.get_terminal_size()
    left = "=" * (int(size.columns / 2) - int((len(title) + 1) / 2))
    right = "=" * (size.columns - (len(left) + len(title) + 2))
    print(stylize(f"{left} {title} {right}", colored.fg("blue") + colored.attr("bold")))
    yield

def stringify(value: Any):
    if isinstance(value, dict):
        return json.dumps(value, indent=2)
    if isinstance(value, str):
        return value
    if isinstance(value, Request):
        return json.dumps(json.loads(value.body), indent=2)
    return str(value)

def status_of_nym(get_nym_response):
    print("Retrieved NYM Value:")
    print(stylize(json.dumps(json.loads(get_nym_response["data"]), indent=2), colored.fg("green")))

def log_call(func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    args_str = ", ".join(stringify(arg) for arg in args)
    kwargs_str = ", ".join(f"{key}={value}" for key, value in kwargs.items())
    parameters = ", ".join([
        *([args_str] if args_str else []),
        *([kwargs_str] if kwargs_str else [])
    ])
    print(
        f"{func.__name__}({parameters})"
    )
    ret = func(*args, **kwargs)
    print("Result:")
    if iscoroutine(ret):
        async def _wrapper(ret):
            ret = await ret
            print(stringify(ret))
            return ret
        return cast(R, _wrapper(ret))

    print(stringify(ret))
    return ret


@pytest.mark.asyncio
async def test_write_diddoc_content(pool: Pool, did_gen: Callable[[], DIDGen], steward: DIDGen):
    print()
    key, did, verkey, sigkey = did_gen()
    steward_key, steward_did, *_ = steward

    with section("Write new nym to ledger"):
        request = log_call(build_nym_request, steward_did, did, verkey, role="ENDORSER", version=2)
        request.set_signature(steward_key.sign_message(request.signature_input))
        response = await log_call(pool.submit_request, request)
        original_seq_no = response["txnMetadata"]["seqNo"]

    with section("Retrive the nym"):
        request = log_call(build_get_nym_request, did, did, None, None)
        response = await log_call(pool.submit_request, request)
        status_of_nym(response)

    with section("Add diddoc content to nym"):
        request = log_call(
            build_nym_request,
            did,
            did,
            diddoc_content=json.dumps({
                "@context": [
                    "https://www.w3.org/ns/did/v1",
                    "https://identity.foundation/didcomm-messaging/service-endpoint/v1",
                ],
                "serviceEndpoint": [
                    {
                        "id": "did:indy:sovrin:123456#didcomm",
                        "type": "didcomm-messaging",
                        "serviceEndpoint": "https://example.com",
                        "recipientKeys": ["#verkey"],
                        "routingKeys": [],
                    }
                ],
            })
        )
        request.set_signature(key.sign_message(request.signature_input))
        response = await log_call(pool.submit_request, request)

    with section("Retrieve nym after diddoc is written"):
        request = log_call(build_get_nym_request, did, did, None, None)
        response = await log_call(pool.submit_request, request)
        status_of_nym(response)

    with section("Retrieve past version of nym"):
        request = log_call(build_get_nym_request, did, did, original_seq_no, None)
        response = await log_call(pool.submit_request, request)
        status_of_nym(response)
