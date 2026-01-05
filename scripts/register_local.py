#!/usr/bin/env python3
"""
Register or unregister a plugin project as a local marketplace for testing.

Usage:
    # Register a local plugin
    python register_local.py --path /path/to/plugin/project

    # Unregister a local plugin
    python register_local.py --path /path/to/plugin/project --unregister

    # Force registration even if plugin is registered elsewhere
    python register_local.py --path /path/to/plugin/project --force

    # Dry run to preview changes
    python register_local.py --path /path/to/plugin/project --dry-run

Features:
- Detects duplicate registrations (same plugin from different marketplaces)
- Supports unregistering local plugins
- Cross-platform path normalization
- JSON output mode for automation

This script:
1. Reads the user's ~/.claude/settings.json
2. Checks for existing plugin registrations (duplicate detection)
3. Adds/removes the plugin path to/from extraKnownMarketplaces
4. Enables/disables the plugin in enabledPlugins
5. Saves the updated settings
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
            print(f"Warning: Could not parse {settings_path}, starting fresh")
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


def get_plugin_name(plugin_path: Path) -> str:
    """Extract first plugin name from marketplace.json."""
    marketplace_json = plugin_path / ".claude-plugin" / "marketplace.json"
    if marketplace_json.exists():
        try:
            with open(marketplace_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                plugins = data.get("plugins", [])
                if plugins:
                    return plugins[0].get("name", "plugin")
        except (json.JSONDecodeError, KeyError):
            pass
    return "plugin"


def detect_existing_registration(plugin_name: str, settings: dict, exclude_marketplace: str = None) -> list:
    """
    Detect if plugin is already registered from another marketplace.

    Args:
        plugin_name: Name of the plugin to check
        settings: Current settings dict
        exclude_marketplace: Marketplace key to exclude from check (e.g., the local key)

    Returns:
        List of existing registrations like ["plugin@marketplace", ...]
    """
    existing = []
    enabled_plugins = settings.get("enabledPlugins", {})

    # Handle both dict and list formats
    if isinstance(enabled_plugins, dict):
        for plugin_ref, enabled in enabled_plugins.items():
            if not enabled:
                continue
            # Parse plugin@marketplace format
            if "@" in plugin_ref:
                name, marketplace = plugin_ref.rsplit("@", 1)
                if name == plugin_name:
                    if exclude_marketplace and marketplace == exclude_marketplace:
                        continue
                    existing.append(plugin_ref)
    else:
        # Legacy list format
        for plugin_ref in enabled_plugins:
            if "@" in plugin_ref:
                name, marketplace = plugin_ref.rsplit("@", 1)
                if name == plugin_name:
                    if exclude_marketplace and marketplace == exclude_marketplace:
                        continue
                    existing.append(plugin_ref)

    return existing


def unregister_local(plugin_path: Path, settings_path: Path) -> dict:
    """
    Unregister a local marketplace registration.

    Returns:
        Dict with removed_marketplace, removed_plugin, and updated settings
    """
    settings = read_settings(settings_path)

    marketplace_name = get_marketplace_name(plugin_path)
    plugin_name = get_plugin_name(plugin_path)
    local_key = f"{marketplace_name}-local"
    plugin_ref = f"{plugin_name}@{local_key}"

    removed_marketplace = False
    removed_plugin = False

    # Remove from extraKnownMarketplaces
    if "extraKnownMarketplaces" in settings:
        if local_key in settings["extraKnownMarketplaces"]:
            del settings["extraKnownMarketplaces"][local_key]
            removed_marketplace = True

    # Remove from enabledPlugins
    if "enabledPlugins" in settings:
        if isinstance(settings["enabledPlugins"], dict):
            if plugin_ref in settings["enabledPlugins"]:
                del settings["enabledPlugins"][plugin_ref]
                removed_plugin = True
        elif isinstance(settings["enabledPlugins"], list):
            if plugin_ref in settings["enabledPlugins"]:
                settings["enabledPlugins"].remove(plugin_ref)
                removed_plugin = True

    return {
        "settings": settings,
        "marketplace_key": local_key,
        "plugin_ref": plugin_ref,
        "removed_marketplace": removed_marketplace,
        "removed_plugin": removed_plugin
    }


def register_local(plugin_path: Path, settings_path: Path) -> dict:
    """Register plugin as local marketplace."""
    settings = read_settings(settings_path)

    # Get names
    marketplace_name = get_marketplace_name(plugin_path)
    plugin_name = get_plugin_name(plugin_path)
    local_key = f"{marketplace_name}-local"

    # Ensure extraKnownMarketplaces exists
    if "extraKnownMarketplaces" not in settings:
        settings["extraKnownMarketplaces"] = {}

    # Add local marketplace
    # Use forward slashes for cross-platform compatibility
    plugin_path_str = str(plugin_path).replace("\\", "/")

    # CRITICAL: Use "source": "directory" - the discriminator field name is "source"
    # Valid discriminator values: 'url' | 'github' | 'git' | 'npm' | 'file' | 'directory'
    # Schema reference: Claude Code settings.json extraKnownMarketplaces schema
    settings["extraKnownMarketplaces"][local_key] = {
        "source": {
            "source": "directory",
            "path": plugin_path_str
        }
    }

    # Ensure enabledPlugins exists and is an OBJECT (not array!)
    # Claude Code expects: {"plugin@marketplace": true}
    if "enabledPlugins" not in settings:
        settings["enabledPlugins"] = {}
    elif isinstance(settings["enabledPlugins"], list):
        # Convert list format to object format
        # Old format: ["plugin@marketplace"]
        # Correct format: {"plugin@marketplace": true}
        old_plugins = settings["enabledPlugins"]
        settings["enabledPlugins"] = {p: True for p in old_plugins}

    # Add plugin to enabled plugins (object format)
    plugin_ref = f"{plugin_name}@{local_key}"
    settings["enabledPlugins"][plugin_ref] = True

    return {
        "settings": settings,
        "marketplace_key": local_key,
        "plugin_ref": plugin_ref
    }


def save_settings(settings: dict, settings_path: Path) -> None:
    """Save settings to file."""
    # Ensure directory exists
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="Register or unregister a plugin project as a local marketplace for testing"
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Path to the plugin project directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force registration even if plugin is already registered elsewhere"
    )
    parser.add_argument(
        "--unregister",
        action="store_true",
        help="Unregister the local plugin instead of registering"
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
        sys.exit(1)

    # Handle unregister mode
    if args.unregister:
        result = unregister_local(plugin_path, settings_path)

        if args.dry_run:
            if args.json:
                print(json.dumps({
                    "success": True,
                    "dry_run": True,
                    "action": "unregister",
                    "marketplace_key": result["marketplace_key"],
                    "plugin_ref": result["plugin_ref"],
                    "would_remove_marketplace": result["removed_marketplace"],
                    "would_remove_plugin": result["removed_plugin"]
                }, indent=2))
            else:
                print("Dry run - would unregister:")
                print(f"  Marketplace: {result['marketplace_key']} {'(exists)' if result['removed_marketplace'] else '(not found)'}")
                print(f"  Plugin: {result['plugin_ref']} {'(exists)' if result['removed_plugin'] else '(not found)'}")
        else:
            if not result["removed_marketplace"] and not result["removed_plugin"]:
                if args.json:
                    print(json.dumps({"success": False, "error": "Plugin not registered locally"}))
                else:
                    print("Plugin is not registered locally. Nothing to unregister.")
                sys.exit(1)

            save_settings(result["settings"], settings_path)

            if args.json:
                print(json.dumps({
                    "success": True,
                    "action": "unregister",
                    "marketplace_key": result["marketplace_key"],
                    "plugin_ref": result["plugin_ref"],
                    "removed_marketplace": result["removed_marketplace"],
                    "removed_plugin": result["removed_plugin"]
                }, indent=2))
            else:
                print("Successfully unregistered local plugin!")
                if result["removed_marketplace"]:
                    print(f"  Removed marketplace: {result['marketplace_key']}")
                if result["removed_plugin"]:
                    print(f"  Removed plugin: {result['plugin_ref']}")
                print(f"  Settings: {settings_path}")
                print()
                print("Restart Claude Code to apply changes.")
        return

    # Check for existing registrations before registering
    plugin_name = get_plugin_name(plugin_path)
    marketplace_name = get_marketplace_name(plugin_path)
    local_key = f"{marketplace_name}-local"

    settings = read_settings(settings_path)
    existing = detect_existing_registration(plugin_name, settings, exclude_marketplace=local_key)

    if existing and not args.force:
        if args.json:
            print(json.dumps({
                "success": False,
                "error": "duplicate_registration",
                "message": f"Plugin '{plugin_name}' is already registered elsewhere",
                "existing_registrations": existing,
                "hint": "Use --force to register anyway"
            }, indent=2))
            sys.exit(1)
        else:
            print(f"⚠️  Plugin '{plugin_name}' is already registered:", file=sys.stderr)
            for reg in existing:
                print(f"    {reg}", file=sys.stderr)
            print(file=sys.stderr)
            print("This may cause conflicts. Options:", file=sys.stderr)
            print("  1. Use --force to register anyway (creates duplicate)", file=sys.stderr)
            print("  2. Uninstall the existing plugin first", file=sys.stderr)
            sys.exit(1)

    # Register
    result = register_local(plugin_path, settings_path)

    if args.dry_run:
        if args.json:
            output = {
                "success": True,
                "dry_run": True,
                "marketplace_key": result["marketplace_key"],
                "plugin_ref": result["plugin_ref"],
                "settings_path": str(settings_path),
                "settings_preview": result["settings"]
            }
            if existing:
                output["warning"] = "duplicate_registration"
                output["existing_registrations"] = existing
            print(json.dumps(output, indent=2))
        else:
            print("Dry run - would make the following changes:")
            print(f"  Settings file: {settings_path}")
            print(f"  Marketplace key: {result['marketplace_key']}")
            print(f"  Plugin reference: {result['plugin_ref']}")
            if existing:
                print(f"\n⚠️  Warning: Plugin already registered as: {', '.join(existing)}")
            print(f"\nSettings preview:")
            print(json.dumps(result["settings"], indent=2))
    else:
        save_settings(result["settings"], settings_path)

        if args.json:
            output = {
                "success": True,
                "marketplace_key": result["marketplace_key"],
                "plugin_ref": result["plugin_ref"],
                "settings_path": str(settings_path)
            }
            if existing:
                output["warning"] = "duplicate_registration"
                output["existing_registrations"] = existing
            print(json.dumps(output, indent=2))
        else:
            print(f"Successfully registered local plugin!")
            print(f"  Marketplace: {result['marketplace_key']}")
            print(f"  Plugin: {result['plugin_ref']}")
            print(f"  Settings: {settings_path}")
            if existing:
                print(f"\n⚠️  Warning: Plugin also registered as: {', '.join(existing)}")
                print("  Consider uninstalling duplicate registrations to avoid conflicts.")
            print()
            print("Next steps:")
            print("  1. Restart Claude Code to apply changes")
            print("  2. Test your plugin functionality")
            print("  3. Run '/wizard publish' after testing")


if __name__ == "__main__":
    main()
