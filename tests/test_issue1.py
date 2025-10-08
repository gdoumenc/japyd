import typing as t

from japyd.jsonapi import ResourceIdentifier, TopLevel
from japyd.utils import extract_from_resource_identifier, extract_relationship

data = {
    "data": [
        {
            "type": "eshop.order.product_line",
            "id": "1sSUPPLIER:11200220-148x210-0100000-:::-:::-:::-6:6",
            "attributes": {},
            "relationships": {
                "lines": {"data": [{"id": "14880", "type": "eshop.order.production_line"}]},
                "shipping_address": {"data": {"id": "30317", "type": "eshop.user.shipping_address"}},
            },
        }
    ],
    "meta": {"count": 1, "pagination": {"page": 1, "per_page": 20, "has_next": False, "has_prev": False}},
    "included": [
        {
            "type": "eshop.order.production_line",
            "id": "14880",
            "attributes": {
                "asku": "1sSUPPLIER:11200220-148x210-0100000-:::-:::-:::-6:6",
                "product_reference": "flyers",
                "page_slug": "flyer-a5-recto",
                "quantity": 1000,
                "vsku": {"default": {"recto": {"key": "prod/compliant/gmp/14880/recto", "bucket": "neorezo-visuals"}}},
            },
            "relationships": {"line": {"data": {"id": "14880", "type": "eshop.order.line"}}},
        },
        {
            "type": "eshop.user.shipping_address",
            "id": "30317",
            "attributes": {
                "created": "2025-08-12T22:37:10.453111Z",
                "modified": "2025-08-12T22:37:10.453111Z",
                "email": "c.denis.ouvrard@hotmail.fr",
                "is_removed": False,
                "frozen": True,
                "first_name": "David",
                "last_name": "OUVRARD",
                "company": "BOULANGERIE OUVRARD",
                "address_line1": "27 rue Henri Barbusse",
                "address_line2": None,
                "postal_code": "18150",
                "city": "LA GUERCHE SUR l'AUBOIS",
                "country": "france",
                "instructions": "",
                "vat": None,
                "designation": "10013521",
                "phone": "0248748081",
            },
            "relationships": {},
        },
    ],
}


class TestIssue1:

    def test_extract_relationship(self):
        toplevel = TopLevel(**data)
        lines = extract_relationship(toplevel, "lines")
        assert isinstance(lines, list)
        assert len(lines) == 1

    def test_extract_from_resource_identifier(self):
        toplevel = TopLevel(**data)
        lines = extract_relationship(toplevel, "lines")
        assert isinstance(lines, list)
        slugs = [
            extract_from_resource_identifier(toplevel, t.cast(ResourceIdentifier, l)).attributes["page_slug"]
            for l in lines
        ]
        assert len(slugs) == 1
        assert slugs[0] == "flyer-a5-recto"
