# BlackShisaサイト全体仕様書

最終更新日: 2026-08-13

対象リポジトリ: `yom201/blackshisa-web`

対象構成: `agent/ja-three-keyword-seo`で確定した重点3キーワード版

基準コミット: `547cdb3`と本仕様書追加差分

正規オリジン: `https://blackshisa.com`

### 検証根拠

本書の現状記述は、2026-08-13に次の方法で確認した結果です。将来の担当者は、日付依存の状態をそのまま恒久仕様だと扱わず、更新時に再確認してください。

- **[git検証]** ブランチ、コミット、tracked file、本番配信元との差分
- **[実ファイル検証]** HTML、CSS、JavaScript、画像、canonical、hreflang、sitemap、内部リンク
- **[実コード検証]** 隣接する`blackshisa_app`の録画・検知・保存条件
- **[実ログ検証]** GitHub Pages設定、公開レスポンス、ローカル検査、モバイル表示
- **[Google実画面検証]** 日本語重点3検索語の単発SERP。恒久順位ではなく監査時点の参考値

## 1. 文書の目的と優先順位

この文書は、BlackShisa公式サイトを初めて触る担当者が、既存URLやSEO評価を壊さずに更新・検証・公開・復旧できるようにするための実装仕様です。ページ一覧だけでなく、次の契約を一体として定義します。

- 公開URLとページごとの役割
- 多言語URL、canonical、hreflang
- HTMLテンプレート、CSS、JavaScript、画像
- SEO上の検索意図と担当URL
- アプリ機能について記載可能な事実と禁止表現
- サイトマップ、robots、llms、構造化データ
- ローカル検証、Pull Request、GitHub Pages公開、ロールバック

実装とこの文書が食い違う場合、変更を公開する前に両者を同じPull Requestで整合させます。過去の監査資料は判断経緯として参照できますが、現在の公開構成についてはこの文書を優先します。

## 2. 現在地

### 2.1 ローカル・Git・本番の区別

| 対象 | 状態 |
| --- | --- |
| 本番配信元 | GitHub Pages、`main`ブランチ、リポジトリ直下`/` |
| 本番ドメイン | `https://blackshisa.com`、HTTPS強制 |
| 本番の確認済みコミット | `6c7690c`。2026-08-13時点では重点3キーワード差分より前 |
| 重点3キーワード版 | ローカルブランチ`agent/ja-three-keyword-seo` |
| 重点版の実装コミット | `547cdb3` |
| 重点版の公開状態 | この文書作成時点では未push・未公開 |
| 生成型40ガイド案 | `agent/multilingual-seo`に隔離。現行仕様では非採用 |

「ローカルで完成」「GitHubへpush済み」「`main`へマージ済み」「本番Pagesで配信済み」は別の状態です。どの状態かを確認せずに「公開済み」と表現しません。

### 2.2 技術方式

- 純粋な静的サイトです。
- HTML、CSS、JavaScript、画像を直接配信します。
- Node.js、npm、Pythonパッケージ、SSG、CMS、テンプレートエンジンは本番生成に使いません。
- Pythonは検査スクリプトにのみ使い、標準ライブラリだけで動きます。
- `.nojekyll`によりJekyll処理を避けます。削除しません。
- URL末尾の`.html`は既存契約です。安易に拡張子なしURLへ変更しません。

## 3. リポジトリ構成

```text
blackshisa-web/
├── README.md
├── docs/
│   └── SITE_SPEC.md
├── index.html                       # 英語ホーム
├── de/                              # ドイツ語ローカライズ
├── es/                              # スペイン語ローカライズ
├── ja/                              # 日本語ローカライズ・重点SEOページ
├── *.html                           # 英語ガイド、法務、機能ページ
├── assets/
│   ├── css/
│   │   ├── styles.css               # 全体共通
│   │   └── security-light.css       # Security Light専用追加CSS
│   ├── img/                         # ロゴ、スクリーン、ユースケース画像
│   └── js/
│       └── screen-lightbox.js       # スクリーンショット拡大
├── seo/
│   └── AUDIT-JA-3KEYWORDS-2026-08-13.md
├── tool/
│   └── check_site.py                # 現行22ページ用の必須検査
├── CNAME                            # GitHub Pages独自ドメイン
├── .nojekyll                        # Jekyll無効化
├── robots.txt
├── sitemap.xml
├── llms.txt
├── site.webmanifest
└── googlec9b4c510fa66e954.html      # Google所有権確認。通常ページではない
```

### 3.1 実行時ファイルの規模

2026-08-13のfocused版を基準にした、文書・検査ツールを除く主要ファイル数です。

| 区分 | 数 | 備考 |
| --- | ---: | --- |
| 通常HTML | 22 | canonicalとsitemapの対象 |
| Google確認HTML | 1 | 通常ページ検査の例外 |
| 画像 | 50 | 原本・旧形式・未参照候補を含む |
| CSS | 2 | 共通とSecurity Light専用 |
| JavaScript | 1 | ホームのlightbox専用 |

HTMLは共通header、footer、価格、schemaを直接複製しています。変更は1ファイルで全体へ反映されないため、対象ページ群を明示してから一括検索し、各階層の相対URLを確認します。

### 3.2 公開ルートに置くファイルの注意

GitHub Pagesは`main`直下を配信します。リポジトリへコミットしたREADMEや`docs/`もURLを知っていれば取得できます。次のものを絶対に置きません。

- APIキー、秘密鍵、Cookie、トークン
- Search Consoleやストアの非公開エクスポート
- 個人情報を含むログやスクリーンショット
- 公開してはいけない契約書・内部メモ

