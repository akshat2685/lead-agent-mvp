import os
from pathlib import Path


def load_env(path=None):
    env_path = Path(path) if path else Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return 0
    loaded = 0
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = clean_env_value(value)
        loaded += 1
    return loaded


def clean_env_value(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value
