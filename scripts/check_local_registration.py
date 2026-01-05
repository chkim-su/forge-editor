#!/usr/bin/env python3
"""
Check if a plugin project is registered as a local marketplace.

Usage:
    python check_local_registration.py --path /path/to/plugin/project

Exit codes:
    0 - Plugin is registered locally
    1 - Plugin is not registered locally
    2 - Error (not a plugin project, etc.)
"""

import argparse
import json
import os
import sys
from pathlib import Path


def get_settings_path() -> Path:
    """Get the path to Claude settings.json."""
    if sys.platform == "win32":
        base = Path(os.environ.get("USERPROFILE", ""))
    else:
        base = Path.home()
    return base / ".claude" / "settings.json"


def read_settings(settings_path: Path) -> dict:
    """Read existing settings or return empty dict."""
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def get_marketplace_name(plugin_path: Path) -> str:
    """Extract marketplace name from marketplace.json."""
    marketplace_json = plugin_path / ".claude-plugin" / "marketplace.json"
    if marketplace_json.exists():
        try:
            with open(marketplace_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("name", plugin_path.name)
        except (json.JSONDecodeError, KeyError):
            pass
    return plugin_path.name


def normalize_path(path: str) -> str:
    """Normalize path for comparison."""
    return str(Path(path).resolve()).replace("\\", "/").lower()


def check_local_registration(plugin_path: Path, settings_path: Path) -> dict:
    """Check if plugin is registered as local marketplace."""
    settings = read_settings(settings_path)

    marketplace_name = get_marketplace_name(plugin_path)
    local_key = f"{marketplace_name}-local"
    plugin_path_normalized = normalize_path(str(plugin_path))

    # Check extraKnownMarketplaces
    extra_marketplaces = settings.get("extraKnownMarketplaces", {})

    registered_key = None
    registered_path = None

    for key, config in extra_marketplaces.items():
        source = config.get("source", {})
        if source.get("source") == "directory":
            path = source.get("path", "")
            if normalize_path(path) == plugin_path_normalized:
                registered_key = key
                registered_path = path
                break

    # Check enabledPlugins (supports both dict and list formats)
    enabled_plugins = settings.get("enabledPlugins", {})
    is_enabled = False
    enabled_ref = None

    if registered_key:
        # Handle both dict format (new) and list format (legacy)
        if isinstance(enabled_plugins, dict):
            for plugin_ref, enabled in enabled_plugins.items():
                if f"@{registered_key}" in plugin_ref and enabled:
                    is_enabled = True
                    enabled_ref = plugin_ref
                    break
        else:
            # Legacy list format
            for plugin_ref in enabled_plugins:
                if f"@{registered_key}" in plugin_ref:
                    is_enabled = True
                    enabled_ref = plugin_ref
                    break

    return {
        "is_registered": registered_key is not None,
        "is_enabled": is_enabled,
        "marketplace_key": registered_key,
        "registered_path": registered_path,
        "enabled_ref": enabled_ref,
        "expected_key": local_key
    }


def main():
    parser = argparse.ArgumentParser(
        description="Check if a plugin project is registered as a local marketplace"
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Path to the plugin project directory"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON"
    )

    args = parser.parse_args()

    plugin_path = Path(args.path).resolve()
    settings_path = get_settings_path()

    # Validate plugin path
    marketplace_json = plugin_path / ".claude-plugin" / "marketplace.json"
    if not marketplace_json.exists():
        error = f"Error: Not a plugin project. Missing {marketplace_json}"
        if args.json:
            print(json.dumps({"success": False, "error": error}))
        else:
            print(error, file=sys.stderr)
        sys.exit(2)

    # Check registration
    result = check_local_registration(plugin_path, settings_path)

    if args.json:
        print(json.dumps({
            "success": True,
            **result
        }, indent=2))
    else:
        if result["is_registered"]:
            print(f"Plugin is registered locally")
            print(f"  Marketplace key: {result['marketplace_key']}")
            print(f"  Path: {result['registered_path']}")
            if result["is_enabled"]:
                print(f"  Enabled as: {result['enabled_ref']}")
            else:
                print(f"  Warning: Not in enabledPlugins list")
        else:
            print(f"Plugin is NOT registered locally")
            print(f"  Expected key: {result['expected_key']}")
            print(f"  Run: /wizard register")

    # Exit code based on registration status
    if result["is_registered"] and result["is_enabled"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