## 4. URLインベントリ

通常公開ページは22件です。`sitemap.xml`もこの22件だけを持ちます。

### 4.1 ホーム

| 言語 | URL | ファイル | 役割 |
| --- | --- | --- | --- |
| 英語 | `/` | `index.html` | 英語製品ホーム |
| ドイツ語 | `/de/` | `de/index.html` | ドイツ語製品ホーム |
| スペイン語 | `/es/` | `es/index.html` | スペイン語製品ホーム |
| 日本語 | `/ja/` | `ja/index.html` | 日本語製品ホーム。「当て逃げ監視 アプリ」担当 |

### 4.2 Parking mode app

| 言語 | URL | ファイル | 役割 |
| --- | --- | --- | --- |
| 英語 | `/parking-mode-app.html` | `parking-mode-app.html` | 英語駐車監視アプリガイド |
| ドイツ語 | `/de/parking-mode-app.html` | `de/parking-mode-app.html` | ドイツ語版 |
| スペイン語 | `/es/parking-mode-app.html` | `es/parking-mode-app.html` | スペイン語版 |
| 日本語 | `/ja/parking-mode-app.html` | `ja/parking-mode-app.html` | 「駐車監視 アプリ」担当 |

### 4.3 Security Light

| 言語 | URL | ファイル | 役割 |
| --- | --- | --- | --- |
| 英語 | `/security-light.html` | `security-light.html` | 無料Security Light機能 |
| ドイツ語 | `/de/security-light.html` | `de/security-light.html` | ドイツ語版 |
| スペイン語 | `/es/security-light.html` | `es/security-light.html` | スペイン語版 |
| 日本語 | `/ja/security-light.html` | `ja/security-light.html` | 日本語版 |

### 4.4 当て逃げ・ドラレコ比較

| 言語 | URL | ファイル | 役割 |
| --- | --- | --- | --- |
| 英語 | `/parking-lot-hit-and-run-evidence.html` | 同名HTML | 英語の当て逃げ証拠ガイド |
| 日本語 | `/ja/parking-lot-hit-and-run-evidence.html` | 同名HTML | 当て逃げ録画設定・元動画保全・被害後確認の補助ガイド |
| 英語 | `/dash-cam-parking-mode-alternative.html` | 同名HTML | 英語の専用ドラレコ代替比較 |
| 日本語 | `/ja/dash-cam-parking-mode-alternative.html` | 同名HTML | 「ドラレコ アプリ」担当。用途別比較 |

この2組にはドイツ語・スペイン語ページがありません。存在しない翻訳URLをhreflangや言語切替へ追加しません。

### 4.5 英語単独ガイド

| URL | ファイル | 検索意図 |
| --- | --- | --- |
| `/door-ding-evidence.html` | `door-ding-evidence.html` | ドアパンチの記録 |
| `/car-vandalism-evidence.html` | `car-vandalism-evidence.html` | 車へのいたずら記録 |
| `/spare-phone-car-security-camera.html` | `spare-phone-car-security-camera.html` | 余ったスマホの再利用 |
| `/parked-car-monitoring-app.html` | `parked-car-monitoring-app.html` | iPhone・Androidの駐車中監視 |

英語単独ページには、実在する翻訳ができるまでhreflangを付けません。

### 4.6 法務・確認用

| URL | ファイル | 扱い |
| --- | --- | --- |
| `/privacy-policy.html` | `privacy-policy.html` | プライバシーポリシー。index対象 |
| `/eula.html` | `eula.html` | EULA・利用条件。index対象 |
| `/googlec9b4c510fa66e954.html` | 同名HTML | Google所有権確認専用。sitemap対象外 |

Google確認ファイルはtitle、H1、canonicalを持たない例外です。通常ページへ作り替えたり削除したりしません。

## 5. 言語・URL・hreflang仕様

### 5.1 言語コード

| 表示言語 | ディレクトリ | `<html lang>` | hreflang |
| --- | --- | --- | --- |
| 英語 | ルート | `en-US` | `en-US` |
| ドイツ語 | `/de/` | `de-DE` | `de-DE` |
| スペイン語 | `/es/` | `es-ES` | `es-ES` |
| 日本語 | `/ja/` | `ja-JP` | `ja-JP` |

### 5.2 canonical

- 正規オリジンは必ず`https://blackshisa.com`です。
- `www.blackshisa.com`をcanonicalへ使いません。
- 通常ページは必ず自己参照canonicalを1件持ちます。
- `/ja/index.html`のcanonicalは`https://blackshisa.com/ja/`です。
- URLを移す場合、canonicalだけを別URLへ向けて本文を残す運用はしません。移管が必要なら301の可否と既存検索データを先に確認します。

### 5.3 hreflangクラスター

| ページ群 | 必須alternate |
| --- | --- |
| ホーム4言語 | `en-US`、`de-DE`、`es-ES`、`ja-JP`、`x-default` |
| Parking mode 4言語 | 同上 |
| Security Light 4言語 | 同上 |
| Hit-and-run英日 | `en-US`、`ja-JP`、`x-default` |
| Dash-cam英日 | `en-US`、`ja-JP`、`x-default` |
| 英語単独・法務 | なし |

`x-default`は英語URLです。alternateはHTMLと`sitemap.xml`で同じ集合にします。

翻訳追加時は、次を同じ変更で行います。

