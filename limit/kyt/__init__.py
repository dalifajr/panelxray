import base64
import datetime as DT
import json
import logging
import math
import os
import random
import re
import sqlite3
import subprocess
import sys
import time
from typing import Dict, List, Optional

import requests
from telethon import Button, TelegramClient, events

logging.basicConfig(level=logging.INFO)
uptime = DT.datetime.now()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAR_FILE = os.path.join(BASE_DIR, "var.txt")
DB_FILE = os.path.join(BASE_DIR, "database.db")
ALLOW_LIST_FILE = os.path.join(BASE_DIR, "allow_list_kyt.txt")

if not os.path.isfile(VAR_FILE):
	raise FileNotFoundError(f"Bot config tidak ditemukan: {VAR_FILE}")

with open(VAR_FILE, "r", encoding="utf-8") as f:
	exec(f.read(), globals())

API_ID = int(globals().get("API_ID", 6))
API_HASH = str(globals().get("API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e"))
BOT_TOKEN = str(globals().get("BOT_TOKEN", "")).strip()

if not BOT_TOKEN:
	raise ValueError("BOT_TOKEN kosong pada var.txt")


def _telethon_session_artifacts(session_base: str) -> List[str]:
	session_db = f"{session_base}.session"
	return [
		session_db,
		f"{session_db}-journal",
		f"{session_db}-wal",
		f"{session_db}-shm",
	]


def _cleanup_telethon_session(session_base: str):
	for path in _telethon_session_artifacts(session_base):
		try:
			os.remove(path)
		except FileNotFoundError:
			continue
		except Exception as exc:
			logging.warning("Gagal hapus session artifact %s: %s", path, exc)


def _is_recoverable_session_error(exc: Exception) -> bool:
	msg = str(exc or "")
	msg_lower = msg.lower()
	if isinstance(exc, sqlite3.DatabaseError):
		return True
	if isinstance(exc, TypeError) and "none" in msg_lower and "subscriptable" in msg_lower:
		return True
	if "sqlite" in msg_lower and "session" in msg_lower:
		return True
	return False


def _start_bot_client() -> TelegramClient:
	# Use a fixed absolute session path to avoid collisions with cwd changes.
	session_base = os.path.join(BASE_DIR, "ddsdswl")
	try:
		return TelegramClient(session_base, API_ID, API_HASH).start(bot_token=BOT_TOKEN)
	except Exception as exc:
		if not _is_recoverable_session_error(exc):
			raise
		logging.warning("Session Telethon terdeteksi rusak, mencoba recovery otomatis: %s", exc)
		_cleanup_telethon_session(session_base)
		return TelegramClient(session_base, API_ID, API_HASH).start(bot_token=BOT_TOKEN)


bot = _start_bot_client()


def _normalize_tg_id(value) -> str:
	return str(value or "").strip()


def _now() -> str:
	return DT.datetime.utcnow().replace(microsecond=0).isoformat(sep=" ")


def _dedupe_keep_order(values: List[str]) -> List[str]:
	seen = set()
	result = []
	for value in values:
		item = _normalize_tg_id(value)
		if not item or item in seen:
			continue
		seen.add(item)
		result.append(item)
	return result


def _read_allow_list_ids() -> List[str]:
	if not os.path.isfile(ALLOW_LIST_FILE):
		return []

	rows = []
	try:
		with open(ALLOW_LIST_FILE, "r", encoding="utf-8") as f:
			for line in f:
				text = line.strip()
				if not text or text.startswith("#"):
					continue
				rows.append(text.split()[0])
	except Exception:
		return []

	return _dedupe_keep_order(rows)


def _write_allow_list_ids(admin_id: str, user_ids: List[str]):
	ordered = []
	admin_id = _normalize_tg_id(admin_id)
	if admin_id:
		ordered.append(admin_id)

	for user_id in user_ids:
		uid = _normalize_tg_id(user_id)
		if not uid or uid == admin_id:
			continue
		ordered.append(uid)

	ordered = _dedupe_keep_order(ordered)
	with open(ALLOW_LIST_FILE, "w", encoding="utf-8") as f:
		for uid in ordered:
			f.write(f"{uid}\n")


def _sync_allow_list_from_db():
	db = sqlite3.connect(DB_FILE)
	db.row_factory = sqlite3.Row
	try:
		rows = db.execute(
			"""
			SELECT tg_id
			FROM telegram_users
			WHERE status = 'approved'
			ORDER BY CASE WHEN role = 'admin' THEN 0 ELSE 1 END, tg_id
			"""
		).fetchall()
		approved_ids = [str(r[0]) for r in rows]
	finally:
		db.close()

	admin_id = _normalize_tg_id(globals().get("ADMIN", ""))
	if not admin_id and approved_ids:
		admin_id = approved_ids[0]

	_write_allow_list_ids(admin_id, approved_ids)


def _table_columns(cursor, table_name: str) -> set:
	try:
		rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
		return {str(row[1]) for row in rows}
	except Exception:
		return set()


def _add_column_if_missing(cursor, table_name: str, column_name: str, column_sql: str):
	cols = _table_columns(cursor, table_name)
	if column_name in cols:
		return
	cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")


def _migrate_legacy_schema(cursor):
	# Ensure legacy installs are upgraded in-place so new access/quota queries do not fail.
	_add_column_if_missing(cursor, "telegram_users", "tg_id", "TEXT")
	_add_column_if_missing(cursor, "telegram_users", "username", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "telegram_users", "full_name", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "telegram_users", "role", "TEXT NOT NULL DEFAULT 'user'")
	_add_column_if_missing(cursor, "telegram_users", "status", "TEXT NOT NULL DEFAULT 'pending'")
	_add_column_if_missing(cursor, "telegram_users", "note", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "telegram_users", "created_at", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "telegram_users", "updated_at", "TEXT DEFAULT ''")

	_add_column_if_missing(cursor, "access_requests", "tg_id", "TEXT")
	_add_column_if_missing(cursor, "access_requests", "username", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "access_requests", "full_name", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "access_requests", "reason", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "access_requests", "status", "TEXT NOT NULL DEFAULT 'pending'")
	_add_column_if_missing(cursor, "access_requests", "admin_id", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "access_requests", "admin_reason", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "access_requests", "created_at", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "access_requests", "processed_at", "TEXT DEFAULT ''")

	_add_column_if_missing(cursor, "quota_limits", "tg_id", "TEXT")
	_add_column_if_missing(cursor, "quota_limits", "ssh_limit", "INTEGER NOT NULL DEFAULT 0")
	_add_column_if_missing(cursor, "quota_limits", "xray_limit", "INTEGER NOT NULL DEFAULT 0")
	_add_column_if_missing(cursor, "quota_limits", "updated_by", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "quota_limits", "updated_at", "TEXT DEFAULT ''")

	_add_column_if_missing(cursor, "quota_requests", "tg_id", "TEXT")
	_add_column_if_missing(cursor, "quota_requests", "reason", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "quota_requests", "status", "TEXT NOT NULL DEFAULT 'pending'")
	_add_column_if_missing(cursor, "quota_requests", "admin_id", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "quota_requests", "admin_reason", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "quota_requests", "created_at", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "quota_requests", "processed_at", "TEXT DEFAULT ''")

	_add_column_if_missing(cursor, "account_registry", "tg_id", "TEXT")
	_add_column_if_missing(cursor, "account_registry", "service", "TEXT")
	_add_column_if_missing(cursor, "account_registry", "category", "TEXT")
	_add_column_if_missing(cursor, "account_registry", "username", "TEXT")
	_add_column_if_missing(cursor, "account_registry", "expires_at", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "account_registry", "is_trial", "INTEGER NOT NULL DEFAULT 0")
	_add_column_if_missing(cursor, "account_registry", "active", "INTEGER NOT NULL DEFAULT 1")
	_add_column_if_missing(cursor, "account_registry", "created_at", "TEXT DEFAULT ''")
	_add_column_if_missing(cursor, "account_registry", "updated_at", "TEXT DEFAULT ''")

	# Backfill tg_id from legacy admin table when needed.
	cursor.execute(
		"""
		UPDATE telegram_users
		SET tg_id = (SELECT user_id FROM admin LIMIT 1)
		WHERE (tg_id IS NULL OR tg_id = '')
		  AND role = 'admin'
		"""
	)

	cursor.execute("UPDATE telegram_users SET role = 'user' WHERE role IS NULL OR role = ''")
	cursor.execute("UPDATE telegram_users SET status = 'pending' WHERE status IS NULL OR status = ''")
	cursor.execute("UPDATE telegram_users SET note = '' WHERE note IS NULL")
	cursor.execute("UPDATE telegram_users SET username = '' WHERE username IS NULL")
	cursor.execute("UPDATE telegram_users SET full_name = '' WHERE full_name IS NULL")
	cursor.execute("UPDATE telegram_users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL OR created_at = ''")
	cursor.execute("UPDATE telegram_users SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL OR updated_at = ''")
	cursor.execute("UPDATE access_requests SET status = 'pending' WHERE status IS NULL OR status = ''")
	cursor.execute("UPDATE access_requests SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL OR created_at = ''")
	cursor.execute("UPDATE access_requests SET processed_at = '' WHERE processed_at IS NULL")
	cursor.execute("UPDATE quota_limits SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL OR updated_at = ''")
	cursor.execute("UPDATE quota_requests SET status = 'pending' WHERE status IS NULL OR status = ''")
	cursor.execute("UPDATE quota_requests SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL OR created_at = ''")
	cursor.execute("UPDATE quota_requests SET processed_at = '' WHERE processed_at IS NULL")
	cursor.execute("UPDATE account_registry SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL OR created_at = ''")
	cursor.execute("UPDATE account_registry SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL OR updated_at = ''")


