#!/usr/bin/env python3
"""Stage verified newsroom outputs without requiring optional artifacts."""
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
    "data/newsroom_health.json", "data/newsroom_dead_letters.json", "health",
)
AUXILIARY_PATHS = {
    "archive": ("archive", "data/archive_index.json"),
    "notifications": ("notification-health", "data/server_follows.json", "data/notification_queue.json", "data/notification_health.json", "data/email_delivery_health.json"),
    "metadata": (),  # Metadata is installed into the already-core homepage.
    "recent": ("recent",),
    "feed": ("feed.xml",),
    "distribution": ("data/distribution_candidates.json",),
    "sitemap": ("sitemap.xml", "news-sitemap.xml"),
}
GOOD = {"HEALTHY", "RECOVERED"}


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
