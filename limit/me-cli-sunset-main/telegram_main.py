import asyncio
import base64
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import cast

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

from app.client.ciam import get_otp, submit_otp
from app.client.circle import (
    accept_circle_invitation,
    get_bonus_data,
    get_group_data,
    get_group_members,
    invite_circle_member,
    remove_circle_member,
    spending_tracker,
)
from app.client.encrypt import decrypt_circle_msisdn
from app.client.engsel import (
    dashboard_segments,
    get_balance,
    get_family,
    get_notification_detail,
    get_notifications,
    get_package,
    get_tiering_info,
    get_transaction_history,
    send_api_request,
    unsubscribe,
)
from app.client.famplan import change_member, get_family_data, remove_member, set_quota_limit, validate_msisdn
from app.client.purchase.balance import settlement_balance
from app.client.purchase.ewallet import settlement_multipayment
from app.client.purchase.qris import get_qris_code, settlement_qris
from app.client.registration import dukcapil
from app.client.store.redeemables import get_redeemables
from app.client.store.search import get_family_list, get_store_packages
from app.client.store.segments import get_segments
from app.bot_handlers.catalog_handler import render_hot_page, render_items_page
from app.bot_handlers.catalog_flow import handle_catalog_flow
from app.bot_handlers.catalog_state import render_catalog_state_page
from app.bot_handlers.package_flow import handle_package_flow
from app.bot_handlers.payment_flow import handle_payment_flow
from app.bot_handlers.ui_primitives import (
    build_context_help_panel,
    build_panel,
    build_error_with_next,
    build_first_use_onboarding_panel,
    build_home_compact_panel,
    build_package_detail_panel,
    build_paged_list_panel,
    build_home_fancy_panel,
    build_home_guest_panel,
    build_progress_panel,
)
from app.menus import purchase as purchase_menu
from app.menus.util import format_quota_byte
from app.service.auth import AuthInstance
from app.service.bookmark import BookmarkInstance
from app.service.decoy import DecoyInstance
from app.type_dict import PaymentItem

ROOT_DIR = Path(__file__).resolve().parent
ALLOW_FILE = ROOT_DIR / "user_allow.txt"
ACCESS_STATE_FILE = ROOT_DIR / "access_state.json"
FLOW_KEY = "native_flow"
PANEL_MESSAGE_IDS: dict[int, int] = {}
RESPONSE_CACHE: dict[str, tuple[float, object]] = {}
PAYMENT_LOCKS: dict[int, asyncio.Lock] = {}
PAYMENT_CANCEL_FLAGS: dict[int, bool] = {}
BALANCE_N_TASKS: dict[int, asyncio.Task] = {}
ACCESS_REQUEST_LAST_SENT: dict[int, float] = {}
ACCESS_REQUEST_COOLDOWN_SEC = 60

logger = logging.getLogger(__name__)


def _cache_get(key: str, ttl_sec: int):
    item = RESPONSE_CACHE.get(key)
    if not item:
        return None
    created_at, value = item
    if (time.time() - created_at) > ttl_sec:
        RESPONSE_CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: object):
    RESPONSE_CACHE[key] = (time.time(), value)


def _cache_invalidate(prefixes: list[str]):
    keys = list(RESPONSE_CACHE.keys())
    for key in keys:
        if any(key.startswith(prefix) for prefix in prefixes):
            RESPONSE_CACHE.pop(key, None)


def _get_payment_lock(chat_id: int) -> asyncio.Lock:
    lock = PAYMENT_LOCKS.get(chat_id)
    if lock is None:
        lock = asyncio.Lock()
        PAYMENT_LOCKS[chat_id] = lock
    return lock


def _set_payment_cancel(chat_id: int, cancelled: bool):
    PAYMENT_CANCEL_FLAGS[chat_id] = cancelled


def _is_payment_cancelled(chat_id: int) -> bool:
    return PAYMENT_CANCEL_FLAGS.get(chat_id, False)


def _progress_bar(done: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return "[--------------------]"
    filled = int((done / total) * width)
    filled = max(0, min(width, filled))
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def _state_total_items(state: str, data: dict) -> int:
    if state in {"await_package_detail_pick", "await_package_unsub_pick"}:
        return len(data.get("packages", []))
    if state in {"hot_select", "hot2_select"}:
        return len(data.get("hot_packages", []))
    if state in {"await_store_segments_pick", "await_store_family_pick", "await_store_package_pick", "await_redeem_pick", "await_circle_bonus_pick", "await_family_option_pick"}:
        return len(data.get("items", []))
    if state in {"await_famplan_remove", "await_famplan_limit", "await_circle_remove", "await_circle_accept"}:
        return len(data.get("members", []))
    if state in {"await_switch_idx", "await_delete_idx", "await_bookmark_remove"}:
        return int(data.get("count", 0))
    return 0


def _mk_inline(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    inline_rows: list[list[InlineKeyboardButton]] = []
    for row in rows:
        inline_rows.append([InlineKeyboardButton(text=label, callback_data=data) for label, data in row])
    return InlineKeyboardMarkup(inline_rows)

def _row_home_cancel() -> list[tuple[str, str]]:
    return [("🏠 Home", "home"), ("↩️ Batal", "cancel")]

def _row_back_home(back_data: str) -> list[tuple[str, str]]:
    return [("⬅️ Kembali", back_data), ("🏠 Home", "home")]

def keyboard_main() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("1 👤 Akun", "1"), ("2 📦 Paket", "2"), ("3 🔥 HOT", "3"), ("4 🔥 HOT2", "4")],
            [("5 🧩 Option", "5"), ("6 👪 Family", "6"), ("7 🔁 Loop", "7"), ("8 🧾 Riwayat", "8")],
            [("9 👨‍👩‍👧 FamPlan", "9"), ("10 ⭕ Circle", "10"), ("11 🏪 Segments", "11"), ("12 🧬 Families", "12")],
            [("13 🛒 Store", "13"), ("14 🎟 Redeem", "14"), ("00 ⭐ Bookmark", "00")],
            [("A 🛡 Akses User", "a")],
            [("R 📝 Register", "r"), ("N 🔔 Notif", "n"), ("V ✅ Validate", "v")],
            [("🏠 Home", "home"), ("↩️ Batal", "cancel"), ("❓ Bantuan", "help")],
        ]
    )


def keyboard_account() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("➕ Tambah", "acc_add"), ("🔁 Ganti", "acc_switch"), ("🗑 Hapus", "acc_delete")],
            _row_home_cancel(),
        ]
    )


def keyboard_hot_select() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5")],
            [("6", "6"), ("7", "7"), ("8", "8"), ("9", "9"), ("10", "10")],
            _row_home_cancel(),
        ]
    )


def keyboard_single_input() -> InlineKeyboardMarkup:
    return _mk_inline([_row_home_cancel()])


def keyboard_number_picker(total: int, page: int = 0, page_size: int = 10, cap: int = 200, cols: int = 5) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []
    n = max(0, min(total, cap))
    max_page = max(0, (n - 1) // page_size) if n else 0
    page = max(0, min(page, max_page))
    start = page * page_size
    end = min(n, start + page_size)

    current: list[tuple[str, str]] = []
    for i in range(start + 1, end + 1):
        current.append((str(i), str(i)))
        if len(current) == cols:
            rows.append(current)
            current = []
    if current:
        rows.append(current)

    nav: list[tuple[str, str]] = []
    if page > 0:
        nav.append(("Prev", "pg_prev"))
    if page < max_page:
        nav.append(("Next", "pg_next"))
    if nav:
        rows.append(nav)

    rows.append(_row_home_cancel())
    return _mk_inline(rows)


def keyboard_famplan() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("🔄 Refresh", "fam_refresh"), ("👥 Ganti", "fam_change")],
            [("🗑 Hapus", "fam_remove"), ("📏 Set Limit", "fam_limit")],
            _row_home_cancel(),
        ]
    )


def keyboard_circle() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("🔄 Refresh", "cir_refresh"), ("➕ Invite", "cir_invite")],
            [("🗑 Remove", "cir_remove"), ("✅ Accept", "cir_accept")],
            [("🎁 Bonus", "cir_bonus")],
            _row_home_cancel(),
        ]
    )


def keyboard_packages_menu() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("🔄 Refresh", "pkg_refresh"), ("🧾 Detail", "pkg_detail"), ("⛔ Unsub", "pkg_unsub")],
            _row_home_cancel(),
        ]
    )


def keyboard_history_menu() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("🔄 Refresh", "hist_refresh")],
            _row_home_cancel(),
        ]
    )


def keyboard_notif_menu() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("🔄 Refresh", "notif_refresh"), ("✅ Mark All", "notif_mark_all")],
            _row_home_cancel(),
        ]
    )


def keyboard_bookmark_menu() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("🔄 Refresh", "bm_refresh"), ("➕ Add", "bm_add"), ("🗑 Delete", "bm_delete")],
            _row_home_cancel(),
        ]
    )


def keyboard_admin_access() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("📥 Pending", "allow_pending"), ("👥 Kelola User", "allow_manage")],
            [("📋 List Allow", "allow_list"), ("➕ Add User", "allow_add")],
            _row_home_cancel(),
        ]
    )


def keyboard_admin_user_actions(user_id: int) -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("⛔ Suspend", f"allow_suspend:{user_id}"), ("👢 Kick", f"allow_kick:{user_id}")],
            [("✅ Unsuspend", f"allow_unsuspend:{user_id}")],
            [("⬅️ Kelola User", "allow_manage"), ("🏠 Home", "home")],
        ]
    )


def keyboard_request_access() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("🙋 Minta Akses", "access_req")],
        ]
    )


def keyboard_yes_no(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("✅ Ya", yes_data), ("❌ Tidak", no_data)],
            _row_home_cancel(),
        ]
    )


def keyboard_package_detail_menu() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("⚡ Bayar Pulsa", "pay_balance"), ("💳 Bayar E-Wallet", "pay_ewallet")],
            [("📷 Bayar QRIS", "pay_qris"), ("🔁 Pulsa N Kali", "pay_balance_n")],
            [("🕶 Pulsa+Decoy", "pay_decoy_balance"), ("🕶 Pulsa+Decoy V2", "pay_decoy_balance_v2")],
            [("🧾 QRIS+Decoy", "pay_decoy_qris"), ("🧾 QRIS+Decoy V2", "pay_decoy_qris0")],
            [("🛠 QRIS+Decoy Manual", "pay_decoy_qris_manual"), ("🛠 QRIS+Decoy V2 Manual", "pay_decoy_qris0_manual")],
            _row_back_home("pkg_back_list"),
        ]
    )


def keyboard_ewallet_methods() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("💳 DANA", "ew_dana"), ("💳 ShopeePay", "ew_shopeepay")],
            [("💳 GoPay", "ew_gopay"), ("💳 OVO", "ew_ovo")],
            _row_back_home("pkg_back_detail"),
        ]
    )


def keyboard_cancel_progress() -> InlineKeyboardMarkup:
    return _mk_inline(
        [
            [("⛔ Batal Progress", "bal_n_cancel")],
            _row_home_cancel(),
        ]
    )


def get_flow(context: ContextTypes.DEFAULT_TYPE) -> dict:
    if context.user_data is None:
        return {"state": "home", "data": {}}

    flow = context.user_data.get(FLOW_KEY)
    if not isinstance(flow, dict):
        flow = {"state": "home", "data": {}}
        context.user_data[FLOW_KEY] = flow
    return flow


def set_flow(context: ContextTypes.DEFAULT_TYPE, state: str, data: dict | None = None):
    if context.user_data is None:
        return
    context.user_data[FLOW_KEY] = {"state": state, "data": data or {}}


def current_keyboard(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    flow = get_flow(context)
    state = flow.get("state", "home")
    data = flow.get("data", {})

    if state == "account_menu":
        return keyboard_account()
    if state == "packages_menu":
        return keyboard_packages_menu()
    if state == "history_menu":
        return keyboard_history_menu()
    if state == "notifications_menu":
        return keyboard_notif_menu()
    if state == "bookmark_menu":
        return keyboard_bookmark_menu()
    if state == "admin_access_menu":
        return keyboard_admin_access()
    if state == "await_package_unsub_confirm":
        return keyboard_yes_no("pkg_unsub_yes", "pkg_unsub_no")
    if state == "await_balance_n_decoy":
        return keyboard_yes_no("bal_n_decoy_yes", "bal_n_decoy_no")
    if state == "package_detail_menu":
        return keyboard_package_detail_menu()
    if state == "await_ewallet_method":
        return keyboard_ewallet_methods()
    if state == "await_balance_n_running":
        return keyboard_cancel_progress()
    if state == "await_package_detail_pick":
        return keyboard_number_picker(len(data.get("packages", [])), int(data.get("page", 0)))
    if state == "await_package_unsub_pick":
        return keyboard_number_picker(len(data.get("packages", [])), int(data.get("page", 0)))
    if state == "await_switch_idx":
        return keyboard_number_picker(int(data.get("count", 0)), int(data.get("page", 0)))
    if state == "await_delete_idx":
        return keyboard_number_picker(int(data.get("count", 0)), int(data.get("page", 0)))
    if state in {"hot_select", "hot2_select"}:
        return keyboard_number_picker(len(data.get("hot_packages", [])), int(data.get("page", 0)))
    if state in {"await_store_segments_pick", "await_store_family_pick", "await_store_package_pick", "await_redeem_pick", "await_circle_bonus_pick", "await_family_option_pick"}:
        return keyboard_number_picker(len(data.get("items", [])), int(data.get("page", 0)))
    if state == "await_bookmark_remove":
        return keyboard_number_picker(int(data.get("count", 0)), int(data.get("page", 0)))
    if state in {"await_famplan_remove", "await_famplan_limit"}:
        return keyboard_number_picker(len(data.get("members", [])), int(data.get("page", 0)))
    if state in {"await_circle_remove", "await_circle_accept"}:
        return keyboard_number_picker(len(data.get("members", [])), int(data.get("page", 0)))
    if state in {
        "await_login_phone",
        "await_login_otp",
        "await_option_code",
        "await_family_code",
        "await_validate_msisdn",
        "await_register",
        "await_switch_idx",
        "await_delete_idx",
        "await_store_segments_pick",
        "await_store_family_pick",
        "await_store_package_pick",
        "await_redeem_pick",
        "await_bookmark_remove",
        "await_bookmark_add",
        "await_purchase_loop",
        "await_famplan_change",
        "await_famplan_remove",
        "await_famplan_limit_mb",
        "await_circle_invite",
        "await_circle_remove",
        "await_circle_accept",
        "await_circle_bonus_pick",
        "await_ewallet_number",
        "await_decoy_qris_manual_amount",
        "await_balance_n_count",
        "await_balance_n_delay",
        "await_admin_allow_add_id",
        "await_admin_action_reason",
    }:
        return keyboard_single_input()
    if state == "famplan_menu":
        return keyboard_famplan()
    if state == "circle_menu":
        return keyboard_circle()
    return keyboard_main()


def _single_panel_text(text: str, max_len: int = 3900) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: (max_len - 40)] + "\n\n...[output dipotong]"


