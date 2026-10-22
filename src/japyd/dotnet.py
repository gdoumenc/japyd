from __future__ import annotations

import re
import typing as t
import warnings
from http import HTTPStatus

from flask import Response, request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from werkzeug.exceptions import (
    BadRequest,
    InternalServerError,
    NotFound,
    UnprocessableEntity,
)

from .filter import FilterError, Oper
from .jsonapi import (
    Error,
    MultiResourcesTopLevel,
    Resource,
    SingleResourceTopLevel,
    TopLevel,
    flatten_resource,
)
from .models import JsonApiBaseModel

FIELDS_REGEXP = re.compile(r"fields\[(.*)]")

NUMERIC_REGEXP = r"[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?"
# Any character except the filter syntax delimiters, to allow keys like 'gmp+' in a JSON attribute
IDENTIFIER_REGEXP = r"([^\s(),']+)"
KEYWORD_VALUES: dict[str, bool | None] = {"null": None, "true": True, "false": False}
QUOTED_REGEXP = r"('[^']|'')*'"
VALUE_REGEXP = rf"(?P<value>'([^']|'')*')|(?P<numeric>{NUMERIC_REGEXP})|(?P<other_attr>{IDENTIFIER_REGEXP})"
OPER_REGEXP = (
    rf"({Oper.EQUALS}|{Oper.LESS_THAN}"
    rf"|{Oper.LESS_OR_EQUAL}|{Oper.GREATER_THAN}|{Oper.GREATER_OR_EQUAL}"
    rf"|{Oper.CONTAINS}|{Oper.STARTS_WITH}|{Oper.ENDS_WITH}"
    rf"|{Oper.CONTAINS_IGNORE_CASE}|{Oper.STARTS_WITH_IGNORE_CASE}|{Oper.ENDS_WITH_IGNORE_CASE})"
)
LIST_OPER_REGEXP = rf"({Oper.ANY})"
LIST_VALUES_REGEXP = rf"(('([^']|'')*')|{NUMERIC_REGEXP})"
FILTER_REGEXP = (
    rf"(?P<oper>{OPER_REGEXP})\s*[(]\s*(?P<attr>{IDENTIFIER_REGEXP})\s*,\s*({VALUE_REGEXP})\s*[)]"
    rf"|(?P<list_oper>{LIST_OPER_REGEXP})\s*[(]\s*(?P<list_attr>{IDENTIFIER_REGEXP})\s*,"
    rf"\s*(?P<values>{LIST_VALUES_REGEXP}(\s*[,]\s*{LIST_VALUES_REGEXP}\s*)*)\s*[)]"
)
COMPILED_FILTER_REGEXP = re.compile(rf"^\s*{FILTER_REGEXP}\s*$")

# Arguments of logical operators may be nested, so they are split by _split_arguments and not by the regexp
LOGICAL_REGEXP = rf"^\s*(?P<oper>{Oper.NOT}|{Oper.OR}|{Oper.AND}|{Oper.HAS})\s*[(](?P<args>.*)[)]\s*$"
COMPILED_LOGICAL_REGEXP = re.compile(LOGICAL_REGEXP)
COMPILED_IDENTIFIER_REGEXP = re.compile(IDENTIFIER_REGEXP)


class JsonApiPagination(BaseModel):
    number: int = 1
    size: int = 20
    total: int | None = None