def _bootstrap_db():
	x = sqlite3.connect(DB_FILE)
	c = x.cursor()
	c.execute("CREATE TABLE IF NOT EXISTS admin (user_id TEXT PRIMARY KEY)")
	c.execute(
		"""
		CREATE TABLE IF NOT EXISTS telegram_users (
			tg_id TEXT PRIMARY KEY,
			username TEXT DEFAULT '',
			full_name TEXT DEFAULT '',
			role TEXT NOT NULL DEFAULT 'user',
			status TEXT NOT NULL DEFAULT 'pending',
			note TEXT DEFAULT '',
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
		)
		"""
	)
	c.execute(
		"""
		CREATE TABLE IF NOT EXISTS access_requests (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			tg_id TEXT NOT NULL,
			username TEXT DEFAULT '',
			full_name TEXT DEFAULT '',
			reason TEXT DEFAULT '',
			status TEXT NOT NULL DEFAULT 'pending',
			admin_id TEXT DEFAULT '',
			admin_reason TEXT DEFAULT '',
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			processed_at TEXT DEFAULT ''
		)
		"""
	)
	c.execute(
		"""
		CREATE TABLE IF NOT EXISTS quota_limits (
			tg_id TEXT PRIMARY KEY,
			ssh_limit INTEGER NOT NULL DEFAULT 0,
			xray_limit INTEGER NOT NULL DEFAULT 0,
			updated_by TEXT DEFAULT '',
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
		)
		"""
	)
	c.execute(
		"""
		CREATE TABLE IF NOT EXISTS quota_requests (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			tg_id TEXT NOT NULL,
			reason TEXT DEFAULT '',
			status TEXT NOT NULL DEFAULT 'pending',
			admin_id TEXT DEFAULT '',
			admin_reason TEXT DEFAULT '',
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			processed_at TEXT DEFAULT ''
		)
		"""
	)
	c.execute(
		"""
		CREATE TABLE IF NOT EXISTS account_registry (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			tg_id TEXT NOT NULL,
			service TEXT NOT NULL,
			category TEXT NOT NULL,
			username TEXT NOT NULL,
			expires_at TEXT DEFAULT '',
			is_trial INTEGER NOT NULL DEFAULT 0,
			active INTEGER NOT NULL DEFAULT 1,
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
		)
		"""
	)
	c.execute(
		"""
		CREATE TABLE IF NOT EXISTS expiry_notifications (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			account_id INTEGER NOT NULL,
			target_id TEXT NOT NULL,
			notice_date TEXT NOT NULL,
			created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
			UNIQUE(account_id, target_id, notice_date)
		)
		"""
	)
	_migrate_legacy_schema(c)
	c.execute("CREATE INDEX IF NOT EXISTS idx_access_requests_status ON access_requests(status, created_at)")
	c.execute("CREATE INDEX IF NOT EXISTS idx_quota_requests_status ON quota_requests(status, created_at)")
	c.execute("CREATE INDEX IF NOT EXISTS idx_account_registry_owner ON account_registry(tg_id, category, service)")
	c.execute("CREATE INDEX IF NOT EXISTS idx_expiry_notifications_target ON expiry_notifications(target_id, notice_date)")

	admin_id = _normalize_tg_id(globals().get("ADMIN", ""))
	if admin_id:
		c.execute("INSERT OR IGNORE INTO admin (user_id) VALUES (?)", (admin_id,))
		now = _now()
		c.execute(
			"""
			INSERT INTO telegram_users (tg_id, role, status, note, created_at, updated_at)
			VALUES (?, 'admin', 'approved', 'Bootstrap admin', ?, ?)
			ON CONFLICT(tg_id) DO UPDATE SET
				role = 'admin',
				status = 'approved',
				updated_at = excluded.updated_at
			""",
			(admin_id, now, now),
		)

	seed_ids = _read_allow_list_ids()
	if seed_ids:
		now = _now()
		for idx, uid in enumerate(seed_ids):
			role = "admin" if idx == 0 else "user"
			c.execute(
				"""
				INSERT INTO telegram_users (tg_id, role, status, note, created_at, updated_at)
				VALUES (?, ?, 'approved', 'Seeded from allow_list_kyt.txt', ?, ?)
				ON CONFLICT(tg_id) DO UPDATE SET
					role = CASE WHEN telegram_users.role = 'admin' THEN 'admin' ELSE excluded.role END,
					status = 'approved',
					updated_at = excluded.updated_at
				""",
				(uid, role, now, now),
			)

	x.commit()
	x.close()
	_sync_allow_list_from_db()


_bootstrap_db()


def get_db():
	x = sqlite3.connect(DB_FILE)
	x.row_factory = sqlite3.Row
	return x


def _row_to_dict(row) -> Optional[Dict]:
	if row is None:
		return None
	return {k: row[k] for k in row.keys()}


def touch_user(tg_id, username: str = "", full_name: str = ""):
	uid = _normalize_tg_id(tg_id)
	if not uid:
		return

	username = str(username or "").strip()
	full_name = str(full_name or "").strip()
	now = _now()

	db = get_db()
	try:
		row = db.execute("SELECT username, full_name FROM telegram_users WHERE tg_id = ?", (uid,)).fetchone()
		if row is None:
			db.execute(
				"""
				INSERT INTO telegram_users (tg_id, username, full_name, role, status, note, created_at, updated_at)
				VALUES (?, ?, ?, 'user', 'pending', '', ?, ?)
				""",
				(uid, username, full_name, now, now),
			)
		else:
			db.execute(
				"UPDATE telegram_users SET username = ?, full_name = ?, updated_at = ? WHERE tg_id = ?",
				(username or row["username"] or "", full_name or row["full_name"] or "", now, uid),
			)
		db.commit()
	finally:
		db.close()


