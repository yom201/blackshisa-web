#!/usr/bin/env python3
"""Deterministic local integrity checks for the BlackShisa static site."""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://blackshisa.com"
VERIFICATION_PAGE = "googlec9b4c510fa66e954.html"
FORBIDDEN_FOCUSED_PATHS = (
    "seo/generate.py",
    "seo/topics.json",
    "seo/SPEC.md",
    "tool/check_seo.py",
    ".github/workflows/seo.yml",
    "worklog.yaml",
)
EXPECTED_PUBLIC_URLS = {
    f"{ORIGIN}/",
    f"{ORIGIN}/de/",
    f"{ORIGIN}/es/",
    f"{ORIGIN}/ja/",
    f"{ORIGIN}/security-light.html",
    f"{ORIGIN}/de/security-light.html",
    f"{ORIGIN}/es/security-light.html",
    f"{ORIGIN}/ja/security-light.html",
    f"{ORIGIN}/parking-mode-app.html",
    f"{ORIGIN}/de/parking-mode-app.html",
    f"{ORIGIN}/es/parking-mode-app.html",
    f"{ORIGIN}/ja/parking-mode-app.html",
    f"{ORIGIN}/parking-lot-hit-and-run-evidence.html",
    f"{ORIGIN}/ja/parking-lot-hit-and-run-evidence.html",
    f"{ORIGIN}/dash-cam-parking-mode-alternative.html",
    f"{ORIGIN}/ja/dash-cam-parking-mode-alternative.html",
    f"{ORIGIN}/door-ding-evidence.html",
    f"{ORIGIN}/car-vandalism-evidence.html",
    f"{ORIGIN}/spare-phone-car-security-camera.html",
    f"{ORIGIN}/parked-car-monitoring-app.html",
    f"{ORIGIN}/privacy-policy.html",
    f"{ORIGIN}/eula.html",
}


def alternate_cluster(**languages: str) -> dict[str, str]:
    return {**languages, "x-default": languages["en-US"]}


ALTERNATE_CLUSTERS = (
    alternate_cluster(
        **{
            "en-US": f"{ORIGIN}/",
            "de-DE": f"{ORIGIN}/de/",
            "es-ES": f"{ORIGIN}/es/",
            "ja-JP": f"{ORIGIN}/ja/",
        }
    ),
    alternate_cluster(
        **{
            "en-US": f"{ORIGIN}/security-light.html",
            "de-DE": f"{ORIGIN}/de/security-light.html",
            "es-ES": f"{ORIGIN}/es/security-light.html",
            "ja-JP": f"{ORIGIN}/ja/security-light.html",
        }
    ),
    alternate_cluster(
        **{
            "en-US": f"{ORIGIN}/parking-mode-app.html",
            "de-DE": f"{ORIGIN}/de/parking-mode-app.html",
            "es-ES": f"{ORIGIN}/es/parking-mode-app.html",
            "ja-JP": f"{ORIGIN}/ja/parking-mode-app.html",
        }
    ),
    alternate_cluster(
        **{
            "en-US": f"{ORIGIN}/parking-lot-hit-and-run-evidence.html",
            "ja-JP": f"{ORIGIN}/ja/parking-lot-hit-and-run-evidence.html",
        }
    ),
    alternate_cluster(
        **{
            "en-US": f"{ORIGIN}/dash-cam-parking-mode-alternative.html",
            "ja-JP": f"{ORIGIN}/ja/dash-cam-parking-mode-alternative.html",
        }
    ),
)
EXPECTED_ALTERNATES = {url: {} for url in EXPECTED_PUBLIC_URLS}
for _cluster in ALTERNATE_CLUSTERS:
    for _url in _cluster.values():
        EXPECTED_ALTERNATES[_url] = _cluster
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


