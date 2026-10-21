#!/usr/bin/env python3
"""Single anonymous Chrome browser smoke test on the GitHub-hosted runner.

No Instagram account, cookies, password, proxy, or paid service. This only
tests whether real public Reels metadata is returned to a GitHub runner.
"""
from datetime import datetime, timezone
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from public_instagram import extract_public_metrics, get_accounts


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--profile", default="elianarute_")
    cli.add_argument("--output", default="data/instagram-public.json")
    args = cli.parse_args()
    accounts = get_accounts()
    if args.profile not in accounts:
        raise ValueError("Test handle not in observatory list")

    browser = next((shutil.which(name) for name in
                    ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
                    if shutil.which(name)), None)
    observed = None
    reason = "browser_missing"
    if browser:
        with tempfile.TemporaryDirectory(prefix="gh-ig-") as profile_dir:
            command = [browser, "--headless=new", "--no-sandbox",
                       "--disable-gpu", "--disable-dev-shm-usage",
                       "--no-first-run", "--no-default-browser-check",
                       "--disable-extensions",
                       "--user-data-dir=" + profile_dir,
                       "--virtual-time-budget=8000",
                       "--dump-dom",
                       f"https://www.instagram.com/{args.profile}/reels/"]
            try:
                result = subprocess.run(command, capture_output=True,
                                        text=True, timeout=65, check=False)
                html = result.stdout[:4_000_000]
                observed = extract_public_metrics(html, args.profile)
                reason = "verified" if observed else "public_metrics_absent"
                print("Chrome exit status:", result.returncode,
                      "page bytes:", len(html), "observed:", bool(observed))
            except (OSError, subprocess.TimeoutExpired):
                reason = "browser_unavailable"

    posts = observed["reels"] if observed else {}
    payload = {
        "schema_version": 1,
        "source": "anonymous_instagram_public_reels",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sample_scope": "ate_12_reels_publicos_recentes_por_perfil",
        "verified": bool(observed),
        "coverage": {
            "measured_profiles": 1 if observed else 0,
            "requested_profiles": 1,
            "observed_unique_reels": len(posts),
        },
        "views_recent_deduplicated": (sum(x["views"] for x in posts.values()) if posts else None),
        "profiles": [observed] if observed else [],
        "unavailable": [] if observed else [{"username": args.profile, "reason": reason}],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Chrome test: real public metrics verified =", bool(observed), "reason =", reason)


if __name__ == "__main__":
    main()