def load_allowed_id_list() -> list[int]:
    if not ALLOW_FILE.exists():
        return []

    allowed: list[int] = []
    for raw in ALLOW_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.isdigit():
            user_id = int(line)
            if user_id not in allowed:
                allowed.append(user_id)
    return allowed


def load_allowed_ids() -> set[int]:
    return set(load_allowed_id_list())


def get_admin_id() -> int | None:
    allowed = load_allowed_id_list()
    return allowed[0] if allowed else None


def is_admin_user(user_id: int | None) -> bool:
    admin_id = get_admin_id()
    return user_id is not None and admin_id is not None and user_id == admin_id


def write_allowed_id_list(ids: list[int]):
    cleaned: list[int] = []
    for user_id in ids:
        if isinstance(user_id, int) and user_id > 0 and user_id not in cleaned:
            cleaned.append(user_id)

    payload = ""
    if cleaned:
        payload = "\n".join(str(v) for v in cleaned) + "\n"
    ALLOW_FILE.write_text(payload, encoding="utf-8")


def append_allowed_id(user_id: int) -> bool:
    if user_id <= 0:
        return False

    ids = load_allowed_id_list()
    if user_id in ids:
        return False

    ids.append(user_id)
    write_allowed_id_list(ids)
    return True


_ACCESS_STATUSES = {"pending", "approved", "rejected", "suspended", "kicked"}


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat(sep=" ")


def _default_access_state() -> dict:
    return {
        "last_request_id": 0,
        "users": {},
        "requests": [],
    }


def _load_access_state() -> dict:
    if not ACCESS_STATE_FILE.exists():
        return _default_access_state()

    try:
        payload = json.loads(ACCESS_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return _default_access_state()

    if not isinstance(payload, dict):
        return _default_access_state()

    users = payload.get("users")
    requests = payload.get("requests")
    last_request_id = payload.get("last_request_id", 0)
    if not isinstance(users, dict):
        users = {}
    if not isinstance(requests, list):
        requests = []

    return {
        "last_request_id": int(last_request_id) if str(last_request_id).isdigit() else 0,
        "users": users,
        "requests": requests,
    }


def _save_access_state(state: dict):
    ACCESS_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sync_access_state_from_allow_list() -> dict:
    state = _load_access_state()
    users = state.setdefault("users", {})
    ids = load_allowed_id_list()
    now = _now_iso()
    changed = False

    for idx, user_id in enumerate(ids):
        key = str(user_id)
        existing = users.get(key, {})
        role = "admin" if idx == 0 else str(existing.get("role", "user") or "user")
        if idx > 0 and role != "admin":
            role = "user"
        status = str(existing.get("status", "approved") or "approved")
        if status not in _ACCESS_STATUSES:
            status = "approved"
        if status != "approved":
            status = "approved"

        record = {
            "user_id": user_id,
            "role": role,
            "status": status,
            "note": str(existing.get("note", "") or ""),
            "updated_at": str(existing.get("updated_at", now) or now),
        }

        if existing != record:
            users[key] = record
            changed = True

    if changed:
        _save_access_state(state)
    return state


def _write_allow_list_from_state(state: dict):
    users = state.get("users", {}) if isinstance(state, dict) else {}
    allow_ids = load_allowed_id_list()
    admin_id: int | None = allow_ids[0] if allow_ids else None

    if admin_id is None:
        admin_candidates = []
        for key, item in users.items():
            if not str(key).isdigit():
                continue
            if str(item.get("role", "")) == "admin":
                admin_candidates.append(int(key))
        if admin_candidates:
            admin_id = sorted(admin_candidates)[0]

    if admin_id is None:
        write_allowed_id_list([])
        return

    admin_key = str(admin_id)
    admin_rec = users.get(admin_key, {})
    users[admin_key] = {
        "user_id": admin_id,
        "role": "admin",
        "status": "approved",
        "note": str(admin_rec.get("note", "") or ""),
        "updated_at": _now_iso(),
    }

    approved_users: list[int] = []
    for key, item in users.items():
        if not str(key).isdigit():
            continue
        uid = int(key)
        if uid == admin_id:
            continue
        if str(item.get("status", "")) != "approved":
            continue
        approved_users.append(uid)

    approved_users = sorted(set(approved_users))
    write_allowed_id_list([admin_id] + approved_users)


def _get_user_access_record(user_id: int) -> dict:
    state = _sync_access_state_from_allow_list()
    users = state.get("users", {})
    key = str(user_id)
    rec = users.get(key)
    if isinstance(rec, dict):
        return rec
    return {
        "user_id": user_id,
        "role": "user",
        "status": "pending",
        "note": "",
        "updated_at": "",
    }


def _set_user_access_status(user_id: int, status: str, note: str = "") -> dict:
    status = str(status or "").strip().lower()
    if status not in _ACCESS_STATUSES:
        status = "pending"

    state = _sync_access_state_from_allow_list()
    users = state.setdefault("users", {})
    key = str(user_id)
    existing = users.get(key, {}) if isinstance(users.get(key), dict) else {}
    role = "admin" if is_admin_user(user_id) else str(existing.get("role", "user") or "user")

    if role == "admin":
        status = "approved"

    users[key] = {
        "user_id": user_id,
        "role": role,
        "status": status,
        "note": str(note or ""),
        "updated_at": _now_iso(),
    }

    _write_allow_list_from_state(state)
    _save_access_state(state)
    return users[key]


def _list_managed_users_access() -> list[dict]:
    state = _sync_access_state_from_allow_list()
    users = state.get("users", {})
    out: list[dict] = []
    for key, item in users.items():
        if not str(key).isdigit() or not isinstance(item, dict):
            continue
        out.append(item)

    def _rank(rec: dict) -> tuple[int, int]:
        role = str(rec.get("role", "user") or "user")
        status = str(rec.get("status", "pending") or "pending")
        role_rank = 0 if role == "admin" else 1
        status_rank_map = {
            "pending": 0,
            "approved": 1,
            "suspended": 2,
            "kicked": 3,
            "rejected": 4,
        }
        status_rank = status_rank_map.get(status, 99)
        return (role_rank, status_rank)

    out.sort(key=_rank)
    return out


def _next_request_id(state: dict) -> int:
    current = int(state.get("last_request_id", 0) or 0)
    current += 1
    state["last_request_id"] = current
    return current


def _find_pending_request_for_user(state: dict, user_id: int) -> dict | None:
    rows = state.get("requests", []) if isinstance(state.get("requests"), list) else []
    for item in reversed(rows):
        if not isinstance(item, dict):
            continue
        if int(item.get("user_id", 0) or 0) != user_id:
            continue
        if str(item.get("status", "")) == "pending":
            return item
    return None


def _create_access_request(user, reason: str = "") -> tuple[str, dict | None]:
    user_id = int(getattr(user, "id", 0) or 0)
    if user_id <= 0:
        return "invalid", None

    rec = _get_user_access_record(user_id)
    if str(rec.get("status", "")) == "approved":
        return "already-approved", None

    state = _sync_access_state_from_allow_list()
    pending = _find_pending_request_for_user(state, user_id)
    if pending is not None:
        return "pending", pending

    req = {
        "id": _next_request_id(state),
        "user_id": user_id,
        "username": str(getattr(user, "username", "") or ""),
        "full_name": " ".join(filter(None, [getattr(user, "first_name", ""), getattr(user, "last_name", "")])).strip(),
        "reason": str(reason or ""),
        "status": "pending",
        "admin_id": 0,
        "admin_reason": "",
        "created_at": _now_iso(),
        "processed_at": "",
    }
    state.setdefault("requests", []).append(req)

    users = state.setdefault("users", {})
    key = str(user_id)
    existing = users.get(key, {}) if isinstance(users.get(key), dict) else {}
    users[key] = {
        "user_id": user_id,
        "role": "user",
        "status": "pending",
        "note": str(reason or existing.get("note", "") or ""),
        "updated_at": _now_iso(),
    }

    _save_access_state(state)
    return "created", req


def _list_pending_access_requests() -> list[dict]:
    state = _sync_access_state_from_allow_list()
    rows = state.get("requests", []) if isinstance(state.get("requests"), list) else []
    pending = [item for item in rows if isinstance(item, dict) and str(item.get("status", "")) == "pending"]
    pending.sort(key=lambda x: int(x.get("id", 0) or 0))
    return pending


def _process_access_request(user_id: int, approved: bool, admin_id: int, admin_reason: str = "") -> tuple[bool, str]:
    state = _sync_access_state_from_allow_list()
    req = _find_pending_request_for_user(state, user_id)
    if req is None:
        return False, "Permintaan user ini sudah diproses atau tidak ditemukan."

    req["status"] = "approved" if approved else "rejected"
    req["admin_id"] = admin_id
    req["admin_reason"] = str(admin_reason or "")
    req["processed_at"] = _now_iso()

    users = state.setdefault("users", {})
    key = str(user_id)
    existing = users.get(key, {}) if isinstance(users.get(key), dict) else {}
    users[key] = {
        "user_id": user_id,
        "role": str(existing.get("role", "user") or "user"),
        "status": "approved" if approved else "rejected",
        "note": str(admin_reason or ""),
        "updated_at": _now_iso(),
    }

    _write_allow_list_from_state(state)
    _save_access_state(state)
    return True, "ok"


def _status_label(status: str) -> str:
    s = str(status or "").lower()
    if s == "approved":
        return "APPROVED"
    if s == "pending":
        return "PENDING"
    if s == "rejected":
        return "REJECTED"
    if s == "suspended":
        return "SUSPENDED"
    if s == "kicked":
        return "KICKED"
    return s.upper() if s else "UNKNOWN"


def _read_auth_meta(scope_key: str) -> tuple[int | None, int]:
    if scope_key == "global":
        scope_dir = ROOT_DIR
    else:
        scope_dir = ROOT_DIR / "user_data" / scope_key

    refresh_file = scope_dir / "refresh-tokens.json"
    active_file = scope_dir / "active.number"

    token_count = 0
    if refresh_file.exists():
        try:
            payload = json.loads(refresh_file.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                token_count = len(payload)
        except Exception:
            token_count = 0

    active_number: int | None = None
    if active_file.exists():
        raw = active_file.read_text(encoding="utf-8").strip()
        if raw.isdigit():
            active_number = int(raw)

    return active_number, token_count


def _allow_list_panel_text() -> str:
    _sync_access_state_from_allow_list()
    users = _list_managed_users_access()
    admin_id = get_admin_id()
    pending_count = len(_list_pending_access_requests())

    if not users:
        return (
            "Kelola Akses Telegram\n"
            "Belum ada user terdaftar.\n"
            "Gunakan tombol ➕ Add User atau tunggu request akses dari user."
        )

    lines = [
        "Kelola Akses Telegram",
        f"Admin (baris pertama): {admin_id if admin_id is not None else '-'}",
        f"Pending request: {pending_count}",
        "Daftar user:",
    ]
    for idx, rec in enumerate(users, start=1):
        user_id = int(rec.get("user_id", 0) or 0)
        role = str(rec.get("role", "user") or "user").upper()
        status = _status_label(str(rec.get("status", "pending") or "pending"))
        scope_key = "global" if role == "ADMIN" else f"user_{user_id}"
        active_number, token_count = _read_auth_meta(scope_key)
        active_text = str(active_number) if active_number is not None else "-"
        lines.append(f"{idx}. {user_id} [{role}|{status}] | akun={token_count} | aktif={active_text}")

    lines.append("Gunakan menu Pending/Kelola User untuk approve, suspend, kick, atau unsuspend user.")
    return "\n".join(lines)


def _pending_requests_panel_text() -> str:
    pending = _list_pending_access_requests()
    if not pending:
        return "Tidak ada request akses yang pending."

    lines = ["Pending Request Akses:"]
    for req in pending[:25]:
        user_id = int(req.get("user_id", 0) or 0)
        username = str(req.get("username", "") or "-")
        full_name = str(req.get("full_name", "") or "-")
        reason = str(req.get("reason", "") or "-")
        uname = f"@{username}" if username not in {"", "-"} else "-"
        lines.append(f"- {user_id} | {uname} | {full_name} | alasan: {reason}")
    return "\n".join(lines)


def _managed_users_panel_text() -> tuple[str, list[int]]:
    users = [rec for rec in _list_managed_users_access() if str(rec.get("role", "user")) != "admin"]
    if not users:
        return "Belum ada user non-admin yang terdaftar.", []

    lines = ["Kelola User (non-admin):"]
    user_ids: list[int] = []
    for rec in users[:30]:
        user_id = int(rec.get("user_id", 0) or 0)
        if user_id <= 0:
            continue
        user_ids.append(user_id)
        status = _status_label(str(rec.get("status", "pending") or "pending"))
        note = str(rec.get("note", "") or "")
        suffix = f" | note={note}" if note else ""
        lines.append(f"- {user_id} [{status}]{suffix}")
    return "\n".join(lines), user_ids


def _admin_user_detail_text(user_id: int) -> str:
    rec = _get_user_access_record(user_id)
    role = str(rec.get("role", "user") or "user").upper()
    status = _status_label(str(rec.get("status", "pending") or "pending"))
    note = str(rec.get("note", "") or "")
    scope_key = "global" if role == "ADMIN" else f"user_{user_id}"
    active_number, token_count = _read_auth_meta(scope_key)
    active_text = str(active_number) if active_number is not None else "-"
    lines = [
        "Detail User Akses",
        f"User ID: {user_id}",
        f"Role: {role}",
        f"Status: {status}",
        f"Jumlah akun tersimpan: {token_count}",
        f"Akun aktif: {active_text}",
    ]
    if note:
        lines.append(f"Catatan: {note}")
    lines.append("Gunakan tombol aksi di bawah untuk suspend, kick, atau unsuspend.")
    return "\n".join(lines)


async def _submit_access_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return

    user_id = user.id
    _sync_access_state_from_allow_list()
    admin_id = get_admin_id()
    if admin_id is None:
        await msg.reply_text(
            "Admin belum dikonfigurasi. Isi user_allow.txt dan pastikan baris pertama adalah Telegram user id admin."
        )
        return

    if user_id == admin_id:
        await msg.reply_text("Anda terdeteksi sebagai admin.")
        return

    now = time.time()
    last_sent = ACCESS_REQUEST_LAST_SENT.get(user_id, 0)
    if now - last_sent < ACCESS_REQUEST_COOLDOWN_SEC:
        wait_for = int(ACCESS_REQUEST_COOLDOWN_SEC - (now - last_sent))
        await msg.reply_text(f"Permintaan terakhir baru dikirim. Coba lagi {wait_for} detik lagi.")
        return

    ACCESS_REQUEST_LAST_SENT[user_id] = now

    req_state, req_data = _create_access_request(user, "")
    if req_state == "already-approved":
        await msg.reply_text("Akses Anda sudah aktif. Kirim /start untuk membuka panel.")
        return
    if req_state == "pending":
        req_id = int((req_data or {}).get("id", 0) or 0)
        await msg.reply_text(f"Request Anda masih pending (ID: {req_id}). Mohon tunggu persetujuan admin.")
        return
    if req_state != "created":
        await msg.reply_text("Gagal membuat request akses. Coba lagi.")
        return

    req = req_data or {}
    req_id = int(req.get("id", 0) or 0)

    username = f"@{user.username}" if user.username else "(tidak ada)"
    fullname = " ".join(filter(None, [user.first_name, user.last_name])) or "(tidak ada)"
    text_admin = (
        "Permintaan akses bot me-cli\n"
        f"Request ID: {req_id}\n"
        f"User ID: {user_id}\n"
        f"Username: {username}\n"
        f"Nama: {fullname}\n\n"
        "Setujui atau tolak user ini?"
    )
    kb = _mk_inline([[ ("✅ Setujui", f"allow_approve:{user_id}"), ("❌ Tolak", f"allow_reject:{user_id}") ]])

    try:
        await context.bot.send_message(chat_id=admin_id, text=text_admin, reply_markup=kb)
    except Exception:
        await msg.reply_text("Gagal mengirim permintaan ke admin. Pastikan admin pernah chat bot ini terlebih dahulu.")
        return

    await msg.reply_text("Permintaan akses sudah dikirim ke admin. Tunggu persetujuan.")


async def ensure_allowed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    msg = update.effective_message
    if msg is None:
        return False

    user = update.effective_user
    user_id = user.id if user else None
    _sync_access_state_from_allow_list()
    allowed_ids = load_allowed_id_list()
    admin_id = allowed_ids[0] if allowed_ids else None

    if user_id is None:
        return False

    if not allowed_ids:
        await msg.reply_text(
            "Akses bot belum dikonfigurasi. Isi user_allow.txt dengan Telegram user id yang diizinkan (baris pertama = admin).",
            reply_markup=keyboard_main(),
        )
        return False

    rec = _get_user_access_record(user_id)
    status = str(rec.get("status", "pending") or "pending")
    if status == "approved":
        AuthInstance.set_runtime_owner(user_id, is_admin=(admin_id is not None and user_id == admin_id))
        return True

    callback_data = ""
    if update.callback_query is not None:
        callback_data = (update.callback_query.data or "").strip()

    text_input = (msg.text or "").strip().lower()
    if callback_data == "access_req" or text_input in {"/request_access", "request_access", "minta akses"}:
        if update.callback_query is not None:
            try:
                await update.callback_query.answer("Permintaan akses diproses...")
            except Exception:
                pass
        await _submit_access_request(update, context)
        return False

    note = str(rec.get("note", "") or "")
    if status == "pending":
        text_out = "Akses Anda masih menunggu persetujuan admin."
    elif status == "rejected":
        text_out = "Permintaan akses Anda ditolak admin."
        if note:
            text_out += f"\nCatatan: {note}"
    elif status == "suspended":
        text_out = "Akses Anda sedang disuspend admin."
        if note:
            text_out += f"\nAlasan: {note}"
    elif status == "kicked":
        text_out = "Akses Anda di-kick admin."
        if note:
            text_out += f"\nAlasan: {note}"
    else:
        text_out = "Akses ditolak untuk user ini."

    await msg.reply_text(text_out + "\n\nTekan tombol berikut untuk mengirim request akses.", reply_markup=keyboard_request_access())
    return False


async def _delete_user_input(update: Update):
    msg = update.effective_message
    if msg is None:
        return
    try:
        await msg.delete()
    except Exception:
        return


async def render_panel_for_chat(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup,
):
    panel_text = _single_panel_text(text)
    panel_id = PANEL_MESSAGE_IDS.get(chat_id)

    if panel_id is not None:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=panel_id,
                text=panel_text,
                reply_markup=keyboard,
            )
            return
        except Exception:
            # Fallback for cases where message cannot be edited anymore.
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=panel_id)
            except Exception:
                pass

    sent = await context.bot.send_message(chat_id=chat_id, text=panel_text, reply_markup=keyboard)
    PANEL_MESSAGE_IDS[chat_id] = sent.message_id


