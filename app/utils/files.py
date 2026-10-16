import re
from pathlib import Path


def safe_suffix(filename: str | None) -> str:
    """Keep only a short, ordinary file extension from a user supplied name."""
    suffix = Path(filename or "").suffix.lower()
    return suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) else ".bin"


def path_is_within(path: Path, directory: Path) -> bool:
    """Return whether a resolved path is contained by a resolved directory."""
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False
