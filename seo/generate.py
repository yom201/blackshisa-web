#!/usr/bin/env python3
"""Generate BlackShisa's multilingual, static SEO guide cluster.

The localized copy lives in seo/topics.json. This script owns the forty guide
pages, four guide hubs, sitemap.xml, and llms.txt so canonical/hreflang/link
relationships cannot drift between hand-edited files.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "seo" / "topics.json"
SITE = "https://blackshisa.com"
LOCALES = ("en", "de", "es", "ja")
HREFLANG = {"en": "en-US", "de": "de-DE", "es": "es-ES", "ja": "ja-JP"}
IMAGE_DIMENSIONS = {
    "assets/img/use-case01.webp": (1536, 1024),
    "assets/img/use-case02.webp": (1536, 1024),
    "assets/img/flash.webp": (1536, 1024),
    "assets/img/monitoring_en.webp": (942, 2048),
    "assets/img/monitoring_de.webp": (852, 1846),
    "assets/img/monitoring_es.webp": (853, 1844),
    "assets/img/monitoring_jp.webp": (942, 2048),
    "assets/img/monitoring_vertical_cart_contact.webp": (942, 2048),
    "assets/img/events_en.webp": (853, 1844),
    "assets/img/events_de.webp": (853, 1844),
    "assets/img/events_es.webp": (852, 1846),
    "assets/img/events_jp.webp": (853, 1844),
    "assets/img/details_en.webp": (853, 1844),
    "assets/img/details_de.webp": (852, 1846),
    "assets/img/details_es.webp": (852, 1846),
    "assets/img/details_jp.webp": (942, 2048),
    "assets/img/home_en.webp": (1320, 2868),
    "assets/img/home_de.webp": (1320, 2868),
    "assets/img/home_es.webp": (1320, 2868),
    "assets/img/home_jp.webp": (1320, 2868),
    "assets/img/setting_en.webp": (1320, 2868),
    "assets/img/setting_de.webp": (1320, 2868),
    "assets/img/setting_es.webp": (1320, 2868),
    "assets/img/setting_jp.webp": (1320, 2868),
}

UI = {
    "en": {
        "home": "Home",
        "guides": "Parking guides",
        "features": "Features",
        "privacy": "Privacy",
        "updated": "Updated",
        "summary": "At a glance",
        "article": "Practical guide",
        "facts_kicker": "BlackShisa facts",
        "facts_heading": "Know what the app records—and its limits.",
        "facts": [
            "Motion, sound, and impact can trigger an event.",
            "Clips include 3 seconds before detection and 10, 30, or 60 seconds after.",
            "Evidence is stored locally first; Google Drive backup is optional.",
            "iOS monitoring stays in the foreground with the screen on; Android uses a foreground service subject to permissions and device settings.",
        ],
        "all_guides": "Explore all parking guides",
        "faq": "Questions about this setup",
        "faq_lede": "Direct answers, including the constraints that matter before you rely on a spare phone.",
        "guide_image_alt": "BlackShisa parked-car monitoring example",
        "related": "Related guides",
        "related_heading": "Continue with the next practical decision.",
        "cta": "See how BlackShisa works",
        "hub_title": "Parking Camera Guides for Spare Phones | BlackShisa",
        "hub_description": "Ten practical guides for using a spare phone to monitor a parked car: hit-and-run evidence, door dings, placement, detection, heat, battery, and honest dash-cam comparisons.",
        "hub_h1": "Build a parked-car camera setup one decision at a time.",
        "hub_lede": "Choose the problem you need to solve. Each guide covers a different decision, from camera placement and trigger selection to hit-and-run evidence and heat safety.",
        "hub_kicker": "Parking evidence library",
        "footer": "Practical, limitation-aware guidance for smartphone-based parked-car evidence.",
    },
    "ja": {
        "home": "ホーム",
        "guides": "駐車監視ガイド",
        "features": "機能",
        "privacy": "プライバシー",
        "updated": "更新日",
        "summary": "先に押さえること",
        "article": "実践ガイド",
        "facts_kicker": "BlackShisaの基本仕様",
        "facts_heading": "記録できることと、できないことを確認する。",
        "facts": [
            "動体・音・衝撃をきっかけにイベントを記録します。",
            "検知前3秒と、検知後10秒・30秒・60秒を動画に残します。",
            "証拠はまず端末内に保存し、Google Driveへのバックアップは任意です。",
            "iOSは画面を点灯したまま前面で監視します。Androidは権限と端末設定に応じてフォアグラウンドサービスを使います。",
        ],
        "all_guides": "駐車監視ガイドをすべて見る",
        "faq": "この使い方についての質問",
        "faq_lede": "余ったスマホに任せる前に知っておきたい制約も含め、要点を答えます。",
        "guide_image_alt": "BlackShisaを使った駐車監視の例",
        "related": "関連ガイド",
        "related_heading": "次に決めたいことを確認する。",
        "cta": "BlackShisaの仕組みを見る",
        "hub_title": "スマホ駐車監視・証拠記録ガイド10選 | BlackShisa",
        "hub_description": "余ったスマホで駐車監視を始めるための10ガイド。当て逃げ・ドアパンチの証拠、設置位置、検知方法、発熱・バッテリー、ドラレコとの違いを整理します。",
        "hub_h1": "駐車監視に必要な判断を、ひとつずつ確かめる。",
        "hub_lede": "残したい証拠や心配ごとから選んでください。設置位置、検知方法、当て逃げへの備え、発熱対策まで、検索意図の異なる10テーマに分けています。",
        "hub_kicker": "駐車監視の実践ライブラリ",
        "footer": "スマホで駐車中の証拠を残すための、制約を隠さない実践ガイドです。",
    },
    "es": {
        "home": "Inicio",
        "guides": "Guías de vigilancia",
        "features": "Funciones",
        "privacy": "Privacidad",
        "updated": "Actualizado",
        "summary": "En pocas palabras",
        "article": "Guía práctica",
        "facts_kicker": "Datos de BlackShisa",
        "facts_heading": "Conoce lo que graba la app y sus límites.",
        "facts": [
            "El movimiento, el sonido y el impacto pueden activar un evento.",
            "Los clips incluyen 3 segundos anteriores y 10, 30 o 60 segundos posteriores a la detección.",
            "Las pruebas se guardan primero en el móvil; la copia en Google Drive es opcional.",
            "En iOS la app debe permanecer en primer plano y con la pantalla encendida; Android usa un servicio en primer plano sujeto a permisos y ajustes del dispositivo.",
        ],
        "all_guides": "Ver todas las guías",
        "faq": "Preguntas sobre esta configuración",
        "faq_lede": "Respuestas directas, incluidos los límites que conviene conocer antes de confiar en un móvil de repuesto.",
        "guide_image_alt": "Ejemplo de vigilancia del coche aparcado con BlackShisa",
        "related": "Guías relacionadas",
        "related_heading": "Continúa con la siguiente decisión práctica.",
        "cta": "Ver cómo funciona BlackShisa",
        "hub_title": "Guías para vigilar un coche aparcado con el móvil | BlackShisa",
        "hub_description": "Diez guías prácticas para usar un móvil de repuesto al vigilar un coche aparcado: golpes y fuga, puertas, colocación, detectores, calor, batería y comparación con una dashcam.",
        "hub_h1": "Prepara la cámara del coche aparcado decisión a decisión.",
        "hub_lede": "Empieza por el problema que quieres resolver. Cada guía trata una decisión diferente: desde el ángulo y los detectores hasta las pruebas de un golpe y la seguridad frente al calor.",
        "hub_kicker": "Biblioteca de vigilancia al aparcar",
        "footer": "Consejos prácticos y transparentes sobre los límites de grabar el coche aparcado con un móvil.",
    },
    "de": {
        "home": "Start",
        "guides": "Parküberwachungs-Ratgeber",
        "features": "Funktionen",
        "privacy": "Datenschutz",
        "updated": "Aktualisiert",
        "summary": "Auf einen Blick",
        "article": "Praxisratgeber",
        "facts_kicker": "BlackShisa-Fakten",
        "facts_heading": "Verstehe die Aufzeichnung und ihre Grenzen.",
        "facts": [
            "Bewegung, Geräusch und Erschütterung können ein Ereignis auslösen.",
            "Clips enthalten 3 Sekunden vor der Erkennung und 10, 30 oder 60 Sekunden danach.",
            "Beweise werden zuerst lokal gespeichert; ein Google-Drive-Backup ist optional.",
            "Unter iOS bleibt die App bei eingeschaltetem Display im Vordergrund; Android nutzt abhängig von Berechtigungen und Geräteeinstellungen einen Vordergrunddienst.",
        ],
        "all_guides": "Alle Ratgeber ansehen",
        "faq": "Fragen zu diesem Einsatz",
        "faq_lede": "Klare Antworten, einschließlich der Grenzen, die du vor dem Einsatz eines alten Smartphones kennen solltest.",
        "guide_image_alt": "Beispiel für die Parküberwachung mit BlackShisa",
        "related": "Verwandte Ratgeber",
        "related_heading": "Triff als Nächstes die passende praktische Entscheidung.",
        "cta": "So funktioniert BlackShisa",
        "hub_title": "Ratgeber: Auto beim Parken per Handy überwachen | BlackShisa",
        "hub_description": "Zehn praktische Ratgeber zur Parküberwachung per Smartphone: Fahrerflucht, Türrempler, Positionierung, Erkennung, Hitze, Akku und ehrlicher Dashcam-Vergleich.",
        "hub_h1": "Plane die Kamera im geparkten Auto Schritt für Schritt.",
        "hub_lede": "Wähle das Problem, das du lösen möchtest. Jeder Ratgeber behandelt eine andere Entscheidung – vom Blickwinkel und Auslöser bis zu Parkschäden und Hitzeschutz.",
        "hub_kicker": "Ratgeber zur Beweissicherung beim Parken",
        "footer": "Praxisnahe Hinweise mit offenen Grenzen zur Beweissicherung am geparkten Auto per Smartphone.",
    },
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def locale_path(locale: str, filename: str) -> str:
    return filename if locale == "en" else f"{locale}/{filename}"


def canonical(locale: str, filename: str) -> str:
    return f"{SITE}/{locale_path(locale, filename)}"


def relative_prefix(locale: str) -> str:
    return "" if locale == "en" else "../"


def localized_image(image_path: str, locale: str) -> str:
    """Use a locale-matched app screenshot when a topic selects an English one."""
    suffix = {"en": "en", "de": "de", "es": "es", "ja": "jp"}[locale]
    for family in ("monitoring", "events", "details", "home", "setting"):
        marker = f"assets/img/{family}_en."
        if image_path.startswith(marker):
            extension = image_path.rsplit(".", 1)[1]
            return f"assets/img/{family}_{suffix}.{extension}"
    return image_path


def alternate_links(filename: str) -> str:
    lines = [
        f'    <link rel="alternate" hreflang="{HREFLANG[loc]}" href="{canonical(loc, filename)}">'
        for loc in LOCALES
    ]
    lines.append(f'    <link rel="alternate" hreflang="x-default" href="{canonical("en", filename)}">')
    return "\n".join(lines)


def language_switch(locale: str, filename: str) -> str:
    labels = {"en": "EN", "de": "DE", "es": "ES", "ja": "JA"}
    links = []
    for loc in LOCALES:
        if locale == "en":
            href = filename if loc == "en" else f"{loc}/{filename}"
        else:
            href = filename if loc == locale else (f"../{filename}" if loc == "en" else f"../{loc}/{filename}")
        current = ' class="active" aria-current="page"' if loc == locale else ""
        links.append(f'            <a{current} href="{esc(href)}">{labels[loc]}</a>')
    return "\n".join(links)


def load_data() -> dict:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(data.get("topics"), list):
        raise ValueError("seo/topics.json must contain a topics list")
    return data


def ld_script(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f'    <script type="application/ld+json">\n{raw}\n    </script>'


def page_schema(topic: dict, locale: str, last_modified: str) -> dict:
    copy = topic["locales"][locale]
    filename = f'{topic["slug"]}.html'
    url = canonical(locale, filename)
    image_url = f'{SITE}/{localized_image(topic["image"], locale)}'
    home_url = f"{SITE}/" if locale == "en" else f"{SITE}/{locale}/"
    hub_url = canonical(locale, "parking-guides.html")
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": copy["title"],
                "description": copy["description"],
                "inLanguage": copy["lang"],
                "dateModified": last_modified,
                "isPartOf": {"@type": "WebSite", "name": "BlackShisa - Parking Dashcam App", "url": SITE},
                "about": {"@type": "SoftwareApplication", "name": "BlackShisa - Parking Dashcam App", "operatingSystem": "iOS, Android"},
            },
            {
                "@type": "Article",
                "@id": f"{url}#article",
                "headline": copy["h1"],
                "url": url,
                "description": copy["description"],
                "image": image_url,
                "dateModified": last_modified,
                "inLanguage": copy["lang"],
                "author": {"@type": "Organization", "name": "ICHITAP"},
                "publisher": {"@type": "Organization", "name": "ICHITAP", "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/img/blackshisa-logo.jpg"}},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": UI[locale]["home"], "item": home_url},
                    {"@type": "ListItem", "position": 2, "name": UI[locale]["guides"], "item": hub_url},
                    {"@type": "ListItem", "position": 3, "name": copy["title"], "item": url},
                ],
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": item["q"], "acceptedAnswer": {"@type": "Answer", "text": item["a"]}}
                    for item in copy["faq"]
                ],
            },
        ],
    }


def render_sections(sections: list[dict]) -> str:
    blocks = []
    for section in sections:
        paragraphs = "\n".join(f"              <p>{esc(p)}</p>" for p in section["paragraphs"])
        bullets = ""
        if section.get("bullets"):
            items = "\n".join(f"                <li>{esc(item)}</li>" for item in section["bullets"])
            bullets = f"\n              <ul>\n{items}\n              </ul>"
        blocks.append(f"""            <section>
              <h2>{esc(section['heading'])}</h2>
{paragraphs}{bullets}
            </section>""")
    return "\n".join(blocks)


def render_guide(topic: dict, locale: str, topics_by_slug: dict[str, dict], last_modified: str) -> str:
    copy = topic["locales"][locale]
    ui = UI[locale]
    filename = f'{topic["slug"]}.html'
    url = canonical(locale, filename)
    prefix = relative_prefix(locale)
    image = localized_image(topic["image"], locale)
    image_path = f"{prefix}{image}"
    image_width, image_height = IMAGE_DIMENSIONS[image]
    chips = "\n".join(f"              <span>{esc(item)}</span>" for item in copy["chips"])
    cards = "\n".join(
        f"""          <article class="guide-summary-card">
            <h2>{esc(card['title'])}</h2>
            <p>{esc(card['text'])}</p>
          </article>"""
        for card in copy["summaryCards"]
    )
    facts = "\n".join(f"              <li>{esc(item)}</li>" for item in ui["facts"])
    faq = "\n".join(
        f"""            <details>
              <summary>{esc(item['q'])}</summary>
              <p>{esc(item['a'])}</p>
            </details>"""
        for item in copy["faq"]
    )
    related = []
    for slug in copy["related"]:
        related_copy = topics_by_slug[slug]["locales"][locale]
        related.append(
            f"""            <a href="{esc(slug)}.html">
              <span>{esc(related_copy['kicker'])}</span>
              <strong>{esc(related_copy['h1'])}</strong>
            </a>"""
        )
    schema = page_schema(topic, locale, last_modified)
    return f"""<!doctype html>