async def render_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
):
    if update.effective_chat is None:
        return
    await render_panel_for_chat(
        context,
        update.effective_chat.id,
        text,
        keyboard or current_keyboard(context),
    )


async def _run_payment_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    pending_text: str,
    worker,
):
    chat = update.effective_chat
    if chat is None:
        return "Konteks chat tidak ditemukan."

    lock = _get_payment_lock(chat.id)
    if lock.locked():
        return "Masih ada pembayaran yang sedang diproses. Tunggu beberapa detik lalu coba lagi."

    await render_panel(update, context, pending_text)
    async with lock:
        return await asyncio.to_thread(worker)


async def _run_balance_n_with_progress(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    payment_ctx: dict,
    count: int,
    delay_sec: int,
    use_decoy: bool,
) -> str:
    chat = update.effective_chat
    if chat is None:
        return "Konteks chat tidak ditemukan."

    chat_id = chat.id
    lock = _get_payment_lock(chat_id)
    if lock.locked():
        return "Masih ada pembayaran yang sedang diproses. Tunggu beberapa detik lalu coba lagi."

    _set_payment_cancel(chat_id, False)
    mode = "decoy" if use_decoy else "normal"
    ok = 0
    fail = 0
    last_error = ""

    try:
        async with lock:
            for i in range(count):
                if _is_payment_cancelled(chat_id):
                    summary = f"Pulsa N Kali dibatalkan user. Progress: {i}/{count}, Berhasil: {ok}, Gagal: {fail}."
                    if last_error:
                        return summary + "\n\nError terakhir:\n" + last_error
                    return summary

                await render_panel(
                    update,
                    context,
                    build_progress_panel(
                        mode,
                        i,
                        count,
                        f"Memproses iterasi ke-{i + 1}",
                        ok,
                        fail,
                        delay_sec,
                    ),
                )

                if use_decoy:
                    result = await asyncio.to_thread(_pay_decoy_balance_sync, payment_ctx, False)
                    success = result.startswith("Pembayaran Pulsa+Decoy berhasil")
                else:
                    result = await asyncio.to_thread(_pay_balance_sync, payment_ctx)
                    success = result.startswith("Pembayaran Pulsa berhasil")

                if success:
                    ok += 1
                else:
                    fail += 1
                    last_error = result

                if i < (count - 1) and delay_sec > 0:
                    remaining = delay_sec
                    while remaining > 0:
                        if _is_payment_cancelled(chat_id):
                            summary = (
                                f"Pulsa N Kali dibatalkan user saat delay. Progress: {i + 1}/{count}, "
                                f"Berhasil: {ok}, Gagal: {fail}."
                            )
                            if last_error:
                                return summary + "\n\nError terakhir:\n" + last_error
                            return summary

                        await render_panel(
                            update,
                            context,
                            build_progress_panel(
                                mode,
                                i + 1,
                                count,
                                f"Menunggu delay {remaining} detik",
                                ok,
                                fail,
                                delay_sec,
                            ),
                        )
                        await asyncio.sleep(1)
                        remaining -= 1

        summary = f"Pulsa N Kali ({mode}) selesai. Berhasil: {ok}, Gagal: {fail}, Total: {count}, Delay: {delay_sec} detik."
        if last_error:
            return summary + "\n\nError terakhir:\n" + last_error
        return summary
    finally:
        _set_payment_cancel(chat_id, False)


def _start_balance_n_progress_task(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    payment_ctx: dict,
    count: int,
    delay_sec: int,
    use_decoy: bool,
    back_state: str,
    back_data: dict,
) -> str:
    chat = update.effective_chat
    if chat is None:
        return "Konteks chat tidak ditemukan."

    chat_id = chat.id
    prev = BALANCE_N_TASKS.get(chat_id)
    if prev and not prev.done():
        prev.cancel()

    async def _runner():
        try:
            result = await _run_balance_n_with_progress(update, context, payment_ctx, count, delay_sec, use_decoy)
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
        except asyncio.CancelledError:
            set_flow(
                context,
                "package_detail_menu",
                {
                    "payment_ctx": payment_ctx,
                    "back_state": back_state,
                    "back_data": back_data,
                },
            )
            await render_panel(update, context, "Pulsa N Kali dihentikan (stop session).\n\nPilih metode pembayaran lain atau kembali.")
        finally:
            BALANCE_N_TASKS.pop(chat_id, None)
            _set_payment_cancel(chat_id, False)

    task = asyncio.create_task(_runner())
    BALANCE_N_TASKS[chat_id] = task
    return "Proses Pulsa N Kali dimulai. Tekan tombol Batal Progress untuk stop session."


def _normalize_choice(text: str) -> str:
    t = text.strip().lower()
    if t.startswith("00"):
        return "00"
    if t.startswith("10"):
        return "10"
    if t.startswith("11"):
        return "11"
    if t.startswith("12"):
        return "12"
    if t.startswith("13"):
        return "13"
    if t.startswith("14"):
        return "14"
    if t.startswith("1"):
        return "1"
    if t.startswith("2"):
        return "2"
    if t.startswith("3"):
        return "3"
    if t.startswith("4"):
        return "4"
    if t.startswith("5"):
        return "5"
    if t.startswith("6"):
        return "6"
    if t.startswith("7"):
        return "7"
    if t.startswith("8"):
        return "8"
    if t.startswith("9"):
        return "9"
    if t.startswith("r"):
        return "r"
    if t.startswith("n"):
        return "n"
    if t.startswith("v"):
        return "v"
    if t == "a" or "akses user" in t:
        return "a"
    return t


def _state_help_content(state: str) -> tuple[str, list[str]]:
    if state in {"home", "account_menu", "packages_menu", "history_menu", "notifications_menu", "bookmark_menu", "famplan_menu", "circle_menu", "admin_access_menu"}:
        return (
            "Pilih menu sesuai kebutuhan. Tombol Home/Batal selalu tersedia untuk kembali ke area aman.",
            [
                "1 = akun, 2 = paket, 6 = family, 10 = circle",
                "Gunakan angka tombol untuk memilih item",
            ],
        )

    if state in {"await_package_detail_pick", "await_package_unsub_pick", "hot_select", "hot2_select", "await_store_segments_pick", "await_store_family_pick", "await_store_package_pick", "await_redeem_pick", "await_circle_bonus_pick", "await_family_option_pick"}:
        return (
            "Anda sedang di mode pemilihan list. Pilih nomor item atau pindah halaman.",
            [
                "Prev/Next untuk pindah halaman",
                "p:<halaman> atau hal:<halaman> untuk lompat cepat",
            ],
        )

    if state in {"package_detail_menu", "await_ewallet_method", "await_ewallet_number", "await_decoy_qris_manual_amount", "await_balance_n_count", "await_balance_n_delay", "await_balance_n_decoy", "await_balance_n_running"}:
        return (
            "Anda sedang di flow pembayaran. Ikuti langkah yang diminta satu per satu.",
            [
                "Pulsa N Kali: isi N -> delay -> decoy",
                "Saat running, gunakan tombol Batal Progress untuk stop session",
            ],
        )

    return (
        "Masukkan data sesuai format yang diminta pada panel.",
        [
            "Gunakan Home/Batal untuk kembali",
            "Jika ragu, kirim ulang input dengan format contoh",
        ],
    )


def _get_active_context() -> tuple[str | None, dict | None]:
    active_user = AuthInstance.get_active_user()
    if not active_user:
        return None, None
    return AuthInstance.api_key, active_user.get("tokens")


def _profile_summary_sync() -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif. Buka 1 👤 Akun untuk login/ganti akun."

    active_user = AuthInstance.get_active_user() or {}
    cache_key_balance = f"profile:balance:{active_user.get('number', 'na')}"
    balance = _cache_get(cache_key_balance, 30)
    if balance is None:
        balance = get_balance(api_key, tokens["id_token"]) or {}
        _cache_set(cache_key_balance, balance)
    balance = cast(dict, balance)
    point_info = "Points: N/A | Tier: N/A"

    if active_user.get("subscription_type") == "PREPAID":
        tier_cache_key = f"profile:tiering:{active_user.get('number', 'na')}"
        tiering = _cache_get(tier_cache_key, 60)
        if tiering is None:
            tiering = get_tiering_info(api_key, tokens) or {}
            _cache_set(tier_cache_key, tiering)
        tiering = cast(dict, tiering)
        point_info = f"Points: {tiering.get('current_point', 0)} | Tier: {tiering.get('tier', 0)}"

    expired_at = balance.get("expired_at")
    if expired_at:
        expired_text = datetime.fromtimestamp(expired_at).strftime("%Y-%m-%d")
    else:
        expired_text = "N/A"

    return (
        "Akun aktif\n"
        f"Nomor: {active_user.get('number', 'N/A')}\n"
        f"Subscription: {active_user.get('subscription_type', 'N/A')}\n"
        f"Pulsa: Rp {balance.get('remaining', 'N/A')}\n"
        f"Aktif sampai: {expired_text}\n"
        f"{point_info}"
    )