def get_user_record(tg_id) -> Optional[Dict]:
	uid = _normalize_tg_id(tg_id)
	if not uid:
		return None

	db = get_db()
	try:
		row = db.execute("SELECT * FROM telegram_users WHERE tg_id = ?", (uid,)).fetchone()
		return _row_to_dict(row)
	finally:
		db.close()


def get_primary_admin_id() -> str:
	allow_ids = _read_allow_list_ids()
	if allow_ids:
		return allow_ids[0]
	return _normalize_tg_id(globals().get("ADMIN", ""))


def get_all_admin_ids() -> List[str]:
	db = get_db()
	try:
		rows = db.execute(
			"SELECT tg_id FROM telegram_users WHERE role = 'admin' AND status = 'approved' ORDER BY tg_id"
		).fetchall()
		admin_ids = [str(row[0]) for row in rows]
	finally:
		db.close()

	primary = get_primary_admin_id()
	if primary:
		admin_ids.insert(0, primary)

	return _dedupe_keep_order(admin_ids)


def is_admin_user(tg_id) -> bool:
	uid = _normalize_tg_id(tg_id)
	if not uid:
		return False

	db = get_db()
	try:
		row = db.execute(
			"SELECT 1 FROM telegram_users WHERE tg_id = ? AND role = 'admin' AND status = 'approved'",
			(uid,),
		).fetchone()
		if row is not None:
			return True

		legacy = db.execute("SELECT 1 FROM admin WHERE user_id = ?", (uid,)).fetchone()
		return legacy is not None
	finally:
		db.close()


def is_user_approved(tg_id) -> bool:
	uid = _normalize_tg_id(tg_id)
	if not uid:
		return False

	if is_admin_user(uid):
		return True

	db = get_db()
	try:
		row = db.execute(
			"SELECT 1 FROM telegram_users WHERE tg_id = ? AND status = 'approved'",
			(uid,),
		).fetchone()
		return row is not None
	finally:
		db.close()


def valid(user_id):
	if is_user_approved(user_id):
		return "true"
	return "false"


def create_access_request(tg_id, username: str = "", full_name: str = "", reason: str = "") -> Dict:
	uid = _normalize_tg_id(tg_id)
	if not uid:
		return {"ok": False, "status": "invalid"}

	if is_user_approved(uid):
		return {"ok": False, "status": "already-approved"}

	touch_user(uid, username, full_name)
	reason = str(reason or "").strip()

	db = get_db()
	try:
		pending = db.execute(
			"SELECT * FROM access_requests WHERE tg_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1",
			(uid,),
		).fetchone()
		if pending is not None:
			return {"ok": False, "status": "pending", "request": _row_to_dict(pending)}

		user = db.execute("SELECT username, full_name FROM telegram_users WHERE tg_id = ?", (uid,)).fetchone()
		now = _now()
		cur = db.execute(
			"""
			INSERT INTO access_requests (tg_id, username, full_name, reason, status, created_at)
			VALUES (?, ?, ?, ?, 'pending', ?)
			""",
			(
				uid,
				(username or (user["username"] if user else "") or ""),
				(full_name or (user["full_name"] if user else "") or ""),
				reason,
				now,
			),
		)
		db.execute(
			"UPDATE telegram_users SET status = 'pending', note = ?, updated_at = ? WHERE tg_id = ?",
			(reason, now, uid),
		)
		db.commit()
		request_id = int(cur.lastrowid)
	finally:
		db.close()

	return {"ok": True, "status": "created", "request": get_access_request(request_id)}


def get_access_request(request_id: int) -> Optional[Dict]:
	db = get_db()
	try:
		row = db.execute("SELECT * FROM access_requests WHERE id = ?", (int(request_id),)).fetchone()
		return _row_to_dict(row)
	finally:
		db.close()


def list_pending_access_requests(limit: int = 20) -> List[Dict]:
	db = get_db()
	try:
		rows = db.execute(
			"SELECT * FROM access_requests WHERE status = 'pending' ORDER BY created_at ASC LIMIT ?",
			(max(1, int(limit)),),
		).fetchall()
		return [_row_to_dict(row) for row in rows]
	finally:
		db.close()


def process_access_request(request_id: int, admin_id, approved: bool, admin_reason: str = "") -> Optional[Dict]:
	admin_uid = _normalize_tg_id(admin_id)
	reason = str(admin_reason or "").strip()
	status = "approved" if approved else "rejected"
	now = _now()

	db = get_db()
	try:
		row = db.execute(
			"SELECT * FROM access_requests WHERE id = ? AND status = 'pending'",
			(int(request_id),),
		).fetchone()
		if row is None:
			return None

		request = _row_to_dict(row)
		tg_id = str(request["tg_id"])

		db.execute(
			"""
			UPDATE access_requests
			SET status = ?, admin_id = ?, admin_reason = ?, processed_at = ?
			WHERE id = ?
			""",
			(status, admin_uid, reason, now, int(request_id)),
		)

		user = db.execute("SELECT role FROM telegram_users WHERE tg_id = ?", (tg_id,)).fetchone()
		role = user["role"] if user else "user"
		if role != "admin":
			role = "user"
		db.execute(
			"""
			INSERT INTO telegram_users (tg_id, username, full_name, role, status, note, created_at, updated_at)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)
			ON CONFLICT(tg_id) DO UPDATE SET
				username = excluded.username,
				full_name = excluded.full_name,
				role = CASE WHEN telegram_users.role = 'admin' THEN 'admin' ELSE excluded.role END,
				status = excluded.status,
				note = excluded.note,
				updated_at = excluded.updated_at
			""",
			(
				tg_id,
				request.get("username", "") or "",
				request.get("full_name", "") or "",
				role,
				status,
				reason,
				now,
				now,
			),
		)

		db.commit()
	finally:
		db.close()

	_sync_allow_list_from_db()
	result = get_access_request(request_id)
	if result is None:
		return None
	result["target_status"] = status
	return result


def set_user_status(tg_id, status: str, note: str = "") -> bool:
	uid = _normalize_tg_id(tg_id)
	status = str(status or "").strip().lower()
	if not uid or status not in {"pending", "approved", "rejected", "suspended", "kicked"}:
		return False

	now = _now()
	note = str(note or "").strip()
	db = get_db()
	try:
		row = db.execute("SELECT role FROM telegram_users WHERE tg_id = ?", (uid,)).fetchone()
		if row is None:
			db.execute(
				"""
				INSERT INTO telegram_users (tg_id, role, status, note, created_at, updated_at)
				VALUES (?, 'user', ?, ?, ?, ?)
				""",
				(uid, status, note, now, now),
			)
		else:
			role = row["role"]
			if role == "admin" and status != "approved":
				return False
			db.execute(
				"UPDATE telegram_users SET status = ?, note = ?, updated_at = ? WHERE tg_id = ?",
				(status, note, now, uid),
			)
		db.commit()
	finally:
		db.close()

	_sync_allow_list_from_db()
	return True


def list_managed_users(include_admin: bool = False) -> List[Dict]:
	db = get_db()
	try:
		if include_admin:
			rows = db.execute(
				"SELECT * FROM telegram_users ORDER BY CASE WHEN role = 'admin' THEN 0 ELSE 1 END, status, updated_at DESC"
			).fetchall()
		else:
			rows = db.execute(
				"SELECT * FROM telegram_users WHERE role != 'admin' ORDER BY status, updated_at DESC"
			).fetchall()
		return [_row_to_dict(row) for row in rows]
	finally:
		db.close()


