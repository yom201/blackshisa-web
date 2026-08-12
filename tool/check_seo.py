#!/usr/bin/env python3
"""Fail-closed quality gate for BlackShisa's multilingual SEO guides.

The checker intentionally uses only the Python standard library so the same
command can run locally and in a minimal CI runner. It never accesses the
network and derives the repository root from this file's location.
"""

from __future__ import annotations

import datetime as dt
import difflib
import json
import posixpath
import re
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Optional


ROOT = Path(__file__).resolve().parent.parent
ORIGIN = "https://blackshisa.com"
TOPICS_PATH = ROOT / "seo" / "topics.json"
SITEMAP_PATH = ROOT / "sitemap.xml"
LLMS_PATH = ROOT / "llms.txt"

LOCALES = ("en", "ja", "es", "de")
LANGS = {
    "en": "en-US",
    "ja": "ja-JP",
    "es": "es-ES",
    "de": "de-DE",
}
HREFLANGS = ("en-US", "ja-JP", "es-ES", "de-DE", "x-default")
LATIN_MIN_WORDS = 450
JA_MIN_CHARS = 900
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
XHTML_NS = "http://www.w3.org/1999/xhtml"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WORD_RE = re.compile(r"[^\W\d_]+(?:[’'][^\W\d_]+)*|\d+(?:[.,]\d+)*", re.UNICODE)
JA_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff々〆〻]")
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
NONVISIBLE_TAGS = {"script", "style", "template", "noscript", "svg", "head"}
REQUIRED_LOCALE_FIELDS = (
    "lang", "title", "description", "kicker", "h1", "lede", "chips",
    "summaryCards", "sections", "faq", "related", "ctaHeading", "ctaText",
)


def clean(value: Any) -> str:
    """Normalize user-visible strings for exact semantic comparison."""
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def identity(value: Any) -> str:
    return clean(value).casefold()


def rel_path(locale: str, slug: str) -> Path:
    return Path(f"{slug}.html") if locale == "en" else Path(locale) / f"{slug}.html"


def hub_path(locale: str) -> Path:
    return Path("parking-guides.html") if locale == "en" else Path(locale) / "parking-guides.html"


def home_path(locale: str) -> Path:
    return Path("index.html") if locale == "en" else Path(locale) / "index.html"


def canonical_for(locale: str, slug: str) -> str:
    prefix = "" if locale == "en" else f"/{locale}"
    return f"{ORIGIN}{prefix}/{slug}.html"


def hub_canonical(locale: str) -> str:
    prefix = "" if locale == "en" else f"/{locale}"
    return f"{ORIGIN}{prefix}/parking-guides.html"


def topic_cluster(slug: str) -> dict[str, str]:
    cluster = {LANGS[locale]: canonical_for(locale, slug) for locale in LOCALES}
    cluster["x-default"] = canonical_for("en", slug)
    return cluster


def hub_cluster() -> dict[str, str]:
    cluster = {LANGS[locale]: hub_canonical(locale) for locale in LOCALES}
    cluster["x-default"] = hub_canonical("en")
    return cluster


class Gate:
    def __init__(self) -> None:
        self.errors: list[tuple[str, str, str]] = []
        self._seen: set[tuple[str, str, str]] = set()

    def fail(self, code: str, where: Any, message: str) -> None:
        item = (code, str(where), clean(message))
        if item not in self._seen:
            self._seen.add(item)
            self.errors.append(item)

    def finish(self) -> int:
        if self.errors:
            print(f"SEO QUALITY GATE: RED ({len(self.errors)} violation(s))")
            for code, where, message in sorted(self.errors):
                print(f"- [{code}] {where}: {message}")
            return 1
        print("SEO QUALITY GATE: GREEN (10 topics x 4 languages; 40 guides + 4 hubs)")
        return 0


@dataclass
class Frame:
    tag: str
    attrs: dict[str, str]
    hidden: bool
    in_main: bool
    text: list[str] = field(default_factory=list)
    jsonld: bool = False
    breadcrumb: bool = False
    p_section: Optional[int] = None
    section_index: Optional[int] = None


@dataclass
class HtmlDocument:
    path: Path
    html_langs: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)
    canonicals: list[str] = field(default_factory=list)
    alternates: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    total_h1: int = 0
    visible_h1: list[str] = field(default_factory=list)
    main_text: list[str] = field(default_factory=list)
    visible_links: list[tuple[str, str, bool]] = field(default_factory=list)
    refs: list[tuple[str, str]] = field(default_factory=list)
    ids: list[str] = field(default_factory=list)
    anchor_names: list[str] = field(default_factory=list)
    jsonld_texts: list[str] = field(default_factory=list)
    times: list[tuple[str, str]] = field(default_factory=list)
    has_visible_breadcrumb: bool = False
    sections: list[int] = field(default_factory=list)

    @property
    def visible_main_text(self) -> str:
        return clean(" ".join(self.main_text))


class SeoHTMLParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.doc = HtmlDocument(path=path)
        self.stack: list[Frame] = []

    @staticmethod
    def _attrs(attrs: list[tuple[str, Optional[str]]]) -> dict[str, str]:
        return {str(k).lower(): str(v or "") for k, v in attrs}

    def handle_starttag(self, tag: str, raw_attrs: list[tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attrs = self._attrs(raw_attrs)
        parent = self.stack[-1] if self.stack else None
        classes = {part.casefold() for part in attrs.get("class", "").split()}
        style = attrs.get("style", "").casefold().replace(" ", "")
        self_hidden = (
            "hidden" in attrs
            or attrs.get("aria-hidden", "").casefold() == "true"
            or "display:none" in style
            or "visibility:hidden" in style
            or bool(classes & {"sr-only", "visually-hidden", "screen-reader-only"})
            or tag in NONVISIBLE_TAGS
        )
        hidden = bool(parent and parent.hidden) or self_hidden
        in_main = bool(parent and parent.in_main) or tag == "main"
        frame = Frame(tag=tag, attrs=attrs, hidden=hidden, in_main=in_main)

        element_id = attrs.get("id")
        if element_id:
            self.doc.ids.append(element_id)
        if tag == "a" and attrs.get("name"):
            self.doc.anchor_names.append(attrs["name"])
        for attr_name in ("href", "src"):
            if attr_name in attrs and attrs[attr_name].strip():
                self.doc.refs.append((attr_name, attrs[attr_name].strip()))

        if tag == "html":
            self.doc.html_langs.append(attrs.get("lang", ""))
        elif tag == "meta" and attrs.get("name", "").casefold() == "description":
            self.doc.descriptions.append(attrs.get("content", ""))
        elif tag == "link":
            rels = {part.casefold() for part in attrs.get("rel", "").split()}
            if "canonical" in rels:
                self.doc.canonicals.append(attrs.get("href", ""))
            if "alternate" in rels and "hreflang" in attrs:
                self.doc.alternates[attrs["hreflang"]].append(attrs.get("href", ""))

        if tag == "h1":
            self.doc.total_h1 += 1
        if tag == "script" and attrs.get("type", "").casefold() == "application/ld+json":
            frame.jsonld = True
        if tag == "section" and in_main and not hidden:
            frame.section_index = len(self.doc.sections)
            self.doc.sections.append(0)
        if tag == "p" and in_main and not hidden:
            for ancestor in reversed(self.stack):
                if ancestor.section_index is not None:
                    frame.p_section = ancestor.section_index
                    break

        class_value = attrs.get("class", "").casefold()
        aria_label = attrs.get("aria-label", "").casefold()
        frame.breadcrumb = bool(parent and parent.breadcrumb) or (
            in_main
            and not hidden
            and ("breadcrumb" in class_value or "breadcrumb" in aria_label)
        )

        if tag in VOID_TAGS:
            self._finish(frame)
        else:
            self.stack.append(frame)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        match = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                match = index
                break
        if match is None:
            return
        while len(self.stack) > match:
            self._finish(self.stack.pop())

    def handle_data(self, data: str) -> None:
        if not self.stack:
            return
        for frame in self.stack:
            if frame.jsonld:
                frame.text.append(data)
            if frame.tag in {"title", "h1", "a", "p", "time"}:
                frame.text.append(data)
        if self.stack[-1].hidden:
            return
        if clean(data) and any(frame.breadcrumb for frame in self.stack):
            self.doc.has_visible_breadcrumb = True
        if self.stack[-1].in_main:
            self.doc.main_text.append(data)

    def close(self) -> None:
        super().close()
        while self.stack:
            self._finish(self.stack.pop())

    def _finish(self, frame: Frame) -> None:
        text_value = clean(" ".join(frame.text))
        if frame.tag == "title":
            self.doc.titles.append(text_value)
        elif frame.tag == "h1" and not frame.hidden:
            self.doc.visible_h1.append(text_value)
        elif frame.tag == "a" and not frame.hidden and frame.attrs.get("href") and text_value:
            self.doc.visible_links.append((frame.attrs["href"], text_value, frame.in_main))
        elif frame.tag == "p" and not frame.hidden and text_value and frame.p_section is not None:
            self.doc.sections[frame.p_section] += 1
        elif frame.tag == "time" and not frame.hidden and frame.in_main and text_value:
            self.doc.times.append((frame.attrs.get("datetime", ""), text_value))
        if frame.jsonld:
            self.doc.jsonld_texts.append("".join(frame.text).strip())


def parse_html(path: Path, gate: Gate, cache: dict[Path, HtmlDocument]) -> Optional[HtmlDocument]:
    path = path.resolve()
    if path in cache:
        return cache[path]
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        gate.fail("HTML-MISSING", path.relative_to(ROOT) if path.is_relative_to(ROOT) else path, "required HTML file is missing")
        return None
    except (OSError, UnicodeError) as exc:
        gate.fail("HTML-READ", path, f"cannot read UTF-8 HTML: {exc}")
        return None
    parser = SeoHTMLParser(path)
    try:
        parser.feed(raw)
        parser.close()
    except Exception as exc:  # HTMLParser extensions must fail the gate, not CI itself.
        gate.fail("HTML-PARSE", path, f"HTML parsing failed: {exc}")
        return None
    cache[path] = parser.doc
    duplicates = sorted(key for key, count in Counter(parser.doc.ids).items() if count > 1)
    if duplicates:
        gate.fail("HTML-DUPLICATE-ID", path.relative_to(ROOT), f"duplicate id value(s): {', '.join(duplicates)}")
    return parser.doc


def expect_single(gate: Gate, code: str, where: Path, values: list[str], expected: str, label: str) -> None:
    if len(values) != 1:
        gate.fail(code, where, f"expected exactly one {label}; found {len(values)}")
    elif clean(values[0]) != clean(expected):
        gate.fail(code, where, f"{label} must be exactly {expected!r}; found {values[0]!r}")


def validate_hreflang(gate: Gate, where: Path, doc: HtmlDocument, expected: dict[str, str]) -> None:
    actual_keys = set(doc.alternates)
    if actual_keys != set(HREFLANGS):
        missing = sorted(set(HREFLANGS) - actual_keys)
        extra = sorted(actual_keys - set(HREFLANGS))
        gate.fail("HREFLANG-SET", where, f"hreflang keys differ; missing={missing}, extra={extra}")
    for lang in HREFLANGS:
        values = doc.alternates.get(lang, [])
        if len(values) != 1:
            gate.fail("HREFLANG-COUNT", where, f"{lang} must occur once; found {len(values)}")
        elif values[0] != expected[lang]:
            gate.fail("HREFLANG-URL", where, f"{lang} must point to {expected[lang]}; found {values[0]}")


def flatten_jsonld(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if "@type" in value:
            yield value
        for child in value.values():
            yield from flatten_jsonld(child)
    elif isinstance(value, list):
        for child in value:
            yield from flatten_jsonld(child)


def node_has_type(node: dict[str, Any], wanted: str) -> bool:
    types = node.get("@type", [])
    if isinstance(types, str):
        types = [types]
    return wanted in types


def node_url(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("@id") or value.get("url") or "")
    return ""


def validate_jsonld(
    gate: Gate, where: Path, doc: HtmlDocument, canonical: str, language: str, last_modified: str
) -> None:
    if not doc.jsonld_texts:
        gate.fail("JSONLD-MISSING", where, "no application/ld+json script found")
        return
    nodes: list[dict[str, Any]] = []
    for index, raw in enumerate(doc.jsonld_texts, 1):
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            gate.fail("JSONLD-PARSE", where, f"JSON-LD script {index} is invalid JSON: {exc}")
            continue
        nodes.extend(flatten_jsonld(value))

    for wanted in ("WebPage", "Article", "BreadcrumbList"):
        matching = [node for node in nodes if node_has_type(node, wanted)]
        if not matching:
            gate.fail("JSONLD-TYPE", where, f"missing {wanted} node")
            continue
        if wanted in {"WebPage", "Article"}:
            for node in matching:
                if node_url(node.get("url")) != canonical:
                    gate.fail("JSONLD-URL", where, f"{wanted}.url must be {canonical}")
                if node.get("inLanguage") != language:
                    gate.fail("JSONLD-LANGUAGE", where, f"{wanted}.inLanguage must be {language}")
                if node.get("dateModified") != last_modified:
                    gate.fail("JSONLD-DATE", where, f"{wanted}.dateModified must be {last_modified}")
        else:
            for node in matching:
                items = node.get("itemListElement")
                if not isinstance(items, list) or len(items) < 3:
                    gate.fail("JSONLD-BREADCRUMB", where, "BreadcrumbList needs at least three items")
                    continue
                positions = [item.get("position") for item in items if isinstance(item, dict)]
                if positions != list(range(1, len(items) + 1)):
                    gate.fail("JSONLD-BREADCRUMB", where, "breadcrumb positions must be consecutive from 1")
                last = items[-1] if isinstance(items[-1], dict) else {}
                if node_url(last.get("item")) != canonical:
                    gate.fail("JSONLD-BREADCRUMB", where, f"last breadcrumb item must be {canonical}")


def local_target(source: Path, raw_url: str) -> Optional[tuple[Path, str]]:
    """Resolve a same-origin URL to a repository file and decoded fragment."""
    raw_url = raw_url.strip()
    split = urllib.parse.urlsplit(raw_url)
    if split.scheme.casefold() in {"mailto", "tel", "data", "javascript"}:
        return None
    if split.scheme or split.netloc:
        if split.scheme.casefold() not in {"http", "https"}:
            return None
        host = (split.hostname or "").casefold()
        # Accessing port also validates malformed numeric port syntax.
        port = split.port
        if host != "blackshisa.com" or port is not None:
            return None
        url_path = split.path or "/"
    else:
        base = "/" + source.relative_to(ROOT).as_posix()
        joined = urllib.parse.urljoin(f"{ORIGIN}{base}", raw_url)
        split = urllib.parse.urlsplit(joined)
        url_path = split.path or "/"

    decoded = urllib.parse.unquote(url_path)
    normalized = posixpath.normpath(decoded)
    if decoded.endswith("/"):
        normalized += "/"
    if normalized.startswith("../") or "/../" in normalized:
        return ROOT.parent / "__outside_repository__", urllib.parse.unquote(split.fragment)
    relative = normalized.lstrip("/")
    candidate = ROOT / relative
    if normalized.endswith("/") or candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate.resolve(), urllib.parse.unquote(split.fragment)


def validate_refs(
    gate: Gate, where: Path, doc: HtmlDocument, cache: dict[Path, HtmlDocument]
) -> None:
    for attr_name, raw_url in doc.refs:
        try:
            resolved = local_target(doc.path, raw_url)
        except (UnicodeError, ValueError) as exc:
            gate.fail("LOCAL-URL", where, f'{attr_name}="{raw_url}" is malformed: {exc}')
            continue
        if resolved is None:
            continue
        target, fragment = resolved
        try:
            display = target.relative_to(ROOT)
        except ValueError:
            gate.fail("LOCAL-OUTSIDE", where, f'{attr_name}="{raw_url}" resolves outside the repository')
            continue
        if not target.is_file():
            gate.fail("LOCAL-MISSING", where, f'{attr_name}="{raw_url}" resolves to missing {display}')
            continue
        if fragment:
            if target.suffix.casefold() not in {".html", ".htm"}:
                gate.fail("FRAGMENT-NONHTML", where, f'{raw_url} has a fragment on non-HTML target')
                continue
            target_doc = parse_html(target, gate, cache)
            targets = set(target_doc.ids + target_doc.anchor_names) if target_doc else set()
            if fragment not in targets:
                gate.fail("FRAGMENT-MISSING", where, f'{raw_url} points to absent fragment "{fragment}"')


def href_resolves_to(source: Path, href: str, expected: Path) -> bool:
    try:
        resolved = local_target(source, href)
    except (UnicodeError, ValueError):
        return False
    return bool(resolved and resolved[0] == expected.resolve() and not resolved[1])


CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("guaranteed outcome", re.compile(r"\bguarantee(?:d|s)?\s+(?:to\s+)?(?:capture|record|identify|identification|prevent)", re.I)),
    ("certain outcome", re.compile(r"\b(?:will|always)\s+(?:capture|record|identify|prevent)\b", re.I)),
    ("crime prevention promise", re.compile(r"\b(?:prevents?|stops?)\s+(?:all\s+)?(?:crime|theft|vandalism|hit[- ]and[- ]runs?)", re.I)),
    ("perfect evidence", re.compile(r"\b(?:perfect|conclusive|court[- ]proof)\s+evidence\b", re.I)),
    ("never misses", re.compile(r"\bnever\s+miss(?:es)?\b", re.I)),
    ("100 percent promise", re.compile(r"\b100\s*(?:%|percent)\s+(?:effective|reliable|accurate|guaranteed)\b", re.I)),
    ("readable capture promise", re.compile(r"\bcaptur(?:e|es|ing)[^.!?\n]{0,60}\breadable\b", re.I)),
    ("promesa garantizada", re.compile(r"\b(?:captura|identificaci[oó]n|prevenci[oó]n)\s+garantizada\b|\bgarantiza\s+(?:la\s+)?(?:captura|identificaci[oó]n|prevenci[oó]n)", re.I)),
    ("evita todo", re.compile(r"\bevitar?[áa]?\s+(?:todos?\s+)?(?:los\s+)?(?:delitos?|robos?|vandalismo)", re.I)),
    ("garantiertes Ergebnis", re.compile(r"\bgarantierte\s+(?:aufnahme|identifizierung|beweise?)\b|\bgarantiert\s+(?:die\s+)?(?:aufnahme|identifizierung|verhinderung)", re.I)),
    ("verhindert alles", re.compile(r"\bverhindert\s+(?:alle\s+)?(?:verbrechen|diebst[aä]hle?|vandalismus|fahrerflucht)\b", re.I)),
    ("Japanese certainty promise", re.compile(r"(?:必ず|絶対に)(?:[^。\n]{0,18})(?:撮影|記録|特定|識別|防止|阻止)")),
    ("Japanese complete prevention", re.compile(r"(?:犯罪|盗難|当て逃げ|車上荒らし)(?:を|が)[^。\n]{0,12}完全に(?:防止|阻止)")),
    ("Japanese 100 percent promise", re.compile(r"100\s*(?:%|％)[^。\n]{0,12}(?:確実|有効|正確|撮影|記録|防止)")),
)

NEGATION_RE = re.compile(
    r"(?:\b(?:not|no|never|cannot|can't|doesn't|does\s+not|without|"
    r"nicht|kein(?:e|en|er|es)?|nie|ohne|kann\s+nicht|"
    r"no|nunca|sin)\b|保証(?:しない|できない|されない)|できません|防げません)[^.!?。\n]{0,45}$",
    re.I,
)


def validate_claims(gate: Gate, where: Any, text: str) -> None:
    normalized = unicodedata.normalize("NFKC", text)
    for label, pattern in CLAIM_PATTERNS:
        for match in pattern.finditer(normalized):
            terminal_positions = [
                position
                for marker in (".", "!", "?", "。", "！", "？", "\n")
                if (position := normalized.find(marker, match.end())) >= 0
            ]
            if terminal_positions and normalized[min(terminal_positions)] in {"?", "？"}:
                # A FAQ question challenging an absolute outcome is not itself
                # a promise. Its answer remains subject to the same denylist.
                continue
            before = normalized[max(0, match.start() - 70):match.start()]
            if NEGATION_RE.search(before):
                continue
            excerpt = clean(normalized[match.start():match.end()])
            gate.fail("CLAIM-EXAGGERATED", where, f'{label}: "{excerpt}"')
            break


def all_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from all_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_strings(child)


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(clean(value))


def load_topics(gate: Gate) -> Optional[tuple[str, list[dict[str, Any]]]]:
    try:
        raw = TOPICS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        gate.fail("TOPICS-MISSING", TOPICS_PATH.relative_to(ROOT), "required source file is missing")
        return None
    except (OSError, UnicodeError) as exc:
        gate.fail("TOPICS-READ", TOPICS_PATH.relative_to(ROOT), f"cannot read UTF-8 JSON: {exc}")
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        gate.fail("TOPICS-JSON", TOPICS_PATH.relative_to(ROOT), f"invalid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        gate.fail("TOPICS-SHAPE", TOPICS_PATH.relative_to(ROOT), "top level must be an object")
        return None

    last_modified = data.get("lastModified")
    if not nonempty_string(last_modified) or not DATE_RE.fullmatch(str(last_modified)):
        gate.fail("TOPICS-DATE", TOPICS_PATH.relative_to(ROOT), "lastModified must be YYYY-MM-DD")
        last_modified = ""
    else:
        try:
            parsed_date = dt.date.fromisoformat(str(last_modified))
            if parsed_date.isoformat() != last_modified:
                raise ValueError("date is not canonical")
        except ValueError:
            gate.fail("TOPICS-DATE", TOPICS_PATH.relative_to(ROOT), "lastModified is not a valid calendar date")

    topics = data.get("topics")
    if not isinstance(topics, list):
        gate.fail("TOPICS-SHAPE", TOPICS_PATH.relative_to(ROOT), "topics must be an array")
        return None
    if len(topics) != 10:
        gate.fail("TOPICS-COUNT", TOPICS_PATH.relative_to(ROOT), f"expected exactly 10 topics; found {len(topics)}")

    valid_topics: list[dict[str, Any]] = []
    slug_values: list[str] = []
    for index, topic in enumerate(topics):
        where = f"seo/topics.json topics[{index}]"
        if not isinstance(topic, dict):
            gate.fail("TOPIC-SHAPE", where, "topic must be an object")
            continue
        slug = topic.get("slug")
        if not nonempty_string(slug) or not SLUG_RE.fullmatch(str(slug)):
            gate.fail("TOPIC-SLUG", where, "slug must be lowercase ASCII words separated by single hyphens")
            continue
        slug = str(slug)
        slug_values.append(slug)
        if not nonempty_string(topic.get("image")):
            gate.fail("TOPIC-IMAGE", where, "image must be a non-empty path")
        else:
            image_url = str(topic["image"])
            try:
                resolved = local_target(ROOT / "index.html", image_url)
            except (UnicodeError, ValueError):
                resolved = None
            if resolved is None or not resolved[0].is_file():
                gate.fail("TOPIC-IMAGE", where, f"image does not resolve to a local file: {image_url}")

        locales = topic.get("locales")
        if not isinstance(locales, dict):
            gate.fail("TOPIC-LOCALES", where, "locales must be an object")
            continue
        if set(locales) != set(LOCALES):
            gate.fail("TOPIC-LOCALES", where, f"locale keys must be exactly {list(LOCALES)}; found {sorted(locales)}")
        for locale in LOCALES:
            loc_where = f"{where}.locales.{locale}"
            value = locales.get(locale)
            if not isinstance(value, dict):
                gate.fail("LOCALE-SHAPE", loc_where, "locale value must be an object")
                continue
            missing = [field_name for field_name in REQUIRED_LOCALE_FIELDS if not value.get(field_name)]
            if missing:
                gate.fail("LOCALE-FIELDS", loc_where, f"missing or empty field(s): {', '.join(missing)}")
            if value.get("lang") != LANGS[locale]:
                gate.fail("LOCALE-LANG", loc_where, f"lang must be {LANGS[locale]}")
            for field_name in ("title", "description", "kicker", "h1", "lede", "ctaHeading", "ctaText"):
                if not nonempty_string(value.get(field_name)):
                    gate.fail("LOCALE-TEXT", loc_where, f"{field_name} must be a non-empty string")

            chips = value.get("chips")
            if not isinstance(chips, list) or len(chips) < 3 or not all(nonempty_string(item) for item in chips):
                gate.fail("LOCALE-CHIPS", loc_where, "chips must contain at least three non-empty strings")
            elif len({identity(item) for item in chips}) != len(chips):
                gate.fail("LOCALE-CHIPS", loc_where, "chips must be unique")

            cards = value.get("summaryCards")
            if not isinstance(cards, list) or len(cards) < 3:
                gate.fail("LOCALE-CARDS", loc_where, "summaryCards must contain at least three cards")
            else:
                card_ids: list[str] = []
                for card_index, card in enumerate(cards):
                    if not isinstance(card, dict) or not nonempty_string(card.get("title")) or not nonempty_string(card.get("text")):
                        gate.fail("LOCALE-CARDS", loc_where, f"summaryCards[{card_index}] needs non-empty title and text")
                    else:
                        card_ids.append(identity(card["title"]) + "\x00" + identity(card["text"]))
                if len(card_ids) != len(set(card_ids)):
                    gate.fail("LOCALE-CARDS", loc_where, "summary cards must be unique")

            sections = value.get("sections")
            if not isinstance(sections, list) or len(sections) < 4:
                gate.fail("LOCALE-SECTIONS", loc_where, "sections must contain at least four sections")
            else:
                headings: list[str] = []
                for section_index, section in enumerate(sections):
                    if not isinstance(section, dict) or not nonempty_string(section.get("heading")):
                        gate.fail("LOCALE-SECTIONS", loc_where, f"sections[{section_index}] needs a non-empty heading")
                        continue
                    headings.append(identity(section["heading"]))
                    paragraphs = section.get("paragraphs")
                    if not isinstance(paragraphs, list) or len(paragraphs) < 2 or not all(nonempty_string(p) for p in paragraphs):
                        gate.fail("LOCALE-SECTIONS", loc_where, f"sections[{section_index}] needs at least two non-empty paragraphs")
                if len(headings) != len(set(headings)):
                    gate.fail("LOCALE-SECTIONS", loc_where, "section headings must be unique")

            faq = value.get("faq")
            if not isinstance(faq, list) or len(faq) < 3:
                gate.fail("LOCALE-FAQ", loc_where, "faq must contain at least three entries")
            else:
                questions: list[str] = []
                for faq_index, item in enumerate(faq):
                    if not isinstance(item, dict) or not nonempty_string(item.get("q")) or not nonempty_string(item.get("a")):
                        gate.fail("LOCALE-FAQ", loc_where, f"faq[{faq_index}] needs non-empty q and a")
                    else:
                        questions.append(identity(item["q"]))
                if len(questions) != len(set(questions)):
                    gate.fail("LOCALE-FAQ", loc_where, "FAQ questions must be unique")

            related = value.get("related")
            if not isinstance(related, list) or len(related) < 3 or not all(nonempty_string(item) for item in related):
                gate.fail("LOCALE-RELATED", loc_where, "related must contain at least three non-empty slugs")
            else:
                normalized_related = [str(item) for item in related]
                if len(normalized_related) != len(set(normalized_related)):
                    gate.fail("LOCALE-RELATED", loc_where, "related slugs must be unique")
                if slug in normalized_related:
                    gate.fail("LOCALE-RELATED", loc_where, "a topic cannot relate to itself")
        valid_topics.append(topic)

    duplicates = sorted(slug for slug, count in Counter(slug_values).items() if count > 1)
    if duplicates:
        gate.fail("TOPIC-SLUG-UNIQUE", TOPICS_PATH.relative_to(ROOT), f"duplicate slug(s): {', '.join(duplicates)}")

    slug_set = set(slug_values)
    for topic in valid_topics:
        for locale in LOCALES:
            value = topic.get("locales", {}).get(locale, {})
            if not isinstance(value, dict) or not isinstance(value.get("related"), list):
                continue
            unknown = sorted(str(slug) for slug in value["related"] if str(slug) not in slug_set)
            if unknown:
                gate.fail("LOCALE-RELATED", f"{topic['slug']}/{locale}", f"unknown related slug(s): {', '.join(unknown)}")

    for locale in LOCALES:
        for field_name in ("title", "description", "h1"):
            values: list[str] = []
            for topic in valid_topics:
                value = topic.get("locales", {}).get(locale, {})
                if isinstance(value, dict) and nonempty_string(value.get(field_name)):
                    values.append(identity(value[field_name]))
            duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
            if duplicates:
                gate.fail("LOCALE-UNIQUE", f"seo/topics.json/{locale}", f"{field_name} values must be unique; found {len(duplicates)} duplicate value(s)")

    for string in all_strings(data):
        validate_claims(gate, TOPICS_PATH.relative_to(ROOT), string)
    return str(last_modified), valid_topics


def validate_guide(
    gate: Gate,
    topic: dict[str, Any],
    locale: str,
    last_modified: str,
    cache: dict[Path, HtmlDocument],
) -> Optional[HtmlDocument]:
    slug = str(topic["slug"])
    relative = rel_path(locale, slug)
    path = ROOT / relative
    doc = parse_html(path, gate, cache)
    if doc is None:
        return None
    locale_data = topic.get("locales", {}).get(locale)
    if not isinstance(locale_data, dict):
        return doc
    language = LANGS[locale]
    canonical = canonical_for(locale, slug)

    expect_single(gate, "HTML-LANG", relative, doc.html_langs, language, "html lang")
    expect_single(gate, "HTML-TITLE", relative, doc.titles, str(locale_data.get("title", "")), "title")
    expect_single(gate, "HTML-DESCRIPTION", relative, doc.descriptions, str(locale_data.get("description", "")), "meta description")
    expect_single(gate, "HTML-CANONICAL", relative, doc.canonicals, canonical, "canonical")
    if doc.total_h1 != 1 or len(doc.visible_h1) != 1:
        gate.fail("HTML-H1", relative, f"expected one visible H1 and one H1 total; found total={doc.total_h1}, visible={len(doc.visible_h1)}")
    elif clean(doc.visible_h1[0]) != clean(locale_data.get("h1", "")):
        gate.fail("HTML-H1", relative, f"H1 does not exactly match topics.json: {doc.visible_h1[0]!r}")
    validate_hreflang(gate, relative, doc, topic_cluster(slug))

    main_text = doc.visible_main_text
    if locale == "ja":
        count = len(JA_CHAR_RE.findall(main_text))
        if count < JA_MIN_CHARS:
            gate.fail("CONTENT-LENGTH", relative, f"visible main text has {count} Japanese characters; minimum is {JA_MIN_CHARS}")
    else:
        count = len(WORD_RE.findall(main_text))
        if count < LATIN_MIN_WORDS:
            gate.fail("CONTENT-LENGTH", relative, f"visible main text has {count} word tokens; minimum is {LATIN_MIN_WORDS}")
    substantive_sections = sum(1 for paragraph_count in doc.sections if paragraph_count >= 2)
    if substantive_sections < 4:
        gate.fail("CONTENT-SECTIONS", relative, f"found {substantive_sections} visible sections with at least two paragraphs; minimum is 4")

    validate_jsonld(gate, relative, doc, canonical, language, last_modified)
    if not doc.has_visible_breadcrumb:
        gate.fail("BREADCRUMB-VISIBLE", relative, "no visible breadcrumb region inside main")
    dates = [datetime_value for datetime_value, _ in doc.times]
    if last_modified not in dates:
        gate.fail("UPDATED-VISIBLE", relative, f"no visible main time element with datetime={last_modified}")

    main_hrefs = [href for href, _text, in_main in doc.visible_links if in_main]
    if not any(href_resolves_to(path, href, ROOT / hub_path(locale)) for href in main_hrefs):
        gate.fail("INTERNAL-HUB", relative, f"no visible main-content link to {hub_path(locale)}")
    linked_guide_slugs: set[str] = set()
    for other in topic.get("locales", {}).get(locale, {}).get("related", []):
        target = ROOT / rel_path(locale, str(other))
        if any(href_resolves_to(path, href, target) for href in main_hrefs):
            linked_guide_slugs.add(str(other))
        else:
            gate.fail("INTERNAL-RELATED", relative, f"missing visible main-content link to related topic {other}")
    if len(linked_guide_slugs) < 3:
        gate.fail("INTERNAL-RELATED", relative, f"only {len(linked_guide_slugs)} distinct same-language related guides are linked; minimum is 3")

    validate_refs(gate, relative, doc, cache)
    validate_claims(gate, relative, main_text)
    return doc


def validate_hubs_and_orphans(
    gate: Gate,
    topics: list[dict[str, Any]],
    cache: dict[Path, HtmlDocument],
) -> None:
    slugs = [str(topic["slug"]) for topic in topics]
    expected_cluster = hub_cluster()
    for locale in LOCALES:
        relative = hub_path(locale)
        path = ROOT / relative
        doc = parse_html(path, gate, cache)
        if doc is None:
            continue
        expect_single(gate, "HUB-LANG", relative, doc.html_langs, LANGS[locale], "html lang")
        expect_single(gate, "HUB-CANONICAL", relative, doc.canonicals, hub_canonical(locale), "canonical")
        if doc.total_h1 != 1 or len(doc.visible_h1) != 1 or not clean(doc.visible_h1[0]):
            gate.fail("HUB-H1", relative, "hub must have exactly one non-empty visible H1")
        validate_hreflang(gate, relative, doc, expected_cluster)
        visible_hrefs = [href for href, _text, _in_main in doc.visible_links]
        for slug in slugs:
            target = ROOT / rel_path(locale, slug)
            if not any(href_resolves_to(path, href, target) for href in visible_hrefs):
                gate.fail("ORPHAN-GUIDE", relative, f"hub does not visibly link to {rel_path(locale, slug)}")
        validate_refs(gate, relative, doc, cache)

        home_relative = home_path(locale)
        home = parse_html(ROOT / home_relative, gate, cache)
        if home is not None:
            home_hrefs = [href for href, _text, _in_main in home.visible_links]
            if not any(href_resolves_to(ROOT / home_relative, href, path) for href in home_hrefs):
                gate.fail("ORPHAN-HUB", home_relative, f"home does not visibly link to {relative}")


def similarity_tokens(locale: str, text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    if locale == "ja":
        return JA_CHAR_RE.findall(normalized)
    return [identity(token) for token in WORD_RE.findall(normalized)]


def validate_similarity(
    gate: Gate,
    documents: dict[tuple[str, str], HtmlDocument],
) -> None:
    for locale in LOCALES:
        entries = sorted(
            (slug, similarity_tokens(locale, doc.visible_main_text))
            for (doc_locale, slug), doc in documents.items()
            if doc_locale == locale
        )
        shingle_size = 10 if locale == "ja" else 5
        for index, (left_slug, left_tokens) in enumerate(entries):
            for right_slug, right_tokens in entries[index + 1:]:
                left_shingles = {
                    tuple(left_tokens[offset:offset + shingle_size])
                    for offset in range(max(0, len(left_tokens) - shingle_size + 1))
                }
                right_shingles = {
                    tuple(right_tokens[offset:offset + shingle_size])
                    for offset in range(max(0, len(right_tokens) - shingle_size + 1))
                }
                union = left_shingles | right_shingles
                jaccard = len(left_shingles & right_shingles) / len(union) if union else 1.0
                sequence = difflib.SequenceMatcher(None, left_tokens, right_tokens, autojunk=False).ratio()
                if jaccard > 0.62 or sequence > 0.86:
                    gate.fail(
                        "CONTENT-SIMILARITY",
                        f"{locale}/{left_slug} <> {locale}/{right_slug}",
                        f"near-duplicate main text (shingle Jaccard={jaccard:.3f}, sequence ratio={sequence:.3f})",
                    )


def sitemap_alternates(entry: ET.Element) -> dict[str, list[str]]:
    values: dict[str, list[str]] = defaultdict(list)
    for child in entry:
        if child.tag == f"{{{XHTML_NS}}}link":
            if child.attrib.get("rel") == "alternate" and child.attrib.get("hreflang"):
                values[child.attrib["hreflang"]].append(child.attrib.get("href", ""))
    return values


def child_text(entry: ET.Element, local_name: str) -> str:
    for child in entry:
        if child.tag == f"{{{SITEMAP_NS}}}{local_name}":
            return clean(child.text)
    return ""


def validate_sitemap(gate: Gate, topics: list[dict[str, Any]], last_modified: str) -> None:
    try:
        tree = ET.parse(SITEMAP_PATH)
    except FileNotFoundError:
        gate.fail("SITEMAP-MISSING", SITEMAP_PATH.relative_to(ROOT), "sitemap is missing")
        return
    except (ET.ParseError, OSError) as exc:
        gate.fail("SITEMAP-PARSE", SITEMAP_PATH.relative_to(ROOT), f"cannot parse sitemap XML: {exc}")
        return
    if tree.getroot().tag != f"{{{SITEMAP_NS}}}urlset":
        gate.fail("SITEMAP-NAMESPACE", SITEMAP_PATH.relative_to(ROOT), "root must be a sitemap-protocol urlset")
    entries: dict[str, list[ET.Element]] = defaultdict(list)
    for entry in tree.getroot():
        if entry.tag == f"{{{SITEMAP_NS}}}url":
            entries[child_text(entry, "loc")].append(entry)

    expected: list[tuple[str, dict[str, str]]] = []
    for topic in topics:
        slug = str(topic["slug"])
        for locale in LOCALES:
            expected.append((canonical_for(locale, slug), topic_cluster(slug)))
    expected.extend((hub_canonical(locale), hub_cluster()) for locale in LOCALES)

    for canonical, cluster in expected:
        matches = entries.get(canonical, [])
        if len(matches) != 1:
            gate.fail("SITEMAP-LOC", SITEMAP_PATH.relative_to(ROOT), f"{canonical} must occur once; found {len(matches)}")
            continue
        entry = matches[0]
        if child_text(entry, "lastmod") != last_modified:
            gate.fail("SITEMAP-LASTMOD", canonical, f"lastmod must be {last_modified}")
        alternates = sitemap_alternates(entry)
        if set(alternates) != set(HREFLANGS):
            gate.fail("SITEMAP-HREFLANG", canonical, f"hreflang keys must be exactly {list(HREFLANGS)}")
        for lang in HREFLANGS:
            values = alternates.get(lang, [])
            if len(values) != 1 or values[0] != cluster[lang]:
                gate.fail("SITEMAP-HREFLANG", canonical, f"{lang} must occur once and point to {cluster[lang]}")


def validate_llms(gate: Gate, topics: list[dict[str, Any]]) -> None:
    try:
        text_value = LLMS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        gate.fail("LLMS-MISSING", LLMS_PATH.relative_to(ROOT), "llms.txt is missing")
        return
    except (OSError, UnicodeError) as exc:
        gate.fail("LLMS-READ", LLMS_PATH.relative_to(ROOT), f"cannot read UTF-8 text: {exc}")
        return
    found = {
        match.group(0).rstrip(".,;:!?)]}")
        for match in re.finditer(r"https?://[^\s<>\[\]\"']+", text_value)
    }
    for topic in topics:
        for locale in LOCALES:
            canonical = canonical_for(locale, str(topic["slug"]))
            if canonical not in found:
                gate.fail("LLMS-GUIDE", LLMS_PATH.relative_to(ROOT), f"missing exact guide URL {canonical}")
    validate_claims(gate, LLMS_PATH.relative_to(ROOT), text_value)


def main() -> int:
    gate = Gate()
    loaded = load_topics(gate)
    if loaded is None:
        return gate.finish()
    last_modified, topics = loaded
    cache: dict[Path, HtmlDocument] = {}
    guide_documents: dict[tuple[str, str], HtmlDocument] = {}
    for topic in topics:
        if not isinstance(topic, dict) or "slug" not in topic:
            continue
        for locale in LOCALES:
            doc = validate_guide(gate, topic, locale, last_modified, cache)
            if doc is not None:
                guide_documents[(locale, str(topic["slug"]))] = doc
    validate_hubs_and_orphans(gate, topics, cache)
    validate_similarity(gate, guide_documents)
    validate_sitemap(gate, topics, last_modified)
    validate_llms(gate, topics)
    return gate.finish()


if __name__ == "__main__":
    sys.exit(main())
