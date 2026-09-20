#!/usr/bin/env python3
"""Stage verified newsroom outputs without requiring optional artifacts.

Before staging, normalize volatile generation timestamps when the underlying
artifact is otherwise unchanged. This prevents the autonomous fast loop from
creating a new production commit/deployment merely because a JSON file was
rebuilt a few minutes later with identical substantive state.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_PATHS = (
    "index.html", "stories", "assets/timeline.css", "data/news.json",
    "data/breaking_fast_path.json", "data/storylines.json", "data/history.json",
    "data/published_timelines.json", "data/timeline_state_index.json",
    "data/canonical_ownership_report.json",
    "data/newsroom_health.json", "data/newsroom_dead_letters.json", "health",
)
AUXILIARY_PATHS = {
    "archive": ("archive", "data/archive_index.json", "data/historical_duplicate_candidates.json"),
    "notifications": ("notification-health", "data/server_follows.json", "data/notification_queue.json", "data/notification_health.json", "data/email_delivery_health.json"),
    "metadata": (),  # Metadata is installed into the already-core homepage.
    "recent": ("recent",),
    "feed": ("feed.xml",),
    "distribution": ("data/distribution_candidates.json",),
    "sitemap": ("sitemap.xml", "news-sitemap.xml"),
}
GOOD = {"HEALTHY", "RECOVERED"}
VOLATILE_KEYS = {"generated_at", "updated_at", "refreshed_at", "built_at", "last_run_at", "checked_at"}


def _git_head_text(relative, root=ROOT):
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative}"], cwd=root, capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else None


def _without_volatile(value):
    if isinstance(value, dict):
        return {k: _without_volatile(v) for k, v in value.items() if k not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [_without_volatile(v) for v in value]
    return value


def restore_timestamp_only_json(root=ROOT):
    """Restore tracked JSON whose only differences are volatile timestamps."""
    root = Path(root)
    data_dir = root / "data"
    if not data_dir.exists():
        return []
    restored = []
    for path in data_dir.glob("*.json"):
        relative = path.relative_to(root).as_posix()
        prior_text = _git_head_text(relative, root)
        if prior_text is None:
            continue
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
            prior = json.loads(prior_text)
        except (OSError, json.JSONDecodeError):
            continue
        if current == prior:
            continue
        if _without_volatile(current) == _without_volatile(prior):
            path.write_text(prior_text, encoding="utf-8")
            restored.append(relative)
    return restored


def selected_paths(root=ROOT):
    root = Path(root)
    health = json.loads((root / "data" / "newsroom_health.json").read_text(encoding="utf-8"))
    stages = health.get("stages") or {}
    paths = list(CORE_PATHS)
    for stage, candidates in AUXILIARY_PATHS.items():
        if (stages.get(stage) or {}).get("status") in GOOD:
            paths.extend(candidates)
    selected = []
    for relative in dict.fromkeys(paths):
        path = root / relative
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode == 0
        if path.exists() or tracked:
            selected.append(relative)
    return selected


def stage(root=ROOT):
    restore_timestamp_only_json(root)
    paths = selected_paths(root)
    if not paths:
        raise RuntimeError("no verified publication paths are available")
    subprocess.run(["git", "add", "-A", "--", *paths], cwd=root, check=True)
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()
    paths = selected_paths()
    if not args.print_only:
        stage()
    print("\n".join(paths))