def _sanitize_limit_value(value, default: Optional[int] = None) -> Optional[int]:
	if value is None:
		return default
	text = str(value).strip()
	if not text:
		return default
	if not text.isdigit():
		return default
	return max(0, int(text))


def get_user_limits(tg_id) -> Dict:
	uid = _normalize_tg_id(tg_id)
	if not uid:
		return {"tg_id": "", "ssh_limit": 0, "xray_limit": 0}

	db = get_db()
	try:
		row = db.execute("SELECT * FROM quota_limits WHERE tg_id = ?", (uid,)).fetchone()
		if row is None:
			return {"tg_id": uid, "ssh_limit": 0, "xray_limit": 0}
		return {
			"tg_id": uid,
			"ssh_limit": int(row["ssh_limit"] or 0),
			"xray_limit": int(row["xray_limit"] or 0),
		}
	finally:
		db.close()


def set_user_limits(tg_id, ssh_limit=None, xray_limit=None, updated_by: str = "") -> Dict:
	uid = _normalize_tg_id(tg_id)
	if not uid:
		return {"ok": False, "limits": {"tg_id": "", "ssh_limit": 0, "xray_limit": 0}}

	current = get_user_limits(uid)
	next_ssh = _sanitize_limit_value(ssh_limit, current["ssh_limit"])
	next_xray = _sanitize_limit_value(xray_limit, current["xray_limit"])
	now = _now()

	db = get_db()
	try:
		db.execute(
			"""
			INSERT INTO quota_limits (tg_id, ssh_limit, xray_limit, updated_by, updated_at)
			VALUES (?, ?, ?, ?, ?)
			ON CONFLICT(tg_id) DO UPDATE SET
				ssh_limit = excluded.ssh_limit,
				xray_limit = excluded.xray_limit,
				updated_by = excluded.updated_by,
				updated_at = excluded.updated_at
			""",
			(uid, next_ssh, next_xray, str(updated_by or "").strip(), now),
		)
		db.commit()
	finally:
		db.close()

	return {"ok": True, "limits": get_user_limits(uid)}


def service_to_category(service: str) -> str:
	name = str(service or "").strip().lower()
	if name == "ssh":
		return "ssh"
	return "xray"


def get_user_usage(tg_id, category: str, active_only: bool = False) -> int:
	uid = _normalize_tg_id(tg_id)
	cat = str(category or "").strip().lower()
	if not uid or cat not in {"ssh", "xray"}:
		return 0

	query = "SELECT COUNT(*) AS total FROM account_registry WHERE tg_id = ? AND category = ?"
	params = [uid, cat]
	if active_only:
		query += " AND active = 1"

	db = get_db()
	try:
		row = db.execute(query, tuple(params)).fetchone()
		return int((row["total"] if row else 0) or 0)
	finally:
		db.close()


def get_user_stats(tg_id) -> Dict:
	uid = _normalize_tg_id(tg_id)
	if not uid:
		return {
			"ssh_total": 0,
			"xray_total": 0,
			"ssh_active": 0,
			"xray_active": 0,
		}

	db = get_db()
	try:
		row = db.execute(
			"""
			SELECT
				SUM(CASE WHEN category = 'ssh' THEN 1 ELSE 0 END) AS ssh_total,
				SUM(CASE WHEN category = 'xray' THEN 1 ELSE 0 END) AS xray_total,
				SUM(CASE WHEN category = 'ssh' AND active = 1 THEN 1 ELSE 0 END) AS ssh_active,
				SUM(CASE WHEN category = 'xray' AND active = 1 THEN 1 ELSE 0 END) AS xray_active
			FROM account_registry
			WHERE tg_id = ?
			""",
			(uid,),
		).fetchone()
		return {
			"ssh_total": int((row["ssh_total"] if row else 0) or 0),
			"xray_total": int((row["xray_total"] if row else 0) or 0),
			"ssh_active": int((row["ssh_active"] if row else 0) or 0),
			"xray_active": int((row["xray_active"] if row else 0) or 0),
		}
	finally:
		db.close()


def check_creation_quota(tg_id, category: str) -> Dict:
	uid = _normalize_tg_id(tg_id)
	cat = str(category or "").strip().lower()
	if cat not in {"ssh", "xray"}:
		return {"ok": True, "message": ""}

	if is_admin_user(uid):
		return {"ok": True, "message": ""}

	if not is_user_approved(uid):
		return {
			"ok": False,
			"message": "Akses bot belum disetujui admin.",
		}

	limits = get_user_limits(uid)
	limit_value = int(limits["ssh_limit"] if cat == "ssh" else limits["xray_limit"])
	if limit_value <= 0:
		return {"ok": True, "message": ""}

	used = get_user_usage(uid, cat, active_only=False)
	if used < limit_value:
		remain = limit_value - used
		return {
			"ok": True,
			"message": f"Sisa kuota create {cat.upper()}: {remain}",
		}

	return {
		"ok": False,
		"message": f"Limit pembuatan akun {cat.upper()} sudah tercapai ({used}/{limit_value}).",
	}


def register_account_creation(tg_id, service: str, username: str, expires_at: str = "", is_trial: bool = False):
	uid = _normalize_tg_id(tg_id)
	if not uid:
		return

	service_name = str(service or "").strip().lower()
	account_name = str(username or "").strip()
	if not service_name or not account_name:
		return

	category = service_to_category(service_name)
	now = _now()

	db = get_db()
	try:
		db.execute(
			"""
			INSERT INTO account_registry
			(tg_id, service, category, username, expires_at, is_trial, active, created_at, updated_at)
			VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
			""",
			(uid, service_name, category, account_name, str(expires_at or "").strip(), 1 if is_trial else 0, now, now),
		)
		db.commit()
	finally:
		db.close()


def refresh_account_expiry(service: str, username: str, expires_at: str):
	service_name = str(service or "").strip().lower()
	account_name = str(username or "").strip()
	if not service_name or not account_name:
		return

	now = _now()
	db = get_db()
	try:
		db.execute(
			"""
			UPDATE account_registry
			SET expires_at = ?, updated_at = ?
			WHERE service = ? AND username = ? AND active = 1
			""",
			(str(expires_at or "").strip(), now, service_name, account_name),
		)
		db.commit()
	finally:
		db.close()


def mark_account_inactive(service: str, username: str):
	service_name = str(service or "").strip().lower()
	account_name = str(username or "").strip()
	if not service_name or not account_name:
		return

	now = _now()
	db = get_db()
	try:
		db.execute(
			"""
			UPDATE account_registry
			SET active = 0, updated_at = ?
			WHERE service = ? AND username = ? AND active = 1
			""",
			(now, service_name, account_name),
		)
		db.commit()
	finally:
		db.close()


XRAY_ACCOUNT_MARKERS = {
	"vmess": "###",
	"vless": "#&",
	"trojan": "#!",
	"shadowsocks": "#!#",
}

XRAY_DB_FILES = {
	"vmess": "/etc/vmess/.vmess.db",
	"vless": "/etc/vless/.vless.db",
	"trojan": "/etc/trojan/.trojan.db",
	"shadowsocks": "/etc/shadowsocks/.shadowsocks.db",
}

XRAY_CONF_FILES = {
	"vmess": [],
	"vless": ["/root/akun/vless/.vless.conf"],
	"trojan": ["/root/akun/trojan/.trojan.conf"],
	"shadowsocks": ["/root/akun/shadowsocks/.shadowsocks.conf"],
}

