from __future__ import annotations

from typing import Any

from app.bot_handlers.ui_primitives import build_error_with_next


async def handle_payment_flow(
    update: Any,
    context: Any,
    state: str,
    data: dict,
    text: str,
    deps: dict,
) -> bool:
    set_flow = deps["set_flow"]
    render_panel = deps["render_panel"]
    run_payment_action = deps["run_payment_action"]
    pay_balance_sync = deps["pay_balance_sync"]
    pay_qris_sync = deps["pay_qris_sync"]
    pay_decoy_balance_sync = deps["pay_decoy_balance_sync"]
    pay_decoy_qris_sync = deps["pay_decoy_qris_sync"]
    pay_decoy_qris_manual_sync = deps["pay_decoy_qris_manual_sync"]
    pay_ewallet_sync = deps["pay_ewallet_sync"]
    start_balance_n_progress_task = deps["start_balance_n_progress_task"]

    if state == "package_detail_menu":
        payment_ctx = data.get("payment_ctx", {})
        back_state = data.get("back_state", "home")
        back_data = data.get("back_data", {})

        if text == "pkg_back_list":
            set_flow(context, back_state, back_data)
            await render_panel(update, context, "Kembali ke daftar sebelumnya.")
            return True

        if text == "pay_balance":
            result = await run_payment_action(
                update,
                context,
                "Memproses pembayaran Pulsa...",
                lambda: pay_balance_sync(payment_ctx),
            )
            set_flow(context, "package_detail_menu", data)
            await render_panel(update, context, result + "\n\nPilih metode pembayaran lain atau kembali.")
            return True

        if text == "pay_qris":
            result = await run_payment_action(
                update,
                context,
                "Memproses pembayaran QRIS...",
                lambda: pay_qris_sync(payment_ctx),
            )
            set_flow(context, "package_detail_menu", data)
            await render_panel(update, context, result + "\n\nPilih metode pembayaran lain atau kembali.")
            return True

        if text == "pay_decoy_balance":
            result = await run_payment_action(
                update,
                context,
                "Memproses Pulsa+Decoy...",
                lambda: pay_decoy_balance_sync(payment_ctx, False),
            )
            set_flow(context, "package_detail_menu", data)
            await render_panel(update, context, result + "\n\nPilih metode pembayaran lain atau kembali.")
            return True

        if text == "pay_decoy_balance_v2":
            result = await run_payment_action(
                update,
                context,
                "Memproses Pulsa+Decoy V2...",
                lambda: pay_decoy_balance_sync(payment_ctx, True),
            )
            set_flow(context, "package_detail_menu", data)
            await render_panel(update, context, result + "\n\nPilih metode pembayaran lain atau kembali.")
            return True

        if text == "pay_decoy_qris":
            result = await run_payment_action(
                update,
                context,
                "Memproses QRIS+Decoy...",
                lambda: pay_decoy_qris_sync(payment_ctx, "qris"),
            )
            set_flow(context, "package_detail_menu", data)
            await render_panel(update, context, result + "\n\nPilih metode pembayaran lain atau kembali.")
            return True

        if text == "pay_decoy_qris0":
            result = await run_payment_action(
                update,
                context,
                "Memproses QRIS+Decoy V2...",
                lambda: pay_decoy_qris_sync(payment_ctx, "qris0"),
            )
            set_flow(context, "package_detail_menu", data)
            await render_panel(update, context, result + "\n\nPilih metode pembayaran lain atau kembali.")
            return True

        if text == "pay_decoy_qris_manual":
            set_flow(
                context,
                "await_decoy_qris_manual_amount",
                {
                    "payment_ctx": payment_ctx,
                    "decoy_type": "qris",
                    "back_state": back_state,
                    "back_data": back_data,
                },
            )
            await render_panel(update, context, "Kirim amount manual untuk QRIS+Decoy (boleh 0 untuk malformed).")
            return True

        if text == "pay_decoy_qris0_manual":
            set_flow(
                context,
                "await_decoy_qris_manual_amount",
                {
                    "payment_ctx": payment_ctx,
                    "decoy_type": "qris0",
                    "back_state": back_state,
                    "back_data": back_data,
                },
            )
            await render_panel(update, context, "Kirim amount manual untuk QRIS+Decoy V2 (boleh 0 untuk malformed).")
            return True

        if text == "pay_ewallet":
            set_flow(
                context,
                "await_ewallet_method",
                {
                    "payment_ctx": payment_ctx,
                    "back_state": back_state,
                    "back_data": back_data,
                },
            )
            await render_panel(update, context, "Pilih metode e-wallet.")
            return True

        if text == "pay_balance_n":
            set_flow(
                context,
                "await_balance_n_count",
                {
                    "payment_ctx": payment_ctx,
                    "back_state": back_state,
                    "back_data": back_data,
                },
            )
            await render_panel(update, context, "Kirim jumlah N untuk Pulsa N Kali (contoh: 3).")
            return True

    if state == "await_ewallet_method":
        payment_ctx = data.get("payment_ctx", {})
        back_state = data.get("back_state", "home")
        back_data = data.get("back_data", {})

        if text == "pkg_back_detail":
            set_flow(
                context,
                "package_detail_menu",
                {
                    "payment_ctx": payment_ctx,
                    "back_state": back_state,
                    "back_data": back_data,
                },
            )
            await render_panel(update, context, "Kembali ke menu pembayaran paket.")
            return True

        if text in {"ew_shopeepay", "ew_gopay"}:
            method = "SHOPEEPAY" if text == "ew_shopeepay" else "GOPAY"
            result = await run_payment_action(
                update,
                context,
                f"Memproses pembayaran {method}...",
                lambda: pay_ewallet_sync(payment_ctx, method, ""),
            )
            set_flow(
                context,
                "package_detail_menu",
                {
                    "payment_ctx": payment_ctx,
                    "back_state": back_state,
                    "back_data": back_data,
                },
            )
            await render_panel(update, context, result + "\n\nPilih metode pembayaran lain atau kembali.")
            return True

        if text in {"ew_dana", "ew_ovo"}:
            method = "DANA" if text == "ew_dana" else "OVO"
            set_flow(
                context,
                "await_ewallet_number",
                {
                    "payment_ctx": payment_ctx,
                    "method": method,
                    "back_state": back_state,
                    "back_data": back_data,
                },
            )
            await render_panel(update, context, f"Kirim nomor {method} (format 08xxxx).")
            return True

    if state == "await_ewallet_number":
        payment_ctx = data.get("payment_ctx", {})
        method = data.get("method", "")
        back_state = data.get("back_state", "home")
        back_data = data.get("back_data", {})

        if not text.startswith("08") or not text.isdigit() or len(text) < 10 or len(text) > 13:
            await render_panel(update, context, build_error_with_next("Nomor e-wallet tidak valid.", "Kirim ulang dengan format 08xxxx."))
            return True

        result = await run_payment_action(
            update,
            context,
            f"Memproses pembayaran {method}...",
            lambda: pay_ewallet_sync(payment_ctx, method, text),
        )
        set_flow(
            context,
            "package_detail_menu",
            {
                "payment_ctx": payment_ctx,
                "back_state": back_state,
                "back_data": back_data,
            },
        )
        await render_panel(update, context, result + "\n\nPilih metode pembayaran lain atau kembali.")
        return True

    if state == "await_decoy_qris_manual_amount":
        payment_ctx = data.get("payment_ctx", {})
        decoy_type = data.get("decoy_type", "qris")
        back_state = data.get("back_state", "home")
        back_data = data.get("back_data", {})

        if not text.isdigit():
            await render_panel(update, context, "Amount harus angka. Contoh: 0 atau 1234")
            return True

        amount = int(text)
        result = await run_payment_action(
            update,
            context,
            "Memproses QRIS+Decoy manual...",
            lambda: pay_decoy_qris_manual_sync(payment_ctx, decoy_type, amount),
        )
        set_flow(
            context,
            "package_detail_menu",
            {
                "payment_ctx": payment_ctx,
                "back_state": back_state,
                "back_data": back_data,
            },
        )
        await render_panel(update, context, result + "\n\nPilih metode pembayaran lain atau kembali.")
        return True

    if state == "await_balance_n_count":
        payment_ctx = data.get("payment_ctx", {})
        back_state = data.get("back_state", "home")
        back_data = data.get("back_data", {})

        if not text.isdigit():
            await render_panel(update, context, build_error_with_next("Jumlah N harus angka.", "Contoh input: 3"))
            return True

        count = int(text)
        if count <= 0 or count > 50:
            await render_panel(update, context, build_error_with_next("Jumlah N harus di antara 1 sampai 50.", "Kirim ulang angka 1-50."))
            return True

        set_flow(
            context,
            "await_balance_n_delay",
            {
                "payment_ctx": payment_ctx,
                "back_state": back_state,
                "back_data": back_data,
                "count": count,
            },
        )
        await render_panel(update, context, "Kirim delay per iterasi dalam detik (contoh: 0 atau 2).")
        return True

    if state == "await_balance_n_delay":
        payment_ctx = data.get("payment_ctx", {})
        back_state = data.get("back_state", "home")
        back_data = data.get("back_data", {})
        count = int(data.get("count", 0))

        if not text.isdigit():
            await render_panel(update, context, build_error_with_next("Delay harus angka detik.", "Contoh input: 0 atau 2"))
            return True

        delay_sec = int(text)
        if delay_sec < 0 or delay_sec > 300:
            await render_panel(update, context, build_error_with_next("Delay harus di antara 0 sampai 300 detik.", "Kirim ulang angka 0-300."))
            return True

        set_flow(
            context,
            "await_balance_n_decoy",
            {
                "payment_ctx": payment_ctx,
                "back_state": back_state,
                "back_data": back_data,
                "count": count,
                "delay_sec": delay_sec,
            },
        )
        await render_panel(update, context, "Gunakan decoy? Pilih Ya/Tidak.")
        return True

    if state == "await_balance_n_decoy":
        payment_ctx = data.get("payment_ctx", {})
        back_state = data.get("back_state", "home")
        back_data = data.get("back_data", {})
        count = int(data.get("count", 0))
        delay_sec = int(data.get("delay_sec", 0))

        use_decoy = None
        if text in {"bal_n_decoy_yes", "y", "yes", "Ya"}:
            use_decoy = True
        elif text in {"bal_n_decoy_no", "n", "no", "Tidak"}:
            use_decoy = False
        else:
            await render_panel(update, context, build_error_with_next("Pilihan decoy tidak valid.", "Tekan tombol Ya atau Tidak."))
            return True

        set_flow(
            context,
            "await_balance_n_running",
            {
                "payment_ctx": payment_ctx,
                "back_state": back_state,
                "back_data": back_data,
            },
        )
        result = start_balance_n_progress_task(
            update,
            context,
            payment_ctx,
            count,
            delay_sec,
            bool(use_decoy),
            back_state,
            back_data,
        )
        await render_panel(update, context, result)
        return True

    return False
