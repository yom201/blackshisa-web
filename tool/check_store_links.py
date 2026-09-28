#!/usr/bin/env python3
"""Every store link carries its source mark, and every page loads the click counter.

Checks, one finding per link / page:
  - App Store <a href> without ct=, or with a ct that is not this page's name.
  - Google Play <a href> without referrer=, or with a utm_campaign that is not this page's name.
  - An HTML page that does not load assets/js/store-links.js.
  - The click counter script itself no longer sends to submitWebEvent.

Exit 1 when anything is found.

Scope and limits (on purpose):
  - Only <a href> is checked. JSON-LD (sameAs / downloadUrl) and llms.txt keep clean store
    URLs because they identify the app, they are not clicks.
  - The Google site-verification file is skipped: its body must stay byte-exact.
  - It checks the shape of the links and that the script is loaded. It cannot tell that a
    click really reaches the server (that is checked on the live site).
"""

from __future__ import annotations

import os
import re
import sys
import urllib.parse
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_FILES = {"googlec9b4c510fa66e954.html"}
SCRIPT_PATH = "assets/js/store-links.js"
APP_STORE_HOST = "apps.apple.com"
PLAY_PREFIX = "https://play.google.com/store/apps/details"
CT_RE = re.compile(r"^[a-z0-9_]{1,40}$")
LANG_DIRS = {"de", "es", "ja"}


def page_name(rel: str) -> str:
    """web_<page>_<lang>. rel is a posix path relative to the site root."""
    parts = rel.split("/")
    lang = parts[0] if len(parts) > 1 and parts[0] in LANG_DIRS else "en"
    stem = parts[-1][:-5] if parts[-1].endswith(".html") else parts[-1]
    slug = "home" if stem == "index" else re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")
    return f"web_{slug}_{lang}"[:40]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[int, str]] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k: (v or "") for k, v in attrs}
        if tag == "a" and values.get("href"):
            self.links.append((self.getpos()[0], values["href"]))
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])


def html_files() -> list[str]:
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        for name in sorted(filenames):
            if name.lower().endswith(".html"):
                found.append(os.path.join(dirpath, name))
    return found


def loads_counter(page_path: str, scripts: list[str]) -> bool:
    target = os.path.normpath(os.path.join(ROOT, SCRIPT_PATH))
    for src in scripts:
        path = urllib.parse.urlsplit(src).path
        if not path:
            continue
        if path.startswith("/"):
            resolved = os.path.normpath(os.path.join(ROOT, path.lstrip("/")))
        else:
            resolved = os.path.normpath(os.path.join(os.path.dirname(page_path), path))
        if resolved == target:
            return True
    return False


def main() -> int:
    findings: list[str] = []
    counts = {"pages": 0, "app_store": 0, "play": 0}

    script_file = os.path.join(ROOT, SCRIPT_PATH)
    if not os.path.isfile(script_file):
        findings.append(f"{SCRIPT_PATH}: click counter script is missing")
    else:
        with open(script_file, encoding="utf-8") as handle:
            body = handle.read()
        # Shape only: a rewrite that still sends would pass, a removed call is caught.
        for needle in (
            "cloudfunctions.net/submitWebEvent",
            "navigator.sendBeacon(ENDPOINT",
            'addEventListener("click", onClick',
            '"bs-web-1"',
        ):
            if needle not in body:
                findings.append(f"{SCRIPT_PATH}: does not contain {needle}")

    for path in html_files():
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        if os.path.basename(path) in SKIP_FILES:
            continue
        counts["pages"] += 1
        parser = LinkParser()
        with open(path, encoding="utf-8") as handle:
            parser.feed(handle.read())
        parser.close()
        expected = page_name(rel)

        for line, href in parser.links:
            parsed = urllib.parse.urlsplit(href)
            query = urllib.parse.parse_qs(parsed.query)
            if parsed.netloc == APP_STORE_HOST:
                counts["app_store"] += 1
                ct = query.get("ct", [])
                if not ct:
                    findings.append(f"{rel}:{line}: App Store link without ct=: {href}")
                elif not CT_RE.match(ct[0]):
                    findings.append(f"{rel}:{line}: App Store ct has a bad shape {ct[0]!r}")
                elif ct[0] != expected:
                    findings.append(f"{rel}:{line}: App Store ct={ct[0]!r}, expected {expected!r}")
            elif href.startswith(PLAY_PREFIX):
                counts["play"] += 1
                referrer = query.get("referrer", [])
                if not referrer:
                    findings.append(f"{rel}:{line}: Google Play link without referrer=: {href}")
                    continue
                inner = urllib.parse.parse_qs(referrer[0])
                if inner.get("utm_source") != ["website"]:
                    findings.append(f"{rel}:{line}: Google Play referrer utm_source is not website")
                if inner.get("utm_campaign") != [expected]:
                    findings.append(
                        f"{rel}:{line}: Google Play utm_campaign={inner.get('utm_campaign')!r}, "
                        f"expected {expected!r}"
                    )

        if not loads_counter(path, parser.scripts):
            findings.append(f"{rel}: does not load {SCRIPT_PATH}")

    summary = (
        f"{counts['pages']} pages, {counts['app_store']} App Store links, "
        f"{counts['play']} Google Play links"
    )
    if findings:
        print(f"STORE LINKS: RED ({summary})")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"STORE LINKS: GREEN ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