1. 翻訳HTMLを追加する。
2. 全クラスター構成員のheadへ新言語alternateを追加する。
3. 新ページにも全構成員へのalternateを追加する。
4. `sitemap.xml`の全構成員へ同じalternate集合を反映する。
5. `tool/check_site.py`で相互性を確認する。

## 6. ページテンプレート

現サイトはテンプレートエンジンを使いませんが、HTML構造上は次の4系統があります。

### 6.1 製品ホーム

対象: 4言語の`index.html`

標準構成:

1. sticky header、ブランド、主要ナビ、言語切替
2. hero、製品説明、CTA、信頼情報
3. スクリーンショットストリップとlightbox
4. セットアップ
5. 証拠記録の要点
6. Parking mode導線
7. 仕組み・利用例
8. 検知機能
9. Security Light導線
10. プライバシー
11. 制約・熱・OS差
12. FAQ
13. 料金・Google Play導線
14. footer

日本語ホームだけは重点SEOのため、運営者・確認方法と重点3テーマ導線を追加しています。別言語へ機械翻訳して同じSEO設計を移植しません。

### 6.2 実践ガイド

対象: Parking mode、hit-and-run、dash-cam比較、英語単独ガイド

重点日本語ガイドの標準構成:

1. headerと関連ページ導線
2. breadcrumb
3. hero、H1、lede、更新日、要点chip、重点内部リンク
4. 3枚のsummary card
5. 作成方法・未実測事項のeditorial note
6. 本文articleとsticky side panel
7. 必要に応じ比較表・一次資料
8. visible FAQ
9. 関連3ページ
10. CTA
11. footer

比較表は`.guide-comparison-wrap`の中に置きます。表自体の最小幅は860pxとし、狭い画面ではページ全体ではなくwrapperだけを横スクロールさせます。

### 6.3 Security Light

対象: 4言語の`security-light.html`

- 共通`assets/css/styles.css`に加え`assets/css/security-light.css`を読み込みます。
- hero写真、無料機能の説明、利用手順、無料・有料比較、安全注意、Google Play CTAで構成します。
- 課金画面は日本語だけ`paywall-ja.jpg`、それ以外は`paywall-us.jpg`を使用します。
- ストア価格は地域で変わるため、画像の価格が全地域の価格だと断定しません。

### 6.4 法務ページ

対象: `privacy-policy.html`、`eula.html`

- `body.legal-page`、`.legal-hero`、`.legal-layout`、`.legal-toc`、`.legal-card`を使います。
- 法務本文の変更はデザイン変更と分け、効力発生日と連絡先を確認します。
- 表は`.legal-table-wrap`で囲み、狭幅で横スクロール可能にします。

### 6.5 共通UIはテンプレート化されていない

現在のheader、言語切替、footerはページ種別ごとに少しずつ異なります。

| ページ群 | header・言語切替の現状 | footerの現状 |
| --- | --- | --- |
| 英語ホーム | Features、Security Light、Guides、Privacy、FAQ、4言語 | 4言語、Privacy、EULA |
| DE/ESホーム | Features、Security Light、Privacy、FAQ、4言語 | 4言語、Privacy、EULA |
| 日本語ホーム | 機能、Security Light、駐車監視アプリ、Privacy、FAQ、4言語 | 4言語、Privacy、EULA |
| Security Light | ページ内導線、ホーム、4言語 | ホーム、Privacy、EULA |
| EN/DE/ES Parking mode | ホーム、Features、Privacy、4言語 | ホーム、Privacy、EULA |
| 日本語Parking mode | ホーム、ドラレコ比較、機能、4言語 | ホーム、駐車監視アプリ、Privacy |
| 英語ガイド | ホーム、Features、Guides、Privacy | ホーム、Guides、Privacy、EULA |
| 日本語hit-and-run・dash-cam | ホーム、駐車監視アプリ、機能、EN/JA | ホーム、駐車監視アプリ、Privacy |
| 法務 | Features、Privacy、EULA | ホーム、Privacy、EULA |

EN/JA hreflangを持つ英語hit-and-run・dash-camページは、headで相互参照しますが、狭幅headerのoverflowを避けるため表示上の日本語切替を置いていません。hreflangと可視言語切替は別の仕組みです。

日本語重点ガイドのfooterには現在EULAリンクがありません。将来footerを統一する場合は、全ページを機械置換せず、ルート階層ごとの相対URLと390px表示を確認します。

## 7. 共通デザイン仕様

### 7.1 デザイントークン

`assets/css/styles.css`の`:root`が正本です。

| 用途 | 変数 | 現在値 |
| --- | --- | --- |
| 背景 | `--bg` | `#030303` |
| やや明るい背景 | `--bg-soft` | `#090909` |
| パネル | `--panel` | `#111113` |
| 主文字 | `--text` | `#f7f4ea` |
| 補助文字 | `--muted` | `#a8a8ad` |
| ゴールド | `--gold` | `#d4a640` |
| 明るいゴールド | `--gold-bright` | `#f2d27a` |
| コンテンツ最大幅 | `--max` | `1180px` |

外部Webフォントは読み込みません。Apple・Windowsのシステムフォントスタックを使います。

### 7.2 レスポンシブ境界

- 主要タブレット境界: `920px`
- 主要モバイル境界: `640px`
- 最低確認幅: `390px`、高さ`844px`
- `.guide-article { min-width: 0; }`を維持します。
- 小画面の`.guide-layout`は`minmax(0, 1fr)`です。
- 比較表以外で`documentElement.scrollWidth > clientWidth`を発生させません。

### 7.3 ナビゲーション