def _home_panel_text_sync() -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return build_home_guest_panel()

    active_user = AuthInstance.get_active_user() or {}
    cache_key_balance = f"profile:balance:{active_user.get('number', 'na')}"
    balance = _cache_get(cache_key_balance, 30)
    if balance is None:
        balance = get_balance(api_key, tokens["id_token"]) or {}
        _cache_set(cache_key_balance, balance)
    balance = cast(dict, balance)

    points = "N/A"
    tier = "N/A"
    if active_user.get("subscription_type") == "PREPAID":
        tier_cache_key = f"profile:tiering:{active_user.get('number', 'na')}"
        tiering = _cache_get(tier_cache_key, 60)
        if tiering is None:
            tiering = get_tiering_info(api_key, tokens) or {}
            _cache_set(tier_cache_key, tiering)
        tiering = cast(dict, tiering)
        points = str(tiering.get("current_point", "N/A"))
        tier = str(tiering.get("tier", "N/A"))

    expired_at = balance.get("expired_at")
    if expired_at:
        expired_text = datetime.fromtimestamp(expired_at).strftime("%Y-%m-%d")
    else:
        expired_text = "N/A"

    number = str(active_user.get("number", "N/A"))
    subs_type = str(active_user.get("subscription_type", "N/A"))
    balance_value = balance.get("remaining", "N/A")

    # Fancy theme for PRIO variants, compact for others.
    is_fancy = subs_type.upper().startswith("PRIO")
    if is_fancy:
        return build_home_fancy_panel(number, subs_type, str(balance_value), expired_text, points, tier)

    return build_home_compact_panel(number, subs_type, str(balance_value), expired_text, points, tier)


def _my_packages_sync(limit: int = 15) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    path = "api/v8/packages/quota-details"
    payload = {"is_enterprise": False, "lang": "en", "family_member_id": ""}
    res = send_api_request(api_key, path, payload, tokens["id_token"], "POST")
    if not isinstance(res, dict) or res.get("status") != "SUCCESS":
        return "Gagal mengambil paket saya."

    quotas = res.get("data", {}).get("quotas", [])
    if not quotas:
        return "Tidak ada paket aktif."

    lines = ["Paket saya:"]
    for idx, quota in enumerate(quotas[:limit], start=1):
        name = quota.get("name", "N/A")
        benefits = quota.get("benefits", [])
        brief = ""
        if benefits:
            benefit = benefits[0]
            data_type = benefit.get("data_type", "")
            remaining = benefit.get("remaining", 0)
            total = benefit.get("total", 0)
            if data_type == "DATA":
                brief = f" | {format_quota_byte(remaining)} / {format_quota_byte(total)}"
            elif data_type == "VOICE":
                brief = f" | {remaining/60:.1f}/{total/60:.1f} menit"
            elif data_type == "TEXT":
                brief = f" | {remaining}/{total} SMS"
        lines.append(f"{idx}. {name}{brief}")

    if len(quotas) > limit:
        lines.append(f"... dan {len(quotas) - limit} paket lain")
    return "\n".join(lines)


