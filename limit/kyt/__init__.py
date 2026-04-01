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

bot = TelegramClient("ddsdswl", API_ID, API_HASH).start(bot_token=BOT_TOKEN)


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
	_migrate_legacy_schema(c)
	c.execute("CREATE INDEX IF NOT EXISTS idx_access_requests_status ON access_requests(status, created_at)")
	c.execute("CREATE INDEX IF NOT EXISTS idx_quota_requests_status ON quota_requests(status, created_at)")
	c.execute("CREATE INDEX IF NOT EXISTS idx_account_registry_owner ON account_registry(tg_id, category, service)")

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