- headerはsticky、標準高さ64pxです。
- モバイルで省略可能なリンクには`.hide-small`を付けます。
- ブランドと4言語切替を同時に置くため、狭幅でリンクを増やす場合は必ず実表示を確認します。
- 現在言語は`.active`と`aria-current="page"`で示します。
- ナビ項目を追加するだけでも横overflowが起き得るため、CSSの見た目だけで判断しません。

## 8. JavaScript仕様

サイト固有JavaScriptは`assets/js/screen-lightbox.js`だけです。

### 8.1 lightboxのDOM契約

- lightbox root: `[data-screen-lightbox]`
- 拡大画像: `[data-lightbox-image]`
- 閉じるボタン: `[data-lightbox-close]`
- 起動ボタン: `.screen-open`
- 元画像URL: 起動ボタンの`data-full`

### 8.2 操作契約

- クリックで拡大します。
- Escapeで閉じます。
- 左右矢印キーで前後移動します。
- タッチの横スワイプで前後移動します。
- 閉じた後は起動したボタンへfocusを戻します。
- 背景クリックで閉じます。
- lightboxがないページでは何もせず終了します。

JavaScriptへページ固有のSEO本文を持たせません。主要コンテンツとリンクはHTMLへ直接記述します。

## 9. 画像・メディア仕様

### 9.1 ロゴの役割

| ファイル | 寸法 | 用途 |
| --- | --- | --- |
| `blackshisa-logo-nav.webp` | 64×64 | ナビ用。軽量 |
| `blackshisa-logo-mark.webp` | 1024×1024 | 日本語ホームhero装飾 |
| `blackshisa-favicon.jpg` | 64×64 | favicon |
| `blackshisa-apple-touch.jpg` | 180×180 | Apple touch icon |
| `blackshisa-logo.jpg` | 1024×1024 | 既存OG、manifest、旧ページ互換 |
| `blackshisa-logo.png` | 1024×1024 | 既存原本。参照確認後でなければ削除しない |

### 9.2 日本語重点ページの軽量画像

| ファイル | 寸法 | 主用途 |
| --- | --- | --- |
| `monitoring_jp.webp` | 942×2048 | 監視画面・ガイドhero |
| `events_jp.webp` | 853×1844 | イベント一覧 |
| `home_jp.webp` | 1320×2868 | ホーム画面 |
| `setting_jp.webp` | 1320×2868 | 設定画面 |
| `details_jp.webp` | 942×2048 | 詳細画面 |
| `flash.webp` | 1536×1024 | ライト利用例 |
| `use-case01.webp` | 1536×1024 | 昼の利用例 |
| `use-case02.webp` | 1536×1024 | 夜の利用例 |
| `security-light/parked-car.webp` | 1536×1024 | Security Light導線 |

旧PNG・JPEGは英語、ドイツ語、スペイン語や拡大元で現在も使われます。ファイルサイズが大きいという理由だけで一括削除しません。削除前に`rg`で全HTML/CSS/JSからの参照が0件であることを確認します。

### 9.3 新しい画像の受け入れ条件

- 写真・スクリーンショットは原則WebPを使用します。
- HTMLの`width`と`height`へ画像固有寸法を入れます。
- below-the-fold画像は原則`loading="lazy" decoding="async"`です。
- そのページのLCP候補はlazyにせず、必要な場合だけ`fetchpriority="high"`を付けます。
- 情報画像には内容を説明するaltを付けます。
- 装飾画像は`alt=""`とし、必要なら親を`aria-hidden="true"`にします。
- 同じ情報を示さない画像へ既存altをコピーしません。
- 画像差し替え後はOG/Twitter画像、JSON-LD image、lightbox `data-full`も確認します。

### 9.4 画像資産の保守状況

2026-08-13時点の画像50件は合計32,005,818 bytesです。内訳はPNG 24件、`.jpeg` 8件、`.jpg` 7件、WebP 11件です。日本語重点ページはWebP化済みですが、英語・ドイツ語・スペイン語の旧ページには大きなPNG/JPEGが残ります。

次の8件はHTML/CSS/JavaScriptから参照されていませんが、原本または移行前資産の可能性があるため自動削除しません。

- `home_jp.jpeg`
- `setting_jp.jpeg`
- `events_jp.png`
- `details_jp.png`
- `monitoring_jp.png`
- `monitoring-off_JP.png`
- `monitoring-on-bike_jp.png`
- `icon-record-videocam.png`

内容が同じ別名ファイルもあります。`details_jp.png`と`monitoring_jp.png`、`details_jp.webp`と`monitoring_jp.webp`、`monitoring_en.png`と`monitoring_vertical_cart_contact.png`は監査時のSHA-256が一致しました。整理する場合は、参照先を先に統一し、checkerと全ページ表示を確認してから別タスクで削除します。

## 10. SEO基本契約

### 10.1 index対象ページのhead

通常ページは次を満たします。

- 正しい`<html lang>`
- `<title>`が1件
- 非空のmeta descriptionが1件
- 自己参照canonicalが1件
- visible H1が1件
- 必要なページだけ相互hreflang
- Open Graph metadata
- 法務以外のコンテンツページはTwitter metadata
- ページ内容と一致するJSON-LD
- `robots`は原則`index,follow,max-image-preview:large`

title、meta description、OG title/description、Twitter title/description、JSON-LD headline/description、visible H1は文字列を完全一致させる必要はありませんが、ページの役割と主張を矛盾させません。

### 10.2 構造化データ