def _render_packages_page(packages: list[dict], page: int, page_size: int = 10) -> str:
    total = len(packages)
    if total == 0:
        return "Tidak ada paket aktif."

    max_page = max(0, (total - 1) // page_size)
    page = max(0, min(page, max_page))
    start = page * page_size
    end = min(total, start + page_size)

    lines: list[str] = []
    for idx in range(start, end):
        pkg = packages[idx]
        lines.append(f"{idx + 1}. {pkg.get('name', 'N/A')}{pkg.get('brief', '')}")
    lines.append("Aksi menu Paket: 🔄 Refresh, 🧾 Detail, ⛔ Unsub")
    return build_paged_list_panel("Paket saya", lines, page, max_page)


def _my_packages_menu_sync(limit: int = 120) -> tuple[str, list[dict]]:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif.", []

    active_user = AuthInstance.get_active_user() or {}
    cache_key = f"packages:list:{active_user.get('number', 'na')}"
    cached = _cache_get(cache_key, 45)
    if isinstance(cached, list):
        return _render_packages_page(cached, 0), cached

    path = "api/v8/packages/quota-details"
    payload = {"is_enterprise": False, "lang": "en", "family_member_id": ""}
    res = send_api_request(api_key, path, payload, tokens["id_token"], "POST")
    if not isinstance(res, dict) or res.get("status") != "SUCCESS":
        return "Gagal mengambil paket saya.", []

    quotas = res.get("data", {}).get("quotas", [])
    if not quotas:
        return "Tidak ada paket aktif.", []

    mapped: list[dict] = []
    lines = ["Paket saya:"]
    for idx, quota in enumerate(quotas[:limit], start=1):
        name = quota.get("name", "N/A")
        quota_code = quota.get("quota_code", "")
        product_subscription_type = quota.get("product_subscription_type", "")
        product_domain = quota.get("product_domain", "")

        brief = ""
        benefits = quota.get("benefits", [])
        if benefits:
            b = benefits[0]
            dtype = b.get("data_type", "")
            remaining = b.get("remaining", 0)
            total = b.get("total", 0)
            if dtype == "DATA":
                brief = f" | {format_quota_byte(remaining)} / {format_quota_byte(total)}"
            elif dtype == "VOICE":
                brief = f" | {remaining/60:.1f}/{total/60:.1f} menit"
            elif dtype == "TEXT":
                brief = f" | {remaining}/{total} SMS"

        mapped_brief = brief
        mapped.append(
            {
                "name": name,
                "quota_code": quota_code,
                "product_subscription_type": product_subscription_type,
                "product_domain": product_domain,
                "brief": mapped_brief,
            }
        )

    _cache_set(cache_key, mapped)
    return _render_packages_page(mapped, 0), mapped


def _unsubscribe_package_sync(pkg: dict) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    ok = unsubscribe(
        api_key,
        tokens,
        pkg.get("quota_code", ""),
        pkg.get("product_subscription_type", ""),
        pkg.get("product_domain", ""),
    )
    if ok:
        _cache_invalidate(["packages:list:", "profile:balance:"])
        return f"Berhasil unsubscribe: {pkg.get('name', 'N/A')}"
    return f"Gagal unsubscribe: {pkg.get('name', 'N/A')}"


def _history_sync(limit: int = 10) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    active_user = AuthInstance.get_active_user() or {}
    cache_key = f"history:{active_user.get('number', 'na')}"
    data = _cache_get(cache_key, 20)
    if data is None:
        data = get_transaction_history(api_key, tokens) or {}
        _cache_set(cache_key, data)
    rows = data.get("list", []) if isinstance(data, dict) else []
    if not rows:
        return "Riwayat transaksi kosong."

    lines: list[str] = []
    for idx, row in enumerate(rows[:limit], start=1):
        lines.append(f"{idx}. {row.get('title', 'N/A')} | {row.get('price', 'N/A')} | {row.get('status', 'N/A')}")
    return build_panel("Riwayat transaksi:", lines)


def _notifications_sync(mark_all: bool = False, limit: int = 10) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    active_user = AuthInstance.get_active_user() or {}
    cache_key = f"notif:{active_user.get('number', 'na')}"
    data = _cache_get(cache_key, 20)
    if data is None or mark_all:
        data = dashboard_segments(api_key, tokens)
        _cache_set(cache_key, data)
    rows = data.get("data", {}).get("notification", {}).get("data", []) if isinstance(data, dict) else []
    if not rows:
        return "Tidak ada notifikasi."

    if mark_all:
        for item in rows:
            if item.get("is_read"):
                continue
            nid = item.get("notification_id")
            if nid:
                get_notification_detail(api_key, tokens, nid)
        _cache_invalidate(["notif:"])

    unread = 0
    lines: list[str] = []
    for idx, item in enumerate(rows[:limit], start=1):
        status = "READ" if item.get("is_read") else "UNREAD"
        if status == "UNREAD":
            unread += 1
        lines.append(f"{idx}. [{status}] {item.get('brief_message', 'N/A')}")
    lines.append(f"Total: {len(rows)} | Unread: {unread}")
    if not mark_all:
        lines.append("Kirim: mark all notif")
    return build_panel("Notifikasi:", lines)


def _load_hot_file_sync(filename: str) -> list[dict]:
    with open(ROOT_DIR / "hot_data" / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def _hot_list_text(hot_packages: list[dict], page: int = 0) -> str:
    return render_hot_page(hot_packages, page, 10)


def _resolve_hot_option_code_sync(selected_hot: dict) -> str | None:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return None

    family_data = get_family(
        api_key,
        tokens,
        selected_hot.get("family_code", ""),
        selected_hot.get("is_enterprise", False),
    )
    if not family_data:
        return None

    for variant in family_data.get("package_variants", []):
        if variant.get("name") != selected_hot.get("variant_name"):
            continue
        for option in variant.get("package_options", []):
            if option.get("order") == selected_hot.get("order"):
                return option.get("package_option_code")
    return None


def _package_detail_text_sync(option_code: str) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    package = get_package(api_key, tokens, option_code)
    if not package:
        return "Paket tidak ditemukan atau gagal diambil."

    option = package.get("package_option", {})
    family = package.get("package_family", {})

    benefit_lines: list[str] = []
    benefits = option.get("benefits", [])
    if benefits:
        for benefit in benefits:
            b_type = benefit.get("data_type", "")
            total = benefit.get("total", 0)
            if b_type == "DATA":
                total = format_quota_byte(total)
            elif b_type == "VOICE":
                total = f"{total/60:.1f} menit"
            elif b_type == "TEXT":
                total = f"{total} SMS"
            benefit_lines.append(f"- {benefit.get('name', '')} ({b_type}): {total}")

    package_name = f"{family.get('name', '')} - {option.get('name', '')}".strip(" -")
    return build_package_detail_panel(
        package_name,
        str(option.get("price", "N/A")),
        str(option.get("validity", "N/A")),
        str(option.get("point", "N/A")),
        str(family.get("payment_for", "N/A")),
        option_code,
        benefit_lines,
    )


def _package_payment_context_sync(option_code: str) -> dict | None:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return None

    package = get_package(api_key, tokens, option_code)
    if not package:
        return None

    option = package.get("package_option", {})
    family = package.get("package_family", {})
    payment_for = family.get("payment_for", "") or "BUY_PACKAGE"
    item = {
        "item_code": option_code,
        "product_type": "",
        "item_price": int(option.get("price", 0)),
        "item_name": option.get("name", "") or "Package",
        "tax": 0,
        "token_confirmation": package.get("token_confirmation", ""),
    }
    return {
        "option_code": option_code,
        "title": f"{family.get('name', '')} - {option.get('name', '')}".strip(" -"),
        "price": int(option.get("price", 0)),
        "payment_for": payment_for,
        "items": [item],
    }


def _pay_balance_sync(payment_ctx: dict) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    res = settlement_balance(
        api_key,
        tokens,
        payment_ctx.get("items", []),
        payment_ctx.get("payment_for", "BUY_PACKAGE"),
        False,
        overwrite_amount=int(payment_ctx.get("price", 0)),
    )
    if isinstance(res, dict) and res.get("status") == "SUCCESS":
        _cache_invalidate(["packages:list:", "profile:balance:", "history:"])
        return "Pembayaran Pulsa berhasil dibuat. Cek status di aplikasi MyXL."
    return f"Pembayaran Pulsa gagal.\n{json.dumps(res, indent=2) if isinstance(res, dict) else str(res)}"


def _pay_balance_n_sync(payment_ctx: dict, count: int, delay_sec: int, use_decoy: bool) -> str:
    if count <= 0:
        return "Jumlah N harus lebih dari 0."
    if delay_sec < 0:
        return "Delay tidak boleh negatif."

    ok = 0
    fail = 0
    last_error = ""
    mode = "decoy" if use_decoy else "normal"
    for i in range(count):
        if use_decoy:
            result = _pay_decoy_balance_sync(payment_ctx, False)
            success = result.startswith("Pembayaran Pulsa+Decoy berhasil")
        else:
            result = _pay_balance_sync(payment_ctx)
            success = result.startswith("Pembayaran Pulsa berhasil")

        if success:
            ok += 1
        else:
            fail += 1
            last_error = result

        if delay_sec > 0 and i < (count - 1):
            time.sleep(delay_sec)

    summary = f"Pulsa N Kali ({mode}) selesai. Berhasil: {ok}, Gagal: {fail}, Total: {count}, Delay: {delay_sec} detik."
    if last_error:
        return summary + "\n\nError terakhir:\n" + last_error
    return summary


def _pay_qris_sync(payment_ctx: dict) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    tx_id = settlement_qris(
        api_key,
        tokens,
        payment_ctx.get("items", []),
        payment_ctx.get("payment_for", "BUY_PACKAGE"),
        False,
        overwrite_amount=int(payment_ctx.get("price", 0)),
    )
    if not tx_id or not isinstance(tx_id, str):
        return "Gagal membuat transaksi QRIS."

    qris_code = get_qris_code(api_key, tokens, tx_id)
    if not qris_code:
        return f"Transaksi QRIS berhasil dibuat (ID: {tx_id}) tapi gagal ambil kode QR."

    qris_b64 = base64.urlsafe_b64encode(str(qris_code).encode()).decode()
    qris_url = f"https://ki-ar-kod.netlify.app/?data={qris_b64}"
    _cache_invalidate(["packages:list:", "profile:balance:", "history:"])
    return f"QRIS siap dibayar.\nTransaction ID: {tx_id}\nLink QR: {qris_url}"


def _pay_ewallet_sync(payment_ctx: dict, method: str, wallet_number: str = "") -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    res = settlement_multipayment(
        api_key,
        tokens,
        payment_ctx.get("items", []),
        wallet_number,
        method,
        payment_ctx.get("payment_for", "BUY_PACKAGE"),
        False,
        overwrite_amount=int(payment_ctx.get("price", 0)),
    )
    if isinstance(res, dict) and res.get("status") == "SUCCESS":
        _cache_invalidate(["packages:list:", "profile:balance:", "history:"])
        deeplink = res.get("data", {}).get("deeplink", "")
        if deeplink:
            return f"Pembayaran {method} berhasil dibuat.\nLink bayar: {deeplink}"
        return f"Pembayaran {method} berhasil dibuat. Lanjutkan di aplikasi e-wallet."

    return f"Pembayaran {method} gagal.\n{json.dumps(res, indent=2) if isinstance(res, dict) else str(res)}"


def _extract_valid_amount_from_error(res: dict | str | None) -> int | None:
    if not isinstance(res, dict):
        return None
    msg = str(res.get("message", ""))
    if "Bizz-err.Amount.Total" not in msg or "=" not in msg:
        return None
    try:
        return int(msg.split("=")[-1].strip())
    except Exception:
        return None


def _build_decoy_items_sync(payment_ctx: dict, decoy_type: str) -> tuple[list[PaymentItem], int, str] | None:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return None

    decoy = DecoyInstance.get_decoy(decoy_type)
    if not decoy:
        return None

    decoy_package = get_package(api_key, tokens, decoy.get("option_code", ""))
    if not decoy_package:
        return None

    main_items = payment_ctx.get("items", [])
    if not main_items:
        return None

    items: list[PaymentItem] = [cast(PaymentItem, item) for item in main_items]
    decoy_item: PaymentItem = {
        "item_code": decoy_package.get("package_option", {}).get("package_option_code", ""),
        "product_type": "",
        "item_price": int(decoy_package.get("package_option", {}).get("price", 0)),
        "item_name": decoy_package.get("package_option", {}).get("name", "Decoy"),
        "tax": 0,
        "token_confirmation": decoy_package.get("token_confirmation", ""),
    }
    items.append(decoy_item)

    total = int(payment_ctx.get("price", 0)) + int(decoy_item.get("item_price", 0))
    return items, total, decoy_type


def _pay_decoy_balance_sync(payment_ctx: dict, v2: bool = False) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    built = _build_decoy_items_sync(payment_ctx, "balance")
    if not built:
        return "Gagal memuat paket decoy balance."
    items, total, _ = built

    payment_for = "🤫" if v2 else payment_ctx.get("payment_for", "BUY_PACKAGE")
    token_idx = 1 if v2 else 0
    res = settlement_balance(
        api_key,
        tokens,
        items,
        payment_for,
        False,
        overwrite_amount=total,
        token_confirmation_idx=token_idx,
    )

    if isinstance(res, dict) and res.get("status") == "SUCCESS":
        _cache_invalidate(["packages:list:", "profile:balance:", "history:"])
        return "Pembayaran Pulsa+Decoy berhasil dibuat."

    valid_amount = _extract_valid_amount_from_error(res)
    if valid_amount is not None:
        retry_idx = -1 if v2 else token_idx
        retry_res = settlement_balance(
            api_key,
            tokens,
            items,
            payment_for,
            False,
            overwrite_amount=valid_amount,
            token_confirmation_idx=retry_idx,
        )
        if isinstance(retry_res, dict) and retry_res.get("status") == "SUCCESS":
            _cache_invalidate(["packages:list:", "profile:balance:", "history:"])
            return f"Pembayaran Pulsa+Decoy berhasil setelah penyesuaian amount: {valid_amount}."
        return f"Pulsa+Decoy gagal setelah retry.\n{json.dumps(retry_res, indent=2) if isinstance(retry_res, dict) else str(retry_res)}"

    return f"Pulsa+Decoy gagal.\n{json.dumps(res, indent=2) if isinstance(res, dict) else str(res)}"


def _pay_decoy_qris_sync(payment_ctx: dict, decoy_type: str) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    built = _build_decoy_items_sync(payment_ctx, decoy_type)
    if not built:
        return "Gagal memuat paket decoy QRIS."
    items, total, _ = built

    tx_id = settlement_qris(
        api_key,
        tokens,
        items,
        "SHARE_PACKAGE",
        False,
        overwrite_amount=total,
        token_confirmation_idx=1,
    )
    if not tx_id or not isinstance(tx_id, str):
        return "Gagal membuat transaksi QRIS+Decoy."

    qris_code = get_qris_code(api_key, tokens, tx_id)
    if not qris_code:
        return f"Transaksi QRIS+Decoy berhasil dibuat (ID: {tx_id}) tapi gagal ambil kode QR."

    qris_b64 = base64.urlsafe_b64encode(str(qris_code).encode()).decode()
    qris_url = f"https://ki-ar-kod.netlify.app/?data={qris_b64}"
    label = "QRIS+Decoy V2" if decoy_type == "qris0" else "QRIS+Decoy"
    _cache_invalidate(["packages:list:", "profile:balance:", "history:"])
    return f"{label} siap dibayar.\nAmount: {total}\nTransaction ID: {tx_id}\nLink QR: {qris_url}"


def _pay_decoy_qris_manual_sync(payment_ctx: dict, decoy_type: str, amount: int) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    built = _build_decoy_items_sync(payment_ctx, decoy_type)
    if not built:
        return "Gagal memuat paket decoy QRIS."
    items, _, _ = built

    tx_id = settlement_qris(
        api_key,
        tokens,
        items,
        "SHARE_PACKAGE",
        False,
        overwrite_amount=amount,
        token_confirmation_idx=1,
    )
    if not tx_id or not isinstance(tx_id, str):
        return "Gagal membuat transaksi QRIS+Decoy manual."

    qris_code = get_qris_code(api_key, tokens, tx_id)
    if not qris_code:
        return f"Transaksi QRIS+Decoy manual berhasil dibuat (ID: {tx_id}) tapi gagal ambil kode QR."

    qris_b64 = base64.urlsafe_b64encode(str(qris_code).encode()).decode()
    qris_url = f"https://ki-ar-kod.netlify.app/?data={qris_b64}"
    label = "QRIS+Decoy V2 Manual" if decoy_type == "qris0" else "QRIS+Decoy Manual"
    _cache_invalidate(["packages:list:", "profile:balance:", "history:"])
    return f"{label} siap dibayar.\nAmount manual: {amount}\nTransaction ID: {tx_id}\nLink QR: {qris_url}"


def _family_list_text_sync(family_code: str) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    data = get_family(api_key, tokens, family_code)
    if not data:
        return "Family code tidak ditemukan atau gagal diambil."

    family = data.get("package_family", {})
    lines = [f"Family: {family.get('name', 'N/A')}", f"Code: {family_code}", "Daftar paket:"]

    count = 0
    for variant in data.get("package_variants", []):
        for option in variant.get("package_options", []):
            count += 1
            lines.append(
                f"{count}. {variant.get('name', 'N/A')} - {option.get('name', 'N/A')} | Rp {option.get('price', 'N/A')} | order={option.get('order', 'N/A')}"
            )
            if count >= 25:
                lines.append("... dibatasi 25 item")
                return "\n".join(lines)
    return "\n".join(lines)


def _family_options_sync(family_code: str) -> tuple[str, list[dict]]:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif.", []

    data = get_family(api_key, tokens, family_code)
    if not data:
        return "Family code tidak ditemukan atau gagal diambil.", []

    family = data.get("package_family", {})
    mapped: list[dict] = []
    for variant in data.get("package_variants", []):
        for option in variant.get("package_options", []):
            mapped.append(
                {
                    "option_code": option.get("package_option_code", ""),
                    "label": f"{variant.get('name', 'N/A')} - {option.get('name', 'N/A')} | Rp {option.get('price', 'N/A')} | order={option.get('order', 'N/A')}",
                }
            )

    if not mapped:
        return f"Family {family.get('name', 'N/A')} tidak punya package option.", []

    header = f"Family: {family.get('name', 'N/A')} | Code: {family_code}\nTotal opsi: {len(mapped)}"
    return header + "\n\n" + render_items_page("Family Packages", mapped, 0, 10), mapped


def _account_summary_sync() -> str:
    AuthInstance.load_tokens()
    users = AuthInstance.refresh_tokens
    active_user = AuthInstance.get_active_user()

    lines = ["Akun tersimpan:"]
    if not users:
        lines.append("(kosong)")
    for idx, user in enumerate(users, start=1):
        active_mark = " ✅" if active_user and user.get("number") == active_user.get("number") else ""
        lines.append(f"{idx}. {user.get('number')} [{user.get('subscription_type', 'N/A')}]" + active_mark)

    lines.append("Perintah:")
    lines.append("- ➕ Tambah Akun")
    lines.append("- 🔁 Ganti Akun")
    lines.append("- 🗑 Hapus Akun")
    return "\n".join(lines)


def _switch_account_sync(index_1based: int) -> str:
    AuthInstance.load_tokens()
    users = AuthInstance.refresh_tokens
    if index_1based < 1 or index_1based > len(users):
        return "Nomor akun tidak valid."
    number = users[index_1based - 1]["number"]
    AuthInstance.set_active_user(number)
    return f"Akun aktif diganti ke {number}."


def _delete_account_sync(index_1based: int) -> str:
    AuthInstance.load_tokens()
    users = AuthInstance.refresh_tokens
    active = AuthInstance.get_active_user() or {}
    if index_1based < 1 or index_1based > len(users):
        return "Nomor akun tidak valid."

    target = users[index_1based - 1]
    if active and target.get("number") == active.get("number"):
        return "Tidak bisa hapus akun aktif. Ganti akun aktif dulu."

    AuthInstance.remove_refresh_token(target["number"])
    return f"Akun {target['number']} dihapus."


def _store_segments_sync(is_enterprise: bool = False, limit: int = 30) -> tuple[str, list[dict]]:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif.", []

    res = get_segments(api_key, tokens, is_enterprise)
    if not isinstance(res, dict):
        return "Gagal mengambil store segments.", []

    segments = res.get("data", {}).get("store_segments", [])
    if not segments:
        return "Store segments kosong.", []

    mapped: list[dict] = []
    item_no = 0
    for seg in segments:
        seg_title = seg.get("title", "N/A")
        for banner in seg.get("banners", []):
            item_no += 1
            mapped.append(
                {
                    "action_type": banner.get("action_type", ""),
                    "action_param": banner.get("action_param", ""),
                    "label": f"[{seg_title}] {banner.get('family_name', 'N/A')} - {banner.get('title', 'N/A')} | Rp{banner.get('discounted_price', 'N/A')}",
                }
            )
            if item_no >= limit:
                return render_items_page("Store Segments", mapped, 0, 10), mapped
    return render_items_page("Store Segments", mapped, 0, 10), mapped


def _store_family_list_sync(subs_type: str = "PREPAID", is_enterprise: bool = False, limit: int = 30) -> tuple[str, list[dict]]:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif.", []

    res = get_family_list(api_key, tokens, subs_type, is_enterprise)
    if not isinstance(res, dict):
        return "Gagal mengambil family list.", []

    items = res.get("data", {}).get("results", [])
    if not items:
        return "Family list kosong.", []

    mapped: list[dict] = []
    for idx, family in enumerate(items[:limit], start=1):
        mapped.append({"family_code": family.get("id", ""), "label": f"{family.get('label', 'N/A')} | code={family.get('id', 'N/A')}"})
    return render_items_page("Store Family List", mapped, 0, 10), mapped


def _store_packages_sync(subs_type: str = "PREPAID", is_enterprise: bool = False, limit: int = 30) -> tuple[str, list[dict]]:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif.", []

    res = get_store_packages(api_key, tokens, subs_type, is_enterprise)
    if not isinstance(res, dict):
        return "Gagal mengambil store packages.", []

    items = res.get("data", {}).get("results_price_only", [])
    if not items:
        return "Store packages kosong.", []

    mapped: list[dict] = []
    for idx, pkg in enumerate(items[:limit], start=1):
        mapped.append({"action_type": pkg.get("action_type", ""), "action_param": pkg.get("action_param", "")})
        price = pkg.get("discounted_price", 0) or pkg.get("original_price", 0)
        mapped[-1]["label"] = f"{pkg.get('title', 'N/A')} | {pkg.get('family_name', 'N/A')} | Rp{price}"
    return render_items_page("Store Packages", mapped, 0, 10), mapped


def _redeemables_sync(is_enterprise: bool = False, limit: int = 30) -> tuple[str, list[dict]]:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif.", []

    res = get_redeemables(api_key, tokens, is_enterprise)
    if not isinstance(res, dict):
        return "Gagal mengambil redeemables.", []

    categories = res.get("data", {}).get("categories", [])
    if not categories:
        return "Redeemables kosong.", []

    mapped: list[dict] = []
    n = 0
    for cat in categories:
        cat_name = cat.get("category_name", "N/A")
        for item in cat.get("redeemables", []):
            n += 1
            mapped.append({
                "action_type": item.get("action_type", ""),
                "action_param": item.get("action_param", ""),
                "label": f"[{cat_name}] {item.get('name', 'N/A')} | {item.get('action_type', 'N/A')}",
            })
            if n >= limit:
                return render_items_page("Redeemables", mapped, 0, 10), mapped
    return render_items_page("Redeemables", mapped, 0, 10), mapped


def _bookmark_text_sync() -> str:
    bookmarks = BookmarkInstance.get_bookmarks()
    lines: list[str] = []
    if not bookmarks:
        lines.append("(kosong)")
    for idx, b in enumerate(bookmarks, start=1):
        lines.append(
            f"{idx}. {b.get('family_name', '')} | {b.get('family_code', '')} | {b.get('variant_name', '')} | {b.get('option_name', '')} | order={b.get('order', 0)}"
        )
    lines.append("Kirim: add bookmark")
    lines.append("Kirim: del bookmark")
    return build_panel("Bookmark paket:", lines)


def _bookmark_remove_sync(index_1based: int) -> str:
    bookmarks = BookmarkInstance.get_bookmarks()
    if index_1based < 1 or index_1based > len(bookmarks):
        return "Nomor bookmark tidak valid."

    b = bookmarks[index_1based - 1]
    ok = BookmarkInstance.remove_bookmark(
        b.get("family_code", ""),
        bool(b.get("is_enterprise", False)),
        b.get("variant_name", ""),
        int(b.get("order", 0)),
    )
    return "Bookmark dihapus." if ok else "Gagal hapus bookmark."


def _bookmark_add_sync(family_code: str, is_enterprise: bool, variant_name: str, option_name: str, order: int) -> str:
    api_key, tokens = _get_active_context()
    family_name = ""
    if api_key and tokens:
        family = get_family(api_key, tokens, family_code, is_enterprise)
        if family:
            family_name = family.get("package_family", {}).get("name", "")

    ok = BookmarkInstance.add_bookmark(
        family_code=family_code,
        family_name=family_name,
        is_enterprise=is_enterprise,
        variant_name=variant_name,
        option_name=option_name,
        order=order,
    )
    return "Bookmark ditambahkan." if ok else "Bookmark sudah ada."


def _purchase_family_loop_sync(family_code: str, start_from_option: int, delay_seconds: int) -> str:
    old_pause = purchase_menu.pause
    purchase_menu.pause = lambda: None
    try:
        purchase_menu.purchase_by_family(
            family_code=family_code,
            use_decoy=False,
            pause_on_success=False,
            delay_seconds=delay_seconds,
            start_from_option=start_from_option,
        )
        return "Loop purchase selesai (mode non-decoy)."
    except Exception as e:
        return f"Loop purchase gagal: {e}"
    finally:
        purchase_menu.pause = old_pause


def _famplan_snapshot_sync() -> tuple[str, list[dict]]:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif.", []

    res = get_family_data(api_key, tokens)
    detail = res.get("data", {}) if isinstance(res, dict) else {}
    member_info = detail.get("member_info", {})
    plan_type = member_info.get("plan_type", "")
    if not plan_type:
        return "Akun ini bukan organizer Family Plan.", []

    members = member_info.get("members", [])
    total_quota = format_quota_byte(member_info.get("total_quota", 0))
    remaining_quota = format_quota_byte(member_info.get("remaining_quota", 0))

    lines = [
        f"FamPlan: {plan_type}",
        f"Parent: {member_info.get('parent_msisdn', 'N/A')}",
        f"Quota: {remaining_quota} / {total_quota}",
        "Members:",
    ]

    mapped: list[dict] = []
    for idx, m in enumerate(members, start=1):
        mapped.append(m)
        msisdn = m.get("msisdn") or "<Empty Slot>"
        alias = m.get("alias", "N/A")
        usage = m.get("usage", {})
        lines.append(
            f"{idx}. {msisdn} ({alias}) | used {format_quota_byte(usage.get('quota_used', 0))}/{format_quota_byte(usage.get('quota_allocated', 0))}"
        )

    lines.append("Aksi:")
    lines.append("- 👥 Ganti Member: slot|msisdn|alias_parent|alias_member")
    lines.append("- 🗑 Hapus Member: slot")
    lines.append("- 📏 Set Limit: slot|mb")
    return "\n".join(lines), mapped


def _famplan_change_sync(slot_idx: int, msisdn: str, parent_alias: str, child_alias: str) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    res = get_family_data(api_key, tokens)
    members = res.get("data", {}).get("member_info", {}).get("members", [])
    if slot_idx < 1 or slot_idx > len(members):
        return "Slot tidak valid."

    slot = members[slot_idx - 1]
    if slot.get("msisdn"):
        return "Slot tidak kosong."

    validation = validate_msisdn(api_key, tokens, msisdn)
    if str(validation.get("status", "")).upper() != "SUCCESS":
        return "MSISDN tidak valid untuk Family Plan."

    result = change_member(
        api_key,
        tokens,
        parent_alias,
        child_alias,
        slot.get("slot_id"),
        slot.get("family_member_id"),
        msisdn,
    )
    return json.dumps(result, indent=2)


def _famplan_remove_sync(slot_idx: int) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    res = get_family_data(api_key, tokens)
    members = res.get("data", {}).get("member_info", {}).get("members", [])
    if slot_idx < 1 or slot_idx > len(members):
        return "Slot tidak valid."

    slot = members[slot_idx - 1]
    if not slot.get("msisdn"):
        return "Slot sudah kosong."

    result = remove_member(api_key, tokens, slot.get("family_member_id"))
    return json.dumps(result, indent=2)


def _famplan_limit_sync(slot_idx: int, mb: int) -> str:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif."

    res = get_family_data(api_key, tokens)
    members = res.get("data", {}).get("member_info", {}).get("members", [])
    if slot_idx < 1 or slot_idx > len(members):
        return "Slot tidak valid."

    slot = members[slot_idx - 1]
    if not slot.get("msisdn"):
        return "Slot kosong."

    result = set_quota_limit(
        api_key,
        tokens,
        slot.get("usage", {}).get("quota_allocated", 0),
        mb * 1024 * 1024,
        slot.get("family_member_id"),
    )
    return json.dumps(result, indent=2)


def _circle_snapshot_sync() -> tuple[str, dict]:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif.", {}

    grp = get_group_data(api_key, tokens)
    data = grp.get("data", {}) if isinstance(grp, dict) else {}
    group_id = data.get("group_id", "")
    if not group_id:
        return "Akun tidak tergabung Circle.", {}

    members_res = get_group_members(api_key, tokens, group_id)
    members_data = members_res.get("data", {}) if isinstance(members_res, dict) else {}
    members = members_data.get("members", [])

    parent_member_id = ""
    parent_subs_id = ""
    for m in members:
        if m.get("member_role") == "PARENT":
            parent_member_id = m.get("member_id", "")
            parent_subs_id = m.get("subscriber_number", "")
            break

    spend = spending_tracker(api_key, tokens, parent_subs_id, group_id).get("data", {})

    lines = [
        f"Circle: {data.get('group_name', 'N/A')} ({data.get('group_status', 'N/A')})",
        f"Owner: {data.get('owner_name', 'N/A')}",
        f"Spending: Rp{spend.get('spend', 0)} / Rp{spend.get('target', 0)}",
        "Members:",
    ]

    for idx, member in enumerate(members, start=1):
        msisdn = decrypt_circle_msisdn(api_key, member.get("msisdn", ""))
        lines.append(f"{idx}. {msisdn or '<No Number>'} | {member.get('member_name', 'N/A')} | {member.get('member_role', 'N/A')}")

    lines.append("Aksi:")
    lines.append("- ➕ Invite Circle: msisdn|nama")
    lines.append("- 🗑 Remove Circle: nomor member")
    lines.append("- ✅ Accept Circle: nomor member")

    return "\n".join(lines), {
        "group_id": group_id,
        "members": members,
        "parent_member_id": parent_member_id,
        "parent_subs_id": parent_subs_id,
    }


def _circle_invite_sync(msisdn: str, name: str) -> str:
    api_key, tokens = _get_active_context()
    snap_text, snap = _circle_snapshot_sync()
    if not api_key or tokens is None or not snap:
        return "Circle tidak tersedia."

    res = invite_circle_member(
        api_key,
        tokens,
        msisdn,
        name,
        snap.get("group_id", ""),
        snap.get("parent_member_id", ""),
    )
    return json.dumps(res, indent=2)


def _circle_remove_sync(member_index_1based: int) -> str:
    api_key, tokens = _get_active_context()
    snap_text, snap = _circle_snapshot_sync()
    if not api_key or tokens is None or not snap:
        return "Circle tidak tersedia."

    members = snap.get("members", [])
    if member_index_1based < 1 or member_index_1based > len(members):
        return "Nomor member tidak valid."

    member = members[member_index_1based - 1]
    res = remove_circle_member(
        api_key,
        tokens,
        member.get("member_id", ""),
        snap.get("group_id", ""),
        snap.get("parent_member_id", ""),
        False,
    )
    return json.dumps(res, indent=2)


def _circle_accept_sync(member_index_1based: int) -> str:
    api_key, tokens = _get_active_context()
    snap_text, snap = _circle_snapshot_sync()
    if not api_key or tokens is None or not snap:
        return "Circle tidak tersedia."

    members = snap.get("members", [])
    if member_index_1based < 1 or member_index_1based > len(members):
        return "Nomor member tidak valid."

    member = members[member_index_1based - 1]
    res = accept_circle_invitation(
        api_key,
        tokens,
        snap.get("group_id", ""),
        member.get("member_id", ""),
    )
    return json.dumps(res, indent=2)


def _circle_bonuses_sync() -> tuple[str, list[dict]]:
    api_key, tokens = _get_active_context()
    if not api_key or tokens is None:
        return "Belum ada akun aktif.", []

    snap_text, snap = _circle_snapshot_sync()
    if not snap:
        return "Circle tidak tersedia.", []

    bonus = get_bonus_data(api_key, tokens, snap.get("parent_subs_id", ""), snap.get("group_id", ""))
    rows = bonus.get("data", {}).get("bonuses", []) if isinstance(bonus, dict) else []
    if not rows:
        return "Bonus Circle kosong.", []

    mapped: list[dict] = []
    for idx, item in enumerate(rows, start=1):
        mapped.append({
            "action_type": item.get("action_type", ""),
            "action_param": item.get("action_param", ""),
            "label": f"{item.get('name', 'N/A')} | {item.get('bonus_type', 'N/A')} | {item.get('action_type', 'N/A')}",
        })
    return render_items_page("Bonus Circle", mapped, 0, 10), mapped


async def _show_package_detail_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    option_code: str,
    back_state: str,
    back_data: dict,
):
    detail_text = await asyncio.to_thread(_package_detail_text_sync, option_code)
    payment_ctx = await asyncio.to_thread(_package_payment_context_sync, option_code)
    if not payment_ctx:
        await render_panel(update, context, "Gagal memuat konteks pembayaran paket.")
        return

    set_flow(
        context,
        "package_detail_menu",
        {
            "payment_ctx": payment_ctx,
            "back_state": back_state,
            "back_data": back_data,
        },
    )
    await render_panel(
        update,
        context,
        detail_text + "\n\nPilih metode pembayaran.",
    )


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_allowed(update, context):
        return
    set_flow(context, "home", {})
    home_panel = await asyncio.to_thread(_home_panel_text_sync)
    is_first_use = bool(context.user_data is not None and not context.user_data.get("onboarding_done", False))
    if context.user_data is not None:
        context.user_data["onboarding_done"] = True
    if is_first_use:
        onboarding = build_first_use_onboarding_panel()
        await render_panel(update, context, onboarding + "\n\n" + home_panel)
        return
    await render_panel(update, context, home_panel)


async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_allowed(update, context):
        return
    set_flow(context, "home", {})
    home_panel = await asyncio.to_thread(_home_panel_text_sync)
    await render_panel(update, context, "State bot di-reset ke menu utama.\n\n" + home_panel)


async def request_access_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return

    rec = _get_user_access_record(user.id)
    if str(rec.get("status", "")) == "approved":
        await msg.reply_text("Akses Anda sudah aktif. Gunakan /start untuk membuka panel.")
        return

    await _submit_access_request(update, context)


async def _handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    t0 = time.perf_counter()
    lowered = text.lower()
    flow = get_flow(context)
    state = flow.get("state", "home")
    data = flow.get("data", {})

    if (
        text.startswith("allow_approve:")
        or text.startswith("allow_reject:")
        or text.startswith("allow_suspend:")
        or text.startswith("allow_unsuspend:")
        or text.startswith("allow_kick:")
        or text.startswith("allow_user:")
    ):
        actor_id = update.effective_user.id if update.effective_user else None
        if not is_admin_user(actor_id):
            await render_panel(update, context, "Aksi ini khusus admin.")
            return

        target_raw = text.split(":", 1)[1] if ":" in text else ""
        if not target_raw.isdigit():
            await render_panel(update, context, "Format callback approval tidak valid.")
            return

        target_id = int(target_raw)
        if text.startswith("allow_user:"):
            await render_panel(
                update,
                context,
                _admin_user_detail_text(target_id),
                keyboard_admin_user_actions(target_id),
            )
            return

        if text.startswith("allow_approve:"):
            action = "approve_request"
            label = "APPROVE"
        elif text.startswith("allow_reject:"):
            action = "reject_request"
            label = "REJECT"
        elif text.startswith("allow_suspend:"):
            action = "suspend_user"
            label = "SUSPEND"
        elif text.startswith("allow_unsuspend:"):
            action = "unsuspend_user"
            label = "UNSUSPEND"
        else:
            action = "kick_user"
            label = "KICK"

        set_flow(context, "await_admin_action_reason", {"action": action, "target_id": target_id})
        await render_panel(
            update,
            context,
            f"Aksi {label} untuk user {target_id}.\nKirim alasan (opsional), atau kirim '-' untuk tanpa alasan.",
        )
        return

    if text == "bal_n_cancel":
        chat = update.effective_chat
        if chat is None:
            await render_panel(update, context, "Konteks chat tidak ditemukan.")
            return
        _set_payment_cancel(chat.id, True)
        task = BALANCE_N_TASKS.get(chat.id)
        if task and not task.done():
            task.cancel()
            await render_panel(update, context, "Stop session diminta. Menghentikan proses Pulsa N Kali...")
            return
        await render_panel(update, context, "Tidak ada proses Pulsa N Kali yang sedang berjalan.")
        return

    if lowered.startswith("p:") or lowered.startswith("hal:"):
        raw_page = lowered[2:] if lowered.startswith("p:") else lowered[4:]
        if not raw_page.isdigit():
            await render_panel(update, context, build_error_with_next("Format jump page tidak valid.", "Gunakan p:<nomor> atau hal:<nomor>, contoh p:3."))
            return

        total = _state_total_items(state, data)
        if total <= 0:
            await render_panel(update, context, build_error_with_next("State ini tidak memiliki list untuk pagination.", "Gunakan tombol menu lain atau Home."))
            return

        page_size = 10
        max_page = max(0, (total - 1) // page_size)
        requested_page = int(raw_page)
        if requested_page < 1 or requested_page > (max_page + 1):
            await render_panel(
                update,
                context,
                build_error_with_next(
                    f"Halaman di luar jangkauan. Range valid: 1-{max_page + 1}.",
                    "Kirim ulang nomor halaman dalam range tersebut.",
                ),
            )
            return

        page = requested_page - 1
        data["page"] = page
        set_flow(context, state, data)

        if state in {"packages_menu", "await_package_detail_pick", "await_package_unsub_pick"}:
            await render_panel(update, context, _render_packages_page(data.get("packages", []), page))
        else:
            page_text = render_catalog_state_page(state, data)
            if page_text is not None:
                await render_panel(update, context, page_text)
            else:
                await render_panel(update, context, f"Halaman {page + 1}/{max_page + 1}")
        return

    if text in {"pg_prev", "pg_next"}:
        total = _state_total_items(state, data)
        if total > 0:
            page_size = 10
            max_page = max(0, (total - 1) // page_size)
            page = int(data.get("page", 0))
            page = page - 1 if text == "pg_prev" else page + 1
            page = max(0, min(page, max_page))
            data["page"] = page
            set_flow(context, state, data)
            if state in {"packages_menu", "await_package_detail_pick", "await_package_unsub_pick"}:
                await render_panel(update, context, _render_packages_page(data.get("packages", []), page))
            else:
                page_text = render_catalog_state_page(state, data)
                if page_text is not None:
                    await render_panel(update, context, page_text)
                else:
                    await render_panel(update, context, f"Halaman {page + 1}/{max_page + 1}")
            logger.info("ui_action state=%s action=%s page=%s", state, text, page)
            return

    if text in {"🏠 Home", "↩️ Batal", "Home", "Batal", "home", "cancel"}:
        set_flow(context, "home", {})
        home_panel = await asyncio.to_thread(_home_panel_text_sync)
        await render_panel(update, context, "Kembali ke menu utama.\n\n" + home_panel)
        return

    if text in {"❓ Bantuan", "Bantuan", "help"}:
        guidance, shortcuts = _state_help_content(state)
        help_panel = build_context_help_panel(state, guidance, shortcuts)
        await render_panel(update, context, help_panel)
        return

    if state == "await_login_phone":
        phone = text
        if not phone.isdigit() or not phone.startswith("628"):
            await render_panel(update, context, "Nomor tidak valid. Format: 628xxxx")
            return
        subscriber = await asyncio.to_thread(get_otp, phone)
        if not subscriber:
            await render_panel(update, context, "Gagal request OTP. Coba lagi.")
            return
        set_flow(context, "await_login_otp", {"phone": phone})
        await render_panel(update, context, f"OTP terkirim ke {phone}. Kirim 6 digit OTP.")
        return

    if state == "await_login_otp":
        phone = data.get("phone", "")
        if not text.isdigit() or len(text) != 6:
            await render_panel(update, context, "OTP harus 6 digit angka.")
            return
        tokens = await asyncio.to_thread(submit_otp, AuthInstance.api_key, "SMS", phone, text)
        if not tokens or not tokens.get("refresh_token"):
            await render_panel(update, context, "OTP salah atau gagal submit. Coba lagi.")
            return
        await asyncio.to_thread(AuthInstance.add_refresh_token, int(phone), tokens["refresh_token"])
        set_flow(context, "account_menu", {})
        await render_panel(update, context, await asyncio.to_thread(_account_summary_sync))
        return

    if state == "await_switch_idx":
        if not text.isdigit():
            await render_panel(update, context, "Kirim nomor urut akun.")
            return
        result = await asyncio.to_thread(_switch_account_sync, int(text))
        set_flow(context, "account_menu", {})
        await render_panel(update, context, result + "\n\n" + await asyncio.to_thread(_account_summary_sync))
        return

    if state == "await_delete_idx":
        if not text.isdigit():
            await render_panel(update, context, "Kirim nomor urut akun.")
            return
        result = await asyncio.to_thread(_delete_account_sync, int(text))
        set_flow(context, "account_menu", {})
        await render_panel(update, context, result + "\n\n" + await asyncio.to_thread(_account_summary_sync))
        return

    if await handle_payment_flow(
        update,
        context,
        state,
        data,
        text,
        {
            "set_flow": set_flow,
            "render_panel": render_panel,
            "run_payment_action": _run_payment_action,
            "pay_balance_sync": _pay_balance_sync,
            "pay_qris_sync": _pay_qris_sync,
            "pay_decoy_balance_sync": _pay_decoy_balance_sync,
            "pay_decoy_qris_sync": _pay_decoy_qris_sync,
            "pay_decoy_qris_manual_sync": _pay_decoy_qris_manual_sync,
            "pay_ewallet_sync": _pay_ewallet_sync,
            "start_balance_n_progress_task": _start_balance_n_progress_task,
        },
    ):
        return

    if await handle_package_flow(
        update,
        context,
        state,
        data,
        text,
        {
            "set_flow": set_flow,
            "render_panel": render_panel,
            "my_packages_menu_sync": _my_packages_menu_sync,
            "render_packages_page": _render_packages_page,
            "show_package_detail_menu": _show_package_detail_menu,
            "unsubscribe_package_sync": _unsubscribe_package_sync,
        },
    ):
        return

    if await handle_catalog_flow(
        update,
        context,
        state,
        data,
        text,
        {
            "set_flow": set_flow,
            "render_panel": render_panel,
            "resolve_hot_option_code_sync": _resolve_hot_option_code_sync,
            "show_package_detail_menu": _show_package_detail_menu,
            "family_list_text_sync": _family_list_text_sync,
        },
    ):
        return

    if state == "history_menu":
        if text in {"hist_refresh", "Refresh"}:
            out = await asyncio.to_thread(_history_sync)
            await render_panel(update, context, out)
            return

    if state == "notifications_menu":
        if text in {"notif_refresh", "Refresh"}:
            out = await asyncio.to_thread(_notifications_sync, False)
            await render_panel(update, context, out)
            return
        if text in {"notif_mark_all", "mark all notif", "Mark All"}:
            out = await asyncio.to_thread(_notifications_sync, True)
            await render_panel(update, context, out)
            return

    if state == "bookmark_menu":
        if text in {"bm_refresh", "Refresh"}:
            out = await asyncio.to_thread(_bookmark_text_sync)
            await render_panel(update, context, out)
            return
        if text in {"bm_add", "add bookmark", "Add"}:
            set_flow(context, "await_bookmark_add", {})
            await render_panel(update, context, "Kirim format: family_code|is_enterprise(0/1)|variant_name|option_name|order")
            return
        if text in {"bm_delete", "del bookmark", "Delete"}:
            count = len(BookmarkInstance.get_bookmarks())
            set_flow(context, "await_bookmark_remove", {"count": count})
            await render_panel(update, context, "Pilih nomor bookmark yang akan dihapus.")
            return

    if state == "await_option_code":
        detail_text = await asyncio.to_thread(_package_detail_text_sync, text)
        set_flow(context, "home", {})
        await render_panel(update, context, detail_text)
        return

    if state == "await_family_code":
        family_text, items = await asyncio.to_thread(_family_options_sync, text)
        if not items:
            await render_panel(update, context, family_text)
            return
        set_flow(context, "await_family_option_pick", {"items": items, "page": 0})
        await render_panel(update, context, family_text + "\n\nPilih nomor package untuk buka detail.")
        return

    if state == "await_validate_msisdn":
        api_key, tokens = _get_active_context()
        if not api_key or tokens is None:
            set_flow(context, "home", {})
            await render_panel(update, context, "Belum ada akun aktif.")
            return
        res = await asyncio.to_thread(validate_msisdn, api_key, tokens, text)
        set_flow(context, "home", {})
        await render_panel(update, context, json.dumps(res, indent=2))
        return

    if state == "await_register":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await render_panel(update, context, "Format salah. Gunakan: msisdn|nik|kk")
            return
        msisdn, nik, kk = parts
        res = await asyncio.to_thread(dukcapil, AuthInstance.api_key, msisdn, kk, nik)
        set_flow(context, "home", {})
        await render_panel(update, context, json.dumps(res, indent=2))
        return


    if state == "await_bookmark_remove":
        if not text.isdigit():
            await render_panel(update, context, "Kirim nomor bookmark.")
            return
        res = await asyncio.to_thread(_bookmark_remove_sync, int(text))
        out = await asyncio.to_thread(_bookmark_text_sync)
        set_flow(context, "bookmark_menu", {})
        await render_panel(update, context, res + "\n\n" + out)
        return

    if state == "await_bookmark_add":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 5:
            await render_panel(update, context, "Format: family_code|is_enterprise(0/1)|variant_name|option_name|order")
            return
        family_code = parts[0]
        is_enterprise = parts[1] == "1"
        variant_name = parts[2]
        option_name = parts[3]
        if not parts[4].isdigit():
            await render_panel(update, context, "order harus angka.")
            return
        res = await asyncio.to_thread(_bookmark_add_sync, family_code, is_enterprise, variant_name, option_name, int(parts[4]))
        out = await asyncio.to_thread(_bookmark_text_sync)
        set_flow(context, "bookmark_menu", {})
        await render_panel(update, context, res + "\n\n" + out)
        return

    if state == "await_purchase_loop":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await render_panel(update, context, "Format: family_code|start_order|delay_seconds")
            return
        family_code = parts[0]
        if not parts[1].isdigit() or not parts[2].isdigit():
            await render_panel(update, context, "start_order dan delay_seconds harus angka.")
            return
        res = await asyncio.to_thread(_purchase_family_loop_sync, family_code, int(parts[1]), int(parts[2]))
        set_flow(context, "home", {})
        await render_panel(update, context, res)
        return

    if state == "await_famplan_change":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 4 or not parts[0].isdigit():
            await render_panel(update, context, "Format: slot|msisdn|alias_parent|alias_member")
            return
        res = await asyncio.to_thread(_famplan_change_sync, int(parts[0]), parts[1], parts[2], parts[3])
        snap_text, members = await asyncio.to_thread(_famplan_snapshot_sync)
        set_flow(context, "famplan_menu", {"members": members})
        await render_panel(update, context, res + "\n\n" + snap_text)
        return

    if state == "await_famplan_remove":
        if not text.isdigit():
            await render_panel(update, context, "Kirim slot angka.")
            return
        res = await asyncio.to_thread(_famplan_remove_sync, int(text))
        snap_text, members = await asyncio.to_thread(_famplan_snapshot_sync)
        set_flow(context, "famplan_menu", {"members": members})
        await render_panel(update, context, res + "\n\n" + snap_text)
        return

    if state == "await_famplan_limit":
        if text.isdigit():
            set_flow(context, "await_famplan_limit_mb", {"slot": int(text)})
            await render_panel(update, context, f"Slot {text} dipilih. Kirim limit MB (contoh: 1024).")
            return

        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            await render_panel(update, context, "Pilih slot dengan tombol, atau kirim format: slot|mb")
            return
        res = await asyncio.to_thread(_famplan_limit_sync, int(parts[0]), int(parts[1]))
        snap_text, members = await asyncio.to_thread(_famplan_snapshot_sync)
        set_flow(context, "famplan_menu", {"members": members})
        await render_panel(update, context, res + "\n\n" + snap_text)
        return

    if state == "await_famplan_limit_mb":
        slot = int(data.get("slot", 0))
        if slot <= 0:
            set_flow(context, "famplan_menu", {})
            await render_panel(update, context, "State slot tidak ditemukan. Ulangi dari menu FamPlan.")
            return
        if not text.isdigit():
            await render_panel(update, context, "Kirim angka MB, contoh: 1024")
            return
        res = await asyncio.to_thread(_famplan_limit_sync, slot, int(text))
        snap_text, members = await asyncio.to_thread(_famplan_snapshot_sync)
        set_flow(context, "famplan_menu", {"members": members})
        await render_panel(update, context, res + "\n\n" + snap_text)
        return

    if state == "await_circle_invite":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 2:
            await render_panel(update, context, "Format: msisdn|nama")
            return
        res = await asyncio.to_thread(_circle_invite_sync, parts[0], parts[1])
        snap_text, snap = await asyncio.to_thread(_circle_snapshot_sync)
        set_flow(context, "circle_menu", snap)
        await render_panel(update, context, res + "\n\n" + snap_text)
        return

    if state == "await_circle_remove":
        if not text.isdigit():
            await render_panel(update, context, "Kirim nomor member.")
            return
        res = await asyncio.to_thread(_circle_remove_sync, int(text))
        snap_text, _ = await asyncio.to_thread(_circle_snapshot_sync)
        _, snap = await asyncio.to_thread(_circle_snapshot_sync)
        set_flow(context, "circle_menu", snap)
        await render_panel(update, context, res + "\n\n" + snap_text)
        return

    if state == "await_circle_accept":
        if not text.isdigit():
            await render_panel(update, context, "Kirim nomor member.")
            return
        res = await asyncio.to_thread(_circle_accept_sync, int(text))
        snap_text, _ = await asyncio.to_thread(_circle_snapshot_sync)
        _, snap = await asyncio.to_thread(_circle_snapshot_sync)
        set_flow(context, "circle_menu", snap)
        await render_panel(update, context, res + "\n\n" + snap_text)
        return

    if state == "account_menu":
        if text in {"➕ Tambah Akun", "Tambah Akun", "acc_add"}:
            set_flow(context, "await_login_phone", {})
            await render_panel(update, context, "Kirim nomor XL format 628xxxx")
            return
        if text in {"🔁 Ganti Akun", "Ganti Akun", "acc_switch"}:
            account_text = await asyncio.to_thread(_account_summary_sync)
            count = len(AuthInstance.refresh_tokens)
            set_flow(context, "await_switch_idx", {"count": count, "page": 0})
            await render_panel(update, context, account_text + "\n\nPilih nomor akun yang ingin diaktifkan.")
            return
        if text in {"🗑 Hapus Akun", "Hapus Akun", "acc_delete"}:
            account_text = await asyncio.to_thread(_account_summary_sync)
            count = len(AuthInstance.refresh_tokens)
            set_flow(context, "await_delete_idx", {"count": count, "page": 0})
            await render_panel(update, context, account_text + "\n\nPilih nomor akun yang ingin dihapus.")
            return

    if state == "admin_access_menu":
        actor_id = update.effective_user.id if update.effective_user else None
        if not is_admin_user(actor_id):
            set_flow(context, "home", {})
            await render_panel(update, context, "Menu akses user hanya untuk admin.")
            return

        if text in {"allow_list", "📋 List Allow", "List Allow"}:
            await render_panel(update, context, _allow_list_panel_text(), keyboard_admin_access())
            return

        if text in {"allow_pending", "📥 Pending", "Pending"}:
            pending = _list_pending_access_requests()
            rows: list[list[tuple[str, str]]] = []
            for req in pending[:20]:
                user_id = int(req.get("user_id", 0) or 0)
                req_id = int(req.get("id", 0) or 0)
                if user_id <= 0:
                    continue
                rows.append(
                    [
                        (f"✅ #{req_id}", f"allow_approve:{user_id}"),
                        (f"❌ #{req_id}", f"allow_reject:{user_id}"),
                    ]
                )
            rows.append([("⬅️ Kelola Akses", "allow_list"), ("🏠 Home", "home")])
            await render_panel(update, context, _pending_requests_panel_text(), _mk_inline(rows))
            return

        if text in {"allow_manage", "👥 Kelola User", "Kelola User"}:
            panel_text, user_ids = _managed_users_panel_text()
            rows: list[list[tuple[str, str]]] = []
            for user_id in user_ids[:24]:
                rec = _get_user_access_record(user_id)
                status = _status_label(str(rec.get("status", "pending") or "pending"))
                rows.append([(f"{status[:1]} {user_id}", f"allow_user:{user_id}")])
            rows.append([("⬅️ Kelola Akses", "allow_list"), ("🏠 Home", "home")])
            await render_panel(update, context, panel_text, _mk_inline(rows))
            return

        if text in {"allow_add", "➕ Add User", "Add User"}:
            set_flow(context, "await_admin_allow_add_id", {})
            await render_panel(update, context, "Kirim Telegram user id yang ingin ditambahkan ke allow list.")
            return

    if state == "await_admin_allow_add_id":
        actor_id = update.effective_user.id if update.effective_user else None
        if not is_admin_user(actor_id):
            set_flow(context, "home", {})
            await render_panel(update, context, "Aksi ini hanya untuk admin.")
            return

        if not text.isdigit():
            await render_panel(update, context, "Telegram user id harus angka. Contoh: 123456789")
            return

        target_id = int(text)
        if target_id <= 0:
            await render_panel(update, context, "Telegram user id tidak valid.")
            return

        rec_before = _get_user_access_record(target_id)
        added = str(rec_before.get("status", "")) != "approved"
        _set_user_access_status(target_id, "approved", "Ditambahkan manual oleh admin")
        set_flow(context, "admin_access_menu", {})
        if added:
            result = f"User {target_id} berhasil ditambahkan ke allow list."
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text="Akses bot me-cli Anda sudah diaktifkan admin. Silakan kirim /start.",
                )
            except Exception:
                pass
        else:
            result = f"User {target_id} sudah ada di allow list."

        await render_panel(update, context, result + "\n\n" + _allow_list_panel_text(), keyboard_admin_access())
        return

    if state == "await_admin_action_reason":
        actor_id = update.effective_user.id if update.effective_user else None
        if not is_admin_user(actor_id):
            set_flow(context, "home", {})
            await render_panel(update, context, "Aksi ini hanya untuk admin.")
            return

        action = str(data.get("action", "") or "")
        target_id = int(data.get("target_id", 0) or 0)
        if target_id <= 0 or not action:
            set_flow(context, "admin_access_menu", {})
            await render_panel(update, context, "State aksi admin tidak valid.", keyboard_admin_access())
            return

        reason = "" if text.strip() in {"-", ".", "skip", "none"} else text.strip()
        set_flow(context, "admin_access_menu", {})

        if action in {"suspend_user", "kick_user"} and is_admin_user(target_id):
            await render_panel(update, context, "Akun admin tidak dapat di-suspend atau di-kick.", keyboard_admin_access())
            return

        if action == "approve_request":
            ok, info = _process_access_request(target_id, True, int(actor_id or 0), reason)
            if not ok:
                await render_panel(update, context, info + "\n\n" + _allow_list_panel_text(), keyboard_admin_access())
                return
            notify = "Permintaan akses Anda disetujui admin."
            if reason:
                notify += f"\nCatatan: {reason}"
            try:
                await context.bot.send_message(chat_id=target_id, text=notify + "\n\nSilakan kirim /start.")
            except Exception:
                pass
            await render_panel(update, context, f"Request user {target_id} di-approve.\n\n" + _allow_list_panel_text(), keyboard_admin_access())
            return

        if action == "reject_request":
            ok, info = _process_access_request(target_id, False, int(actor_id or 0), reason)
            if not ok:
                await render_panel(update, context, info + "\n\n" + _allow_list_panel_text(), keyboard_admin_access())
                return
            notify = "Permintaan akses Anda ditolak admin."
            if reason:
                notify += f"\nAlasan: {reason}"
            try:
                await context.bot.send_message(chat_id=target_id, text=notify)
            except Exception:
                pass
            await render_panel(update, context, f"Request user {target_id} di-reject.\n\n" + _allow_list_panel_text(), keyboard_admin_access())
            return

        if action == "suspend_user":
            _set_user_access_status(target_id, "suspended", reason)
            notify = "Akses bot Anda disuspend admin."
            if reason:
                notify += f"\nAlasan: {reason}"
            try:
                await context.bot.send_message(chat_id=target_id, text=notify)
            except Exception:
                pass
            await render_panel(update, context, f"User {target_id} disuspend.\n\n" + _allow_list_panel_text(), keyboard_admin_access())
            return

        if action == "kick_user":
            _set_user_access_status(target_id, "kicked", reason)
            notify = "Akses bot Anda di-kick admin."
            if reason:
                notify += f"\nAlasan: {reason}"
            try:
                await context.bot.send_message(chat_id=target_id, text=notify)
            except Exception:
                pass
            await render_panel(update, context, f"User {target_id} di-kick.\n\n" + _allow_list_panel_text(), keyboard_admin_access())
            return

        if action == "unsuspend_user":
            _set_user_access_status(target_id, "approved", reason)
            notify = "Akses bot Anda diaktifkan kembali admin."
            if reason:
                notify += f"\nCatatan: {reason}"
            try:
                await context.bot.send_message(chat_id=target_id, text=notify + "\n\nSilakan kirim /start.")
            except Exception:
                pass
            await render_panel(update, context, f"User {target_id} diaktifkan kembali.\n\n" + _allow_list_panel_text(), keyboard_admin_access())
            return

        await render_panel(update, context, "Aksi admin tidak dikenali.", keyboard_admin_access())
        return

    if state == "famplan_menu":
        if text in {"🔄 Refresh FamPlan", "Refresh FamPlan", "fam_refresh"}:
            snap_text, members = await asyncio.to_thread(_famplan_snapshot_sync)
            set_flow(context, "famplan_menu", {"members": members})
            await render_panel(update, context, snap_text)
            return
        if text in {"👥 Ganti Member", "Ganti Member", "fam_change"}:
            set_flow(context, "await_famplan_change", {})
            await render_panel(update, context, "Kirim: slot|msisdn|alias_parent|alias_member")
            return
        if text in {"🗑 Hapus Member", "Hapus Member", "fam_remove"}:
            members = flow.get("data", {}).get("members", [])
            set_flow(context, "await_famplan_remove", {"members": members, "page": 0})
            await render_panel(update, context, "Pilih nomor slot member yang akan dihapus.")
            return
        if text in {"📏 Set Limit", "Set Limit", "fam_limit"}:
            members = flow.get("data", {}).get("members", [])
            set_flow(context, "await_famplan_limit", {"members": members, "page": 0})
            await render_panel(update, context, "Pilih slot dulu, lalu kirim nilai MB.")
            return

    if state == "circle_menu":
        if text in {"🔄 Refresh Circle", "Refresh Circle", "cir_refresh"}:
            snap_text, snap = await asyncio.to_thread(_circle_snapshot_sync)
            set_flow(context, "circle_menu", snap)
            await render_panel(update, context, snap_text)
            return
        if text in {"➕ Invite Circle", "Invite Circle", "cir_invite"}:
            set_flow(context, "await_circle_invite", {})
            await render_panel(update, context, "Kirim: msisdn|nama")
            return
        if text in {"🗑 Remove Circle", "Remove Circle", "cir_remove"}:
            members = flow.get("data", {}).get("members", [])
            set_flow(context, "await_circle_remove", {"members": members, "page": 0})
            await render_panel(update, context, "Pilih nomor member yang akan dihapus.")
            return
        if text in {"✅ Accept Circle", "Accept Circle", "cir_accept"}:
            members = flow.get("data", {}).get("members", [])
            set_flow(context, "await_circle_accept", {"members": members, "page": 0})
            await render_panel(update, context, "Pilih nomor member yang akan di-accept.")
            return
        if text in {"🎁 Bonus Circle", "Bonus Circle", "cir_bonus"}:
            bonus_text, items = await asyncio.to_thread(_circle_bonuses_sync)
            set_flow(context, "await_circle_bonus_pick", {"items": items, "page": 0})
            await render_panel(update, context, bonus_text)
            return

    choice = _normalize_choice(text)

    if choice == "1":
        set_flow(context, "account_menu", {})
        await render_panel(update, context, await asyncio.to_thread(_account_summary_sync))
        return

    if choice == "2":
        text_out, packages = await asyncio.to_thread(_my_packages_menu_sync)
        set_flow(context, "packages_menu", {"packages": packages, "page": 0})
        await render_panel(update, context, text_out)
        return

    if choice == "3":
        hot_packages = await asyncio.to_thread(_load_hot_file_sync, "hot.json")
        set_flow(context, "hot_select", {"hot_packages": hot_packages, "page": 0})
        await render_panel(update, context, _hot_list_text(hot_packages))
        return

    if choice == "4":
        hot_packages = await asyncio.to_thread(_load_hot_file_sync, "hot2.json")
        set_flow(context, "hot2_select", {"hot_packages": hot_packages, "page": 0})
        await render_panel(update, context, _hot_list_text(hot_packages))
        return

    if choice == "5":
        set_flow(context, "await_option_code", {})
        await render_panel(update, context, "Kirim option code.")
        return

    if choice == "6":
        set_flow(context, "await_family_code", {})
        await render_panel(update, context, "Kirim family code. List package akan ditampilkan full, paginated, dan bisa dipilih via angka.")
        return

    if choice == "7":
        set_flow(context, "await_purchase_loop", {})
        await render_panel(update, context, "Kirim format: family_code|start_order|delay_seconds\nCatatan: mode native loop saat ini non-decoy.")
        return

    if choice == "8":
        set_flow(context, "history_menu", {})
        await render_panel(update, context, await asyncio.to_thread(_history_sync))
        return

    if choice == "9":
        snap_text, members = await asyncio.to_thread(_famplan_snapshot_sync)
        set_flow(context, "famplan_menu", {"members": members})
        await render_panel(update, context, snap_text)
        return

    if choice == "10":
        snap_text, snap = await asyncio.to_thread(_circle_snapshot_sync)
        set_flow(context, "circle_menu", snap)
        await render_panel(update, context, snap_text)
        return

    if choice == "11":
        text_out, items = await asyncio.to_thread(_store_segments_sync)
        set_flow(context, "await_store_segments_pick", {"items": items, "page": 0})
        await render_panel(update, context, text_out)
        return

    if choice == "12":
        active_user = AuthInstance.get_active_user() or {}
        text_out, items = await asyncio.to_thread(_store_family_list_sync, active_user.get("subscription_type", "PREPAID"), False)
        set_flow(context, "await_store_family_pick", {"items": items, "page": 0})
        await render_panel(update, context, text_out)
        return

    if choice == "13":
        active_user = AuthInstance.get_active_user() or {}
        text_out, items = await asyncio.to_thread(_store_packages_sync, active_user.get("subscription_type", "PREPAID"), False)
        set_flow(context, "await_store_package_pick", {"items": items, "page": 0})
        await render_panel(update, context, text_out)
        return

    if choice == "14":
        text_out, items = await asyncio.to_thread(_redeemables_sync)
        set_flow(context, "await_redeem_pick", {"items": items, "page": 0})
        await render_panel(update, context, text_out)
        return

    if choice == "00":
        set_flow(context, "bookmark_menu", {})
        await render_panel(update, context, await asyncio.to_thread(_bookmark_text_sync))
        return

    if choice == "a":
        actor_id = update.effective_user.id if update.effective_user else None
        if not is_admin_user(actor_id):
            await render_panel(update, context, "Menu Akses User hanya untuk admin.")
            return

        set_flow(context, "admin_access_menu", {})
        await render_panel(update, context, _allow_list_panel_text(), keyboard_admin_access())
        return

    if lowered == "add bookmark":
        set_flow(context, "await_bookmark_add", {})
        await render_panel(update, context, "Kirim format: family_code|is_enterprise(0/1)|variant_name|option_name|order")
        return

    if lowered == "del bookmark":
        count = len(BookmarkInstance.get_bookmarks())
        set_flow(context, "await_bookmark_remove", {"count": count, "page": 0})
        await render_panel(update, context, "Pilih nomor bookmark yang akan dihapus.")
        return

    if choice == "r":
        set_flow(context, "await_register", {})
        await render_panel(update, context, "Kirim format: msisdn|nik|kk")
        return

    if choice == "n":
        set_flow(context, "notifications_menu", {})
        await render_panel(update, context, await asyncio.to_thread(_notifications_sync, False))
        return

    if lowered == "mark all notif":
        set_flow(context, "notifications_menu", {})
        await render_panel(update, context, await asyncio.to_thread(_notifications_sync, True))
        return

    if choice == "v":
        set_flow(context, "await_validate_msisdn", {})
        await render_panel(update, context, "Kirim msisdn untuk validasi (628xxxx).")
        return

    await render_panel(update, context, build_error_with_next("Input tidak dikenali di konteks saat ini.", "Gunakan tombol menu atau kirim p:<halaman>/hal:<halaman> saat di list."))
    logger.info("ui_action state=%s action=%s latency_ms=%s", state, text, int((time.perf_counter() - t0) * 1000))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_allowed(update, context):
        return

    message = update.effective_message
    if message is None:
        return

    await _delete_user_input(update)
    text = (message.text or "").strip()
    await _handle_input(update, context, text)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_allowed(update, context):
        return

    query = update.callback_query
    if query is None:
        return

    await query.answer()
    text = (query.data or "").strip()
    await _handle_input(update, context, text)


def build_application() -> Application:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN belum di-set di .env")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("request_access", request_access_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return app


def main():
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = build_application()
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