XRAY_UNSUSPEND_COMMANDS = {
	"vmess": "unsuspws",
	"vless": "unsuspvless",
	"trojan": "unsusptr",
	"shadowsocks": "unsuspss",
}

XRAY_SUSPEND_COMMANDS = {
	"vmess": "suspws",
	"vless": "suspvless",
	"trojan": "susptr",
	"shadowsocks": "suspss",
}

SERVICE_LABELS = {
	"ssh": "SSH",
	"vmess": "VMESS",
	"vless": "VLESS",
	"trojan": "TROJAN",
	"shadowsocks": "SHADOWSOCKS",
}


def _xray_line_parts(line: str) -> List[str]:
	return str(line or "").strip().split()


def _xray_marker_matches(line: str, marker: str, username: str) -> bool:
	parts = _xray_line_parts(line)
	return len(parts) >= 3 and parts[0] == marker and parts[1] == username


def _read_text_lines(path: str) -> List[str]:
	try:
		with open(path, "r", encoding="utf-8", errors="ignore") as fh:
			return fh.readlines()
	except FileNotFoundError:
		return []


def _write_text_lines(path: str, lines: List[str]):
	with open(path, "w", encoding="utf-8") as fh:
		fh.writelines(lines)


def _find_xray_expiry(service: str, username: str) -> str:
	marker = XRAY_ACCOUNT_MARKERS.get(service)
	if not marker:
		return ""

	for line in _read_text_lines("/etc/xray/config.json"):
		if _xray_marker_matches(line, marker, username):
			parts = _xray_line_parts(line)
			return parts[2]
	return ""


def list_xray_system_accounts(service: str) -> List[Dict]:
	service_name = str(service or "").strip().lower()
	marker = XRAY_ACCOUNT_MARKERS.get(service_name)
	if not marker:
		return []

	seen = set()
	accounts = []
	for line in _read_text_lines("/etc/xray/config.json"):
		parts = _xray_line_parts(line)
		if len(parts) < 3 or parts[0] != marker:
			continue
		username = parts[1]
		key = username.lower()
		if key in seen:
			continue
		seen.add(key)
		accounts.append({"service": service_name, "username": username, "expires_at": parts[2]})

	accounts.sort(key=lambda item: (str(item.get("username") or "").lower(), str(item.get("expires_at") or "")))
	return accounts


def _ssh_user_expiry(username: str) -> str:
	try:
		out = subprocess.check_output(
			f'chage -l "{username}" | awk -F": " \'/Account expires/ {{print $2}}\'',
			shell=True,
			stderr=subprocess.DEVNULL,
		).decode("utf-8", errors="ignore").strip()
	except Exception:
		return "-"

	if not out:
		return "-"
	if out.lower() == "never":
		return "never"

	try:
		return subprocess.check_output(
			f'date -d "{out}" +%Y-%m-%d',
			shell=True,
			stderr=subprocess.DEVNULL,
		).decode("utf-8", errors="ignore").strip() or out
	except Exception:
		return out


def _ssh_user_status(username: str) -> str:
	try:
		return subprocess.check_output(
			f'passwd -S "{username}" | awk \'{{print $2}}\'',
			shell=True,
			stderr=subprocess.DEVNULL,
		).decode("utf-8", errors="ignore").strip()
	except Exception:
		return ""


def _ssh_uid(username: str) -> int:
	try:
		return int(subprocess.check_output(["id", "-u", username], stderr=subprocess.DEVNULL).decode().strip())
	except Exception:
		return -1


def _ssh_user_exists(username: str) -> bool:
	return _ssh_uid(username) >= 1000


def list_ssh_system_accounts() -> List[Dict]:
	accounts = []
	for line in _read_text_lines("/etc/passwd"):
		parts = line.rstrip("\n").split(":")
		if len(parts) < 3:
			continue
		username = parts[0]
		try:
			uid = int(parts[2])
		except Exception:
			continue
		if uid < 1000 or username == "nobody":
			continue
		accounts.append(
			{
				"service": "ssh",
				"username": username,
				"expires_at": _ssh_user_expiry(username),
				"status": _ssh_user_status(username),
			}
		)
	accounts.sort(key=lambda item: str(item.get("username") or "").lower())
	return accounts


def list_suspended_accounts(service: str) -> List[Dict]:
	service_name = str(service or "").strip().lower()
	if service_name not in SERVICE_LABELS:
		return []

	state_dir = f"/etc/kyt/suspended/{service_name}"
	try:
		names = sorted(os.listdir(state_dir), key=lambda item: item.lower())
	except Exception:
		names = []

	accounts = []
	for username in names:
		if not re.fullmatch(r"[A-Za-z0-9_.-]{1,32}", username or ""):
			continue
		exp = "-"
		lines = _read_text_lines(os.path.join(state_dir, username))
		if lines:
			parts = _xray_line_parts(lines[0])
			if parts:
				exp = parts[0]
		accounts.append(
			{
				"service": service_name,
				"username": username,
				"expires_at": exp,
				"status": "suspended",
			}
		)
	return accounts


def _account_exists_in_system(service: str, username: str) -> bool:
	service_name = str(service or "").strip().lower()
	account_name = str(username or "").strip()
	if service_name == "ssh":
		return _ssh_user_exists(account_name)
	return bool(_find_xray_expiry(service_name, account_name))


def list_account_menu_accounts(
	tg_id,
	service: str,
	action: str,
	admin_mode: bool = False,
	query: str = "",
) -> List[Dict]:
	service_name = str(service or "").strip().lower()
	action_name = str(action or "").strip().lower()
	search = str(query or "").strip().lower()
	if service_name not in SERVICE_LABELS:
		return []

	if action_name == "unsuspend":
		base = list_suspended_accounts(service_name)
		if service_name == "ssh":
			seen = {str(item.get("username") or "").lower() for item in base}
			for item in list_ssh_system_accounts():
				if str(item.get("status") or "") != "L":
					continue
				key = str(item.get("username") or "").lower()
				if key not in seen:
					item["status"] = "suspended"
					base.append(item)
					seen.add(key)
	elif service_name == "ssh":
		base = list_ssh_system_accounts()
	else:
		base = list_xray_system_accounts(service_name)

	if action_name == "delete":
		seen = {str(item.get("username") or "").lower() for item in base}
		for item in list_suspended_accounts(service_name):
			key = str(item.get("username") or "").lower()
			if key not in seen:
				base.append(item)
				seen.add(key)

	if not admin_mode:
		owned = get_user_accounts(
			str(tg_id),
			service=service_name,
			active_only=False if action_name in {"delete", "unsuspend"} else True,
			limit=500,
		)
		owned_names = {str(item.get("username") or "").strip().lower() for item in owned}
		base = [item for item in base if str(item.get("username") or "").strip().lower() in owned_names]

	if search:
		base = [item for item in base if search in str(item.get("username") or "").lower()]

	base.sort(key=lambda item: (str(item.get("username") or "").lower(), str(item.get("expires_at") or "")))
	return base


def _update_marker_expiry_file(path: str, marker: str, username: str, expires_at: str) -> bool:
	lines = _read_text_lines(path)
	if not lines:
		return False

	changed = False
	next_lines = []
	for line in lines:
		if _xray_marker_matches(line, marker, username):
			next_lines.append(f"{marker} {username} {expires_at}\n")
			changed = True
		else:
			next_lines.append(line)

	if changed:
		_write_text_lines(path, next_lines)
	return changed


def _update_db_expiry_file(path: str, username: str, expires_at: str) -> bool:
	lines = _read_text_lines(path)
	if not lines:
		return False

	changed = False
	next_lines = []
	for line in lines:
		parts = _xray_line_parts(line)
		if len(parts) >= 3 and parts[0] == "###" and parts[1] == username:
			parts[2] = expires_at
			next_lines.append(" ".join(parts) + "\n")
			changed = True
		else:
			next_lines.append(line)

	if changed:
		_write_text_lines(path, next_lines)
	return changed


