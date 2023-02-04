import json
import random
import re
from typing import Optional

import requests
from fastapi import APIRouter, Depends, Request, Response
from fastapi_limiter.depends import RateLimiter
from urllib.parse import urlparse

import utils

router = APIRouter()

URL_REGEX = re.compile(
    r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
)

with open("proxies.json") as f:
    proxies = json.load(f)


@router.get(
    "/read",
    dependencies=[Depends(RateLimiter(times=1, seconds=5))],
)
def read(request: Request, url: str, original_type: bool = False):
    parsed_url = urlparse(url)
    
    if parsed_url.netloc in ["127.0.0.1", "localhost"]:
        return "fuck you"

    allowed_content_types = [
        "application/json",
        "text/html",
        "text/css",
        "text/javascript",
        "text/plain",
        "text/x-python",
    ]

    fmt_proxies = {
        i[
            "protocol"
        ]: f"http://{i['username']}:{i['password']}@{i['domain']}:{i['port']}/"
        for i in proxies["proxies"]
    }

    resp = requests.head(url, timeout=10, allow_redirects=False, proxies=proxies)
    content_type = resp.headers.get("Content-Type", "").split(";")[0]
    content_length: int = resp.headers.get("Content-Length", 0)
    
    if content_length == 0:
        return {
            "error": True,
            "exceptions": [
                f"Content Length is not provided by server"
            ],
        }
        
    if content_length > 8000000:
        return {
            "error": True,
            "exceptions": [
                f"File is over 8MB"
            ],
        }

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

    if original_type:
        headers = {"Content-Type": content_type}

    return Response(resp.text, headers=headers)
