# BlackShisa website

BlackShisaの公式サイト `https://blackshisa.com` を構成する静的HTML/CSS/JavaScriptリポジトリです。
ビルドツールやCMSは使わず、GitHub Pagesが`main`ブランチのリポジトリ直下をそのまま配信します。

サイトを更新する前に、必ず[サイト全体仕様書](docs/SITE_SPEC.md)を読んでください。URL設計、多言語、SEO、構造化データ、画像、検証、公開、ロールバックまで同文書を正本とします。

## 現在の引き継ぎ状態

2026-08-27時点の公開候補は、重点3キーワード版を引き継いだローカル`codex/seo-rebuild-20260827`です。全22ページのmetadata、構造化データ、内部リンク、画像配信、モバイル表示、sitemap、検査ゲートを再構築していますが、まだ`origin/main`へpush・公開していません。[仕様書の初回公開手順](docs/SITE_SPEC.md#161-初回公開前の引き継ぎ)に従い、このブランチをPull Request経由で反映してください。`origin/main`から作り直すと、未公開の重点版と今回の再構築を失います。

重点版が`main`へ反映された後は、次が通常の更新手順です。

## 通常の更新手順

```bash
git fetch origin --prune
git switch -c <work-branch> origin/main

# HTML/CSS/画像などを編集

env PYTHONDONTWRITEBYTECODE=1 python3 tool/check_site.py
git diff --check
xmllint --noout sitemap.xml
python3 -m http.server 8765
```

ブラウザで`http://127.0.0.1:8765/`を開き、変更ページをデスクトップ幅と390px幅で確認します。確認後は作業ブランチをpushし、Pull Request経由で`main`へ反映します。`main`への反映はそのまま本番公開になるため、直接pushは原則行いません。

## 重要な現状

- 正規ドメインは`https://blackshisa.com`です。`www`は正規URLにしません。
- index対象は22ページです。別にGoogle Search Console所有権確認用HTMLが1件あります。
- 22 URLと翻訳クラスターは`tool/check_site.py`にも固定されています。URLを意図的に追加・削除する場合は、HTML・仕様書・checker・sitemap・llmsを同じ変更で更新します。
- 全通常ページは固有のtitle・description・OG/Twitter metadata、author、画像寸法を持ちます。ホームはOrganization/WebSite/SoftwareApplication/FAQPage、ガイドはWebPage/Article/BreadcrumbList/FAQPageを必須とします。
- 実行時に参照するローカル画像34件のうち30件はWebPです。参照画像に300 KB超を混ぜるとcheckerが失敗します。原本画像は削除していません。
- 日本語SEOは「駐車監視 アプリ」「当て逃げ監視 アプリ」「ドラレコ アプリ」の3検索意図をそれぞれ別URLへ割り当てています。
- `agent/multilingual-seo`にある40ガイド生成案は、現行サイト仕様に含まれません。生成スクリプトや生成ページを現在の構成へ混ぜないでください。
- アプリ機能、価格、無料期間、ストア情報は変動します。サイトの記述を更新する前に、アプリ実装と公式ストアを再確認してください。

## 主な入口

- [サイト全体仕様書](docs/SITE_SPEC.md)
- [日本語重点3キーワード監査](seo/AUDIT-JA-3KEYWORDS-2026-08-13.md)
- [全サイト整合性検査](tool/check_site.py)
- [サイトマップ](sitemap.xml)
- [クローラー設定](robots.txt)
- [LLM向けページ一覧](llms.txt)

このリポジトリはGitHub Pagesでそのまま公開されます。認証情報、個人情報、内部限定資料をコミットしないでください。