@dataclass
class Page:
    path: Path
    lang: str = ""
    title: str = ""
    title_count: int = 0
    h1_count: int = 0
    descriptions: list[str] = field(default_factory=list)
    robots: list[str] = field(default_factory=list)
    canonicals: list[str] = field(default_factory=list)
    alternates: dict[str, str] = field(default_factory=dict)
    duplicate_alternates: list[str] = field(default_factory=list)
    ids: list[str] = field(default_factory=list)
    refs: list[tuple[str, str]] = field(default_factory=list)
    visible_links: list[str] = field(default_factory=list)
    json_ld: list[str] = field(default_factory=list)
    meta_names: dict[str, list[str]] = field(default_factory=dict)
    meta_properties: dict[str, list[str]] = field(default_factory=dict)
    images: list[dict[str, str]] = field(default_factory=list)


class PageParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.page = Page(path=path)
        self._in_title = False
        self._title_parts: list[str] = []
        self._json_ld_depth = 0
        self._json_ld_parts: list[str] = []
        self._body_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "body":
            self._body_depth += 1
        if tag == "html":
            self.page.lang = values.get("lang", "")
        if tag == "title":
            self._in_title = True
            self.page.title_count += 1
        if tag == "h1":
            self.page.h1_count += 1
        if tag == "meta" and values.get("name", "").lower() == "description":
            self.page.descriptions.append(values.get("content", "").strip())
        if tag == "meta" and values.get("name"):
            name = values["name"].strip().lower()
            self.page.meta_names.setdefault(name, []).append(values.get("content", "").strip())
        if tag == "meta" and values.get("property"):
            name = values["property"].strip().lower()
            self.page.meta_properties.setdefault(name, []).append(values.get("content", "").strip())
        if tag == "meta" and values.get("name", "").lower() == "robots":
            self.page.robots.append(values.get("content", "").strip().lower())
        if tag == "link" and values.get("rel", "").lower() == "canonical":
            self.page.canonicals.append(values.get("href", "").strip())
        if tag == "link" and values.get("rel", "").lower() == "alternate":
            hreflang = values.get("hreflang", "").strip()
            href = values.get("href", "").strip()
            if hreflang:
                if hreflang in self.page.alternates:
                    self.page.duplicate_alternates.append(hreflang)
                self.page.alternates[hreflang] = href
        if values.get("id"):
            self.page.ids.append(values["id"])
        for attr in ("href", "src", "data-full", "poster"):
            if values.get(attr):
                self.page.refs.append((attr, values[attr]))
        if tag == "a" and self._body_depth and values.get("href"):
            self.page.visible_links.append(values["href"])
        if tag == "img":
            self.page.images.append(values)
        if values.get("srcset"):
            for candidate in values["srcset"].split(","):
                url = candidate.strip().split(maxsplit=1)[0]
                if url:
                    self.page.refs.append(("srcset", url))
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._json_ld_depth = 1
            self._json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._json_ld_depth:
            self.page.json_ld.append("".join(self._json_ld_parts).strip())
            self._json_ld_depth = 0
            self._json_ld_parts = []
        if tag == "body" and self._body_depth:
            self._body_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if self._json_ld_depth:
            self._json_ld_parts.append(data)

    def close(self) -> None:
        super().close()
        self.page.title = " ".join("".join(self._title_parts).split())


def canonical_for(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return f"{ORIGIN}/"
    if rel.endswith("/index.html"):
        return f"{ORIGIN}/{rel[:-10]}"
    return f"{ORIGIN}/{rel}"


def resolve_local(source: Path, value: str) -> tuple[Path, str] | None:
    parsed = urllib.parse.urlsplit(value)
    if value.startswith(("mailto:", "tel:", "data:", "javascript:")):
        return None
    same_origin = parsed.netloc == "blackshisa.com" and parsed.scheme in {"", "http", "https"}
    if (parsed.scheme or parsed.netloc) and not same_origin:
        return None
    raw_path = urllib.parse.unquote(parsed.path)
    if same_origin:
        raw_path = raw_path or "/"
        target = (ROOT / raw_path.lstrip("/")).resolve()
    elif not raw_path:
        target = source
    elif raw_path.startswith("/"):
        target = (ROOT / raw_path.lstrip("/")).resolve()
    else:
        target = (source.parent / raw_path).resolve()
    if raw_path.endswith("/"):
        target = target / "index.html"
    return target, urllib.parse.unquote(parsed.fragment)


def is_within_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT)
        return True
    except ValueError:
        return False


