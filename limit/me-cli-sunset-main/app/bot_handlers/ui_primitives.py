from __future__ import annotations


def build_panel(title: str, lines: list[str], footer: str = "") -> str:
    parts = [title]
    parts.extend(lines)
    if footer:
        parts.append(footer)
    return "\n".join(parts)


def build_error_with_next(message: str, next_step: str) -> str:
    return build_panel("Gagal", [message, f"Langkah berikutnya: {next_step}"])


def build_home_guest_panel() -> str:
    return build_panel(
        "HOME PANEL - BELUM LOGIN",
        [
            "Silakan buka 1 👤 Akun untuk login/ganti akun.",
            "Mode Native aktif. Pilih menu dari tombol di bawah.",
        ],
    )


def build_home_compact_panel(number: str, subs_type: str, balance_value: str, expired_text: str, points: str, tier: str) -> str:
    return build_panel(
        "HOME PANEL - COMPACT",
        [
            f"Nomor: {number} | Type: {subs_type}",
            f"Pulsa: Rp {balance_value} | Aktif sampai: {expired_text}",
            f"Points: {points} | Tier: {tier}",
        ],
        "Pilih menu dari tombol di bawah.",
    )


def build_home_fancy_panel(number: str, subs_type: str, balance_value: str, expired_text: str, points: str, tier: str) -> str:
    return build_panel(
        "✨ HOME PANEL - FANCY",
        [
            f"📱 Nomor: {number}",
            f"🏷️ Type: {subs_type}",
            f"💰 Pulsa: Rp {balance_value}",
            f"📅 Aktif sampai: {expired_text}",
            f"🎯 Points: {points} | 👑 Tier: {tier}",
        ],
        "Siap dipakai. Pilih menu dari tombol di bawah.",
    )


def build_progress_panel(mode: str, done: int, total: int, status: str, ok: int, fail: int, delay_sec: int, can_cancel: bool = True) -> str:
    total_safe = max(1, total)
    width = 20
    filled = int((done / total_safe) * width)
    filled = max(0, min(width, filled))
    bar = "[" + ("#" * filled) + ("-" * (width - filled)) + "]"

    lines = [
        f"Progress Pulsa N Kali ({mode})",
        f"{bar} {done}/{total}",
        f"Status: {status}",
        f"Berhasil: {ok} | Gagal: {fail} | Delay: {delay_sec}s",
    ]
    if can_cancel:
        lines.append("Tekan tombol Batal Progress untuk menghentikan.")

    return "\n".join(lines)


def build_paged_list_panel(title: str, lines: list[str], page: int, max_page: int) -> str:
    out = [f"{title} (hal {page + 1}/{max_page + 1}):"]
    out.extend(lines)
    out.append("Gunakan tombol angka untuk memilih item.")
    out.append("Navigasi: Prev/Next, p:<halaman>, atau hal:<halaman> (contoh: p:3).")
    return "\n".join(out)


def build_package_detail_panel(
    package_name: str,
    price: str,
    validity: str,
    point: str,
    payment_for: str,
    option_code: str,
    benefits: list[str],
) -> str:
    lines = [
        f"Nama: {package_name}",
        f"Harga: Rp {price}",
        f"Masa aktif: {validity}",
        f"Point: {point}",
        f"Payment For: {payment_for}",
        f"Option Code: {option_code}",
        "Benefits:",
    ]
    if benefits:
        lines.extend(benefits)
    else:
        lines.append("- N/A")
    return build_panel("Detail paket:", lines)


def build_first_use_onboarding_panel() -> str:
    return build_panel(
        "🚀 Onboarding Singkat (3 Langkah)",
        [
            "1) Gunakan 1 👤 Akun untuk login atau ganti akun aktif.",
            "2) Buka 2 📦 Paket untuk lihat detail dan pilih metode pembayaran.",
            "3) Saat berada di daftar panjang, gunakan Prev/Next atau p:<halaman>/hal:<halaman>.",
        ],
        "Tip: Tekan ❓ Bantuan kapan saja untuk panduan kontekstual.",
    )


def build_context_help_panel(state: str, guidance: str, shortcuts: list[str]) -> str:
    lines = [f"Konteks saat ini: {state}", guidance]
    if shortcuts:
        lines.append("Shortcut cepat:")
        lines.extend([f"- {item}" for item in shortcuts])
    return build_panel("❓ Bantuan Kontekstual", lines)
