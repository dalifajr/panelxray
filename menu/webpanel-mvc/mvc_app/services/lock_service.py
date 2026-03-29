from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - runtime utama di Linux
    fcntl = None


class LockTimeoutError(RuntimeError):
    pass


@contextmanager
def mutation_lock(lock_file: str, timeout_seconds: int = 30) -> Iterator[None]:
    path = Path(lock_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    if fcntl is not None and hasattr(fcntl, "flock"):
        flock_fn = getattr(fcntl, "flock")
        lock_ex = int(getattr(fcntl, "LOCK_EX", 2))
        lock_nb = int(getattr(fcntl, "LOCK_NB", 4))
        lock_un = int(getattr(fcntl, "LOCK_UN", 8))

        with path.open("a+", encoding="utf-8") as handle:
            started_at = time.monotonic()
            while True:
                try:
                    flock_fn(handle.fileno(), lock_ex | lock_nb)
                    break
                except BlockingIOError:
                    if time.monotonic() - started_at >= timeout_seconds:
                        raise LockTimeoutError(
                            "Operasi lain masih berjalan. Coba beberapa detik lagi."
                        )
                    time.sleep(0.2)

            try:
                yield
            finally:
                flock_fn(handle.fileno(), lock_un)
        return

    # Fallback non-Linux.
    started_at = time.monotonic()
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            if time.monotonic() - started_at >= timeout_seconds:
                raise LockTimeoutError("Operasi lain masih berjalan.")
            time.sleep(0.2)

    try:
        yield
    finally:
        try:
            os.close(fd)
        finally:
            if path.exists():
                path.unlink(missing_ok=True)
