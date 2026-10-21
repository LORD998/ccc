#!/usr/bin/env python3
"""Single anonymous Playwright-Chrome verification from a GitHub-hosted runner."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from public_instagram import extract_public_metrics, get_accounts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="elianarute_")
    parser.add_argument("--output", default="data/instagram-public.json")
    args = parser.parse_args()
    if args.profile not in get_accounts():
        raise ValueError("Perfil nao consta da lista autorizada")

    observed = None
    reason = "browser_unavailable"
    http_status = None
    page_size = 0
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel="chrome",
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                page = browser.new_page(locale="pt-PT")
                response = page.goto(
                    f"https://www.instagram.com/{args.profile}/reels/",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                http_status = response.status if response else None
                if http_status == 429:
                    reason = "rate_limited"
                elif http_status != 200:
                    reason = "http_unavailable"
                else:
                    page.wait_for_timeout(2100)
                    markup = page.content()[:4_000_000]
                    page_size = len(markup)
                    observed = extract_public_metrics(markup, args.profile)
                    reason = "verified" if observed else "public_metrics_absent"
            finally:
                browser.close()
    except Exception as err:
        reason = type(err).__name__

    reels = observed["reels"] if observed else {}
    document = {
        "schema_version": 1,
        "source": "anonymous_instagram_public_reels",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sample_scope": "ate_12_reels_publicos_recentes_por_perfil",
        "verified": bool(observed),
        "coverage": {
            "measured_profiles": 1 if observed else 0,
            "requested_profiles": 1,
            "observed_unique_reels": len(reels),
        },
        "views_recent_deduplicated": sum(r["views"] for r in reels.values()) if reels else None,
        "profiles": [observed] if observed else [],
        "unavailable": [] if observed else [{"username": args.profile, "reason": reason}],
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Playwright HTTP status:", http_status, "HTML characters:", page_size)
    print("Playwright real public metrics:", bool(observed), "reason:", reason)


if __name__ == "__main__":
    main()
