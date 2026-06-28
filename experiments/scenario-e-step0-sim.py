#!/usr/bin/env python3
"""Simulate Step 0 delta detection logic for incremental re-ingest.

Reads .ingest-state.json, recomputes SHA-256 for tracked files,
compares against recorded values, and reverse-maps changed files
to affected entities via entity page frontmatter.
"""

import json
import hashlib
import sys
import os
import yaml
from pathlib import Path

REPO_DIR = "/Users/yuanlimiao/Work/codebase-wiki/wiki/repos/openclaw"
SOURCE_PATH = "/Users/yuanlimiao/Work/agent_harness/openclaw"
STATE_FILE = os.path.join(REPO_DIR, ".ingest-state.json")
ENTITIES_DIR = os.path.join(REPO_DIR, "entities")


def sha256_file(filepath):
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_ingest_state():
    with open(STATE_FILE) as f:
        return json.load(f)


def load_entity_source_files():
    """Build a reverse map: source_file -> [entity_slugs] from entity page frontmatter."""
    if not os.path.isdir(ENTITIES_DIR):
        return {}
    reverse_map = {}
    for fname in sorted(os.listdir(ENTITIES_DIR)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(ENTITIES_DIR, fname)
        with open(fpath) as f:
            content = f.read()
        if not content.startswith("---"):
            continue
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        try:
            fm = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            continue
        slug = fm.get("slug", fname.replace(".md", ""))
        source_files = fm.get("source_files", [])
        for sf in source_files:
            reverse_map.setdefault(sf, []).append(slug)
    return reverse_map


def main():
    state = load_ingest_state()
    recorded_files = state.get("files", {})
    source_path = state.get("source_path", SOURCE_PATH)

    # Build reverse map: source_file -> entities
    file_to_entities = load_entity_source_files()

    changed_files = []
    affected_entities = set()

    for rel_path, recorded_sha in recorded_files.items():
        abs_path = os.path.join(source_path, rel_path)
        if not os.path.isfile(abs_path):
            changed_files.append((rel_path, recorded_sha, "FILE_MISSING", None))
            for slug in file_to_entities.get(rel_path, []):
                affected_entities.add(slug)
            continue

        actual_sha = sha256_file(abs_path)
        if actual_sha != recorded_sha:
            changed_files.append((rel_path, recorded_sha, actual_sha, "SHA_MISMATCH"))
            for slug in file_to_entities.get(rel_path, []):
                affected_entities.add(slug)

    # Build entity dependency info
    entity_deps = {}
    for slug in affected_entities:
        for sf, slugs in file_to_entities.items():
            if slug in slugs and sf in recorded_files:
                entity_deps.setdefault(slug, []).append(sf)

    # Report
    print(f"Changed files: {len(changed_files)}")
    for rel_path, recorded, actual, reason in changed_files:
        if reason == "SHA_MISMATCH":
            print(f"  - {rel_path} (SHA mismatch: recorded={recorded[:16]}..., actual={actual[:16]}...)")
        elif reason == "FILE_MISSING":
            print(f"  - {rel_path} (FILE MISSING: recorded={recorded[:16]}...)")

    print(f"Affected entities: {len(affected_entities)}")
    for slug in sorted(affected_entities):
        deps = entity_deps.get(slug, [])
        print(f"  - {slug}: depends on {deps}")

    if not changed_files:
        print("\nNo changes detected. Repo is up-to-date.")

    return 0 if not changed_files else len(changed_files)


if __name__ == "__main__":
    sys.exit(main())
