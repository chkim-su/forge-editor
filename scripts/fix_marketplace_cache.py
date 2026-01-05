#!/usr/bin/env python3
"""
Fix Claude marketplace cache consistency issues.

This script fixes E023/E024 errors by:
1. Detecting mismatches between known_marketplaces.json and cached git remotes
2. Updating known_marketplaces.json to correct repo
3. Updating git remote in cached directory
4. Optionally re-cloning from correct source

Usage:
    python fix_marketplace_cache.py                    # Show issues
    python fix_marketplace_cache.py --fix              # Fix all issues
    python fix_marketplace_cache.py --fix <name>       # Fix specific marketplace
    python fix_marketplace_cache.py --remove <name>    # Remove marketplace entirely
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def get_cache_paths():
    """Get paths to Claude plugin cache files."""
    home = Path.home()
    return {
        "known_marketplaces": home / ".claude" / "plugins" / "known_marketplaces.json",
        "installed_plugins": home / ".claude" / "plugins" / "installed_plugins.json",
        "cache_base": home / ".claude" / "plugins" / "marketplaces",
        "settings": home / ".claude" / "settings.json",
    }


def load_json(path: Path) -> dict:
    """Load JSON file, return empty dict on error."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, IOError):
        return {}


def save_json(path: Path, data: dict) -> bool:
    """Save JSON file."""
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding='utf-8')
        return True
    except IOError as e:
        print(f"Error saving {path}: {e}", file=sys.stderr)
        return False


def get_git_remote(cache_dir: Path) -> str:
    """Get git remote origin URL from cache directory."""
    if not (cache_dir / ".git").exists():
        return ""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=cache_dir,
            timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def normalize_repo(url: str) -> str:
    """Normalize GitHub URL to owner/repo format."""
    return url.replace("https://github.com/", "").replace(".git", "")


def analyze_marketplace_cache():
    """Analyze all marketplace caches for consistency issues."""
    paths = get_cache_paths()
    known = load_json(paths["known_marketplaces"])
    issues = []

    for name, config in known.items():
        source = config.get("source", {})
        install_location = config.get("installLocation", "")

        cache_dir = Path(install_location) if install_location else paths["cache_base"] / name

        issue = {
            "name": name,
            "config": config,
            "cache_dir": cache_dir,
            "problems": []
        }

        # Check if cache exists
        if install_location and not cache_dir.exists():
            issue["problems"].append({
                "code": "E024",
                "message": f"Cache directory missing: {cache_dir}"
            })
        elif cache_dir.exists():
            # Check git remote consistency
            if isinstance(source, dict) and source.get("source") == "github":
                expected_repo = source.get("repo", "")
                actual_remote = get_git_remote(cache_dir)
                actual_repo = normalize_repo(actual_remote) if actual_remote else ""

                if actual_repo and expected_repo and actual_repo != expected_repo:
                    issue["problems"].append({
                        "code": "E023",
                        "message": f"Repo mismatch",
                        "expected_repo": expected_repo,
                        "actual_repo": actual_repo,
                        "actual_remote": actual_remote
                    })

        if issue["problems"]:
            issues.append(issue)

    return issues


def fix_repo_mismatch(name: str, correct_repo: str = None, use_actual: bool = True):
    """
    Fix repo mismatch by updating known_marketplaces.json and/or git remote.

    Args:
        name: Marketplace name
        correct_repo: The correct repo to use (owner/repo format)
        use_actual: If True and correct_repo not specified, use actual git remote as source of truth
    """
    paths = get_cache_paths()
    known = load_json(paths["known_marketplaces"])

    if name not in known:
        print(f"Marketplace '{name}' not found in known_marketplaces.json")
        return False

    config = known[name]
    source = config.get("source", {})
    install_location = config.get("installLocation", "")
    cache_dir = Path(install_location) if install_location else paths["cache_base"] / name

    if not isinstance(source, dict) or source.get("source") != "github":
        print(f"Marketplace '{name}' is not a GitHub source")
        return False

    current_repo = source.get("repo", "")
    actual_remote = get_git_remote(cache_dir)
    actual_repo = normalize_repo(actual_remote) if actual_remote else ""

    # Determine correct repo
    if correct_repo:
        target_repo = correct_repo
    elif use_actual and actual_repo:
        target_repo = actual_repo
    else:
        print(f"Cannot determine correct repo for '{name}'")
        return False

    print(f"\nFixing marketplace: {name}")
    print(f"  Current in known_marketplaces.json: {current_repo}")
    print(f"  Current git remote: {actual_repo}")
    print(f"  Target repo: {target_repo}")

    changes_made = False

    # Update known_marketplaces.json if needed
    if current_repo != target_repo:
        known[name]["source"]["repo"] = target_repo
        if save_json(paths["known_marketplaces"], known):
            print(f"  [OK] Updated known_marketplaces.json: {current_repo} -> {target_repo}")
            changes_made = True
        else:
            print(f"  [FAIL] Could not update known_marketplaces.json")
            return False

    # Update git remote if needed
    if actual_repo != target_repo and cache_dir.exists():
        new_url = f"https://github.com/{target_repo}.git"
        try:
            result = subprocess.run(
                ["git", "remote", "set-url", "origin", new_url],
                capture_output=True,
                text=True,
                cwd=cache_dir,
                timeout=5
            )
            if result.returncode == 0:
                print(f"  [OK] Updated git remote: {actual_remote} -> {new_url}")
                changes_made = True

                # Pull latest from correct repo
                print(f"  Fetching from new remote...")
                subprocess.run(
                    ["git", "fetch", "origin"],
                    capture_output=True,
                    cwd=cache_dir,
                    timeout=30
                )
                subprocess.run(
                    ["git", "reset", "--hard", "origin/main"],
                    capture_output=True,
                    cwd=cache_dir,
                    timeout=10
                )
                print(f"  [OK] Updated cache to latest")
            else:
                print(f"  [FAIL] Could not update git remote: {result.stderr}")
        except Exception as e:
            print(f"  [FAIL] Error updating git remote: {e}")

    if changes_made:
        print(f"  [DONE] Fixed marketplace '{name}'")
    else:
        print(f"  [OK] No changes needed for '{name}'")

    return True


