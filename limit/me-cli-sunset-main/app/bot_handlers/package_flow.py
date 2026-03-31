from __future__ import annotations

import asyncio
from typing import Any


async def handle_package_flow(
    update: Any,
    context: Any,
    state: str,
    data: dict,
    text: str,
    deps: dict,
) -> bool:
    set_flow = deps["set_flow"]
    render_panel = deps["render_panel"]
    my_packages_menu_sync = deps["my_packages_menu_sync"]
    render_packages_page = deps["render_packages_page"]
    show_package_detail_menu = deps["show_package_detail_menu"]
    unsubscribe_package_sync = deps["unsubscribe_package_sync"]

    if state == "packages_menu":
        if text in {"pkg_refresh", "Refresh"}:
            text_out, packages = await asyncio.to_thread(my_packages_menu_sync)
            set_flow(context, "packages_menu", {"packages": packages, "page": 0})
            await render_panel(update, context, text_out)
            return True
        if text in {"pkg_detail", "Detail"}:
            packages = data.get("packages", [])
            page = int(data.get("page", 0))
            set_flow(context, "await_package_detail_pick", {"packages": packages, "page": page})
            await render_panel(update, context, render_packages_page(packages, page) + "\n\nPilih nomor paket untuk lihat detail.")
            return True
        if text in {"pkg_unsub", "Unsub"}:
            packages = data.get("packages", [])
            page = int(data.get("page", 0))
            set_flow(context, "await_package_unsub_pick", {"packages": packages, "page": page})
            await render_panel(update, context, render_packages_page(packages, page) + "\n\nPilih nomor paket untuk unsubscribe.")
            return True

    if state == "await_package_detail_pick":
        packages = data.get("packages", [])
        if not text.isdigit() or int(text) < 1 or int(text) > len(packages):
            await render_panel(update, context, "Nomor paket tidak valid.")
            return True
        pkg = packages[int(text) - 1]
        await show_package_detail_menu(
            update,
            context,
            pkg.get("quota_code", ""),
            "packages_menu",
            {"packages": packages, "page": int(data.get("page", 0))},
        )
        return True

    if state == "await_package_unsub_pick":
        packages = data.get("packages", [])
        if not text.isdigit() or int(text) < 1 or int(text) > len(packages):
            await render_panel(update, context, "Nomor paket tidak valid.")
            return True
        pkg = packages[int(text) - 1]
        set_flow(context, "await_package_unsub_confirm", {"package": pkg, "packages": packages, "page": int(data.get("page", 0))})
        await render_panel(update, context, f"Yakin unsubscribe paket: {pkg.get('name', 'N/A')}?")
        return True

    if state == "await_package_unsub_confirm":
        pkg = data.get("package", {})
        packages = data.get("packages", [])
        page = int(data.get("page", 0))
        if text in {"pkg_unsub_yes", "y", "yes", "Ya"}:
            result = await asyncio.to_thread(unsubscribe_package_sync, pkg)
            _, fresh_packages = await asyncio.to_thread(my_packages_menu_sync)
            set_flow(context, "packages_menu", {"packages": fresh_packages, "page": page})
            await render_panel(update, context, result + "\n\n" + render_packages_page(fresh_packages, page))
            return True
        if text in {"pkg_unsub_no", "n", "no", "Tidak"}:
            set_flow(context, "packages_menu", {"packages": packages, "page": page})
            await render_panel(update, context, "Unsubscribe dibatalkan.\n\n" + render_packages_page(packages, page))
            return True
        await render_panel(update, context, "Pilih Ya atau Tidak.")
        return True

    return False
