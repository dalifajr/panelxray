from __future__ import annotations

from app.bot_handlers.ui_primitives import build_paged_list_panel


def _render_page(title: str, lines: list[str], page: int, page_size: int = 10) -> str:
    total = len(lines)
    if total == 0:
        return f"{title}: kosong."

    max_page = max(0, (total - 1) // page_size)
    page = max(0, min(page, max_page))
    start = page * page_size
    end = min(total, start + page_size)

    out_lines: list[str] = []
    for idx in range(start, end):
        out_lines.append(f"{idx + 1}. {lines[idx]}")
    return build_paged_list_panel(title, out_lines, page, max_page)


def render_hot_page(hot_packages: list[dict], page: int, page_size: int = 10) -> str:
    lines: list[str] = []
    for pkg in hot_packages:
        lines.append(
            f"{pkg.get('family_name', '')} - {pkg.get('variant_name', '')} - {pkg.get('option_name', '')}"
        )
    return _render_page("Daftar HOT", lines, page, page_size)


def render_items_page(title: str, items: list[dict], page: int, page_size: int = 10) -> str:
    lines = [str(item.get("label", "N/A")) for item in items]
    return _render_page(title, lines, page, page_size)
