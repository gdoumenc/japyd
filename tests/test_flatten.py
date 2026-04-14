from japyd import Resource, TopLevel, flatten_resource, extract_relationship

BODY = {
    "included": [
        {
            "type": "billing.invoice.odoo_config",
            "id": "22_2020-12-08 15:59:29",
            "attributes": {
                "start_date": "2020-12-08T15:59:29",
            },
            "relationships": {},
            "links": None,
            "meta": None,
        },
        {
            "type": "auth.tenant.tenant",
            "id": "tenant",
            "attributes": {
                "ref": "tenant",
                "name": "tenant",
                "host": "tenant",
            },
            "relationships": {
                "old_plans": {"data": [], "links": None, "meta": None},
            },
            "links": None,
            "meta": None,
        },
        {
            "type": "eshop.user.login",
            "id": "1058",
            "attributes": {
                "created": "2026-04-10T09:09:15.430478Z",
                "modified": "2026-04-10T09:09:15.430478Z",
                "email": "test@test.fr",
            },
            "relationships": {},
            "links": None,
            "meta": None,
        },
        {
            "type": "eshop.user.billing",
            "id": "1068",
            "attributes": {
                "created": "2026-04-10T09:09:15.430366Z",
                "modified": "2026-04-10T09:09:15.430366Z",
                "email": "test@test.fr",
            },
            "relationships": {
                "login": {"data": {"type": "eshop.user.login", "id": "1058"}, "links": None, "meta": None}
            },
            "links": None,
            "meta": None,
        },
        {
            "type": "eshop.user.shipping_address",
            "id": "1937",
            "attributes": {
                "designation": "Livraison",
            },
            "relationships": {},
            "links": None,
            "meta": None,
        },
        {
            "type": "eshop.catalog.product",
            "id": "3970",
            "attributes": {"reference": "Produit livré", "product_type": None},
            "relationships": {},
            "links": None,
            "meta": None,
        },
        {
            "type": "eshop.catalog.product_page",
            "id": "3963",
            "attributes": {
                "slug": "mon_produit",
                "product": "PRODUIT123",
            },
            "relationships": {},
            "links": None,
            "meta": None,
        },
        {
            "type": "eshop.order.line",
            "id": "3817",
            "attributes": {
                "quantity": 1,
            },
            "relationships": {
                "billing_addr": {
                    "data": {"type": "eshop.user.billing_address", "id": "1936", "meta": None},
                    "links": None,
                    "meta": None,
                },
                "shipping_addr": {
                    "data": {"type": "eshop.user.shipping_address", "id": "1937", "meta": None},
                    "links": None,
                    "meta": None,
                },
                "product": {
                    "data": {"type": "eshop.catalog.product", "id": "3970", "meta": None},
                    "links": None,
                    "meta": None,
                },
                "product_page": {
                    "data": {"type": "eshop.catalog.product_page", "id": "3963", "meta": None},
                    "links": None,
                    "meta": None,
                },
            },
            "links": None,
            "meta": None,
        },
        {
            "type": "eshop.catalog.product",
            "id": "3969",
            "attributes": {"reference": "PRODUIT123", "product_type": None},
            "relationships": {},
            "links": None,
            "meta": None,
        },
        {
            "type": "eshop.catalog.product_page",
            "id": "3962",
            "attributes": {
                "slug": "autre_produit",
                "product": None,
            },
            "relationships": {},
            "links": None,
            "meta": None,
        },
        {
            "type": "eshop.order.line",
            "id": "3816",
            "attributes": {
                "quantity": 6,
            },
            "relationships": {
                "billing_addr": {
                    "data": {"type": "eshop.user.billing_address", "id": "1936", "meta": None},
                    "links": None,
                    "meta": None,
                },
                "shipping_addr": {
                    "data": {"type": "eshop.user.shipping_address", "id": "1937", "meta": None},
                    "links": None,
                    "meta": None,
                },
                "product": {
                    "data": {"type": "eshop.catalog.product", "id": "3969", "meta": None},
                    "links": None,
                    "meta": None,
                },
                "product_page": {
                    "data": {"type": "eshop.catalog.product_page", "id": "3962", "meta": None},
                    "links": None,
                    "meta": None,
                },
            },
            "links": None,
            "meta": None,
        },
        {
            "type": "eshop.order.order",
            "id": "916",
            "attributes": {
                "created": "2026-04-10T09:09:15.567734Z",
            },
            "relationships": {
                "frozen_login": {
                    "data": {"type": "eshop.user.login", "id": "1058", "meta": None},
                    "links": None,
                    "meta": None,
                },
                "frozen_billing": {
                    "data": {"type": "eshop.user.billing", "id": "1068", "meta": None},
                    "links": None,
                    "meta": None,
                },
                "lines": {
                    "data": [
                        {"type": "eshop.order.line", "id": "3817", "meta": None},
                        {"type": "eshop.order.line", "id": "3816", "meta": None},
                    ],
                    "links": None,
                    "meta": None,
                },
            },
            "links": None,
            "meta": None,
        },
        {
            "type": "eshop.user.billing_address",
            "id": "1936",
            "attributes": {
                "designation": "Facturation",
            },
            "relationships": {"billing_user": {"data": {"type": "eshop.user.billing", "id": "1068"}, "meta": None}},
            "links": None,
            "meta": None,
        },
    ],
    "meta": {"count": 1},
    "data": {
        "type": "eshop.order.billing_element",
        "id": "ID",
        "attributes": {
            "supplier": "supplier",
        },
        "relationships": {
            "tenant": {
                "data": {"type": "auth.tenant.tenant", "id": "tenant", "meta": None},
                "links": None,
                "meta": None,
            },
            "order": {"data": {"type": "eshop.order.order", "id": "916", "meta": None}, "links": None, "meta": None},
            "billing_addr": {
                "data": {"type": "eshop.user.billing_address", "id": "1936", "meta": None},
                "links": None,
                "meta": None,
            },
        },
        "links": None,
        "meta": None,
    },
}