def _delete_marker_blocks_file(path: str, marker: str, username: str) -> bool:
	lines = _read_text_lines(path)
	if not lines:
		return False

	changed = False
	next_lines = []
	skip_next_client = False
	for line in lines:
		if skip_next_client:
			if line.lstrip().startswith("},{"):
				changed = True
				skip_next_client = False
				continue
			skip_next_client = False

		if _xray_marker_matches(line, marker, username):
			changed = True
			skip_next_client = True
			continue

		next_lines.append(line)

	if changed:
		_write_text_lines(path, next_lines)
	return changed


def _delete_db_entry_file(path: str, username: str) -> bool:
	lines = _read_text_lines(path)
	if not lines:
		return False

	changed = False
	next_lines = []
	for line in lines:
		parts = _xray_line_parts(line)
		if len(parts) >= 2 and parts[0] == "###" and parts[1] == username:
			changed = True
			continue
		next_lines.append(line)

	if changed:
		_write_text_lines(path, next_lines)
	return changed


def _remove_file(path: str):
	try:
		os.remove(path)
	except FileNotFoundError:
		return
	except IsADirectoryError:
		return


def _write_limit_file(path: str, value: int):
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "w", encoding="utf-8") as fh:
		fh.write(f"{int(value)}\n")


def _restart_xray() -> str:
	try:
		proc = subprocess.run(
			"systemctl restart xray",
			shell=True,
			text=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			timeout=60,
		)
	except subprocess.TimeoutExpired:
		return "Restart xray timeout."

	if proc.returncode != 0:
		return (proc.stdout or "Restart xray gagal.").strip()
	return ""


def _try_unsuspend_xray_account(service: str, username: str):
	cmd = XRAY_UNSUSPEND_COMMANDS.get(service)
	if not cmd:
		return
	suspended_path = f"/etc/kyt/suspended/{service}/{username}"
	if not os.path.isfile(suspended_path):
		return
	try:
		subprocess.run(
			[cmd, "--user", username],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL,
			timeout=60,
		)
	except Exception:
		return


def renew_xray_account(service: str, username: str, days, quota_gb=0, ip_limit=1) -> Dict:
	service_name = str(service or "").strip().lower()
	account_name = str(username or "").strip()
	marker = XRAY_ACCOUNT_MARKERS.get(service_name)
	if not marker or not account_name:
		return {"ok": False, "message": "Service atau username tidak valid."}

	try:
		add_days = int(str(days).strip())
	except Exception:
		return {"ok": False, "message": "Jumlah hari harus angka."}
	if add_days <= 0:
		return {"ok": False, "message": "Jumlah hari harus lebih dari 0."}

	try:
		ip_value = max(0, int(str(ip_limit or "0").strip()))
	except Exception:
		return {"ok": False, "message": "Limit IP harus angka."}

	try:
		quota_value = max(0, int(str(quota_gb or "0").strip()))
	except Exception:
		return {"ok": False, "message": "Quota harus angka."}

	current_exp = _find_xray_expiry(service_name, account_name)
	if not current_exp:
		_try_unsuspend_xray_account(service_name, account_name)
		current_exp = _find_xray_expiry(service_name, account_name)
	if not current_exp:
		return {"ok": False, "message": f"User `{account_name}` tidak ditemukan di /etc/xray/config.json."}

	today = DT.date.today()
	base_expiry = parse_account_expiry_date(current_exp) or today
	if base_expiry < today:
		base_expiry = today
	new_expiry = (base_expiry + DT.timedelta(days=add_days)).isoformat()

	config_changed = _update_marker_expiry_file("/etc/xray/config.json", marker, account_name, new_expiry)
	for conf_file in XRAY_CONF_FILES.get(service_name, []):
		_update_marker_expiry_file(conf_file, marker, account_name, new_expiry)
	db_changed = _update_db_expiry_file(XRAY_DB_FILES.get(service_name, ""), account_name, new_expiry)

	ip_path = f"/etc/kyt/limit/{service_name}/ip/{account_name}"
	if ip_value > 0:
		_write_limit_file(ip_path, ip_value)
	else:
		_remove_file(ip_path)

	if service_name != "shadowsocks":
		quota_path = f"/etc/{service_name}/{account_name}"
		_remove_file(quota_path)
		if quota_value > 0:
			_write_limit_file(quota_path, quota_value * 1024 * 1024 * 1024)

	restart_warning = _restart_xray()
	return {
		"ok": config_changed,
		"message": restart_warning,
		"expires_at": new_expiry,
		"db_changed": db_changed,
	}


def delete_xray_account(service: str, username: str) -> Dict:
	service_name = str(service or "").strip().lower()
	account_name = str(username or "").strip()
	marker = XRAY_ACCOUNT_MARKERS.get(service_name)
	if not marker or not account_name:
		return {"ok": False, "message": "Service atau username tidak valid."}

	current_exp = _find_xray_expiry(service_name, account_name)
	config_changed = _delete_marker_blocks_file("/etc/xray/config.json", marker, account_name)
	for conf_file in XRAY_CONF_FILES.get(service_name, []):
		_delete_marker_blocks_file(conf_file, marker, account_name)
	db_changed = _delete_db_entry_file(XRAY_DB_FILES.get(service_name, ""), account_name)

	_remove_file(f"/etc/{service_name}/{account_name}")
	_remove_file(f"/etc/kyt/limit/{service_name}/ip/{account_name}")
	_remove_file(f"/etc/funny/limit/{service_name}/ip/{account_name}")
	_remove_file(f"/etc/limit/{service_name}/{account_name}")
	_remove_file(f"/etc/limit/{service_name}/quota/{account_name}")
	state_path = f"/etc/kyt/suspended/{service_name}/{account_name}"
	state_removed = os.path.isfile(state_path)
	_remove_file(state_path)

	if config_changed:
		restart_warning = _restart_xray()
	else:
		restart_warning = ""

	if config_changed or db_changed or state_removed:
		return {
			"ok": True,
			"message": restart_warning,
			"expires_at": current_exp,
			"config_changed": config_changed,
			"db_changed": db_changed,
			"state_removed": state_removed,
		}

	return {"ok": False, "message": f"User `{account_name}` tidak ditemukan."}


def _xray_db_fields(service: str, username: str) -> Dict:
	path = XRAY_DB_FILES.get(service, "")
	for line in _read_text_lines(path):
		parts = _xray_line_parts(line)
		if len(parts) >= 3 and parts[0] == "###" and parts[1] == username:
			return {
				"expires_at": parts[2] if len(parts) > 2 else "",
				"uuid": parts[3] if len(parts) > 3 else "",
				"quota": parts[4] if len(parts) > 4 else "",
				"ip_limit": parts[5] if len(parts) > 5 else "",
			}
	return {}


def _xray_identifier_from_config(service: str, username: str) -> str:
	marker = XRAY_ACCOUNT_MARKERS.get(service, "")
	lines = _read_text_lines("/etc/xray/config.json")
	for idx, line in enumerate(lines):
		if not _xray_marker_matches(line, marker, username):
			continue
		for next_line in lines[idx + 1 : idx + 3]:
			key = "password" if service in {"trojan", "shadowsocks"} else "id"
			match = re.search(rf'"{key}"\s*:\s*"([^"]+)"', next_line)
			if match:
				return match.group(1)
	return ""


def _file_int_text(path: str) -> str:
	try:
		with open(path, "r", encoding="utf-8", errors="ignore") as fh:
			return fh.read().strip()
	except Exception:
		return ""