def remove_marketplace(name: str):
    """Remove a marketplace entirely from all caches."""
    import shutil

    paths = get_cache_paths()

    # Remove from known_marketplaces.json
    known = load_json(paths["known_marketplaces"])
    if name in known:
        install_location = known[name].get("installLocation", "")
        del known[name]
        save_json(paths["known_marketplaces"], known)
        print(f"[OK] Removed from known_marketplaces.json")

        # Remove cache directory
        cache_dir = Path(install_location) if install_location else paths["cache_base"] / name
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            print(f"[OK] Removed cache directory: {cache_dir}")
    else:
        print(f"'{name}' not found in known_marketplaces.json")

    # Remove from installed_plugins.json
    installed = load_json(paths["installed_plugins"])
    to_remove = [k for k in installed.keys() if k.endswith(f"@{name}")]
    for k in to_remove:
        del installed[k]
    if to_remove:
        save_json(paths["installed_plugins"], installed)
        print(f"[OK] Removed {len(to_remove)} plugin(s) from installed_plugins.json")

    # Remove from settings.json enabledPlugins
    settings = load_json(paths["settings"])
    enabled = settings.get("enabledPlugins", {})
    if isinstance(enabled, dict):
        to_remove = [k for k in enabled.keys() if k.endswith(f"@{name}")]
        for k in to_remove:
            del enabled[k]
        if to_remove:
            settings["enabledPlugins"] = enabled
            save_json(paths["settings"], settings)
            print(f"[OK] Removed {len(to_remove)} plugin(s) from settings.json")

    print(f"\n[DONE] Marketplace '{name}' removed. Restart Claude Code to apply.")


def main():
    parser = argparse.ArgumentParser(
        description="Fix Claude marketplace cache consistency issues"
    )
    parser.add_argument(
        "--fix",
        nargs="?",
        const="__all__",
        metavar="NAME",
        help="Fix issues (optionally specify marketplace name)"
    )
    parser.add_argument(
        "--remove",
        metavar="NAME",
        help="Remove a marketplace entirely"
    )
    parser.add_argument(
        "--repo",
        metavar="OWNER/REPO",
        help="Specify correct repo when using --fix"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    if args.remove:
        remove_marketplace(args.remove)
        return

    # Analyze issues
    issues = analyze_marketplace_cache()

    if args.json:
        output = []
        for issue in issues:
            output.append({
                "name": issue["name"],
                "cache_dir": str(issue["cache_dir"]),
                "problems": issue["problems"]
            })
        print(json.dumps(output, indent=2))
        return

    if not issues:
        print("No cache consistency issues found.")
        return

    print("=" * 60)
    print("MARKETPLACE CACHE CONSISTENCY ISSUES")
    print("=" * 60)

    for issue in issues:
        print(f"\n{issue['name']}:")
        print(f"  Cache: {issue['cache_dir']}")
        for problem in issue["problems"]:
            print(f"  [{problem['code']}] {problem['message']}")
            if "expected_repo" in problem:
                print(f"         known_marketplaces.json: {problem['expected_repo']}")
                print(f"         actual git remote: {problem['actual_repo']}")

    print("\n" + "=" * 60)
    print(f"Total: {len(issues)} marketplace(s) with issues")
    print("=" * 60)

    if not args.fix:
        print("\nTo fix these issues, run:")
        print("  python fix_marketplace_cache.py --fix")
        print("  python fix_marketplace_cache.py --fix <name> --repo owner/repo")
        print("  python fix_marketplace_cache.py --remove <name>")
        return

    # Fix issues
    print("\n" + "=" * 60)
    print("FIXING ISSUES")
    print("=" * 60)

    if args.fix == "__all__":
        for issue in issues:
            for problem in issue["problems"]:
                if problem["code"] == "E023":
                    # For mismatch, we need user to specify which is correct
                    print(f"\n{issue['name']}: Repo mismatch detected")
                    print(f"  known_marketplaces.json says: {problem['expected_repo']}")
                    print(f"  git remote says: {problem['actual_repo']}")
                    print(f"  Specify --repo to fix, or use --remove to start fresh")
                elif problem["code"] == "E024":
                    print(f"\n{issue['name']}: Cache missing - use --remove to clean up registry")
    else:
        # Fix specific marketplace
        if args.repo:
            fix_repo_mismatch(args.fix, correct_repo=args.repo)
        else:
            print(f"Please specify --repo owner/repo for '{args.fix}'")


if __name__ == "__main__":
    main()
