"""Check acceptance-data consistency, not application correctness."""

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parent
D = Decimal


def money(value):
    return value.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def main():
    fixtures = json.loads((ROOT / "fixtures.json").read_text())
    suite = json.loads((ROOT / "golden-cases.json").read_text())
    products = {p["sku"]: p for p in fixtures["products"]}
    assert len(products) == len(fixtures["products"]) == 6
    assert fixtures["synthetic"] and suite["synthetic"]
    cases = suite["cases"]
    assert len(cases) == 25
    assert len({c["id"] for c in cases}) == len(cases)
    monetary_cases = 0
    for case in cases:
        expected = case["expected"]
        assert case["enquiry"] and expected["outcome"]
        for sku in case.get("overrides", {}):
            assert sku in products, (case["id"], sku)
        for line in case.get("lines", []):
            assert line["sku"] in products, case["id"]
        for sku in expected.get("candidate_skus", []):
            assert sku in products, case["id"]
        if "subtotal" not in expected:
            continue
        monetary_cases += 1
        units, amounts, roles = [], [], set()
        for line in case["lines"]:
            sku = line["sku"]
            product = {**products[sku], **case.get("overrides", {}).get(sku, {})}
            qty = line["qty"]
            assert product["active"] and qty >= product["moq"]
            assert qty % product["pack"] == 0
            source = D(product.get("contract", product.get("gold", product["list"])))
            extra = D(line.get("discretionary_percent", "0"))
            assert D(0) <= extra <= D(100)
            volume = D("0.03") if product["uom"] == "EA" and qty >= 50 else D(0)
            if "contract" in product:
                assert extra == 0
                net = source
            else:
                net = money(money(source * (1 - volume)) * (1 - extra / 100))
            assert net > 0
            discount = 100 * (1 - net / source)
            margin = 100 * (net - D(product["cost"])) / net
            if discount > 12 or margin < 15:
                roles.add("Finance Approver")
            if 5 < discount <= 12 or 15 <= margin < 20:
                roles.add("Sales Manager")
            units.append(f"{net:.2f}")
            amounts.append(net * qty)
            if "margin_display_percent" in expected:
                assert f"{money(margin):.2f}" == expected["margin_display_percent"]
        subtotal = sum(amounts, D(0))
        tax = money(subtotal * D("0.09"))
        total = subtotal + tax
        if total > 100000:
            roles.update(["Sales Manager", "Finance Approver"])
        assert units == expected["net_units"], case["id"]
        for field, value in [("subtotal", subtotal), ("tax", tax), ("total", total)]:
            assert f"{value:.2f}" == expected[field], (case["id"], field, value)
        assert roles == set(expected["approvers"]), case["id"]
        assert expected["outcome"] == ("approval" if roles else "draft"), case["id"]
    print(f"25 fixture records validated; {monetary_cases} monetary expectations recomputed.")
    print("Application behavior, security and model evaluation have NOT been tested.")


if __name__ == "__main__":
    main()