def _quota_label(service: str, username: str, db_fields: Dict = None) -> str:
	if service == "shadowsocks":
		return "-"
	raw = _file_int_text(f"/etc/{service}/{username}")
	if raw.isdigit():
		gb = int(raw) / (1024 * 1024 * 1024)
		return str(int(gb)) if gb.is_integer() else f"{gb:.2f}"
	db_quota = str((db_fields or {}).get("quota") or "").strip()
	return db_quota or "0"


def _ip_limit_label(service: str, username: str, db_fields: Dict = None) -> str:
	raw = _file_int_text(f"/etc/kyt/limit/{service}/ip/{username}")
	if raw:
		return raw
	db_ip = str((db_fields or {}).get("ip_limit") or "").strip()
	return db_ip or "-"


def _link_lines_for_account(service: str, username: str) -> List[str]:
	domain = str(globals().get("DOMAIN", globals().get("domain", "-")) or "-")
	if service == "ssh":
		return [
			f"• Payload WSS: `GET wss://BUG.COM/ HTTP/1.1[crlf]Host: {domain}[crlf]Upgrade: websocket[crlf][crlf]`",
			f"• OVPN WS SSL: `https://{domain}:81/ws-ssl.ovpn`",
			f"• OVPN SSL: `https://{domain}:81/ssl.ovpn`",
			f"• OVPN TCP: `https://{domain}:81/tcp.ovpn`",
			f"• OVPN UDP: `https://{domain}:81/udp.ovpn`",
			f"• Save Link: `https://{domain}:81/ssh-{username}.txt`",
		]
	if service == "vmess":
		return [
			f"• OpenClash: `https://{domain}:81/vmess-{username}.txt`",
			f"• QR TLS: `https://{domain}:81/vmess-{username}-tls.png`",
		]
	if service == "vless":
		return [
			f"• OpenClash: `https://{domain}:81/vless-{username}.txt`",
			f"• QR TLS: `https://{domain}:81/vless-{username}-tls.png`",
		]
	if service == "trojan":
		return [
			f"• OpenClash: `https://{domain}:81/trojan-{username}.txt`",
			f"• QR WS TLS: `https://{domain}:81/trojan-{username}-ws.png`",
		]
	if service == "shadowsocks":
		return [
			f"• JSON WS: `https://{domain}:81/sodosokws-{username}.txt`",
			f"• JSON gRPC: `https://{domain}:81/sodosokgrpc-{username}.txt`",
		]
	return []


def account_detail_text(service: str, username: str) -> str:
	service_name = str(service or "").strip().lower()
	account_name = str(username or "").strip()
	label = SERVICE_LABELS.get(service_name, service_name.upper())
	status = "aktif"
	exp = "-"
	identifier = ""
	quota = "-"
	ip_limit = "-"

	if service_name == "ssh":
		if _ssh_user_exists(account_name):
			exp = _ssh_user_expiry(account_name)
			status_raw = _ssh_user_status(account_name)
			status = "suspended" if status_raw == "L" else "aktif"
			ip_limit = _file_int_text(f"/etc/kyt/limit/ssh/ip/{account_name}") or "-"
		else:
			suspended = {item["username"]: item for item in list_suspended_accounts("ssh")}
			if account_name in suspended:
				exp = suspended[account_name].get("expires_at", "-")
				status = "suspended"
			else:
				return f"❌ Akun `{account_name}` tidak ditemukan."
	else:
		exp = _find_xray_expiry(service_name, account_name)
		if not exp:
			suspended = {item["username"]: item for item in list_suspended_accounts(service_name)}
			if account_name in suspended:
				exp = suspended[account_name].get("expires_at", "-")
				status = "suspended"
			else:
				return f"❌ Akun `{account_name}` tidak ditemukan."
		db_fields = _xray_db_fields(service_name, account_name)
		identifier = db_fields.get("uuid") or _xray_identifier_from_config(service_name, account_name)
		quota = _quota_label(service_name, account_name, db_fields)
		ip_limit = _ip_limit_label(service_name, account_name, db_fields)

	lines = [
		f"📄 **Detail Konfigurasi {label}**",
		"",
		f"• Username: `{account_name}`",
		f"• Status: `{status}`",
		f"• Expired: `{exp}`",
	]
	if service_name != "ssh":
		lines.append(f"• Quota: `{quota} GB`")
	lines.append(f"• Limit IP: `{ip_limit}`")
	if identifier:
		id_label = "Password" if service_name in {"trojan", "shadowsocks"} else "UUID"
		lines.append(f"• {id_label}: `{identifier}`")

	links = _link_lines_for_account(service_name, account_name)
	if links:
		lines.append("")
		lines.append("🔗 **Konfigurasi**")
		lines.extend(links)

	return "\n".join(lines)


def delete_ssh_account(username: str) -> Dict:
	account_name = str(username or "").strip()
	if not _ssh_user_exists(account_name):
		return {"ok": False, "message": f"User `{account_name}` tidak ditemukan."}

	try:
		proc = subprocess.run(
			["userdel", account_name],
			text=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			timeout=60,
		)
	except subprocess.TimeoutExpired:
		return {"ok": False, "message": "Delete SSH timeout."}
	if proc.returncode != 0:
		return {"ok": False, "message": (proc.stdout or "Gagal menghapus SSH user.").strip()}

	_remove_file(f"/etc/ssh/{account_name}")
	_delete_db_entry_file("/etc/ssh/.ssh.db", account_name)
	_remove_file(f"/etc/kyt/limit/ssh/ip/{account_name}")
	_remove_file(f"/etc/kyt/suspended/ssh/{account_name}")
	_remove_file(f"/var/www/html/ssh-{account_name}.txt")
	return {"ok": True, "message": f"SSH account deleted: {account_name}"}


def execute_account_action(service: str, action: str, username: str) -> Dict:
	service_name = str(service or "").strip().lower()
	action_name = str(action or "").strip().lower()
	account_name = str(username or "").strip()

	if service_name not in SERVICE_LABELS or not account_name:
		return {"ok": False, "message": "Service atau username tidak valid."}

	if action_name == "delete":
		return delete_ssh_account(account_name) if service_name == "ssh" else delete_xray_account(service_name, account_name)

	if action_name not in {"suspend", "unsuspend"}:
		return {"ok": False, "message": "Aksi tidak valid."}

	if service_name == "ssh":
		cmd = "suspssh" if action_name == "suspend" else "unsuspssh"
	else:
		cmd = XRAY_SUSPEND_COMMANDS.get(service_name) if action_name == "suspend" else XRAY_UNSUSPEND_COMMANDS.get(service_name)

	if not cmd:
		return {"ok": False, "message": "Command service tidak ditemukan."}

	try:
		proc = subprocess.run(
			[cmd, "--user", account_name],
			text=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			timeout=120,
		)
	except subprocess.TimeoutExpired:
		return {"ok": False, "message": "Command timeout."}
	except Exception as exc:
		return {"ok": False, "message": str(exc)}

	return {
		"ok": proc.returncode == 0,
		"message": (proc.stdout or "").strip() or ("Berhasil." if proc.returncode == 0 else "Gagal."),
	}


