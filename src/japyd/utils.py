from .jsonapi import Resource


def flatten_resource(res: Resource | dict, *, more: dict | None = None) -> dict:
    """Returns the resource attributes with the 'id' added. Can add more data if needed."""
    more = more or {}
    if isinstance(res, Resource):
        return {"type": res.type, "id": res.id, **res.attributes, **more}
    return {"type": res["type"], "id": res["id"], **res["attributes"], **more}
