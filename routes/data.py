import json
import random
import re

import requests
from fastapi import APIRouter, Depends, Request, Response
from fastapi_limiter.depends import RateLimiter

import utils

router = APIRouter()

URL_REGEX = re.compile(
    r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
)

with open("proxies.json") as f:
    proxies = json.load(f)


def probe_args(args: dict, required: dict):
    exceptions = []

    for req_arg, req_type in required.items():
        if req_arg not in args:
            exceptions.append(f'"{req_arg}" is a required query parameter that is missing.')

        elif isinstance(req_type, re.Pattern) and not re.match(req_type, args[req_arg]):
            exceptions.append(
                f'Query parameter "{req_arg}" doesn\'t match assigned regex, if this argument is valid please contact my developer.'
            )

        elif not isinstance(args[req_arg], type) and not isinstance(
            req_type, re.Pattern
        ):
            exceptions.append(
                f'Query parameter "{req_arg}" expects type {type.__name__}, got {type(args[req_arg].__name__)} instead.'
            )

    return {"error": len(exceptions) > 0, "exceptions": exceptions}


@router.get("/read", dependencies=[Depends(RateLimiter(times=1, seconds=5))])
def read(request: Request):
    params = request.query_params
    required = {"url": URL_REGEX}

    allowed_content_types = [
        "application/json",
        "text/html",
        "text/css",
        "text/javascript",
        "text/plain",
        "text/x-python",
    ]

    res = probe_args(params, required)
    if res["error"]:
        return res

    url = params.get("url")
    fmt_proxies = {
        i[
            "protocol"
        ]: f"http://{i['username']}:{i['password']}@{i['domain']}:{i['port']}/"
        for i in proxies["proxies"]
    }

    resp = requests.head(url, timeout=10, allow_redirects=False, proxies=proxies)
    content_type = resp.headers.get("Content-Type", "").split(";")[0]

    if content_type not in allowed_content_types:
        fmt_allowed_content_types = utils.format_list(allowed_content_types)
        return {
            "error": True,
            "exceptions": [
                f"Content Type of passed URL can only be one of {fmt_allowed_content_types}, but is {content_type}"
            ],
        }

    resp = requests.get(url, allow_redirects=False, proxies=fmt_proxies)

    headers = {}

    if params.get("as_original_content_type", "").lower() == "true":
        headers = {"Content-Type": content_type}

    return Response(resp.text, headers=headers)
