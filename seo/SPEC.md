# BlackShisa multilingual SEO guide specification

Status: implementation specification

This document defines the machine-checkable contract for ten guide topic
families in four languages. `tool/check_seo.py` is the executable acceptance
gate. A release is not acceptable while that command exits non-zero.

## Source data and routes

`seo/topics.json` MUST be a UTF-8 JSON object with this shape:

```json
{
  "lastModified": "YYYY-MM-DD",
  "topics": [
    {
      "slug": "lowercase-ascii-slug",
      "image": "assets/img/example.webp",
      "locales": {
        "en": {},
        "ja": {},
        "es": {},
        "de": {}
      }
    }
  ]
}
```

There MUST be exactly ten topic objects. Every topic MUST have all and only
the four locale keys `en`, `ja`, `es`, and `de`. Locale objects MUST contain
non-empty `lang`, `title`, `description`, `kicker`, `h1`, `lede`, `chips`,
`summaryCards`, `sections`, `faq`, `related`, `ctaHeading`, and `ctaText`
values. `lang` MUST respectively be `en-US`, `ja-JP`, `es-ES`, and `de-DE`.
Each locale MUST have at least three summary cards, four sections, three FAQ
items, and three unique related topic slugs. A topic MUST NOT relate to itself.

Slugs MUST match `[a-z0-9]+(?:-[a-z0-9]+)*` and be unique. For each locale,
all ten slugs, titles, descriptions, and H1 values MUST be unique after Unicode
normalization, case folding, and whitespace normalization.

The route mapping is fixed:

| Locale | Guide route | Hub route | Home route |
|---|---|---|---|
| `en` | `/<slug>.html` | `/parking-guides.html` | `/` |
| `ja` | `/ja/<slug>.html` | `/ja/parking-guides.html` | `/ja/` |
| `es` | `/es/<slug>.html` | `/es/parking-guides.html` | `/es/` |
| `de` | `/de/<slug>.html` | `/de/parking-guides.html` | `/de/` |

The canonical origin is exactly `https://blackshisa.com`, without `www`.

## Per-guide HTML contract

Every guide MUST satisfy all of the following:

- UTF-8 HTML with the exact locale `lang` value on `<html>`.
- Exactly one `<title>`, one meta description, one canonical link, and one
  visible H1. Title, description, and H1 MUST exactly match `topics.json`
  after whitespace normalization. The canonical MUST exactly match the route.
- Exactly one alternate for each of `en-US`, `ja-JP`, `es-ES`, `de-DE`, and
  `x-default`. The four language alternates MUST point to the corresponding
  topic pages, and `x-default` MUST point to English. Every member therefore
  publishes the same reciprocal cluster.
- Substantive visible text inside `<main>`. Script, style, template, noscript,
  hidden, `aria-hidden="true"`, and CSS-hidden text does not count. Minimums
  are 450 word tokens for English, Spanish, and German, and 900 Japanese
  kana/kanji characters for Japanese. At least four rendered content sections
  MUST each contain at least two non-empty visible paragraphs.
- At least one valid JSON-LD script. All JSON-LD scripts MUST parse as JSON.
  The combined graph MUST contain `WebPage`, `Article`, and `BreadcrumbList`.
  `WebPage` and `Article` nodes MUST carry the exact canonical `url`, exact
  `inLanguage`, and exact source `dateModified`. The breadcrumb list MUST have
  at least three ordered items and end at the guide canonical.
- A visible breadcrumb region, identifiable by a `breadcrumb` class or an
  English `aria-label` containing `breadcrumb`, inside `<main>`.
- A visible `<time datetime="YYYY-MM-DD">` inside `<main>` whose date equals
  `lastModified`.
- A visible main-content link to the same-language hub and links to every slug
  named by the locale's `related` array. There MUST be at least three distinct
  links to other guides in the same language.
- No duplicate HTML IDs. Every local `href` and `src` on a guide or hub MUST
  resolve to a file. Every non-empty local fragment MUST resolve to an ID or
  legacy anchor name in the target HTML document.

## Hub, discovery, sitemap, and LLM discovery contract

Each of the four hub pages MUST exist, have exact canonical and reciprocal
hreflang metadata, one visible H1, and visible links to all ten guides in that
language. Each language home page MUST visibly link to its hub. This establishes
the crawl path `home -> hub -> every guide`; a guide outside that path is an
orphan and fails the gate.

`sitemap.xml` MUST contain exactly one `<url>` entry for each of the 40 guides
and four hubs. Each expected entry MUST use its canonical as `<loc>`, use
`lastModified` as `<lastmod>`, and publish exactly the same five-link hreflang
cluster as HTML.

`llms.txt` MUST contain the exact canonical URL of every one of the 40 guides.

## Claim safety and content differentiation

Source copy, rendered guide copy, and `llms.txt` MUST NOT promise guaranteed
capture, guaranteed identification, prevention of crime or hit-and-runs,
perfect evidence, never missing an event, or 100 percent effectiveness. The
gate checks a conservative multilingual phrase denylist. Claims should instead
describe evidence collection as conditional assistance and state relevant
device, placement, lighting, platform, power, and detection limits.

Within each locale, guide main content MUST not be near-duplicate. The gate
compares every pair with token shingles and sequence similarity. It fails a
pair when five-token shingle Jaccard similarity exceeds `0.62` for Latin-script
languages, when ten-token similarity exceeds `0.62` for Japanese, or when the
normalized token sequence ratio exceeds `0.86`. Common navigation is excluded
because comparison uses visible `<main>` text only.

## Local execution

Run from the repository root:

```sh
python3 seo/generate.py --check
python3 tool/check_seo.py
```

The first command proves that rendered pages, sitemap, and `llms.txt` match the
source data and that no retired generated page remains. The second emits a
deterministic list of semantic violations and exits `1` on RED. It prints a
summary and exits `0` only when the whole contract is green. Both commands use
only the Python standard library and do not perform network requests.