class JsonApiQueryFilter(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    oper: Oper
    subfilter: tuple[JsonApiQueryFilter, ...] | JsonApiQueryFilter | None = None
    attr: str | None = None
    value: bool | str | float | int | list | None = None
    other_attr: str | None = None

    @model_validator(mode="before")
    def parse_value(cls, data: dict) -> dict:
        # On subfilter validation does nothing
        if isinstance(data, dict) and data["oper"] == Oper.ANY:
            typed_values = []
            for value in data["value"]:
                value = _to_string_or_numeric(value)
                typed_values.append(value)
            data["value"] = typed_values

        return data

    def match(self, model) -> bool:
        if self.oper == Oper.NOT:
            assert isinstance(self.subfilter, JsonApiQueryFilter)
            return not self.subfilter.match(model)
        if self.oper == Oper.AND:
            assert isinstance(self.subfilter, tuple)
            return all(f.match(model) for f in self.subfilter)
        if self.oper == Oper.OR:
            assert isinstance(self.subfilter, tuple)
            return any(f.match(model) for f in self.subfilter)
        if self.oper == Oper.HAS:
            # As JsonApiDotNetCore: has(collection) or has(collection, filter on the collection items)
            assert self.attr is not None
            collection = model.resolve_attr(self.attr) or []
            if self.subfilter is None:
                return len(collection) > 0
            assert isinstance(self.subfilter, JsonApiQueryFilter)
            if any(not isinstance(item, JsonApiBaseModel) for item in collection):
                msg = f"Filter has({self.attr}, ...) is only allowed on a collection of resources, use contains instead"
                raise FilterError(msg)
            return any(self.subfilter.match(item) for item in collection)

        # Comparison with another attribute of the model
        value = model.resolve_attr(self.other_attr) if self.other_attr else self.value
        return model.match(self.oper, self.attr, value)


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
    pagination: JsonApiPagination = Field(default_factory=lambda: JsonApiPagination())
    flatten: str | None = None

    def get_fields(self, jsonapi_type) -> set[str] | None:
        """Returns the list of fields to dump for the given JSON API type."""
        if self.fields and jsonapi_type:
            values = self.fields.get(jsonapi_type)
            if values:
                return set(values)
        return None

    def match(self, model: JsonApiBaseModel):
        """Checks if the model matches the query filters.

        Raises BadRequest if a filter cannot be applied on the model.
        """
        try:
            for filter in self.filters:
                if not filter.match(model):
                    return False
        except FilterError as e:
            raise BadRequest(str(e)) from e
        return True

    @staticmethod
    def no_content() -> Response:
        """Returns a no content response."""
        return Response(status=HTTPStatus.NO_CONTENT)

    def one(self, value: JsonApiBaseModel | Resource | dict) -> SingleResourceTopLevel:
        """Returns a single JSON:API toplevel's data."""
        if value is None:
            raise NotFound()

        included: list[Resource] = []
        meta = {
            "count": 1,
        }
        if isinstance(value, JsonApiBaseModel):
            data = value.as_resource(included, self)
        elif isinstance(value, Resource):
            data = value
        else:
            data = Resource(id=value.pop("id", ""), type=value.pop("type", ""), attributes=value)
        res = SingleResourceTopLevel(data=data, included=included, meta=meta)

        if self.flatten:
            flat_res = self._flat_resource(data, flatten_resource(data, toplevel=res, pattern=self.flatten))
            return SingleResourceTopLevel(data=flat_res, included=self._unflattened_included([value]), meta=meta)

        return res

    def one_or_none(self, value: JsonApiBaseModel | dict | None) -> SingleResourceTopLevel:
        """Returns a single JSON:API toplevel's data."""
        if value is None:
            return SingleResourceTopLevel.empty()

        return self.one(value)

    def paginate(
        self,
        values: t.Sequence[Resource | JsonApiBaseModel],
        *,
        full_list: bool = True,
        total: int | None = None,
    ) -> MultiResourcesTopLevel:
        """Returns multi JSON:API toplevel's data from a value iterable.

        :param values: List for pagination.
        :param full_list: If true, the list is fully completed.
        :param total: The pagination total number of records if not a full list.
        """
        included: list[Resource] = []
        start = (self.pagination.number - 1) * self.pagination.size
        end = start + self.pagination.size
        if full_list:
            data = values[start:end]
            has_next = end < len(values)
            total = len(data)
        else:
            if self.pagination.size < len(values):
                raise InternalServerError("The pagination size was not respected.")
            data = values
            if total is not None:
                has_next = total > self.pagination.size * self.pagination.number
            else:
                has_next = self.pagination.size == len(values)

        meta: dict[str, t.Any] = {
            "pagination": {
                "page": self.pagination.number,
                "per_page": self.pagination.size,
                "has_next": has_next,
                "has_prev": self.pagination.number > 1,
            },
        }
        if total is not None:
            meta["count"] = total

        resources: list[Resource] = [d if isinstance(d, Resource) else d.as_resource(included, self) for d in data]
        res = MultiResourcesTopLevel(data=resources, included=included, meta=meta)
        if self.flatten:
            flat_list = flatten_resource(resources, toplevel=res, pattern=self.flatten)
            flat_res = [self._flat_resource(r, d) for r, d in zip(resources, flat_list, strict=True)]
            return MultiResourcesTopLevel(data=flat_res, included=self._unflattened_included(data), meta=meta)

        return res

    @staticmethod
    def error(code: int, title: str, detail: str) -> tuple[TopLevel, int]:
        return (
            TopLevel(errors=[Error(id=str(code), title=title, detail=detail, status=str(code), code=str(code))]),
            code,
        )

    @staticmethod
    def not_found(detail: str | None = None) -> tuple[TopLevel, int]:
        error = NotFound(description=detail)
        return JsonApiQueryModel.error(error.code, error.name, error.get_description())

    @model_validator(mode="before")
    def _parse_query_args(cls, data: dict) -> dict:
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

            elif arg == "fields":
                if isinstance(value, dict):
                    fields.update(value)
                else:
                    msg = f"Wrong fields parameters: must be defined as fields[<type>]=<field1>,<field2>,...{arg}"
                    raise UnprocessableEntity(msg)
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

        # Populate pagination from request.args if not provided
        if "pagination" not in data:
            try:
                page = request.args.get("page[number]")
                size = request.args.get("page[size]")
                if page or size:
                    data["pagination"] = {
                        "number": int(page) if page else 1,
                        "size": int(size) if size else 20,
                    }
            except RuntimeError:
                pass  # No Flask context

        return data

    @field_validator("include", mode="before")
    @classmethod
    def parse_include(cls, include: set[str] | list[str] | None) -> set[str]:
        if not include:
            return set()
        values = include if isinstance(include, set) else include[0].split(",")
        return {v.strip() for v in values if v.strip()}

    @model_validator(mode="after")
    def _include_flatten(self) -> JsonApiQueryModel:
        """Adds the flattened relationships to the include set, as flattening needs the included resources."""
        self.include.update(self.flatten_paths)
        return self

    @property
    def flatten_paths(self) -> set[str]:
        """Returns the relationship paths defined in flatten, with all their prefixes.

        'order.lines.product|page?' gives 'order', 'order.lines', 'order.lines.product' and 'order.lines.page'.
        """
        paths: set[str] = set()
        if not self.flatten:
            return paths
        for pattern in self.flatten.split(","):
            *firsts, lasts = [p.strip() for p in pattern.split(".")]
            path = ""
            for rel in firsts:
                path = f"{path}.{rel.rstrip('?')}" if path else rel.rstrip("?")
                paths.add(path)
            for rel in lasts.split("|"):
                rel = rel.strip().rstrip("?")
                if rel:
                    paths.add(f"{path}.{rel}" if path else rel)
        return paths

    def _flat_resource(self, res: Resource, flat: dict) -> Resource:
        """Returns the flattened resource, keeping the relationships not merged in the attributes."""
        flattened = {p.split(".")[0] for p in self.flatten_paths}
        relationships = {k: v for k, v in (res.relationships or {}).items() if k not in flattened}
        return Resource(
            type=flat.pop("type"),
            id=flat.pop("id"),
            attributes=flat,
            relationships=relationships or None,
            links=res.links,
            meta=res.meta,
        )

    def _unflattened_included(self, values: t.Iterable[t.Any]) -> list[Resource]:
        """Returns the included resources without the flattened ones, already merged in the attributes."""
        flatten_paths = self.flatten_paths
        include = {i for i in self.include if not any(i == p or i.startswith(f"{p}.") for p in flatten_paths)}
        included: list[Resource] = []
        if include:
            query = self.model_copy(update={"include": include, "flatten": None})
            for value in values:
                if isinstance(value, JsonApiBaseModel):
                    value.as_resource(included, query)
        return included

    @property
    def query_pagination(self) -> JsonApiPagination:
        warnings.warn(
            "query_pagination is deprecated, use simply 'query.pagination' instead", DeprecationWarning, stacklevel=2
        )
        return self.pagination

    @classmethod
    def _parse_filter(cls, filter: str) -> JsonApiQueryFilter:
        if reg := COMPILED_FILTER_REGEXP.match(filter):
            oper = reg.group("oper")
            if oper:
                value = cls._parse_value(reg)
                other = reg.group("other_attr")
                if other in KEYWORD_VALUES:
                    value, other = KEYWORD_VALUES[other], None
                return JsonApiQueryFilter(oper=Oper(oper), attr=reg.group("attr"), value=value, other_attr=other)
            oper = reg.group("list_oper")
            if oper:
                values = _split_arguments(reg.group("values"))
                return JsonApiQueryFilter(oper=Oper(oper), attr=reg.group("list_attr"), value=values)

        if reg := COMPILED_LOGICAL_REGEXP.match(filter):
            oper = Oper(reg.group("oper"))
            args = _split_arguments(reg.group("args"))
            if args is not None:
                if oper == Oper.NOT and len(args) == 1:
                    return JsonApiQueryFilter(oper=oper, subfilter=cls._parse_filter(args[0]))
                if oper in (Oper.OR, Oper.AND) and len(args) >= 2:
                    return JsonApiQueryFilter(oper=oper, subfilter=tuple(cls._parse_filter(arg) for arg in args))
                if oper == Oper.HAS and len(args) in (1, 2) and COMPILED_IDENTIFIER_REGEXP.fullmatch(args[0]):
                    subfilter = cls._parse_filter(args[1]) if len(args) == 2 else None
                    return JsonApiQueryFilter(oper=oper, attr=args[0], subfilter=subfilter)
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
                value = value[1:-1].replace("''", "'")

        return value


def _split_arguments(args: str) -> list[str] | None:
    """Splits the arguments on top level commas, ignoring commas in nested parenthesis or quoted strings.

    Returns None if the parenthesis are unbalanced or a string is not closed.
    """
    parts: list[str] = []
    depth = 0
    in_quote = False
    start = 0
    for i, c in enumerate(args):
        if c == "'":
            # A doubled quote inside a string toggles twice, so it is kept as is
            in_quote = not in_quote
        elif in_quote:
            continue
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth < 0:
                return None
        elif c == "," and depth == 0:
            parts.append(args[start:i].strip())
            start = i + 1
    if depth != 0 or in_quote:
        return None
    parts.append(args[start:].strip())
    return parts


def _to_string_or_numeric(value: str) -> str | int | float:
    if value.startswith("'"):
        return value[1:-1].replace("''", "'")
    return float(value) if "." in value else int(value)
