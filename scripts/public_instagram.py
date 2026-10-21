#!/usr/bin/env python3
"""Free, loginless observation of public Instagram Reels on GitHub Actions.

Reads only publicly returned JSON embedded in profile Reels pages. It never
infers missing numbers, downloads media, or circumvents a rate limit.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import re
import sys
import time
from urllib.request import Request, urlopen

from curl_cffi import requests

SOURCE = "https://criadores.109-205-177-192.sslip.io/data.json"
HANDLE = re.compile(r"^[a-zA-Z0-9_.]{1,30}$")
SHORTCODE = re.compile(r"^[a-zA-Z0-9_-]{6,20}$")
MAX_REELS = 12
MAX_PROFILES = 50


class JsonScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.parts = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.inside = dict(attrs).get("type") == "application/json"
            self.parts = []

    def handle_data(self, data):
        if self.inside:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            if self.inside:
                self.scripts.append("".join(self.parts))
            self.parts = []
            self.inside = False


def extract_public_metrics(markup: str, username: str) -> dict | None:
    parser = JsonScripts()
    parser.feed(markup)
    profiles = []
    reels = []

    def walk(obj, depth=0):
        if depth > 70:
            return
        if isinstance(obj, dict):
            owner = obj.get("xig_user_by_username")
            if isinstance(owner, dict) and str(owner.get("username", "")).lower() == username.lower():
                profiles.append(owner)
            if obj.get("product_type") == "clips" and "play_count" in obj and "code" in obj:
                reels.append(obj)
            for value in obj.values():
                walk(value, depth + 1)
        elif isinstance(obj, list):
            for value in obj:
                walk(value, depth + 1)

    for script in parser.scripts:
        try:
            walk(json.loads(script))
        except (ValueError, TypeError):
            continue
    profile = next((p for p in profiles if str(p.get("pk", "")).isdigit()), None)
    if profile is None:
        return None
    owner_id = str(profile["pk"])
    followers = profile.get("follower_count")
    if type(followers) is not int or followers < 0:
        followers = None

    unique = {}
    for item in reels:
        code = item.get("code")
        plays = item.get("play_count")
        reel_owner = item.get("user")
        if (not isinstance(code, str) or not SHORTCODE.fullmatch(code)
                or type(plays) is not int or not 0 <= plays <= 10**12
                or not isinstance(reel_owner, dict)
                or str(reel_owner.get("pk", "")) != owner_id
                or code in unique):
            continue
        likes = item.get("like_count")
        unique[code] = {
            "views": plays,
            "likes": likes if type(likes) is int and 0 <= likes <= 10**12 else None,
        }
        if len(unique) == MAX_REELS:
            break
    if not unique:
        return None
    return {
        "username": username,
        "followers": followers,
        "reels": unique,
        "observed_reels": len(unique),
        "views_recent": sum(v["views"] for v in unique.values()),
        "likes_recent": sum(v["likes"] for v in unique.values() if v["likes"] is not None),
    }


def get_accounts() -> list[str]:
    req = Request(SOURCE, headers={"User-Agent": "CriadoresCristaosPublicMonitor/1.0"})
    with urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    accounts = [row.get("user") for row in data.get("accounts", [])
                if row.get("platform") == "Instagram"]
    if not 1 <= len(accounts) <= MAX_PROFILES or any(
        not isinstance(a, str) or not HANDLE.fullmatch(a) for a in accounts
    ):
        raise ValueError("Lista publica de perfis invalida")
    return accounts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="", help="Teste de um perfil conhecido")
    parser.add_argument("--output", default="data/instagram-public.json")
    opts = parser.parse_args()
    names = get_accounts()
    if opts.profile:
        if opts.profile not in names:
            raise ValueError("Perfil de teste nao consta da lista publica")
        names = [opts.profile]
    print("Instagram: leitura de", len(names), "perfil(is) publico(s)", flush=True)

    captured = []
    failures = []
    for index, username in enumerate(names, 1):
        try:
            result = requests.get(
                f"https://www.instagram.com/{username}/reels/",
                impersonate="chrome",
                timeout=23,
                headers={"Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8"},
            )
            if result.status_code == 429:
                print("Instagram limitou os pedidos (429). A interromper.", flush=True)
                failures.append({"username": username, "reason": "rate_limited"})
                break
            if result.status_code != 200:
                failures.append({"username": username, "reason": "http_unavailable"})
                print(f"{index}/{len(names)} @{username}: HTTP {result.status_code}", flush=True)
            else:
                observed = extract_public_metrics(result.text, username)
                if observed:
                    captured.append(observed)
                    print(f"{index}/{len(names)} @{username}: {observed['observed_reels']} Reels, {observed['views_recent']} visualizacoes", flush=True)
                else:
                    failures.append({"username": username, "reason": "public_metrics_absent"})
                    print(f"{index}/{len(names)} @{username}: sem metricas verificaveis", flush=True)
        except Exception as error:
            failures.append({"username": username, "reason": type(error).__name__})
            print(f"{index}/{len(names)} @{username}: leitura indisponivel", flush=True)
        if index < len(names):
            time.sleep(2)

    # On failure, still write an honest diagnostic: null means unavailable, NOT zero.
    unique_posts = {}
    for profile in captured:
        for code, measures in profile["reels"].items():
            unique_posts[code] = measures["views"]
    document = {
        "schema_version": 1,
        "source": "anonymous_instagram_public_reels",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sample_scope": "ate_12_reels_publicos_recentes_por_perfil",
        "verified": len(captured) > 0,
        "coverage": {"measured_profiles": len(captured),
                     "requested_profiles": len(names),
                     "observed_unique_reels": len(unique_posts)},
        "views_recent_deduplicated": sum(unique_posts.values()) if unique_posts else None,
        "profiles": captured,
        "unavailable": failures,
    }
    from pathlib import Path
    path = Path(opts.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("RESULT:", document["coverage"], "verified=", document["verified"], flush=True)
    # Graceful completion even if Instagram denied anonymous access:
    # the output accurately reports unavailable metrics.
    return 0


if __name__ == "__main__":
    sys.exit(main())
