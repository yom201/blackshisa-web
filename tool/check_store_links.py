#!/usr/bin/env python3
"""Every store link carries its source mark, and every page loads the click counter.

Checks, one finding per link / page:
  - App Store <a href> without ct=, or with a ct that is not this page's name.
  - Google Play <a href> without referrer=, or with a utm_campaign that is not this page's name.
  - An HTML page that does not load assets/js/store-links.js.
  - An HTML page without <meta name="apple-itunes-app" content="app-id=6794595128">.
  - A JSON-LD SoftwareApplication whose downloadUrl does not include the App Store.
  - The click counter script itself no longer sends to submitWebEvent.
  - The script's App Store provider token (pt) differs from the shared fixture.

Exit 1 when anything is found.

Scope and limits (on purpose):
  - Only <a href> is checked. JSON-LD (sameAs / downloadUrl) and llms.txt keep clean store
    URLs because they identify the app, they are not clicks.
  - The Google site-verification file is skipped: its body must stay byte-exact.
  - It checks the shape of the links and that the script is loaded. It cannot tell that a
    click really reaches the server (that is checked on the live site).
"""

from __future__ import annotations

import json
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
EXPECTED_PT = "128814295"


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
        self.itunes_meta: list[str] = []
        self.json_ld: list[str] = []
        self._in_json_ld = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k: (v or "") for k, v in attrs}
        if tag == "a" and values.get("href"):
            self.links.append((self.getpos()[0], values["href"]))
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        if tag == "meta" and values.get("name", "").lower() == "apple-itunes-app":
            self.itunes_meta.append(values.get("content", ""))
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self.json_ld.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._in_json_ld = False

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self.json_ld[-1] += data


def software_nodes(value: object) -> list[dict]:
    found: list[dict] = []
    if isinstance(value, dict):
        if value.get("@type") == "SoftwareApplication":
            found.append(value)
        for child in value.values():
            found.extend(software_nodes(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(software_nodes(child))
    return found


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
        # pt (App Store provider token, read in App Store Connect on 2026-10-04).
        # Always: the script's constant equals EXPECTED_PT.
        # Locally, when the work tree sits next to this repo: also equals the shared fixture
        # (CI checks out this repo alone, so the fixture is not there).
        # Runtime use (every App Store link gets it) is checked by tool/test_store_links.js.
        match = re.search(r'PROVIDER_TOKEN = "([0-9]+)"', body)
        if match is None:
            findings.append(f"{SCRIPT_PATH}: no PROVIDER_TOKEN constant")
        elif match.group(1) != EXPECTED_PT:
            findings.append(f"{SCRIPT_PATH}: PROVIDER_TOKEN={match.group(1)!r}, expected {EXPECTED_PT!r}")
        fixture = os.path.join(ROOT, "..", "blackshisa_work", "tool", "fixtures", "ad_attribution_chain.json")
        if os.path.isfile(fixture):
            try:
                with open(fixture, encoding="utf-8") as handle:
                    fixture_pt = json.load(handle)["pt"]
            except (OSError, ValueError, KeyError) as error:
                findings.append(f"cannot read the shared fixture {fixture}: {error}")
            else:
                if fixture_pt != EXPECTED_PT:
                    findings.append(f"shared fixture pt={fixture_pt!r}, expected {EXPECTED_PT!r}")
        else:
            print(f"note: shared fixture not found ({fixture}); compared pt with EXPECTED_PT only")

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
        if parser.itunes_meta != ["app-id=6794595128"]:
            findings.append(f"{rel}: apple-itunes-app meta is {parser.itunes_meta!r}")
        for index, raw in enumerate(parser.json_ld, 1):
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                findings.append(f"{rel}: JSON-LD #{index} does not parse")
                continue
            for node in software_nodes(data):
                urls = node.get("downloadUrl", [])
                urls = [urls] if isinstance(urls, str) else urls
                if not any(APP_STORE_HOST in str(url) for url in urls):
                    findings.append(f"{rel}: JSON-LD SoftwareApplication has no App Store downloadUrl")

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