| ページ種別 | 主な型 |
| --- | --- |
| 製品ホーム | `SoftwareApplication`、`FAQPage` |
| Security Light | `WebPage`、`WebSite` |
| 重点日本語ガイド | `WebPage`、`Article`、`BreadcrumbList`、`FAQPage` |
| 既存英語ガイド | `WebPage`、`Article`、`BreadcrumbList`、`FAQPage` |
| 法務 | 現在はJSON-LDなし |

重点日本語ガイドでは次を維持します。

- WebPageとArticleの`url`はcanonicalと同じです。
- `inLanguage`は`ja-JP`です。
- `mainEntity`と`mainEntityOfPage`でWebPageとArticleを接続します。
- author/publisherは`ICHITAP`です。
- visible FAQとFAQPageの質問・回答を同期します。
- BreadcrumbListの末尾は現在ページです。

visible FAQは利用者向けコンテンツとして維持します。FAQ構造化データだけを増やすことをSEO施策の目的にしません。

### 10.3 日付

- visible `<time>`とArticleの`dateModified`は本文を最後に実質レビューした日です。
- `sitemap.xml`の`lastmod`は検索に意味のある本文またはmetadataを最後に変更した日です。
- 本文を変えた場合はvisible time、Article dateModified、article modified metadata、sitemap lastmodを同日にそろえます。
- hreflangなどmetadataだけを変更した場合、sitemap lastmodだけが新しくなることは許容します。
- 単なる再ビルド・再保存の日をlastmodへ使いません。

## 11. 日本語重点3キーワードのURL所有権

この章は日本語検索だけの契約です。他言語へ機械的に一般化しません。

| 検索意図 | 担当URL | ページの仕事 |
| --- | --- | --- |
| `駐車監視 アプリ` | `/ja/parking-mode-app.html` | 4種類の「駐車監視」を分類し、BlackShisaの設定と制約を説明 |
| `当て逃げ監視 アプリ` | `/ja/` | 製品、機能、料金、導入判断の中心 |
| `ドラレコ アプリ` | `/ja/dash-cam-parking-mode-alternative.html` | 走行録画・駐車監視・車載機連携を比較 |

`/ja/parking-lot-hit-and-run-evidence.html`は、当て逃げに備える録画設定、元動画保全、被害後の相談を詳しく説明する補助ページです。「当て逃げ監視 アプリ」の主担当ではありません。

### 11.1 内部リンク規則

- exactに近い「当て逃げ監視アプリ」アンカーは`/ja/`へ集約します。
- 「駐車監視アプリ」は`/ja/parking-mode-app.html`へ集約します。
- 「ドラレコアプリ比較」「専用ドラレコとの違い」は`/ja/dash-cam-parking-mode-alternative.html`へ送ります。
- 補助ページへのアンカーは「録画設定と被害後の確認」など、補助タスクを表す文言にします。
- 3語を全ページのtitle/H1へ詰め込みません。
- 同じ検索意図の新規ページを増やす前に、担当URLへ追記できないかを確認します。

### 11.2 URLを変更しない理由

2026-08-13の単発Google観測では、`/ja/parking-mode-app.html`が「駐車監視 アプリ」で可視通常リンク通算23本目、`/ja/`が「当て逃げ監視 アプリ」で3位でした。これは恒久順位ではありませんが、既存シグナルを持つURLを理由なく削除・改名・301しない根拠です。詳細は`seo/AUDIT-JA-3KEYWORDS-2026-08-13.md`を参照します。

公開後はSearch Consoleで28日・90日を比較し、クエリごとの担当外URL混在を確認します。単発順位だけでURLを移管しません。

## 12. 製品事実とコンテンツ安全

Webサイトはアプリ実装より先に機能を発明してはいけません。製品仕様の正本は隣接リポジトリ`blackshisa_app`の現行コードと、実際に公開されているストア情報です。

### 12.1 現在記載できる要点

- BlackShisaは、画像変化、音、端末へ伝わる衝撃をきっかけにイベントを記録します。
- 画像変化は人物認識ではありません。人、車、自転車、カートなどによる画面内変化を扱います。
- 検知前録画は最大3秒です。
- Androidも、監視開始直後など利用可能な事前バッファが不足すれば3秒未満になります。
- iPhoneは通常3秒ですが、低メモリモードまたは一部4K端末条件では約1秒になります。
- 検知後録画は10秒、30秒、60秒から選択します。
- ファイルは端末内保存が先です。
- Google DriveバックアップとGmail通知は任意で、アカウント設定と通信条件があります。
- iPhoneはアプリを前面表示し、画面を点灯した状態で監視します。
- Androidは権限・端末設定の影響を受けるforeground serviceを使います。
- スマホ1台で撮れるのは一方向です。
- 高温が見込まれる車内では使用しません。

### 12.2 禁止する断定

- 「人物をAI検知する」
- 「検知前3秒を必ず残す」
- 「20mまで検知する」など未検証距離
- 「低RAMは一律2GB以下」
- 「当て逃げを防止する」
- 「犯人やナンバーを必ず特定できる」
- 「必ず証拠として採用される」
- 「全周を監視できる」
- 「専用ドラレコを完全に代替する」
- 未計測の検知率、誤検知率、電池消費、端末温度、判読率

「証拠」「監視」という語を使う場合も、撮影成功・判読・証拠能力を保証しない条件を近くに記載します。

### 12.3 変動情報

次は更新のたび一次情報を確認します。

- BlackShisaの価格と無料期間
- 配信OS、対応要件、公開状態
- Google Play URLとpackage ID
- 他社アプリの価格、OS、機能、更新日
- Apple・Google・Android・国土交通省などの案内URL
- 法律・プライバシー・保険・警察手続