<html lang="{esc(copy['lang'])}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{esc(copy['title'])}</title>
    <meta name="description" content="{esc(copy['description'])}">
    <meta name="robots" content="index,follow,max-image-preview:large">
    <link rel="canonical" href="{url}">
{alternate_links(filename)}
    <link rel="icon" type="image/jpeg" sizes="64x64" href="{prefix}assets/img/blackshisa-favicon.jpg">
    <link rel="apple-touch-icon" sizes="180x180" href="{prefix}assets/img/blackshisa-apple-touch.jpg">
    <link rel="manifest" href="{prefix}site.webmanifest">
    <link rel="stylesheet" href="{prefix}assets/css/styles.css?v=20260812-seo-clusters">
    <meta name="theme-color" content="#030303">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="BlackShisa - Parking Dashcam App">
    <meta property="og:title" content="{esc(copy['title'])}">
    <meta property="og:description" content="{esc(copy['description'])}">
    <meta property="og:url" content="{url}">
    <meta property="og:image" content="{SITE}/{esc(image)}">
    <meta property="article:modified_time" content="{last_modified}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{esc(copy['title'])}">
    <meta name="twitter:description" content="{esc(copy['description'])}">
    <meta name="twitter:image" content="{SITE}/{esc(image)}">
{ld_script(schema)}
  </head>
  <body class="seo-page">
    <header class="site-header">
      <nav class="nav" aria-label="{esc(ui['guides'])}">
        <a class="brand" href="./" aria-label="BlackShisa - Parking Dashcam App">
          <img src="{prefix}assets/img/blackshisa-logo-nav.webp" alt="" width="44" height="44">
          BlackShisa <span class="brand-tagline"><span class="brand-separator" aria-hidden="true">- </span>Parking Dashcam App</span>
        </a>
        <div class="nav-links legal-nav-links">
          <a class="hide-small" href="./">{esc(ui['home'])}</a>
          <a class="hide-small" href="parking-guides.html">{esc(ui['guides'])}</a>
          <a class="hide-small" href="./#features">{esc(ui['features'])}</a>
          <div class="language-switch" aria-label="Language switcher">
{language_switch(locale, filename)}
          </div>
        </div>
      </nav>
    </header>
    <main>
      <nav class="guide-breadcrumb wrap" aria-label="Breadcrumb">
        <a href="./">{esc(ui['home'])}</a><span aria-hidden="true">/</span>
        <a href="parking-guides.html">{esc(ui['guides'])}</a><span aria-hidden="true">/</span>
        <span aria-current="page">{esc(copy['kicker'])}</span>
      </nav>
      <section class="guide-hero" aria-labelledby="guide-title">
        <div class="wrap guide-hero-grid">
          <div class="guide-hero-copy">
            <p class="kicker">{esc(copy['kicker'])}</p>
            <h1 id="guide-title">{esc(copy['h1'])}</h1>
            <p class="guide-lede">{esc(copy['lede'])}</p>
            <p class="guide-updated">{esc(ui['updated'])}: <time datetime="{last_modified}">{last_modified}</time></p>
            <div class="guide-chip-row" aria-label="{esc(ui['summary'])}">
{chips}
            </div>
            <div class="hero-actions">
              <a class="button primary" href="#guide-content">{esc(ui['article'])}</a>
              <a class="button" href="parking-guides.html">{esc(ui['all_guides'])}</a>
            </div>
          </div>
          <figure class="guide-hero-media">
            <img src="{esc(image_path)}" alt="{esc(ui['guide_image_alt'])}: {esc(copy['kicker'])}" width="{image_width}" height="{image_height}" fetchpriority="high">
          </figure>
        </div>
      </section>

      <section class="section guide-summary-section" aria-label="{esc(ui['summary'])}">
        <div class="wrap guide-summary-grid">
{cards}
        </div>
      </section>

      <section class="section alt guide-content-section" id="guide-content" aria-label="{esc(ui['article'])}">
        <div class="wrap guide-layout">
          <article class="guide-article">
{render_sections(copy['sections'])}
          </article>
          <aside class="guide-side-panel" aria-label="BlackShisa - Parking Dashcam App">
            <p class="kicker">{esc(ui['facts_kicker'])}</p>
            <h2>{esc(ui['facts_heading'])}</h2>
            <ul>
{facts}
            </ul>
            <a class="button primary" href="./#how-it-works">{esc(ui['cta'])}</a>
          </aside>
        </div>
      </section>

      <section class="section" id="guide-faq" aria-labelledby="guide-faq-title">
        <div class="wrap faq">
          <div>
            <p class="kicker">FAQ</p>
            <h2 id="guide-faq-title">{esc(ui['faq'])}</h2>
            <p class="lede">{esc(ui['faq_lede'])}</p>
          </div>
          <div class="faq-list">
{faq}
          </div>
        </div>
      </section>

      <section class="section compact guide-related-section" aria-labelledby="related-guides-title">
        <div class="wrap">
          <div class="section-head center">
            <p class="kicker">{esc(ui['related'])}</p>
            <h2 id="related-guides-title">{esc(ui['related_heading'])}</h2>
          </div>
          <div class="guide-related-grid">
{chr(10).join(related)}
          </div>
        </div>
      </section>

      <section class="section compact guide-cta-section">
        <div class="wrap parking-mode-band">
          <h2>{esc(copy['ctaHeading'])}</h2>
          <p class="lede">{esc(copy['ctaText'])}</p>
          <div class="hero-actions">
            <a class="button primary" href="./#how-it-works">{esc(ui['cta'])}</a>
          </div>
        </div>
      </section>
    </main>
    <footer class="footer">
      <div class="footer-inner">
        <div>
          <strong>BlackShisa - Parking Dashcam App</strong>
          <p class="fine-print">{esc(ui['footer'])}</p>
        </div>
        <div>
          <a href="./">{esc(ui['home'])}</a> | <a href="parking-guides.html">{esc(ui['guides'])}</a> | <a href="{prefix}privacy-policy.html">{esc(ui['privacy'])}</a>
        </div>
      </div>
    </footer>
  </body>