class TestFlatten:

    def test_flatten(self):
        toplevel = TopLevel.model_validate(BODY)
        assert toplevel is not None
        assert isinstance(toplevel.data, Resource)

        data = flatten_resource(toplevel.data)
        assert data is not None
        assert isinstance(data, dict)
        assert data["type"] == "eshop.order.billing_element"
        assert data["id"] == "ID"
        assert data["supplier"] == "supplier"

        order_data = extract_relationship(toplevel, "order")
        assert order_data is not None
        assert isinstance(order_data, Resource)
        assert order_data.type == "eshop.order.order"
        assert order_data.id == "916"
        assert order_data.attributes["created"] == "2026-04-10T09:09:15.567734Z"

        data = flatten_resource(toplevel.data, toplevel=toplevel, pattern="order")
        assert data is not None
        assert isinstance(data, dict)
        assert data["type"] == "eshop.order.billing_element"
        assert "order" in data
        assert data["order"]["id"] == "916"
        assert data["order"]["created"] == "2026-04-10T09:09:15.567734Z"

        data = flatten_resource(toplevel.data, toplevel=toplevel, pattern="order.frozen_login")
        assert "order" in data
        assert "frozen_login" in data["order"]
        assert data["order"]["frozen_login"]["type"] == "eshop.user.login"
        assert data["order"]["frozen_login"]["id"] == "1058"
        assert data["order"]["frozen_login"]["email"] == "test@test.fr"

        data = flatten_resource(toplevel.data, toplevel=toplevel, pattern="order.lines")
        assert "lines" in data["order"]
        lines = data["order"]["lines"]
        assert isinstance(lines, list)
        assert len(lines) == 2
        line1 = lines[0]
        assert isinstance(line1, dict)
        assert line1["type"] == "eshop.order.line"
        assert line1["id"] == "3817"
        assert line1["quantity"] == 1

        data = flatten_resource(toplevel.data, toplevel=toplevel, pattern="order.lines.product")
        assert "lines" in data["order"]
        lines = data["order"]["lines"]
        line1 = lines[0]
        assert "product" in line1
        product1 = line1["product"]
        assert isinstance(product1, dict)
        assert product1["type"] == "eshop.catalog.product"
        assert product1["id"] == "3970"
        assert product1["reference"] == "Produit livré"
        line2 = lines[1]
        assert "product" in line2
        product2 = line2["product"]
        assert isinstance(product2, dict)
        assert product2["id"] == "3969"
        assert product2["reference"] == "PRODUIT123"

        data = flatten_resource(toplevel.data, toplevel=toplevel, pattern="order.lines.product|product_page")
        assert "lines" in data["order"]
        lines = data["order"]["lines"]
        line1 = lines[0]
        assert "product" in line1
        product1 = line1["product"]
        assert isinstance(product1, dict)
        assert product1["reference"] == "Produit livré"
        page1 = line1["product_page"]
        assert isinstance(page1, dict)
        assert page1["slug"] == "mon_produit"
        line2 = lines[1]
        assert "product" in line2
        product2 = line2["product"]
        assert isinstance(product2, dict)
        assert product2["reference"] == "PRODUIT123"
        page2 = line2["product_page"]
        assert isinstance(page2, dict)
        assert page2["slug"] == "autre_produit"
