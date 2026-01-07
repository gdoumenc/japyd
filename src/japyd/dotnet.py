from __future__ import annotations

import re
import typing as t
from http import HTTPStatus

from flask import Response, request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from werkzeug.exceptions import NotFound, UnprocessableEntity

from .filter import Oper
from .jsonapi import (
    Error,
    MultiResourcesTopLevel,
    Resource,
    SingleResourceTopLevel,
    TopLevel,
)
from .models import JsonApiBaseModel
from .utils import to_string_or_numeric

FIELDS_REGEXP = re.compile(r"fields\[(.*)]")

NUMERIC_REGEXP = r"[-+]?[0-9]*.?[0-9]+([eE][-+]?[0-9]+)?"
IDENTIFIER_REGEXP = r"([A-Za-z_][A-Za-z0-9_\.]*)"
QUOTED_REGEXP = r"('[^']|'')*'"
VALUE_REGEXP = rf"(?P<value>'([^']|'')*')|(?P<numeric>{NUMERIC_REGEXP})|(?P<other_attr>{IDENTIFIER_REGEXP})"
OPER_REGEXP = (
    rf"({Oper.EQUALS}|{Oper.LESS_THAN}"
    rf"|{Oper.LESS_OR_EQUAL}|{Oper.GREATER_THAN}|{Oper.GREATER_OR_EQUAL}"
    rf"|{Oper.CONTAINS}|{Oper.STARTS_WITH}|{Oper.ENDS_WITH})"
)
LIST_OPER_REGEXP = rf"({Oper.ANY}|{Oper.HAS})"
LIST_VALUES_REGEXP = rf"(('([^']|'')*')|{NUMERIC_REGEXP})"
FILTER_REGEXP = (
    rf"(?P<oper>{OPER_REGEXP})\s*[(]\s*(?P<attr>{IDENTIFIER_REGEXP})\s*,\s*({VALUE_REGEXP})\s*[)]"
    rf"|(?P<list_oper>{LIST_OPER_REGEXP})\s*[(]\s*(?P<list_attr>{IDENTIFIER_REGEXP})\s*,"
    rf"\s*(?P<values>{LIST_VALUES_REGEXP}(\s*[,]\s*{LIST_VALUES_REGEXP}\s*)*)\s*[)]"
)
COMPILED_FILTER_REGEXP = re.compile(rf"^\s*{FILTER_REGEXP}\s*$")

NOT_REGEXP = rf"\s*{Oper.NOT}\s*[(]\s*(?P<filter>.*)\s*[)]\s*"
COMPILED_NOT_REGEXP = re.compile(NOT_REGEXP)

OR_AND_REGEXP = rf"\s*({Oper.OR}|{Oper.AND})\s*[(]\s*(?P<filter1>.*)\s*,\s*(?P<filter2>.*)\s*[)]\s*"
COMPILED_OR_AND_REGEXP = re.compile(OR_AND_REGEXP)


class JsonApiPagination(BaseModel):
    number: int
    size: int
    total: int | None = None