def structured_nodes(page: Page) -> list[dict[str, object]]:
    """Return JSON-LD nodes, including nodes nested in @graph arrays."""
    nodes: list[dict[str, object]] = []
    for raw in page.json_ld:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            if not isinstance(item, dict):
                continue
            graph = item.get("@graph")
            if isinstance(graph, list):
                nodes.extend(node for node in graph if isinstance(node, dict))
            else:
                nodes.append(item)
    return nodes


def main() -> int:
    errors: list[str] = []
    pages: dict[Path, Page] = {}

    required_files = (
        "README.md",
        "docs/SITE_SPEC.md",
        "CNAME",
        ".nojekyll",
        "robots.txt",
        "sitemap.xml",
        "llms.txt",
        "site.webmanifest",
        VERIFICATION_PAGE,
    )
    for relative in required_files:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")
    for relative in FORBIDDEN_FOCUSED_PATHS:
        if (ROOT / relative).exists():
            errors.append(f"focused topology contains a 40-guide-only path: {relative}")

    for path in sorted(ROOT.rglob("*.html")):
        if ".git" in path.parts:
            continue
        parser = PageParser(path)
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        pages[path.resolve()] = parser.page

    public_pages = {
        path: page
        for path, page in pages.items()
        if path.name != VERIFICATION_PAGE
    }
    canonical_pages: dict[str, Page] = {}
    title_pages: dict[str, Path] = {}
    description_pages: dict[str, Path] = {}

    guide_paths = {
        "parking-mode-app.html",
        "de/parking-mode-app.html",
        "es/parking-mode-app.html",
        "ja/parking-mode-app.html",
        "parking-lot-hit-and-run-evidence.html",
        "ja/parking-lot-hit-and-run-evidence.html",
        "dash-cam-parking-mode-alternative.html",
        "ja/dash-cam-parking-mode-alternative.html",
        "door-ding-evidence.html",
        "car-vandalism-evidence.html",
        "spare-phone-car-security-camera.html",
        "parked-car-monitoring-app.html",
    }
    home_paths = {"index.html", "de/index.html", "es/index.html", "ja/index.html"}

    for path, page in public_pages.items():
        rel = path.relative_to(ROOT)
        if not page.lang:
            errors.append(f"{rel}: missing html lang")
        expected_lang = "en-US"
        if rel.parts[0] in {"de", "es", "ja"}:
            expected_lang = {"de": "de-DE", "es": "es-ES", "ja": "ja-JP"}[rel.parts[0]]
        if page.lang != expected_lang:
            errors.append(f"{rel}: html lang {page.lang!r} != {expected_lang!r}")
        if page.title_count != 1 or not page.title:
            errors.append(f"{rel}: expected one non-empty title, found {page.title_count}")
        elif not 20 <= len(page.title) <= 65:
            errors.append(f"{rel}: title length {len(page.title)} is outside 20..65 characters")
        elif page.title in title_pages:
            errors.append(f"{rel}: title duplicates {title_pages[page.title].relative_to(ROOT)}")
        else:
            title_pages[page.title] = path
        if len(page.descriptions) != 1 or not page.descriptions[0]:
            errors.append(f"{rel}: expected one non-empty meta description")
        else:
            description = page.descriptions[0]
            minimum = 45 if expected_lang == "ja-JP" else 90
            maximum = 110 if expected_lang == "ja-JP" else 160
            if not minimum <= len(description) <= maximum:
                errors.append(
                    f"{rel}: description length {len(description)} is outside {minimum}..{maximum} characters"
                )
            if description in description_pages:
                errors.append(
                    f"{rel}: description duplicates {description_pages[description].relative_to(ROOT)}"
                )
            else:
                description_pages[description] = path

        expected_meta_names = {
            "author": "ICHITAP",
            "twitter:card": "summary_large_image",
            "twitter:title": page.title,
            "twitter:description": page.descriptions[0] if page.descriptions else "",
        }
        for name, expected_value in expected_meta_names.items():
            actual = page.meta_names.get(name, [])
            if actual != [expected_value]:
                errors.append(f"{rel}: meta {name} {actual!r} != {[expected_value]!r}")
        twitter_images = page.meta_names.get("twitter:image", [])
        if len(twitter_images) != 1 or not twitter_images[0].startswith(f"{ORIGIN}/"):
            errors.append(f"{rel}: expected one same-origin twitter:image")

        expected_locale = {"en-US": "en_US", "de-DE": "de_DE", "es-ES": "es_ES", "ja-JP": "ja_JP"}[
            expected_lang
        ]
        expected_properties = {
            "og:site_name": "BlackShisa - Parking Dashcam App",
            "og:locale": expected_locale,
            "og:title": page.title,
            "og:description": page.descriptions[0] if page.descriptions else "",
            "og:url": canonical_for(path),
        }
        for name, expected_value in expected_properties.items():
            actual = page.meta_properties.get(name, [])
            if actual != [expected_value]:
                errors.append(f"{rel}: property {name} {actual!r} != {[expected_value]!r}")
        og_types = page.meta_properties.get("og:type", [])
        if og_types not in (["website"], ["article"]):
            errors.append(f"{rel}: expected one supported og:type, found {og_types!r}")
        og_images = page.meta_properties.get("og:image", [])
        if len(og_images) != 1 or not og_images[0].startswith(f"{ORIGIN}/"):
            errors.append(f"{rel}: expected one same-origin og:image")

        eager_image_count = 0
        for image_index, attributes in enumerate(page.images, 1):
            if "data-lightbox-image" in attributes:
                continue
            if "alt" not in attributes:
                errors.append(f"{rel}: image #{image_index} is missing alt")
            for dimension in ("width", "height"):
                value = attributes.get(dimension, "")
                if not value.isdigit() or int(value) <= 0:
                    errors.append(f"{rel}: image #{image_index} has invalid {dimension}={value!r}")
            if attributes.get("decoding") != "async":
                errors.append(f"{rel}: image #{image_index} must use decoding=async")
            source = attributes.get("src", "")
            if source and attributes.get("loading") != "lazy":
                eager_image_count += 1
            resolved_image = resolve_local(path, source)
            if resolved_image and resolved_image[0].is_file():
                target = resolved_image[0]
                if target.stat().st_size > 300_000 and target.suffix.lower() != ".webp":
                    errors.append(
                        f"{rel}: image #{image_index} uses a non-WebP asset larger than 300 KB: "
                        f"{target.relative_to(ROOT)}"
                    )

        eager_limit = 4 if rel.as_posix() in {"index.html", "de/index.html", "es/index.html"} else 2
        if rel.as_posix() in {"privacy-policy.html", "eula.html"}:
            eager_limit = 1
        if eager_image_count > eager_limit:
            errors.append(
                f"{rel}: {eager_image_count} eager images exceeds the above-the-fold limit {eager_limit}"
            )

        nodes = structured_nodes(page)
        schema_types = {
            schema_type
            for node in nodes
            for schema_type in ([node.get("@type")] if isinstance(node.get("@type"), str) else [])
        }
        for node in nodes:
            if node.get("@type") == "WebPage":
                if node.get("name") != page.title:
                    errors.append(f"{rel}: WebPage.name does not match title")
                if node.get("description") != (page.descriptions[0] if page.descriptions else ""):
                    errors.append(f"{rel}: WebPage.description does not match meta description")
        if rel.as_posix() in home_paths:
            required_types = {"Organization", "WebSite", "SoftwareApplication", "FAQPage"}
            if not required_types.issubset(schema_types):
                errors.append(f"{rel}: home schema missing {sorted(required_types - schema_types)}")
        if rel.as_posix() in guide_paths:
            required_types = {"WebPage", "Article", "BreadcrumbList", "FAQPage"}
            if not required_types.issubset(schema_types):
                errors.append(f"{rel}: guide schema missing {sorted(required_types - schema_types)}")
        if len(page.robots) != 1 or not {"index", "follow"}.issubset(
            {part.strip() for part in page.robots[0].split(",")}
        ):
            errors.append(f"{rel}: expected one robots meta containing index,follow")
        if page.h1_count != 1:
            errors.append(f"{rel}: expected one H1, found {page.h1_count}")
        if len(page.canonicals) != 1:
            errors.append(f"{rel}: expected one canonical, found {len(page.canonicals)}")
        else:
            expected = canonical_for(path)
            actual = page.canonicals[0]
            if actual != expected:
                errors.append(f"{rel}: canonical {actual!r} != {expected!r}")
            if actual in canonical_pages:
                errors.append(f"{rel}: duplicate canonical {actual}")
            canonical_pages[actual] = page
        duplicates = sorted({value for value in page.ids if page.ids.count(value) > 1})
        if duplicates:
            errors.append(f"{rel}: duplicate IDs {duplicates}")
        if page.duplicate_alternates:
            errors.append(f"{rel}: duplicate hreflang values {sorted(set(page.duplicate_alternates))}")
        for index, raw in enumerate(page.json_ld, 1):
            try:
                json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"{rel}: JSON-LD #{index} is invalid: {exc}")

    for path, page in pages.items():
        rel = path.relative_to(ROOT)
        for attr, value in page.refs:
            resolved = resolve_local(path, value)
            if resolved is None:
                continue
            target, fragment = resolved
            if not is_within_root(target):
                errors.append(f"{rel}: {attr} target escapes repository: {value}")
                continue
            if not target.is_file():
                errors.append(f"{rel}: {attr} target does not exist: {value}")
                continue
            if fragment and target.suffix.lower() == ".html":
                target_page = pages.get(target.resolve())
                if target_page is None or fragment not in target_page.ids:
                    errors.append(f"{rel}: fragment does not exist: {value}")

    for stylesheet in sorted((ROOT / "assets" / "css").glob("*.css")):
        css = stylesheet.read_text(encoding="utf-8")
        for value in re.findall(r"url\(\s*['\"]?([^)'\"\s]+)", css):
            resolved = resolve_local(stylesheet, value)
            if resolved is None:
                continue
            if not is_within_root(resolved[0]):
                errors.append(f"{stylesheet.relative_to(ROOT)}: CSS url target escapes repository: {value}")
            elif not resolved[0].is_file():
                errors.append(f"{stylesheet.relative_to(ROOT)}: CSS url target does not exist: {value}")

    for source_url, page in canonical_pages.items():
        if page.alternates and source_url not in page.alternates.values():
            errors.append(f"{page.path.relative_to(ROOT)}: hreflang cluster does not include self")
        for hreflang, target_url in page.alternates.items():
            target = canonical_pages.get(target_url)
            if target is None:
                errors.append(f"{page.path.relative_to(ROOT)}: hreflang target missing: {hreflang} {target_url}")
                continue
            if hreflang != "x-default" and target.lang != hreflang:
                errors.append(
                    f"{page.path.relative_to(ROOT)}: hreflang {hreflang} targets lang {target.lang}"
                )
            if source_url not in target.alternates.values():
                errors.append(
                    f"{page.path.relative_to(ROOT)}: hreflang is not reciprocal: {source_url} -> {target_url}"
                )

    canonical_set = set(canonical_pages)
    if canonical_set != EXPECTED_PUBLIC_URLS:
        missing = sorted(EXPECTED_PUBLIC_URLS - canonical_set)
        extra = sorted(canonical_set - EXPECTED_PUBLIC_URLS)
        errors.append(f"site topology differs; missing={missing}, extra={extra}")
    for url in sorted(canonical_set & EXPECTED_PUBLIC_URLS):
        if canonical_pages[url].alternates != EXPECTED_ALTERNATES[url]:
            errors.append(f"{canonical_pages[url].path.relative_to(ROOT)}: hreflang cluster differs from contract")

    root_page = (ROOT / "index.html").resolve()
    click_depth: dict[Path, int] = {}
    queue: list[Path] = []
    if root_page in public_pages:
        click_depth[root_page] = 0
        queue.append(root_page)
    else:
        errors.append("index.html: missing root page for visible-link traversal")
    while queue:
        source = queue.pop(0)
        for value in pages[source].visible_links:
            resolved = resolve_local(source, value)
            if resolved is None:
                continue
            target = resolved[0].resolve()
            if not is_within_root(target):
                continue
            if target in public_pages and target not in click_depth:
                click_depth[target] = click_depth[source] + 1
                queue.append(target)
    for path in sorted(set(public_pages) - set(click_depth)):
        errors.append(f"{path.relative_to(ROOT)}: not reachable through visible links from home")
    for path, depth in sorted(click_depth.items()):
        if path in public_pages and depth > 2:
            errors.append(f"{path.relative_to(ROOT)}: visible-link depth is {depth}, expected at most 2")

    sitemap_path = ROOT / "sitemap.xml"
    try:
        sitemap = ET.parse(sitemap_path)
        namespaces = {
            "s": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "xhtml": "http://www.w3.org/1999/xhtml",
        }
        sitemap_urls: dict[str, dict[str, str]] = {}
        for node in sitemap.findall("s:url", namespaces):
            loc = node.findtext("s:loc", default="", namespaces=namespaces).strip()
            if not loc:
                errors.append("sitemap.xml: url without loc")
                continue
            if loc in sitemap_urls:
                errors.append(f"sitemap.xml: duplicate loc {loc}")
            sitemap_urls[loc] = {
                link.attrib.get("hreflang", ""): link.attrib.get("href", "")
                for link in node.findall("xhtml:link", namespaces)
            }
        sitemap_set = set(sitemap_urls)
        for url in sorted(canonical_set - sitemap_set):
            errors.append(f"sitemap.xml: missing canonical {url}")
        for url in sorted(sitemap_set - canonical_set):
            errors.append(f"sitemap.xml: loc has no page {url}")
        for url in sorted(canonical_set & sitemap_set):
            expected_alternates = canonical_pages[url].alternates
            if sitemap_urls[url] != expected_alternates:
                errors.append(f"sitemap.xml: hreflang differs from HTML for {url}")

        llms_text = (ROOT / "llms.txt").read_text(encoding="utf-8")
        llms_urls = {
            value.rstrip(".,;:)")
            for value in re.findall(r"https://blackshisa\.com[^\s<>\"]*", llms_text)
        }
        expected_llms_urls = canonical_set - {
            f"{ORIGIN}/privacy-policy.html",
            f"{ORIGIN}/eula.html",
        }
        expected_llms_urls |= {f"{ORIGIN}/robots.txt", f"{ORIGIN}/sitemap.xml"}
        if llms_urls != expected_llms_urls:
            missing = sorted(expected_llms_urls - llms_urls)
            extra = sorted(llms_urls - expected_llms_urls)
            errors.append(f"llms.txt: URL set differs; missing={missing}, extra={extra}")
    except (ET.ParseError, OSError) as exc:
        errors.append(f"sitemap.xml: cannot parse: {exc}")

    cname_path = ROOT / "CNAME"
    if cname_path.is_file() and cname_path.read_text(encoding="utf-8").strip() != "blackshisa.com":
        errors.append("CNAME: expected blackshisa.com")
    robots_path = ROOT / "robots.txt"
    if robots_path.is_file():
        robots_lines = [
            line.strip()
            for line in robots_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        expected_robots = ["User-agent: *", "Allow: /", f"Sitemap: {ORIGIN}/sitemap.xml"]
        if robots_lines != expected_robots:
            errors.append(f"robots.txt: expected {expected_robots!r}, found {robots_lines!r}")
    manifest_path = ROOT / "site.webmanifest"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        start = resolve_local(ROOT / "site.webmanifest", str(manifest.get("start_url", "")))
        if start is None or not is_within_root(start[0]) or not start[0].is_file():
            errors.append("site.webmanifest: start_url target does not exist")
        for icon in manifest.get("icons", []):
            target = resolve_local(ROOT / "site.webmanifest", str(icon.get("src", "")))
            if target is None or not is_within_root(target[0]) or not target[0].is_file():
                errors.append(f"site.webmanifest: icon target does not exist: {icon.get('src', '')}")
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"site.webmanifest: invalid JSON: {exc}")

    if errors:
        print("SITE CHECK: RED")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"SITE CHECK: GREEN ({len(public_pages)} public HTML pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
