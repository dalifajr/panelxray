import json
import os
from typing import Any


class ChatSessionStore:
    _instance_ = None
    _initialized_ = False

    storage_path = "chat-sessions.json"
    sessions: dict[str, dict[str, Any]] = {}

    def __new__(cls, *args, **kwargs):
        if not cls._instance_:
            cls._instance_ = super().__new__(cls)
        return cls._instance_

    def __init__(self):
        if self._initialized_:
            return

        if os.path.exists(self.storage_path):
            self._load()
        else:
            self._save()

        self._initialized_ = True

    def _load(self):
        with open(self.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                self.sessions = data
            else:
                self.sessions = {}

    def _save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.sessions, f, indent=2)

    def get_selected_number(self, chat_id: int) -> int | None:
        key = str(chat_id)
        chat_state = self.sessions.get(key, {})
        selected_number = chat_state.get("selected_number")
        return int(selected_number) if selected_number is not None else None

    def set_selected_number(self, chat_id: int, number: int):
        key = str(chat_id)
        if key not in self.sessions:
            self.sessions[key] = {}

        self.sessions[key]["selected_number"] = int(number)
        self._save()


ChatSessionStoreInstance = ChatSessionStore()