</html>
"""


def hub_schema(locale: str, topics: list[dict], last_modified: str) -> dict:
    url = canonical(locale, "parking-guides.html")
    home_url = f"{SITE}/" if locale == "en" else f"{SITE}/{locale}/"
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "CollectionPage", "@id": f"{url}#webpage", "url": url, "name": UI[locale]["hub_title"], "description": UI[locale]["hub_description"], "inLanguage": HREFLANG[locale], "dateModified": last_modified},
            {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": index, "name": topic["locales"][locale]["title"], "url": canonical(locale, f'{topic["slug"]}.html')} for index, topic in enumerate(topics, 1)]},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": UI[locale]["home"], "item": home_url},
                {"@type": "ListItem", "position": 2, "name": UI[locale]["guides"], "item": url},
            ]},
        ],
    }


def render_hub(locale: str, topics: list[dict], last_modified: str) -> str:
    ui = UI[locale]
    prefix = relative_prefix(locale)
    filename = "parking-guides.html"
    hub_image = localized_image("assets/img/monitoring_en.webp", locale)
    cards = "\n".join(
        f"""          <a class="seo-hub-card" href="{esc(topic['slug'])}.html">
            <span>{esc(topic['locales'][locale]['kicker'])}</span>
            <strong>{esc(topic['locales'][locale]['h1'])}</strong>
            <em>{esc(topic['locales'][locale]['lede'])}</em>
          </a>"""
        for topic in topics
    )
    schema = hub_schema(locale, topics, last_modified)
    return f"""<!doctype html>