class JsonApiQueryFilter(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    oper: Oper
    subfilter: tuple[JsonApiQueryFilter, JsonApiQueryFilter] | JsonApiQueryFilter | None = None
    attr: str | None = None
    value: str | float | int | list | None = None
    other_attr: str | None = None

    @model_validator(mode="before")
    def parse_value(cls, data: dict) -> dict:
        # On subfilter validation does nothing
        if isinstance(data, dict):
            if data["oper"] in (Oper.ANY, Oper.HAS):
                typed_values = []
                for value in data["value"]:
                    value = to_string_or_numeric(value)
                    typed_values.append(value)
                data["value"] = typed_values

        return data

    def match(self, model) -> bool:
        if self.oper in (
            Oper.EQUALS,
            Oper.LESS_THAN,
            Oper.LESS_OR_EQUAL,
            Oper.GREATER_THAN,
            Oper.GREATER_OR_EQUAL,
        ):
            return model.match(self.oper, self.attr, self.value)
        return False


JsonApiQueryFilter.model_rebuild()


class JsonApiQueryModel(BaseModel):
    """JSON:API query validated model from flask pydantic.

    As request's query defines the fields to be returned, the filters and other parameters
    use this query to paginate the result or the not_found method if no result.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    fields: dict[str, list[str]] = Field(default_factory=dict)
    filter: str | list[str] = Field(default_factory=list)
    filters: list[JsonApiQueryFilter] = Field(default_factory=list)
    include: set[str] = Field(default_factory=set)
    sort: str | None = None

    def get_fields(self, jsonapi_type) -> set[str] | None:
        """Returns the list of fields to dump for the given JSON API type."""
        if self.fields and jsonapi_type:
            values = self.fields.get(jsonapi_type)
            if values:
                return set(values)
        return None

    @property
    def query_pagination(self) -> JsonApiPagination:
        page = request.args.get("page[number]")
        size = request.args.get("page[size]")
        return JsonApiPagination(
            number=int(page) if page else 1,
            size=int(size) if size else 20,
        )

    def match(self, model: JsonApiBaseModel):
        """Checks if the model matches the query filters."""
        for filter in self.filters:
            if not filter.match(model):
                return False
        return True

    @staticmethod
    def no_content() -> Response:
        """Returns a no content response."""
        return Response(status=HTTPStatus.NO_CONTENT)

    def one(self, value: JsonApiBaseModel) -> SingleResourceTopLevel:
        """Returns a single JSON:API toplevel's data."""
        if value is None:
            raise NotFound()

        included: list[Resource] = []
        meta = {
            "count": 1,
        }
        return SingleResourceTopLevel(data=value.as_resource(included, self), included=included, meta=meta)  # noqa

    def one_or_none(self, value: JsonApiBaseModel) -> SingleResourceTopLevel:
        """Returns a single JSON:API toplevel's data."""
        if value is None:
            return MultiResourcesTopLevel.empty()

        return self.one(value)

    def paginate(
        self, values: t.Sequence[Resource | JsonApiBaseModel], *, full_list: bool = True, total: int | None = None
    ) -> MultiResourcesTopLevel:
        """Returns multi JSON:API toplevel's data from a value iterable.

        :param values: List for pagination.
        :param full_list: If true, the list is fully completed.
        :param total: The pagination total number of records if not a full list.
        """
        included: list[Resource] = []
        pagination = self.query_pagination
        total = len(values) if full_list else total
        if full_list:
            start = (pagination.number - 1) * pagination.size
            end = start + pagination.size
            values = values[start:end]
            has_next = end < len(values)
        else:
            values = values
            has_next = "tobedone"  # type: ignore

        meta = {
            "count": total,
            "pagination": {
                "page": pagination.number,
                "per_page": pagination.size,
                # "pages": page.pages,
                "has_next": has_next,
                "has_prev": pagination.number > 1,
            },
        }
        resources: list[Resource] = [v if isinstance(v, Resource) else v.as_resource(included, self) for v in values]
        return MultiResourcesTopLevel.model_validate({"data": resources, "included": included, "meta": meta})

    @staticmethod
    def error(code: int, title: str, detail: str) -> tuple[TopLevel, int]:
        return (
            TopLevel(errors=[Error(id=str(code), title=title, detail=detail, status=str(code), code=str(code))]),
            code,
        )

    @staticmethod
    def not_found(detail: str | None = None) -> tuple[TopLevel, int]:
        error = NotFound(description=detail)
        return JsonApiQueryModel.error(error.code, error.name, error.get_description())  # type: ignore

    @model_validator(mode="before")
    def parse_filter_fields(cls, data: dict) -> dict:
        filters = []
        fields = {}
        for arg, value in data.items():
            if arg == "filter":
                if isinstance(value, str):
                    filters.append(cls._parse_filter(value))
                elif isinstance(value, list):
                    filters += [cls._parse_filter(v) for v in value]
            elif arg.startswith("filter["):
                filters.append(cls._parse_filter(value))
            elif arg.startswith("fields["):
                groups = FIELDS_REGEXP.match(arg)
                if groups:
                    fields[groups[1]] = set(value.split(","))
                else:
                    msg = f"Wrong fields parameters: {arg}"
                    raise UnprocessableEntity(msg)

        if filters:
            data["filters"] = filters
        if fields:
            data["fields"] = fields

        return data

    @field_validator("include", mode="before")
    @classmethod
    def parse_include(cls, include: set[str] | list[str] | None) -> set[str]:
        if isinstance(include, set):
            return include
        return set(include[0].split(",")) if include else set()

    @classmethod
    def _parse_filter(cls, filter: str) -> JsonApiQueryFilter:
        if reg := COMPILED_FILTER_REGEXP.match(filter):
            oper = reg.group("oper")
            if oper:
                value = cls._parse_value(reg)
                other = reg.group("other_attr")
                return JsonApiQueryFilter(
                    oper=Oper(oper), attr=reg.group("attr"), value=value, other_attr=other if other != "null" else None
                )
            oper = reg.group("list_oper")
            if oper:
                values = [v.strip() for v in reg.group("values").split(",")]
                return JsonApiQueryFilter(oper=Oper(oper), attr=reg.group("list_attr"), value=values)

        if reg := COMPILED_NOT_REGEXP.match(filter):
            filter_expr = reg.group("filter")
            return JsonApiQueryFilter(oper=Oper.NOT, subfilter=cls._parse_filter(filter_expr))
        if reg := COMPILED_OR_AND_REGEXP.match(filter):
            filter1_expr = reg.group("filter1")
            filter2_expr = reg.group("filter2")
            return JsonApiQueryFilter(
                oper=Oper.NOT, subfilter=(cls._parse_filter(filter1_expr), cls._parse_filter(filter2_expr))
            )
        msg = f"Wrong filter parameters: {filter}"
        raise UnprocessableEntity(msg)

    @classmethod
    def _parse_value(cls, reg):
        numeric = reg.group("numeric")
        if numeric:
            value = float(numeric) if "." in numeric else int(numeric)
        else:
            value = reg.group("value")
            if value:
                value = value.strip("'")
                value = value.replace("''", "'")

        return value


class _JsonApiBodyModel(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    included: list[Resource] | None = Field(default_factory=list)
    meta: dict | None = None
    debug: bool = False


class JsonApiBodyModel(_JsonApiBodyModel):
    data: Resource | list[Resource] | None = None

    @property
    def attributes(self) -> dict[str, t.Any] | list[dict[str, t.Any]]:
        if isinstance(self.data, list):
            return [d.attributes for d in self.data]
        return self.data.attributes if self.data else {}


class SingleBodyModel(_JsonApiBodyModel):
    data: Resource | None = None

    @property
    def attributes(self) -> dict[str, t.Any]:
        return self.data.attributes if self.data else {}


class MultiBodyModel(_JsonApiBodyModel):
    data: list[Resource] = Field(default_factory=list)

    @property
    def attributes(self) -> list[dict[str, t.Any]]:
        return [d.attributes for d in self.data]
