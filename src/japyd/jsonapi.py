from flask import Flask
from flask import request
from pydantic import AnyUrl
from pydantic import BaseModel
from pydantic import Field
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


class TopLevel(BaseModel):
    data: Resource | list[Resource] | None = None
    errors: list[Error] | None = None
    meta: dict | None = None
    jsonapi: JsonApi | None = None
    links: dict[str, AnyUrl | Link | None] | None = None
    included: list[Resource] | None = None


class JsonApiApp:
    """Flask's extension implementing JSON:API specification.
    """

    def __init__(self, app: Flask = None):
        self.app = None

        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        self.app = app

        handle_http_exception = app.handle_http_exception
        app.after_request(self._change_content_type)

        def _handle_http_exception(e: HTTPException):
            err = handle_http_exception(e)
            errors = [Error(id=e.name, title=e.name, detail=e.description, status=str(err.code))]  # noqa
            return (TopLevel(errors=errors).model_dump_json(exclude_none=True), err.code,
                    {'Content-Type': 'application/vnd.api+json'})

        app.handle_http_exception = _handle_http_exception

    def _change_content_type(self, response):
        if 'application/vnd.api+json' not in request.headers.getlist('accept'):
            return response

        response.content_type = 'application/vnd.api+json'
        return response