比較記事には確認日、公式出典、BlackShisa運営者による比較であること、他社アプリを実機評価していない場合はその事実を表示します。

## 13. アクセシビリティ契約

- 1ページ1 H1です。
- `header`、`nav`、`main`、`footer`を使います。
- 言語切替、パンくず、lightboxに意味のある`aria-label`を付けます。
- 現在ページ・現在言語は`aria-current`で示します。
- FAQはnativeの`details`と`summary`を使います。
- 比較表の見出しは`th scope="col"`です。
- キーボードfocusが見える状態を維持します。
- `prefers-reduced-motion`で不要な動きを抑えます。
- 画像altは用途に合わせます。
- 色だけで状態を伝えません。

現状はskip linkや完全なfocus trapを実装していないため、「WCAG完全準拠」とは表現しません。

## 14. クローラー・発見性ファイル

### 14.1 robots.txt

現行契約:

```text
User-agent: *
Allow: /

Sitemap: https://blackshisa.com/sitemap.xml
```

公開前確認用だからという理由で本番`robots.txt`をDisallowへ変更しません。テストはローカルサーバーまたは非公開ブランチで行います。

### 14.2 sitemap.xml

- index対象22 URLを1回ずつ列挙します。
- canonical URLと完全一致させます。
- Google所有権確認ファイルは含めません。
- hreflangを持つページはHTMLと同じalternate集合を持ちます。
- ページ追加・削除・URL変更・検索に意味のある更新と同時に変更します。
- `tool/check_site.py`はcanonical集合とsitemap集合の完全一致を検査します。

### 14.3 llms.txt

- BlackShisaの短い説明、主要機能、主要ページ、Google Play、robots、sitemapを記載します。
- 「顔やナンバーを必ず読める」など保証表現を入れません。
- index対象22ページのうち法務2ページをPages一覧から除き、主要コンテンツ20ページを載せています。
- Resourcesとしてrobotsとsitemapを載せるため、BlackShisaドメインのunique URLは合計22件です。
- 新しい主要ページを追加・削除したときは同じPull Requestで更新します。

### 14.4 manifestとGoogle確認

- `site.webmanifest`は正しいJSONでなければなりません。
- manifestのname、theme color、iconのパス・寸法を実ファイルと一致させます。
- `googlec9b4c510fa66e954.html`は所有権確認用なので保持します。

## 15. 40ガイド生成案との境界

別ブランチ`agent/multilingual-seo`には、10 topic×4言語の40ガイド、4ハブ、`seo/topics.json`、`seo/generate.py`、`seo/SPEC.md`、`tool/check_seo.py`があります。

これらは現行重点3キーワード版に含まれません。理由は次のとおりです。

- 一度に40ページを公開すると、検索語違いの類似ページ量産と見なされるリスクがある。
- 実機検証・独自画像・地域別法務・ネイティブレビューがページ数に追いついていない。
- 現行重点版とURL所有権、breadcrumb、hreflang、sitemap、llmsの前提が異なる。
- generatorは40ガイドと4ハブを所有するため、focused版で実行すると非採用ページを再生成する。

禁止事項:

- 現行ブランチへ`seo/generate.py`だけをコピーして実行しない。
- 40ガイド生成物の一部だけを手動コピーしない。
- DE/ESの存在しないURLをhreflangへ復活させない。
- focused版の`sitemap.xml`を生成版で上書きしない。

focused版のcheckerは、生成ページだけでなく次の40ガイド専用ファイルが存在してもREDにします。

- `seo/generate.py`
- `seo/topics.json`
- `seo/SPEC.md`
- `tool/check_seo.py`
- `.github/workflows/seo.yml`
- `worklog.yaml`

将来、生成型を正式採用する場合は、この禁止リストを単に削るのではなく、サイト構成、正本、生成ゲート、URLインベントリ、公開手順を本仕様書とcheckerで同時に置き換えます。

将来40ガイド案を採用する場合は、公開判断、一次成果物、全言語レビュー、プライバシー確認、独立SEOレビューを別タスクとして完了し、手編集型から生成型へ運用方式を明示的に切り替えます。

## 16. 更新作業の標準手順

### 16.1 初回公開前の引き継ぎ

2026-08-13時点では、focused版の実装と本仕様書はローカル`agent/ja-three-keyword-seo`にあり、`origin/main`は旧サイトです。初回公開前に新しい担当者が`origin/main`からブランチを作ると、focused版、README、checker、CIを持たない状態へ戻ります。

初回だけは、共有workspaceにある現在のブランチをそのまま検証し、pushしてPull Requestを作成します。

```bash
git switch agent/ja-three-keyword-seo
git status --short --branch
git log --oneline origin/main..HEAD

env PYTHONDONTWRITEBYTECODE=1 python3 tool/check_site.py
git diff --check origin/main..HEAD
xmllint --noout sitemap.xml

git push -u origin agent/ja-three-keyword-seo
gh pr create --draft --base main --head agent/ja-three-keyword-seo
```

PRには重点3キーワード実装と本引き継ぎ仕様を含めます。Pages公開と本番smoke testが完了したら、2.1の本番コミット・公開状態とREADMEの「現在の引き継ぎ状態」を同じ変更で現況へ更新します。その後は次の通常手順へ切り替えます。

### 16.2 通常の着手

```bash
git fetch origin --prune
git switch -c <work-branch> origin/main
git status --short --branch
```

次を最初に確認します。

