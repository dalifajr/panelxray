from __future__ import annotations

import json
import threading
import time
from contextvars import ContextVar
from pathlib import Path

from app.client.ciam import get_new_token
from app.client.engsel import get_profile
from app.util import ensure_api_key

AUTH_SCOPE_KEY = ContextVar("mecli_auth_scope", default="global")
GLOBAL_SCOPE = "global"
USER_SCOPE_PREFIX = "user_"

class Auth:
    _instance_ = None
    _initialized_ = False

    api_key = ""

    refresh_tokens = []
    # Format of refresh_tokens:
    # [
        # {
            # "number": int,
            # "subscriber_id": str,
            # "subscription_type": str,
            # "refresh_token": str
        # }
    # ]

    active_user = None
    # {
    #     "number": int,
    #     "subscriber_id": str,
    #     "subscription_type": str,
    #     "tokens": {
    #         "refresh_token": str,
    #         "access_token": str,
    #         "id_token": str
	#     }
    # }
    
    last_refresh_time = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance_:
            cls._instance_ = super().__new__(cls)
        return cls._instance_
    
    def __init__(self):
        if self._initialized_:
            return

        self._lock = threading.RLock()
        self._root_dir = Path(__file__).resolve().parents[2]
        self._active_scope = ""
        self._refresh_file = self._root_dir / "refresh-tokens.json"
        self._active_file = self._root_dir / "active.number"

        self.api_key = ensure_api_key()
        self.refresh_tokens = []
        self.active_user = None
        self.last_refresh_time = int(time.time())

        self._switch_scope_if_needed(force=True)
        self._initialized_ = True

    def _resolve_scope(self) -> str:
        key = AUTH_SCOPE_KEY.get() or GLOBAL_SCOPE
        return key

    def _scope_dir(self, scope: str) -> Path:
        if scope == GLOBAL_SCOPE:
            return self._root_dir
        return self._root_dir / "user_data" / scope

    def _switch_scope_if_needed(self, force: bool = False):
        with self._lock:
            scope = self._resolve_scope()
            if not force and scope == self._active_scope:
                return

            self._active_scope = scope
            base_dir = self._scope_dir(scope)
            base_dir.mkdir(parents=True, exist_ok=True)

            self._refresh_file = base_dir / "refresh-tokens.json"
            self._active_file = base_dir / "active.number"

            if not self._refresh_file.exists():
                self._refresh_file.write_text("[]\n", encoding="utf-8")

            self.refresh_tokens = []
            self.active_user = None
            self.last_refresh_time = int(time.time())

            self.load_tokens()
            self.load_active_number()

    def set_runtime_owner(self, owner_id: int | str | None, is_admin: bool = False) -> str:
        """
        Set runtime scope for auth data.
        - Admin/default scope uses root refresh-tokens.json + active.number.
        - Non-admin users use isolated files under user_data/user_<telegram_id>/.
        """
        if owner_id is None or is_admin:
            scope = GLOBAL_SCOPE
        else:
            scope = f"{USER_SCOPE_PREFIX}{int(owner_id)}"

        AUTH_SCOPE_KEY.set(scope)
        self._switch_scope_if_needed()
        return scope

    def get_runtime_scope(self) -> str:
        self._switch_scope_if_needed()
        return self._active_scope
            
    def load_tokens(self):
        with self._lock:
            self._switch_scope_if_needed()
            try:
                with self._refresh_file.open("r", encoding="utf-8") as f:
                    refresh_tokens = json.load(f)
            except Exception:
                refresh_tokens = []

            if not isinstance(refresh_tokens, list):
                refresh_tokens = []

            self.refresh_tokens = []
            for rt in refresh_tokens:
                if isinstance(rt, dict) and "number" in rt and "refresh_token" in rt:
                    self.refresh_tokens.append(rt)
                else:
                    print(f"Invalid token entry: {rt}")

    def add_refresh_token(self, number: int, refresh_token: str):
        with self._lock:
            self._switch_scope_if_needed()
            # Check if number already exist, if yes, replace it, if not append
            existing = next((rt for rt in self.refresh_tokens if rt["number"] == number), None)
            if existing:
                existing["refresh_token"] = refresh_token
            else:
                tokens = get_new_token(self.api_key, refresh_token, "")
                profile_data = get_profile(self.api_key, tokens["access_token"], tokens["id_token"])
                sub_id = profile_data["profile"]["subscriber_id"]
                sub_type = profile_data["profile"]["subscription_type"]

                self.refresh_tokens.append({
                    "number": int(number),
                    "subscriber_id": sub_id,
                    "subscription_type": sub_type,
                    "refresh_token": refresh_token
                })

            # Save to file
            self.write_tokens_to_file()

            # Set active user to newly added
            self.set_active_user(number)
            
    def remove_refresh_token(self, number: int):
        with self._lock:
            self._switch_scope_if_needed()
            self.refresh_tokens = [rt for rt in self.refresh_tokens if rt["number"] != number]

            # Save to file
            self.write_tokens_to_file()

            # If the removed user was the active user, select a new active user if available
            if self.active_user and self.active_user["number"] == number:
                # Select the first user as active user by default
                if len(self.refresh_tokens) != 0:
                    first_rt = self.refresh_tokens[0]
                    tokens = get_new_token(self.api_key, first_rt["refresh_token"], first_rt.get("subscriber_id", ""))
                    if tokens:
                        self.set_active_user(first_rt["number"])
                else:
                    self.active_user = None
                    self.write_active_number()

    def set_active_user(self, number: int):
        with self._lock:
            self._switch_scope_if_needed()
            # Get refresh token for the number from refresh_tokens
            rt_entry = next((rt for rt in self.refresh_tokens if rt["number"] == number), None)
            if not rt_entry:
                print(f"No refresh token found for number: {number}")
                return False

            tokens = get_new_token(self.api_key, rt_entry["refresh_token"], rt_entry.get("subscriber_id", ""))
            if not tokens:
                print(f"Failed to get tokens for number: {number}. The refresh token might be invalid or expired.")
                return False

            profile_data = get_profile(self.api_key, tokens["access_token"], tokens["id_token"])
            subscriber_id = profile_data["profile"]["subscriber_id"]
            subscription_type = profile_data["profile"]["subscription_type"]

            self.active_user = {
                "number": int(number),
                "subscriber_id": subscriber_id,
                "subscription_type": subscription_type,
                "tokens": tokens
            }

            # Update refresh token entry with subscriber_id and subscription_type
            rt_entry["subscriber_id"] = subscriber_id
            rt_entry["subscription_type"] = subscription_type

            # Update refresh token. The real client app do this, not sure why cz refresh token should still be valid
            rt_entry["refresh_token"] = tokens["refresh_token"]
            self.write_tokens_to_file()

            self.last_refresh_time = int(time.time())

            # Save active number to file
            self.write_active_number()
            return True

    def renew_active_user_token(self):
        with self._lock:
            self._switch_scope_if_needed()
            if self.active_user:
                tokens = get_new_token(self.api_key, self.active_user["tokens"]["refresh_token"], self.active_user["subscriber_id"])
                if tokens:
                    self.active_user["tokens"] = tokens
                    self.last_refresh_time = int(time.time())
                    self.add_refresh_token(self.active_user["number"], self.active_user["tokens"]["refresh_token"])

                    print("Active user token renewed successfully.")
                    return True
                else:
                    print("Failed to renew active user token.")
            else:
                print("No active user set or missing refresh token.")
            return False
    
    def get_active_user(self):
        with self._lock:
            self._switch_scope_if_needed()
            if not self.active_user:
                # Choose the first user if available
                if len(self.refresh_tokens) != 0:
                    first_rt = self.refresh_tokens[0]
                    tokens = get_new_token(self.api_key, first_rt["refresh_token"], first_rt.get("subscriber_id", ""))
                    if tokens:
                        self.set_active_user(first_rt["number"])
                return None

            if self.last_refresh_time is None or (int(time.time()) - self.last_refresh_time) > 300:
                self.renew_active_user_token()
                self.last_refresh_time = time.time()

            return self.active_user
    
    def get_active_tokens(self) -> dict | None:
        active_user = self.get_active_user()
        return active_user["tokens"] if active_user else None
    
    def write_tokens_to_file(self):
        with self._lock:
            self._switch_scope_if_needed()
            with self._refresh_file.open("w", encoding="utf-8") as f:
                json.dump(self.refresh_tokens, f, indent=4)
    
    def write_active_number(self):
        with self._lock:
            self._switch_scope_if_needed()
            if self.active_user:
                with self._active_file.open("w", encoding="utf-8") as f:
                    f.write(str(self.active_user["number"]))
            else:
                if self._active_file.exists():
                    self._active_file.unlink()
    
    def load_active_number(self):
        with self._lock:
            self._switch_scope_if_needed()
            if self._active_file.exists():
                with self._active_file.open("r", encoding="utf-8") as f:
                    number_str = f.read().strip()
                    if number_str.isdigit():
                        number = int(number_str)
                        self.set_active_user(number)

AuthInstance = Auth()
