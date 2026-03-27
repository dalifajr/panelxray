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

import requests
from telethon import Button, TelegramClient, events

logging.basicConfig(level=logging.INFO)
uptime = DT.datetime.now()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAR_FILE = os.path.join(BASE_DIR, "var.txt")
DB_FILE = os.path.join(BASE_DIR, "database.db")

if not os.path.isfile(VAR_FILE):
	raise FileNotFoundError(f"Bot config tidak ditemukan: {VAR_FILE}")

with open(VAR_FILE, "r", encoding="utf-8") as f:
	exec(f.read(), globals())

API_ID = int(globals().get("API_ID", 6))
API_HASH = str(globals().get("API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e"))

bot = TelegramClient("ddsdswl", API_ID, API_HASH).start(bot_token=BOT_TOKEN)


def _bootstrap_db():
	x = sqlite3.connect(DB_FILE)
	c = x.cursor()
	c.execute("CREATE TABLE IF NOT EXISTS admin (user_id TEXT)")
	admin_id = str(globals().get("ADMIN", "")).strip()
	if admin_id:
		existing = c.execute("SELECT 1 FROM admin WHERE user_id = ?", (admin_id,)).fetchone()
		if existing is None:
			c.execute("INSERT INTO admin (user_id) VALUES (?)", (admin_id,))
	x.commit()
	x.close()


_bootstrap_db()


def get_db():
	x = sqlite3.connect(DB_FILE)
	x.row_factory = sqlite3.Row
	return x


def valid(user_id):
	db = get_db()
	try:
		rows = db.execute("SELECT user_id FROM admin").fetchall()
		allowed = [str(v[0]) for v in rows]
	finally:
		db.close()

	if str(user_id) in allowed:
		return "true"
	return "false"


def convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return "%s %s" % (s, size_name[i])
