from __future__ import annotations

from flask import Flask, Response, make_response, request
from pydantic import AnyUrl, BaseModel, Field
from werkzeug.exceptions import HTTPException


class Link(BaseModel):
    href: str
    meta: dict | None = None


class JsonApi(BaseModel):
    version: str | None = None
    meta: dict | None = None


class Error(BaseModel):
    id: str | None = None
    status: str | None = None
    code: str | None = None
    title: str | None = None
    detail: str | None = None
    source: dict | None = None
    meta: dict | None = None


class ResourceIdentifier(BaseModel):
    type: str
    id: str
    meta: dict | None = None


class Relationship(BaseModel):
    data: ResourceIdentifier | list[ResourceIdentifier] | None = None
    links: dict[str, AnyUrl | Link | None] | None = None
    meta: dict | None = None


class Resource(BaseModel):
    type: str
    id: str
    attributes: dict = Field(default_factory=dict)
    relationships: dict[str, Relationship] | None = None
    links: dict[str, AnyUrl | Link | None] | None = None
    meta: dict | None = None

    def flatten(self):
        return {"id": self.id, **self.attributes}


class TopLevel(BaseModel):
    data: Resource | list[Resource] | None = None
    errors: list[Error] | None = None
    meta: dict | None = None
    jsonapi: JsonApi | None = None
    links: dict[str, AnyUrl | Link | None] | None = None
    included: list[Resource] | None = None

    @classmethod
    def http_error(
        cls, code: int | None, title: str, detail: str, status: str | None = None
    ) -> tuple[TopLevel, int, dict]:
        errors = [Error(id=str(code), title=title, detail=detail, status=status or str(code))]
        return TopLevel(errors=errors), code or 500, {"Content-Type": "application/vnd.api+json"}


class SingleResourceTopLevel(TopLevel):
    data: Resource | None = None  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    def empty(cls, meta=None, jsonapi=None, links=None) -> SingleResourceTopLevel:
        if meta is None:
            meta = {"count": 0}
        return cls(data=None, meta=meta, jsonapi=jsonapi, links=links)


class MultiResourcesTopLevel(TopLevel):
    data: list[Resource] = Field(default_factory=list)  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    def empty(cls, meta=None, jsonapi=None, links=None) -> MultiResourcesTopLevel:
        if meta is None:
            meta = {"count": 0}
        return cls(data=[], meta=meta, jsonapi=jsonapi, links=links)


class JsonApiApp:
    """Flask's extension implementing JSON:API specification."""

    def __init__(self, app: Flask | None = None):
        self.app: Flask | None = None

        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """
        - Adds exception handler to transform any exception to TopLevel error.
        - Forces response content type to JSON:API.
        """
        self.app = app

        handle_exception = app.error_handler_spec[None][None].get(Exception)
        app.after_request(self._change_content_type)

        def _handle_exception(e: Exception) -> Response:
            status_code: str
            title: str
            detail: str

            if handle_exception:
                try:
                    resp = handle_exception(e)
                    if not isinstance(resp, Response):
                        resp = make_response(resp)
                    status_code = str(resp.status_code)
                    title = str(e)
                    detail = str(resp.data)
                except Exception as ex:
                    e = ex

            if isinstance(e, HTTPException):
                status_code = str(e.code or 500)
                title = e.name
                detail = e.description or str(e)
            else:
                status_code = "500"
                title = type(e).__name__
                detail = str(e)

            error = Error(id=status_code, title=title, detail=detail, status=status_code)
            toplevel = TopLevel(errors=[error]).model_dump_json(exclude_none=True)
            return make_response(toplevel, status_code, {"Content-Type": "application/vnd.api+json"})

        app.error_handler_spec[None][None][Exception] = _handle_exception

    def _change_content_type(self, resp: Response) -> Response:
        if "application/vnd.api+json" not in request.headers.getlist("accept"):
            return resp

        resp.content_type = "application/vnd.api+json"
        return resp
