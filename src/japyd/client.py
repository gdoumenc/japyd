import typing as t

import requests

from .jsonapi import JSONAPI_CONTENT_TYPE, MultiResourcesTopLevel, SingleResourceTopLevel


class JapydClient:
    """Minimal JSON:API client.

    An error response is returned as a toplevel with errors, as the JSON:API error document is parsed.
    """

    def __init__(self, url: str, *, timeout: float | None = 30):
        self.url = url.rstrip("/")
        self.timeout = timeout

    @t.overload
    def __call__(self, method: str, entry: str, /, id: str, **kwargs) -> SingleResourceTopLevel: ...

    @t.overload
    def __call__(self, method: str, entry: str, /, **kwargs) -> MultiResourcesTopLevel: ...

    def __call__(self, method: str, entry: str, /, id=None, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        kwargs["headers"] = {"Accept": JSONAPI_CONTENT_TYPE, **kwargs.get("headers", {})}

        url = f"{self.url}/{entry.strip('/')}"
        if id is not None:
            resp = requests.request(method, f"{url}/{id}", **kwargs)
            return SingleResourceTopLevel.model_validate(resp.json())

        resp = requests.request(method, url, **kwargs)
        return MultiResourcesTopLevel.model_validate(resp.json())
