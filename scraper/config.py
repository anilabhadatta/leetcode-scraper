"""ConfigParser-backed configuration for LeetCode Scraper.

Config files live at  ~/.leetcode-scraper/config_<slot>.ini
and use a single [scraper] section.
"""
from __future__ import annotations

import configparser
import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".leetcode-scraper"
_SECTION = "scraper"

# Active slot – mutated by select_config_interactive()
selected_config: str = "0"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Config:
    leetcode_cookie: str = ""
    cards_url_path: str = ""
    questions_url_path: str = ""
    save_path: str = ""
    company_tag_save_path: str = ""
    save_images_locally: bool = False
    overwrite: bool = False
    verbose_logging: bool = False

    def __getitem__(self, key: str):       # dict-compat shim for legacy callers
        return getattr(self, key)

    def get(self, key: str, default=None): # dict-compat
        return getattr(self, key, default)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def _config_path() -> Path:
    return _ensure_dir() / f"config_{selected_config}.ini"


def _parse_bool(val: str) -> bool:
    return val.strip().lower() in ("true", "1", "yes", "t")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_configs() -> list[str]:
    """Return names of all existing config slots."""
    _ensure_dir()
    return sorted(p.name for p in CONFIG_DIR.glob("config_*.ini"))


def load_config() -> Config:
    """Load the active config slot.  Raises if file is missing or incomplete."""
    path = _config_path()
    if not path.exists():
        raise FileNotFoundError(f"No config at {path}. Run option [1] to create one.")
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    if _SECTION not in parser:
        raise ValueError(f"Config {path} is missing the [{_SECTION}] section.")
    s = parser[_SECTION]
    return Config(
        leetcode_cookie=s.get("leetcode_cookie", ""),
        cards_url_path=s.get("cards_url_path", ""),
        questions_url_path=s.get("questions_url_path", ""),
        save_path=s.get("save_path", ""),
        company_tag_save_path=s.get("company_tag_save_path", ""),
        save_images_locally=_parse_bool(s.get("save_images_locally", "false")),
        overwrite=_parse_bool(s.get("overwrite", "false")),
        verbose_logging=_parse_bool(s.get("verbose_logging", "false")),
    )


def save_config(cfg: Config) -> None:
    """Persist a Config dataclass to the active slot."""
    parser = configparser.ConfigParser()
    parser[_SECTION] = {
        "leetcode_cookie": cfg.leetcode_cookie,
        "cards_url_path": cfg.cards_url_path,
        "questions_url_path": cfg.questions_url_path,
        "save_path": cfg.save_path,
        "company_tag_save_path": cfg.company_tag_save_path,
        "save_images_locally": str(cfg.save_images_locally).lower(),
        "overwrite": str(cfg.overwrite).lower(),
        "verbose_logging": str(cfg.verbose_logging).lower(),
    }
    with _config_path().open("w", encoding="utf-8") as fh:
        parser.write(fh)
    log.info("Config saved → %s", _config_path())


def generate_config() -> None:
    """Interactive wizard – create or update the active config slot."""
    print(f"\n  Config file : {_config_path()}")
    print("  Leave blank to keep the existing value.\n")
    try:
        existing = load_config()
    except (FileNotFoundError, ValueError):
        existing = Config()

    def _ask(prompt: str, current) -> str:
        display = str(current)[:20] + ("…" if len(str(current)) > 20 else "")
        return input(f"  {prompt} [{display}]: ").strip() or str(current)

    updated = Config(
        leetcode_cookie    = _ask("LEETCODE_SESSION cookie",  existing.leetcode_cookie),
        cards_url_path     = _ask("Cards URL file path",       existing.cards_url_path),
        questions_url_path = _ask("Questions URL file path",   existing.questions_url_path),
        save_path          = _ask("HTML save folder",          existing.save_path),
        company_tag_save_path = _ask("Company tags file path", existing.company_tag_save_path),
        save_images_locally = (
            input(f"  Save images as base64? [{'T' if existing.save_images_locally else 'F'}] (T/F): ")
            .strip().upper() == "T"
        ),
        overwrite = (
            input(f"  Overwrite existing files? [{'T' if existing.overwrite else 'F'}] (T/F): ")
            .strip().upper() == "T"
        ),
        verbose_logging = (
            input(f"  Show verbose logs? [{'T' if existing.verbose_logging else 'F'}] (T/F): ")
            .strip().upper() == "T"
        ),
    )
    save_config(updated)
    print(f"\n  ✓ Config saved → {_config_path()}\n")


def select_config_interactive() -> None:
    """Let the user pick an existing slot or type a new number."""
    global selected_config
    slots = list_configs()
    if slots:
        print("\n  Existing configs:")
        for s in slots:
            print(f"    {s}")
    selected_config = input(
        "\n  Enter config slot (or a new number to create): "
    ).strip() or "0"
    print(f"  → Using config_{selected_config}.ini\n")
