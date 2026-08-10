import json
from pathlib import Path

from japyd import Resource, TopLevel, flatten_resource, extract_relationship

BODY = json.loads((Path(__file__).parent / "_flatten_data.json").read_text())


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

        data = flatten_resource(toplevel.data, toplevel=toplevel, pattern="order|tenant")
        assert data is not None
        assert isinstance(data, dict)
        assert "order" in data
        assert data["order"]["id"] == "916"
        assert "tenant" in data
        assert data["tenant"]["id"] == "tenant"

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

        data = flatten_resource(
            toplevel.data, toplevel=toplevel, pattern="order|tenant,order.lines.product|product_page"
        )
        assert data is not None
        assert isinstance(data, dict)
        assert "order" in data
        assert data["order"]["id"] == "916"
        assert data["order"]["lines"][0]["id"] == "3817"
        assert data["order"]["lines"][0]["product"]["id"] == "3970"
        assert data["order"]["lines"][1]["product_page"]["slug"] == "autre_produit"
        assert "tenant" in data
        assert data["tenant"]["id"] == "tenant"
