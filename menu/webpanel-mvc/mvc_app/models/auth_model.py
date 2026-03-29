from pathlib import Path


def _read_first_line(file_path: str, fallback: str) -> str:
    path = Path(file_path)
    if not path.exists():
        return fallback

    content = path.read_text(encoding="utf-8", errors="ignore").strip().splitlines()
    if not content:
        return fallback

    return content[0].strip() or fallback


def load_panel_credentials(user_file: str, pass_file: str) -> tuple[str, str]:
    username = _read_first_line(user_file, "admin")
    # Fallback password sama dengan username hanya untuk bootstrap awal.
    password = _read_first_line(pass_file, username)
    return username, password