- 本番`main`から分岐しているか
- 無関係な未コミット変更がないか
- 変更対象URLの現在のcanonicalとSearch Console情報
- 同じ検索意図の担当ページが既にないか
- アプリ仕様・価格・外部資料の再確認が必要か

### 16.3 既存ページを更新する場合

1. visible本文を更新する。
2. title、description、OG、Twitter、JSON-LDを意味整合させる。
3. visible FAQを変えたらFAQPageも更新する。
4. 本文変更ならvisible timeとArticle dateModifiedを更新する。
5. sitemap lastmodを更新する。
6. 必要ならllmsを更新する。
7. CSS/JS URLのcache-busting queryを実変更時だけ更新する。
8. 内部リンクの担当URLを確認する。

### 16.4 新しいページを追加する場合

1. 新規ページが既存ページと異なる利用者タスクを完了するか説明する。
2. URL、言語、検索意図、担当ページを決める。
3. 既存templateからHTMLを作る。
4. title、description、canonical、H1、OG、Twitter、JSON-LDを追加する。
5. ホームまたは関連ページから可視リンクを追加し、孤立させない。
6. 翻訳が実在する場合だけ相互hreflangを全メンバーへ追加する。
7. sitemapへ追加する。
8. 主要ページならllmsへ追加する。
9. 意図した構造変更として`tool/check_site.py`の`EXPECTED_PUBLIC_URLS`と翻訳クラスターも更新する。checkerは事故による削除・追加を検知するため、現行22 URLを明示的に固定している。
10. デスクトップ幅と390px幅で表示確認する。

### 16.5 ページ削除・URL変更

SEOシグナルを失う可能性があるため、通常更新より高リスクです。

- Search Consoleのクエリ・クリック・外部リンクを確認します。
- 新旧URLの役割を決めます。
- GitHub Pages単体では任意の301設定を管理しにくいため、削除前にリダイレクト方式を確定します。
- canonicalだけを新URLへ向けて旧本文を残しません。
- 全内部リンク、hreflang、sitemap、llmsを同時更新します。
- 変更後に旧URLの意図した応答を本番確認します。

## 17. ローカル検証

### 17.1 必須コマンド

```bash
env PYTHONDONTWRITEBYTECODE=1 python3 tool/check_site.py
git diff --check
xmllint --noout sitemap.xml
```

`site.webmanifest`を変更した場合:

```bash
jq empty site.webmanifest
```

`tool/check_site.py`は次を検査します。

- 通常ページの言語階層、title、description、robots、H1、canonical
- canonicalのURL・重複
- JSON-LDのJSON構文
- 重複ID
- HTMLのローカルhref、src、srcset、poster、lightbox `data-full`の実在
- CSSのローカル`url()`参照
- ローカルfragmentの実在
- hreflangの重複、自己参照、対象言語、target、相互性
- 現行22 URLと定義済み翻訳クラスターからの意図しない増減
- ホームから可視リンクで到達でき、2クリック以内であること
- sitemapとcanonical全件の完全一致
- sitemap hreflangとHTML hreflangの一致
- llmsの主要ページURL集合
- CNAME、厳密なrobots全許可契約、manifestとmanifest参照先
- ローカル参照がリポジトリ外へ脱出せず、実ファイルを指すこと
- 40ガイド専用generator・topics・workflow・worklogがfocused版へ混入していないこと

ネットワークやGoogle順位は検査しません。

### 17.2 ローカルサーバー

```bash
python3 -m http.server 8765
```

確認URL: `http://127.0.0.1:8765/`

必須目視:

- 変更ページのtitle、H1、主要本文
- ナビ、言語切替、内部リンク、footer
- 画像表示とaltの妥当性
- 390×844で文書全体の横overflowがないこと
- 比較表だけがwrapper内で横スクロールすること
- lightboxの開閉、Escape、矢印、focus return
- Browser Consoleにerror/warningがないこと
- 外部一次資料とストアリンクが有効なこと

### 17.3 検査を通すためにしてはいけないこと

- 存在しないリンクをcheckerの除外リストへ足す。
- canonicalやsitemap検査を緩める。
- Google確認ファイル以外の通常ページを検査対象外にする。
- broken fragmentを`#`だけに置き換えて隠す。
- JSON-LDを削除してエラーを回避する。

## 18. GitHub Actions

`.github/workflows/site-integrity.yml`がPull Requestと`main` pushで`tool/check_site.py`と`git diff --check`を実行します。checkoutは全履歴を取得し、PRではbase SHAからhead SHA、pushではeventのbefore SHAからhead SHAまでを検査するため、複数コミットをまとめて反映しても全差分が対象です。

ただし、2026-08-13時点では`main`にbranch protection・ruleset・必須レビューが設定されていません。Actionsが赤でも直接pushを技術的には止められないため、運用上は必ずPull Requestを使います。可能ならGitHub設定で次を有効化します。

- `main`へのPull Request必須
- `site-integrity`必須
- 1名以上のレビュー
- force-push禁止

## 19. 公開手順

### 19.1 Pull Request

```bash
git push -u origin <work-branch>
gh pr create --draft --base main --head <work-branch>
```

Pull Request本文へ次を記録します。

- 変更したURLと目的
- title/H1/canonical/hreflangの変更
- 製品事実の確認元
- sitemap/llmsの変更
- `tool/check_site.py`結果
- デスクトップ・390px表示結果
- 公開後に確認するURL

レビュー後にsquash mergeを推奨します。`main`への反映はGitHub Pagesの本番公開を開始します。

### 19.2 Pagesジョブ確認

