#!/usr/bin/env python3
"""
manifest.py — manage ingest state in .manifest.json.

Usage:
  python scripts/manifest.py add <repo-path> [--category <cat>] [--manifest <path>]
  python scripts/manifest.py update <repo-key> --completed a,b --pending c,d [--manifest <path>]
  python scripts/manifest.py stale [--manifest <path>]
  python scripts/manifest.py show [--manifest <path>]
"""
import argparse
import json
import sys
from pathlib import Path

class HashStore:
    """Manages per-repo file hashes in wiki/repos/<name>/.hashes.json."""

    def __init__(self, wiki_root: Path, repo_key: str):
        self.path = Path(wiki_root) / "repos" / repo_key / ".hashes.json"

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def save(self, hashes: dict):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(hashes, indent=2) + "\n")

    def merge_delta(self, delta: dict):
        existing = self.load()
        for entry in delta.get("new", []) + delta.get("modified", []):
            existing[entry["path"]] = entry["hash"]
        for path in delta.get("deleted", []):
            existing.pop(path, None)
        self.save(existing)


_DEFAULT_MANIFEST = {
    "repos": {},
    "dimensions_version": "v1.0",
    "categories": {},
}


class ManifestManager:
    def __init__(self, path: Path):
        self.path = Path(path)
        if self.path.exists():
            self.data = json.loads(self.path.read_text())
        else:
            self.data = json.loads(json.dumps(_DEFAULT_MANIFEST))

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2) + "\n")

    def add_repo(self, repo_key: str, repo_path: str, category: str = None):
        if repo_key not in self.data["repos"]:
            self.data["repos"][repo_key] = {
                "path": repo_path,
                "last_ingest": None,
                "dimensions_version": None,
                "dimensions_completed": [],
                "dimensions_pending": [],
                "category": category,
            }
        if category:
            self.data["repos"][repo_key]["category"] = category
            cats = self.data.setdefault("categories", {})
            if category not in cats:
                cats[category] = []
            if repo_key not in cats[category]:
                cats[category].append(repo_key)

    def update_after_ingest(
        self,
        repo_key: str,
        completed_dimensions: list,
        pending_dimensions: list,
        timestamp: str,
    ):
        if repo_key not in self.data["repos"]:
            raise KeyError(f"Repo '{repo_key}' not found. Call add_repo first.")
        repo = self.data["repos"][repo_key]
        repo["last_ingest"] = timestamp
        repo["dimensions_completed"] = completed_dimensions
        repo["dimensions_pending"] = pending_dimensions
        repo["dimensions_version"] = self.data["dimensions_version"]

    def get_stale_repos(self) -> list:
        """Return list of repo keys whose recorded dimensions_version < current."""
        current_v = self.data.get("dimensions_version", "v1.0")
        return [
            key for key, info in self.data["repos"].items()
            if info.get("dimensions_version") and info["dimensions_version"] != current_v
        ]


def main():
    parser = argparse.ArgumentParser(description="Manage codebase-wiki .manifest.json")
    parser.add_argument("--manifest", default=".manifest.json")
    sub = parser.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add", help="Register a new repo")
    p_add.add_argument("repo_path")
    p_add.add_argument("--key", help="Repo key (default: basename of path)")
    p_add.add_argument("--category")

    p_upd = sub.add_parser("update", help="Update repo after ingest")
    p_upd.add_argument("repo_key")
    p_upd.add_argument("--completed", default="", help="Comma-separated completed dims")
    p_upd.add_argument("--pending", default="", help="Comma-separated pending dims")
    p_upd.add_argument("--timestamp", required=True, help="ISO8601 timestamp")
    p_upd.add_argument("--delta-json", default=None,
                       help="Path to delta.py JSON output; merges file hashes into manifest")

    p_stale = sub.add_parser("stale", help="List stale repos")
    p_stale.add_argument("--json", action="store_true",
                         help="Output count as a plain integer (for scripting)")
    sub.add_parser("show", help="Dump manifest as JSON")

    args = parser.parse_args()
    m = ManifestManager(Path(args.manifest))

    if args.cmd == "add":
        key = args.key or Path(args.repo_path).name
        m.add_repo(key, args.repo_path, category=args.category)
        m.save()
        print(f"Added repo '{key}'")

    elif args.cmd == "update":
        completed = [d for d in args.completed.split(",") if d]
        pending = [d for d in args.pending.split(",") if d]
        # Merge file hashes from delta.py output if provided
        file_hashes = {}
        if args.delta_json:
            delta = json.loads(Path(args.delta_json).read_text())
            # Merge new and modified entries; remove deleted
            existing = dict(m.data.get("repos", {}).get(args.repo_key, {}).get("file_hashes", {}))
            for entry in delta.get("new", []) + delta.get("modified", []):
                existing[entry["path"]] = entry["hash"]
            for path in delta.get("deleted", []):
                existing.pop(path, None)
            file_hashes = existing
        m.update_after_ingest(args.repo_key, completed, pending, file_hashes, args.timestamp)
        m.save()
        print(f"Updated '{args.repo_key}'")

    elif args.cmd == "stale":
        stale = m.get_stale_repos()
        if getattr(args, "json", False):
            # Machine-readable: print count only, used by session-start.sh
            print(len(stale))
        elif stale:
            for r in stale:
                print(r)
        else:
            print("No stale repos.")

    elif args.cmd == "show":
        print(json.dumps(m.data, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
