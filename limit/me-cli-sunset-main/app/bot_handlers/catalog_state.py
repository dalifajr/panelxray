from __future__ import annotations

from app.bot_handlers.catalog_handler import render_hot_page, render_items_page


def render_catalog_state_page(state: str, data: dict) -> str | None:
    page = int(data.get("page", 0))

    if state in {"hot_select", "hot2_select"}:
        return render_hot_page(data.get("hot_packages", []), page, 10)

    if state == "await_store_segments_pick":
        return render_items_page("Store Segments", data.get("items", []), page, 10)

    if state == "await_store_family_pick":
        return render_items_page("Store Family List", data.get("items", []), page, 10)

    if state == "await_store_package_pick":
        return render_items_page("Store Packages", data.get("items", []), page, 10)

    if state == "await_redeem_pick":
        return render_items_page("Redeemables", data.get("items", []), page, 10)

    if state == "await_circle_bonus_pick":
        return render_items_page("Bonus Circle", data.get("items", []), page, 10)

    if state == "await_family_option_pick":
        return render_items_page("Family Packages", data.get("items", []), page, 10)

    return None