<html lang="{HREFLANG[locale]}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{esc(ui['hub_title'])}</title>
    <meta name="description" content="{esc(ui['hub_description'])}">
    <meta name="robots" content="index,follow,max-image-preview:large">
    <link rel="canonical" href="{canonical(locale, filename)}">
{alternate_links(filename)}
    <link rel="icon" type="image/jpeg" sizes="64x64" href="{prefix}assets/img/blackshisa-favicon.jpg">
    <link rel="apple-touch-icon" sizes="180x180" href="{prefix}assets/img/blackshisa-apple-touch.jpg">
    <link rel="stylesheet" href="{prefix}assets/css/styles.css?v=20260812-seo-clusters">
    <meta name="theme-color" content="#030303">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="BlackShisa - Parking Dashcam App">
    <meta property="og:title" content="{esc(ui['hub_title'])}">
    <meta property="og:description" content="{esc(ui['hub_description'])}">
    <meta property="og:url" content="{canonical(locale, filename)}">
    <meta property="og:image" content="{SITE}/{hub_image}">
{ld_script(schema)}
  </head>
  <body class="seo-page">
    <header class="site-header">
      <nav class="nav" aria-label="{esc(ui['guides'])}">
        <a class="brand" href="./" aria-label="BlackShisa - Parking Dashcam App">
          <img src="{prefix}assets/img/blackshisa-logo-nav.webp" alt="" width="44" height="44">
          BlackShisa <span class="brand-tagline"><span class="brand-separator" aria-hidden="true">- </span>Parking Dashcam App</span>
        </a>
        <div class="nav-links legal-nav-links">
          <a class="hide-small" href="./">{esc(ui['home'])}</a>
          <a class="hide-small" href="./#features">{esc(ui['features'])}</a>
          <div class="language-switch" aria-label="Language switcher">
{language_switch(locale, filename)}
          </div>
        </div>
      </nav>
    </header>
    <main>
      <nav class="guide-breadcrumb wrap" aria-label="Breadcrumb">
        <a href="./">{esc(ui['home'])}</a><span aria-hidden="true">/</span><span aria-current="page">{esc(ui['guides'])}</span>
      </nav>
      <section class="guide-hero guide-hub-hero" aria-labelledby="hub-title">
        <div class="wrap">
          <p class="kicker">{esc(ui['hub_kicker'])}</p>
          <h1 id="hub-title">{esc(ui['hub_h1'])}</h1>
          <p class="guide-lede">{esc(ui['hub_lede'])}</p>
          <p class="guide-updated">{esc(ui['updated'])}: <time datetime="{last_modified}">{last_modified}</time></p>
        </div>
      </section>
      <section class="section seo-hub-section" aria-label="{esc(ui['guides'])}">
        <div class="wrap seo-hub-grid">
{cards}
        </div>
      </section>
    </main>
    <footer class="footer">
      <div class="footer-inner">
        <div><strong>BlackShisa - Parking Dashcam App</strong><p class="fine-print">{esc(ui['footer'])}</p></div>
        <div><a href="./">{esc(ui['home'])}</a> | <a href="{prefix}privacy-policy.html">{esc(ui['privacy'])}</a></div>
      </div>
    </footer>
  </body>