```bash
gh run list \
  --repo yom201/blackshisa-web \
  --workflow pages-build-deployment \
  --branch main \
  --limit 5 \
  --json databaseId,headSha,status,conclusion,url

gh run watch <run-id> --exit-status

gh api repos/yom201/blackshisa-web/pages/builds/latest \
  --jq '{status,commit,error,created_at,updated_at}'
```

Pages最新buildのcommitがマージ後の`main` HEADと一致することを確認します。Pagesのsuccessはリンク・SEO・表示の正しさを保証しません。

### 19.3 本番smoke test

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://blackshisa.com/
curl -sS -o /dev/null -w '%{http_code}\n' https://blackshisa.com/robots.txt
curl -sS -o /dev/null -w '%{http_code}\n' https://blackshisa.com/sitemap.xml
curl -sS -o /dev/null -w '%{http_code}\n' <changed-url>
```

本番ブラウザでも変更ページを確認します。現在のPages応答は`cache-control: max-age=600`が観測されているため、公開直後は最大10分程度、旧ファイルが見える可能性を考慮します。

## 20. ロールバック

内容不良は履歴を破壊せずrevertします。

```bash
git switch main
git pull --ff-only origin main

# squashまたは通常の単一コミット
git revert <published-commit-sha>

# merge commitの場合
git revert -m 1 <merge-commit-sha>

git push origin main
```

その後、Pagesジョブと本番URLを再確認します。`git reset --hard`やforce-pushを本番復旧手段にしません。内容が正しくPagesだけが一時失敗した場合に限り、既存ジョブを再実行します。

## 21. GitHub Pages・DNS契約

- GitHub Pages source: `main` / `/`
- Custom domain: `blackshisa.com`
- HTTPS: enforced
- `CNAME`内容: `blackshisa.com`
- apex DNS: GitHub Pages向けAレコード
- `www`: `yom201.github.io`へCNAMEし、apexへ301
- `404.html`: 現在なし。GitHub標準404

DNSはGit管理外です。ドメイン変更時はDNS、GitHub Pages設定、`CNAME`、canonical、hreflang、OG URL、sitemap、robots、manifestを一体で変更します。

GitHub Pagesのドメイン所有権確認TXTは2026-08-13の監査で確認できませんでした。GitHub個人設定のPages domain verificationを別途確認し、設定済みならTXTを保持します。

## 22. 既知の制約と今後の改善候補

| 項目 | 現状 | 更新時の判断 |
| --- | --- | --- |
| カスタム404 | なし | 必要なら独立タスクで`404.html`を追加 |
| branch protection | なし | `site-integrity`必須化を推奨 |
| CI | 本仕様で整合性Actionsを追加 | Pages成功とは別に扱う |
| sitemap | 手編集 | focused版ではcheckerで同期を強制 |
| 生成系 | 非採用40ガイド案のみ | focused版へ混ぜない |
| Search Console自動取得 | なし | 順位判断はGSC 28/90日で人が確認 |
| アクセシビリティ | 基本対応 | WCAG完全準拠とは未確認 |
| 他言語画像 | 旧PNG/JPEGが大きい | 参照を保ちながら段階的WebP化可能 |
| 旧多言語の録画秒数表現 | 一部に固定「3秒」の旧記述 | 「最大3秒、条件で短縮」と実装照合して別タスクで修正 |
| 共通部品 | HTMLへ重複記述 | 変更時はページ群と相対URLを明示して同期 |
| 未参照画像 | 8件を監査で確認 | 原本用途を確認せず削除しない |
| 法務ローカライズ | 英語法務ページのみ | 必要性と法務レビューを経て追加 |

## 23. 引き継ぎ時チェックリスト

新しい担当者は次を確認すれば作業を再開できます。

### 着手前

- [ ] `README.md`と本仕様書を読んだ
- [ ] `origin/main`から作業ブランチを作った
- [ ] 変更対象URLと検索意図を確認した
- [ ] 3キーワードの担当URLを侵食しない
- [ ] 製品事実・価格・外部出典を確認した
- [ ] 40ガイド生成案を混ぜていない

### 編集後

- [ ] 1 H1、title、description、canonicalが正しい
- [ ] 実在翻訳だけ相互hreflangを持つ
- [ ] visible本文とJSON-LDが矛盾しない
- [ ] FAQ本文とFAQPageが同期している
- [ ] 内部リンクが担当URLへ向いている
- [ ] 新画像に寸法、alt、lazy方針がある
- [ ] sitemap、llms、日付を必要に応じ更新した
- [ ] `tool/check_site.py`がGREEN
- [ ] `git diff --check`が成功
- [ ] 390×844とデスクトップで確認した
- [ ] Console errorがない

### 公開後

- [ ] Pages buildのcommitが`main` HEADと一致
- [ ] 変更URLが200
- [ ] canonical・hreflang・sitemapが本番でも正しい
- [ ] 削除URLが意図した応答
- [ ] Search ConsoleでURL検査
- [ ] 28日・90日後にクエリと担当URLを確認

## 24. 関連資料

- `README.md`: 更新者の入口
- `seo/AUDIT-JA-3KEYWORDS-2026-08-13.md`: 日本語3キーワードの順位・検索意図・担当URL決定
- `tool/check_site.py`: 現行focused版の機械検査
- `sitemap.xml`: index対象URLの正本一覧
- `llms.txt`: LLM向け主要ページ一覧
- `robots.txt`: crawler契約
- `site.webmanifest`: PWA metadata
- 隣接`blackshisa_app`: 製品機能の実装正本

この仕様書を更新せずにサイト構造、公開方式、検索意図の担当URLを変更しないでください。
