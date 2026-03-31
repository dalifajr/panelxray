from __future__ import annotations

import asyncio
from typing import Any


async def handle_catalog_flow(
    update: Any,
    context: Any,
    state: str,
    data: dict,
    text: str,
    deps: dict,
) -> bool:
    set_flow = deps["set_flow"]
    render_panel = deps["render_panel"]
    resolve_hot_option_code_sync = deps["resolve_hot_option_code_sync"]
    show_package_detail_menu = deps["show_package_detail_menu"]
    family_list_text_sync = deps["family_list_text_sync"]

    if state in {"hot_select", "hot2_select"} and text.isdigit():
        hot_packages = data.get("hot_packages", [])
        idx = int(text) - 1
        if idx < 0 or idx >= len(hot_packages):
            await render_panel(update, context, "Nomor HOT tidak valid.")
            return True
        option_code = await asyncio.to_thread(resolve_hot_option_code_sync, hot_packages[idx])
        if not option_code:
            await render_panel(update, context, "Gagal menemukan option code HOT.")
            return True
        await show_package_detail_menu(update, context, option_code, state, data)
        return True

    if state == "await_store_segments_pick":
        items = data.get("items", [])
        if not text.isdigit() or int(text) < 1 or int(text) > len(items):
            await render_panel(update, context, "Nomor item tidak valid.")
            return True
        item = items[int(text) - 1]
        action_type = item.get("action_type", "")
        action_param = item.get("action_param", "")
        if action_type == "PDP":
            await show_package_detail_menu(
                update,
                context,
                action_param,
                "await_store_segments_pick",
                {"items": items, "page": int(data.get("page", 0))},
            )
        elif action_type == "PLP":
            fam = await asyncio.to_thread(family_list_text_sync, action_param)
            set_flow(context, "await_store_segments_pick", {"items": items, "page": int(data.get("page", 0))})
            await render_panel(update, context, fam + "\n\nPilih item Segments lain, atau Home.")
        else:
            set_flow(context, "await_store_segments_pick", {"items": items, "page": int(data.get("page", 0))})
            await render_panel(update, context, f"Action belum didukung: {action_type} | {action_param}")
        return True

    if state == "await_store_family_pick":
        items = data.get("items", [])
        if not text.isdigit() or int(text) < 1 or int(text) > len(items):
            await render_panel(update, context, "Nomor item tidak valid.")
            return True
        family_code = items[int(text) - 1].get("family_code", "")
        fam = await asyncio.to_thread(family_list_text_sync, family_code)
        set_flow(context, "await_store_family_pick", {"items": items, "page": int(data.get("page", 0))})
        await render_panel(update, context, fam + "\n\nPilih family lain, atau Home.")
        return True

    if state == "await_store_package_pick":
        items = data.get("items", [])
        if not text.isdigit() or int(text) < 1 or int(text) > len(items):
            await render_panel(update, context, "Nomor item tidak valid.")
            return True
        item = items[int(text) - 1]
        action_type = item.get("action_type", "")
        action_param = item.get("action_param", "")
        if action_type == "PDP":
            await show_package_detail_menu(
                update,
                context,
                action_param,
                "await_store_package_pick",
                {"items": items, "page": int(data.get("page", 0))},
            )
        elif action_type == "PLP":
            fam = await asyncio.to_thread(family_list_text_sync, action_param)
            set_flow(context, "await_store_package_pick", {"items": items, "page": int(data.get("page", 0))})
            await render_panel(update, context, fam + "\n\nPilih paket Store lain, atau Home.")
        else:
            set_flow(context, "await_store_package_pick", {"items": items, "page": int(data.get("page", 0))})
            await render_panel(update, context, f"Action belum didukung: {action_type} | {action_param}")
        return True

    if state == "await_redeem_pick":
        items = data.get("items", [])
        if not text.isdigit() or int(text) < 1 or int(text) > len(items):
            await render_panel(update, context, "Nomor item tidak valid.")
            return True
        item = items[int(text) - 1]
        action_type = item.get("action_type", "")
        action_param = item.get("action_param", "")
        if action_type == "PDP":
            await show_package_detail_menu(
                update,
                context,
                action_param,
                "await_redeem_pick",
                {"items": items, "page": int(data.get("page", 0))},
            )
        elif action_type == "PLP":
            fam = await asyncio.to_thread(family_list_text_sync, action_param)
            set_flow(context, "await_redeem_pick", {"items": items, "page": int(data.get("page", 0))})
            await render_panel(update, context, fam + "\n\nPilih redeem lain, atau Home.")
        else:
            set_flow(context, "await_redeem_pick", {"items": items, "page": int(data.get("page", 0))})
            await render_panel(update, context, f"Action belum didukung: {action_type} | {action_param}")
        return True

    if state == "await_circle_bonus_pick":
        items = data.get("items", [])
        if not text.isdigit() or int(text) < 1 or int(text) > len(items):
            await render_panel(update, context, "Nomor bonus tidak valid.")
            return True
        item = items[int(text) - 1]
        set_flow(context, "await_circle_bonus_pick", {"items": items, "page": int(data.get("page", 0))})
        if item.get("action_type") == "PDP":
            await show_package_detail_menu(
                update,
                context,
                item.get("action_param", ""),
                "await_circle_bonus_pick",
                {"items": items, "page": int(data.get("page", 0))},
            )
        elif item.get("action_type") == "PLP":
            fam = await asyncio.to_thread(family_list_text_sync, item.get("action_param", ""))
            await render_panel(update, context, fam + "\n\nPilih bonus lain, atau Home.")
        else:
            await render_panel(update, context, f"Action belum didukung: {item.get('action_type')} | {item.get('action_param')}")
        return True

    if state == "await_family_option_pick":
        items = data.get("items", [])
        if not text.isdigit() or int(text) < 1 or int(text) > len(items):
            await render_panel(update, context, "Nomor package family tidak valid.")
            return True
        item = items[int(text) - 1]
        option_code = item.get("option_code", "")
        if not option_code:
            await render_panel(update, context, "Option code package tidak ditemukan.")
            return True
        await show_package_detail_menu(
            update,
            context,
            option_code,
            "await_family_option_pick",
            {"items": items, "page": int(data.get("page", 0))},
        )
        return True

    return False