</html>
"""


def add_cluster(urlset: ET.Element, filename: str, lastmod: str) -> None:
    xhtml = "http://www.w3.org/1999/xhtml"
    for locale in LOCALES:
        node = ET.SubElement(urlset, "url")
        ET.SubElement(node, "loc").text = canonical(locale, filename)
        ET.SubElement(node, "lastmod").text = lastmod
        for alternate in LOCALES:
            ET.SubElement(node, f"{{{xhtml}}}link", {"rel": "alternate", "hreflang": HREFLANG[alternate], "href": canonical(alternate, filename)})
        ET.SubElement(node, f"{{{xhtml}}}link", {"rel": "alternate", "hreflang": "x-default", "href": canonical("en", filename)})


def render_sitemap(topics: list[dict], last_modified: str) -> str:
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    ET.register_namespace("xhtml", "http://www.w3.org/1999/xhtml")
    urlset = ET.Element("{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")
    for locale in LOCALES:
        node = ET.SubElement(urlset, "url")
        home_url = f"{SITE}/" if locale == "en" else f"{SITE}/{locale}/"
        ET.SubElement(node, "loc").text = home_url
        ET.SubElement(node, "lastmod").text = last_modified
        for alternate in LOCALES:
            alternate_home = f"{SITE}/" if alternate == "en" else f"{SITE}/{alternate}/"
            ET.SubElement(node, "{http://www.w3.org/1999/xhtml}link", {"rel": "alternate", "hreflang": HREFLANG[alternate], "href": alternate_home})
        ET.SubElement(node, "{http://www.w3.org/1999/xhtml}link", {"rel": "alternate", "hreflang": "x-default", "href": f"{SITE}/"})
    add_cluster(urlset, "security-light.html", "2026-07-28")
    add_cluster(urlset, "parking-guides.html", last_modified)
    for topic in topics:
        add_cluster(urlset, f'{topic["slug"]}.html', last_modified)
    for filename in ("privacy-policy.html", "eula.html"):
        node = ET.SubElement(urlset, "url")
        ET.SubElement(node, "loc").text = f"{SITE}/{filename}"
        ET.SubElement(node, "lastmod").text = "2026-07-25"
    ET.indent(urlset, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(urlset, encoding="unicode") + "\n"


def render_llms(topics: list[dict]) -> str:
    lines = [
        "# BlackShisa - Parking Dashcam App",
        "",
        "> BlackShisa is a smartphone app for recording event clips around motion, sound, or impact while a car is parked. It can help preserve context, but cannot guarantee that an incident, license plate, or face will be detected or readable.",
        "",
        "## Product facts",
        "- Evidence is saved locally first; backup to the user's own Google Drive is optional.",
        "- Clips include 3 seconds before detection and 10, 30, or 60 seconds after detection.",
        "- iOS monitoring requires the app in the foreground with the screen on. Android uses a foreground service subject to permissions and device settings.",
        "",
        "## Main pages",
        f"- English: {SITE}/",
        f"- 日本語: {SITE}/ja/",
        f"- Deutsch: {SITE}/de/",
        f"- Español: {SITE}/es/",
        "",
    ]
    language_names = {"en": "English parking guides", "ja": "日本語の駐車監視ガイド", "es": "Guías en español", "de": "Deutsche Ratgeber"}
    for locale in ("en", "ja", "es", "de"):
        lines.extend([f"## {language_names[locale]}", f"- Guide hub: {canonical(locale, 'parking-guides.html')}"])
        for topic in topics:
            lines.append(f"- {topic['locales'][locale]['title']}: {canonical(locale, topic['slug'] + '.html')}")
        lines.append("")
    lines.extend(["## Resources", f"- Google Play: https://play.google.com/store/apps/details?id=app.blackshisa.blackShisaApp", f"- Sitemap: {SITE}/sitemap.xml", f"- Robots: {SITE}/robots.txt", ""])
    return "\n".join(lines)


def generated_files(data: dict) -> dict[Path, str]:
    topics = data["topics"]
    last_modified = data["lastModified"]
    topics_by_slug = {topic["slug"]: topic for topic in topics}
    outputs: dict[Path, str] = {}
    for topic in topics:
        for locale in LOCALES:
            outputs[ROOT / locale_path(locale, f'{topic["slug"]}.html')] = render_guide(topic, locale, topics_by_slug, last_modified)
    for locale in LOCALES:
        outputs[ROOT / locale_path(locale, "parking-guides.html")] = render_hub(locale, topics, last_modified)
    outputs[ROOT / "sitemap.xml"] = render_sitemap(topics, last_modified)
    outputs[ROOT / "llms.txt"] = render_llms(topics)
    return outputs


def generated_html_files() -> set[Path]:
    """Find previously generated pages so removed slugs cannot stay live."""
    marker = '<body class="seo-page">'
    paths: set[Path] = set()
    for directory in (ROOT, *(ROOT / locale for locale in ("de", "es", "ja"))):
        for path in directory.glob("*.html"):
            if marker in path.read_text(encoding="utf-8"):
                paths.add(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail when generated files differ from their sources")
    args = parser.parse_args()
    data = load_data()
    outputs = generated_files(data)
    stale = []
    expected_html = {path for path in outputs if path.suffix == ".html"}
    extra_html = generated_html_files() - expected_html
    if extra_html:
        stale.extend(f"unexpected generated page: {path.relative_to(ROOT).as_posix()}" for path in sorted(extra_html))
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if stale:
        print("Generated SEO files are stale:")
        print("\n".join(f"- {item}" for item in stale))
        return 1
    if not args.check:
        print(f"Generated {len(outputs)} files from {DATA_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