def get_user_accounts(
	tg_id,
	category: str = "",
	service: str = "",
	active_only: bool = True,
	limit: int = 100,
) -> List[Dict]:
	uid = _normalize_tg_id(tg_id)
	if not uid:
		return []

	query = "SELECT * FROM account_registry WHERE tg_id = ?"
	params = [uid]

	cat = str(category or "").strip().lower()
	if cat in {"ssh", "xray"}:
		query += " AND category = ?"
		params.append(cat)

	svc = str(service or "").strip().lower()
	if svc:
		query += " AND service = ?"
		params.append(svc)

	if active_only:
		query += " AND active = 1"

	query += " ORDER BY created_at DESC LIMIT ?"
	params.append(max(1, int(limit)))

	db = get_db()
	try:
		rows = db.execute(query, tuple(params)).fetchall()
		return [_row_to_dict(row) for row in rows]
	finally:
		db.close()


def user_owns_account(tg_id, service: str, username: str, active_only: bool = True) -> bool:
	uid = _normalize_tg_id(tg_id)
	svc = str(service or "").strip().lower()
	user = str(username or "").strip()

	if not uid or not svc or not user:
		return False

	if is_admin_user(uid):
		return True

	query = """
		SELECT 1
		FROM account_registry
		WHERE tg_id = ?
		  AND service = ?
		  AND LOWER(username) = LOWER(?)
	"""
	params = [uid, svc, user]
	if active_only:
		query += " AND active = 1"

	db = get_db()
	try:
		row = db.execute(query, tuple(params)).fetchone()
		return row is not None
	finally:
		db.close()


def parse_account_expiry_date(value) -> Optional[DT.date]:
	text = str(value or "").strip()
	if not text:
		return None

	if " " in text and re.match(r"^\d{4}-\d{2}-\d{2}\s+", text):
		text = text.split()[0]

	formats = (
		"%Y-%m-%d",
		"%Y/%m/%d",
		"%d %b, %Y",
		"%d %b %Y",
		"%d %B, %Y",
		"%d %B %Y",
		"%b %d, %Y",
		"%B %d, %Y",
	)
	for fmt in formats:
		try:
			return DT.datetime.strptime(text, fmt).date()
		except ValueError:
			continue
	return None


def list_expiring_accounts(days_before: int = 3) -> List[Dict]:
	window = max(0, int(days_before))
	today = DT.date.today()

	db = get_db()
	try:
		rows = db.execute(
			"""
			SELECT
				ar.*,
				tu.username AS telegram_username,
				tu.full_name AS telegram_full_name,
				tu.role AS telegram_role,
				tu.status AS telegram_status
			FROM account_registry ar
			LEFT JOIN telegram_users tu ON tu.tg_id = ar.tg_id
			WHERE ar.active = 1
			  AND ar.service IN ('ssh', 'vmess', 'vless', 'trojan', 'shadowsocks')
			ORDER BY ar.expires_at ASC, ar.service ASC, ar.username ASC
			"""
		).fetchall()
	finally:
		db.close()

	accounts = []
	for row in rows:
		item = _row_to_dict(row)
		expiry = parse_account_expiry_date(item.get("expires_at"))
		if expiry is None:
			continue
		days_left = (expiry - today).days
		if 0 <= days_left <= window:
			item["expiry_date"] = expiry.isoformat()
			item["days_left"] = days_left
			accounts.append(item)
	return accounts


def expiry_notification_sent(account_id, target_id, notice_date: str = "") -> bool:
	try:
		aid = int(account_id)
	except Exception:
		return True

	target = _normalize_tg_id(target_id)
	if not target:
		return True

	day = str(notice_date or DT.date.today().isoformat()).strip()
	db = get_db()
	try:
		row = db.execute(
			"""
			SELECT 1
			FROM expiry_notifications
			WHERE account_id = ? AND target_id = ? AND notice_date = ?
			""",
			(aid, target, day),
		).fetchone()
		return row is not None
	finally:
		db.close()


def mark_expiry_notification_sent(account_id, target_id, notice_date: str = ""):
	try:
		aid = int(account_id)
	except Exception:
		return

	target = _normalize_tg_id(target_id)
	if not target:
		return

	day = str(notice_date or DT.date.today().isoformat()).strip()
	db = get_db()
	try:
		db.execute(
			"""
			INSERT OR IGNORE INTO expiry_notifications (account_id, target_id, notice_date, created_at)
			VALUES (?, ?, ?, ?)
			""",
			(aid, target, day, _now()),
		)
		db.commit()
	finally:
		db.close()


def create_quota_request(tg_id, reason: str = "") -> Dict:
	uid = _normalize_tg_id(tg_id)
	if not uid:
		return {"ok": False, "status": "invalid"}

	if not is_user_approved(uid):
		return {"ok": False, "status": "not-approved"}

	reason = str(reason or "").strip()
	db = get_db()
	try:
		pending = db.execute(
			"SELECT * FROM quota_requests WHERE tg_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1",
			(uid,),
		).fetchone()
		if pending is not None:
			return {"ok": False, "status": "pending", "request": _row_to_dict(pending)}

		cur = db.execute(
			"INSERT INTO quota_requests (tg_id, reason, status, created_at) VALUES (?, ?, 'pending', ?)",
			(uid, reason, _now()),
		)
		db.commit()
		request_id = int(cur.lastrowid)
	finally:
		db.close()

	return {"ok": True, "status": "created", "request": get_quota_request(request_id)}


def get_quota_request(request_id: int) -> Optional[Dict]:
	db = get_db()
	try:
		row = db.execute("SELECT * FROM quota_requests WHERE id = ?", (int(request_id),)).fetchone()
		return _row_to_dict(row)
	finally:
		db.close()


def list_pending_quota_requests(limit: int = 20) -> List[Dict]:
	db = get_db()
	try:
		rows = db.execute(
			"SELECT * FROM quota_requests WHERE status = 'pending' ORDER BY created_at ASC LIMIT ?",
			(max(1, int(limit)),),
		).fetchall()
		return [_row_to_dict(row) for row in rows]
	finally:
		db.close()


def process_quota_request(
	request_id: int,
	admin_id,
	approved: bool,
	admin_reason: str = "",
	new_ssh_limit=None,
	new_xray_limit=None,
) -> Optional[Dict]:
	admin_uid = _normalize_tg_id(admin_id)
	status = "approved" if approved else "rejected"
	reason = str(admin_reason or "").strip()
	now = _now()

	db = get_db()
	try:
		row = db.execute(
			"SELECT * FROM quota_requests WHERE id = ? AND status = 'pending'",
			(int(request_id),),
		).fetchone()
		if row is None:
			return None

		request = _row_to_dict(row)
		tg_id = str(request["tg_id"])

		next_limits = get_user_limits(tg_id)
		if approved:
			next_ssh = _sanitize_limit_value(new_ssh_limit, next_limits["ssh_limit"])
			next_xray = _sanitize_limit_value(new_xray_limit, next_limits["xray_limit"])
			db.execute(
				"""
				INSERT INTO quota_limits (tg_id, ssh_limit, xray_limit, updated_by, updated_at)
				VALUES (?, ?, ?, ?, ?)
				ON CONFLICT(tg_id) DO UPDATE SET
					ssh_limit = excluded.ssh_limit,
					xray_limit = excluded.xray_limit,
					updated_by = excluded.updated_by,
					updated_at = excluded.updated_at
				""",
				(tg_id, next_ssh, next_xray, admin_uid, now),
			)
			next_limits = {"tg_id": tg_id, "ssh_limit": next_ssh, "xray_limit": next_xray}

		db.execute(
			"""
			UPDATE quota_requests
			SET status = ?, admin_id = ?, admin_reason = ?, processed_at = ?
			WHERE id = ?
			""",
			(status, admin_uid, reason, now, int(request_id)),
		)
		db.commit()
	finally:
		db.close()

	result = get_quota_request(request_id)
	if result is None:
		return None
	result["target_status"] = status
	result["limits"] = next_limits
	return result


def convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return "%s %s" % (s, size_name[i])
