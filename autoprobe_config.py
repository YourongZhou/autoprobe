"""Configuration defaults and CLI parsing for the autoprobe entrypoint."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _env_path(name: str, *parts: str) -> Path | None:
    """Build an optional platform path from an environment variable."""
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value).joinpath(*parts)


def _default_config_candidates() -> list[Path]:
    """Return common Clash-family config locations for Linux, macOS, and Windows."""
    mac_app_support = Path.home() / "Library" / "Application Support"
    candidates = [
        Path.home() / ".config" / "clash" / "config.yaml",
        Path.home() / ".config" / "mihomo" / "config.yaml",
        Path.home() / ".local" / "share" / "io.github.clash-verge-rev.clash-verge-rev" / "config.yaml",
        Path.home() / ".local" / "share" / "io.github.clash-verge-rev.clash-verge-rev" / "profiles" / "config.yaml",
        Path.home() / ".local" / "share" / "clash-verge" / "config.yaml",
        Path.home() / ".local" / "share" / "clash-verge" / "profiles" / "config.yaml",
        mac_app_support / "clash" / "config.yaml",
        mac_app_support / "mihomo" / "config.yaml",
        mac_app_support / "ClashX" / "config.yaml",
        mac_app_support / "ClashX Pro" / "config.yaml",
        mac_app_support / "io.github.clash-verge-rev.clash-verge-rev" / "config.yaml",
        mac_app_support / "io.github.clash-verge-rev.clash-verge-rev" / "profiles" / "config.yaml",
        mac_app_support / "clash-verge" / "config.yaml",
        mac_app_support / "clash-verge" / "profiles" / "config.yaml",
    ]
    windows_candidates = [
        _env_path("LOCALAPPDATA", "Clash for Windows", ".config", "config.yaml"),
        _env_path("LOCALAPPDATA", "clash", "config.yaml"),
        _env_path("LOCALAPPDATA", "mihomo", "config.yaml"),
        _env_path("APPDATA", "clash", "config.yaml"),
        _env_path("APPDATA", "mihomo", "config.yaml"),
        _env_path("APPDATA", "io.github.clash-verge-rev.clash-verge-rev", "config.yaml"),
        _env_path("APPDATA", "io.github.clash-verge-rev.clash-verge-rev", "profiles", "config.yaml"),
        _env_path("APPDATA", "clash-verge", "config.yaml"),
        _env_path("APPDATA", "clash-verge", "profiles", "config.yaml"),
    ]
    candidates.extend(path for path in windows_candidates if path is not None)
    return candidates


def _default_config_path() -> Path:
    """Choose a readable fallback path for the current platform."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "clash" / "config.yaml"
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "clash" / "config.yaml"
    return Path.home() / ".config" / "clash" / "config.yaml"


DEFAULT_URLS = [
    "https://chatgpt.com",
    "https://ab.chatgpt.com",
    "https://api.openai.com",
    "https://auth.openai.com",
]
SKIP_NODES = {"DIRECT", "REJECT"}
DEFAULT_SELECTOR = "🔰 选择节点"
DEFAULT_CLASH_CONFIG = _default_config_path()
DEFAULT_DELAY_URL = "https://chatgpt.com"
US_MARKERS = ("美国", "US", "USA", "United States", "America")
DEFAULT_CONFIG_CANDIDATES = _default_config_candidates()


def detect_vpn_context(proxy: str) -> list[str]:
    """Collect proxy-related environment variables for easier troubleshooting."""
    details: list[str] = []
    env_map = {
        "ALL_PROXY": os.environ.get("ALL_PROXY") or os.environ.get("all_proxy"),
        "HTTP_PROXY": os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy"),
        "HTTPS_PROXY": os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"),
        "NO_PROXY": os.environ.get("NO_PROXY") or os.environ.get("no_proxy"),
    }
    for key, value in env_map.items():
        if value:
            details.append(f"{key}={value}")
    if proxy:
        details.append(f"active_probe_proxy={proxy}")
    return details


def parse_simple_yaml(path: Path) -> dict[str, str]:
    """Read the small subset of flat YAML keys we need from Clash config files."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and value:
            values[key] = value
    return values


def normalize_controller(value: str) -> str:
    """Allow users to pass either host:port or a fully qualified controller URL."""
    return value if "://" in value else f"http://{value}"


def discover_config_path(explicit: str | None) -> Path:
    """Pick the first usable Clash-family config path, unless the user overrides it."""
    if explicit:
        return Path(explicit).expanduser()
    env_value = os.environ.get("CLASH_CODEX_CONFIG")
    if env_value:
        return Path(env_value).expanduser()
    for candidate in DEFAULT_CONFIG_CANDIDATES:
        if candidate.exists():
            return candidate
    return DEFAULT_CLASH_CONFIG


def discover_defaults(config_path: Path) -> dict[str, str]:
    """Derive controller/proxy defaults from the selected config file."""
    data = parse_simple_yaml(config_path)
    controller = data.get("external-controller", "").strip()
    controller_unix = data.get("external-controller-unix", "").strip()
    secret = data.get("secret", "")
    port = data.get("mixed-port") or data.get("socks-port") or "7890"
    proxy = f"socks5h://127.0.0.1:{port}"
    return {
        "config": str(config_path),
        "controller": normalize_controller(controller or "127.0.0.1:9090"),
        "controller_unix": controller_unix,
        "secret": secret,
        "proxy": proxy,
    }


def parse_args() -> argparse.Namespace:
    """Build the CLI parser after resolving config-backed default values."""
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", default=None)
    pre_args, _ = pre_parser.parse_known_args()
    config_path = discover_config_path(pre_args.config)
    defaults = discover_defaults(config_path)

    parser = argparse.ArgumentParser(
        description="Probe Clash selector nodes for Codex/OpenAI connectivity and switch to the best one."
    )
    parser.add_argument("--config", default=defaults["config"], help="Clash/Mihomo/Clash Verge config path")
    parser.add_argument("--controller", default=defaults["controller"], help="Clash controller URL")
    parser.add_argument("--controller-unix", default=defaults["controller_unix"], help="Clash controller unix socket path")
    parser.add_argument("--secret", default=defaults["secret"], help="Clash controller secret")
    parser.add_argument("--selector", default=os.environ.get("CLASH_CODEX_SELECTOR", DEFAULT_SELECTOR))
    parser.add_argument("--proxy", default=defaults["proxy"], help="Proxy URL passed to curl")
    parser.add_argument("--url", action="append", dest="urls", default=[], help="Probe URL. Repeatable.")
    parser.add_argument("--nodes", nargs="*", default=[], help="Explicit node names to test")
    parser.add_argument("--attempts", type=int, default=3, help="Attempts per URL per node")
    parser.add_argument("--timeout", type=int, default=12, help="curl max time in seconds")
    parser.add_argument("--delay-url", default=DEFAULT_DELAY_URL, help="URL used for Clash delay precheck")
    parser.add_argument("--delay-timeout-ms", type=int, default=8000, help="Timeout for Clash delay precheck")
    parser.add_argument("--precheck-workers", type=int, default=8, help="Parallel workers for delay precheck")
    parser.add_argument("--finalists", type=int, default=5, help="How many top prechecked nodes to validate with real requests")
    parser.add_argument("--switch-delay", type=float, default=0.8, help="Pause after switching nodes")
    parser.add_argument("--request-delay", type=float, default=0.4, help="Pause between requests")
    parser.add_argument("--top", type=int, default=12, help="Test only the first N nodes when --nodes is not used")
    parser.add_argument("--dry-run", action="store_true", help="Restore the original node at the end")
    return parser.parse_args()
