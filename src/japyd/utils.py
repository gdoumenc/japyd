import typing as t

from .jsonapi import Resource


def flatten_resource(res: Resource | dict, *, more: dict | None = None) -> dict:
    """Returns the resource attributes with the 'id' added. Can add more data if needed."""
    more = more or {}
    if isinstance(res, Resource):
        return {"type": res.type, "id": res.id, **res.attributes, **more}
    return {"type": res["type"], "id": res["id"], **res["attributes"], **more}


def to_bool(val: t.Any) -> bool:
    if isinstance(val, str):
        return val.lower() in ["true", "1", "yes", "y"]
    return bool(val)


def to_string_or_numeric(value: str) -> str | int | float:
    if value.startswith("'"):
        return value.strip("'")
    return float(value) if "." in value else int(value)
