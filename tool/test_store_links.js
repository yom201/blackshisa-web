#!/usr/bin/env node
// store-links.js を本物の HTML のリンクに当てて、広告の印と記録の本文を確かめる。
// 契約＝../blackshisa_work/docs/quality/契約_20261004_広告の計測をキャンペーン別にする.md §4
// 期待値＝../blackshisa_work/tool/fixtures/ad_attribution_chain.json（全区間で共有）
//
// 走らせ方＝`node tool/test_store_links.js`（このリポの直下で）

'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '..');
const SCRIPT = fs.readFileSync(path.join(ROOT, 'assets/js/store-links.js'), 'utf8');
const FIXTURE_PATH = path.resolve(ROOT, '../blackshisa_work/tool/fixtures/ad_attribution_chain.json');
const FIXTURE = JSON.parse(fs.readFileSync(FIXTURE_PATH, 'utf8'));
const ORIGIN = 'https://blackshisa.com';

function decodeEntities(s) {
  return s.replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'");
}

function pageFile(pathname) {
  let rel = pathname.replace(/^\//, '');
  if (rel === '' || rel.endsWith('/')) rel += 'index.html';
  return path.join(ROOT, rel);
}

function anchorsOf(file) {
  const html = fs.readFileSync(file, 'utf8');
  const lang = (/<html[^>]*\blang="([^"]*)"/i.exec(html) || [])[1] || '';
  const hrefs = [];
  const re = /<a\b[^>]*?\bhref="([^"]*)"/gi;
  let m;
  while ((m = re.exec(html)) !== null) hrefs.push(decodeEntities(m[1]));
  return { lang, hrefs };
}

function storeOf(href) {
  if (href.indexOf('://apps.apple.com/') !== -1) return 'ios';
  if (href.indexOf('://play.google.com/store/apps/') !== -1) return 'android';
  return '';
}

/** 本物のスクリプトを偽の DOM で動かす。 */
function run(pageUrl, opts = {}) {
  const url = new URL(pageUrl);
  const { lang, hrefs: pageHrefs } = anchorsOf(pageFile(url.pathname));
  const hrefs = pageHrefs.concat(opts.extra || []);
  const links = hrefs.map((h) => {
    const node = {
      tagName: 'A',
      _href: h,
      getAttribute: (k) => (k === 'href' ? node._href : null),
      setAttribute: (k, v) => { if (k === 'href') node._href = v; },
      parentNode: null,
    };
    Object.defineProperty(node, 'href', { get: () => new URL(node._href, url).href });
    return node;
  });
  const listeners = {};
  const beacons = [];
  const fetches = [];
  const document = {
    readyState: opts.loading ? 'loading' : 'complete',
    documentElement: { getAttribute: (k) => (k === 'lang' ? lang : null) },
    getElementsByTagName: (t) => (t === 'a' ? links : []),
    addEventListener: (type, fn) => { (listeners[type] = listeners[type] || []).push(fn); },
  };
  const navigator = {
    sendBeacon: (endpoint, blob) => {
      beacons.push(blob);
      return opts.beaconReturns === undefined ? true : opts.beaconReturns;
    },
  };
  const window = {
    fetch: (endpoint, init) => { fetches.push(init.body); return Promise.resolve(); },
  };
  const ctx = { document, navigator, window, location: { search: url.search, pathname: url.pathname }, Blob, JSON, RegExp, decodeURIComponent };
  vm.runInNewContext(SCRIPT, ctx);
  if (opts.loading) {
    for (const fn of listeners.DOMContentLoaded || []) fn();
  }
  async function click(link) {
    for (const fn of listeners.click || []) fn({ type: 'click', target: link });
    const bodies = [];
    for (const b of beacons) bodies.push(await b.text());
    return { beaconBodies: bodies, fetchBodies: fetches.slice() };
  }
  return { links, click, beacons, fetches };
}

function playReferrer(href) {
  const u = new URL(href);
  const raw = u.searchParams.get('referrer');
  return raw === null ? null : raw;
}

let checks = 0;
function eq(actual, expected, label) {
  assert.deepStrictEqual(actual, expected, label);
  checks++;
}

async function main() {
  // --- 固定ファイルの 7 本 ---------------------------------------------------
  for (const c of FIXTURE.cases) {
    const r = run(c.landing_url);
    const ios = r.links.filter((l) => storeOf(l._href) === 'ios');
    const play = r.links.filter((l) => storeOf(l._href) === 'android');
    assert.ok(ios.length > 0 && play.length > 0, `${c.name}: ページにストアリンクが無い`);
    for (const l of ios) {
      eq(new URL(l._href).searchParams.get('pt'), FIXTURE.pt, `${c.name}: App Store の pt ${l._href}`);
      if (c.ads) eq(new URL(l._href).searchParams.get('ct'), c.app_store_ct, `${c.name}: ct ${l._href}`);
      else assert.ok(/^web_/.test(new URL(l._href).searchParams.get('ct') || ''), `${c.name}: 自然流入の ct が変わった ${l._href}`);
    }
    for (const l of play) {
      const ref = playReferrer(l._href);
      if (c.ads) eq(ref, c.play_referrer, `${c.name}: Play の referrer ${l._href}`);
      else assert.ok(!/google_ads/.test(ref || ''), `${c.name}: 自然流入に広告の印 ${l._href}`);
    }
    const res = await r.click(play[0]);
    eq(res.beaconBodies.length, 1, `${c.name}: beacon は 1 回`);
    eq(JSON.parse(res.beaconBodies[0]), c.web_wire_body, `${c.name}: 送信本文`);
    eq(res.fetchBodies.length, 0, `${c.name}: beacon が受け付けたら fetch しない`);
  }

  // --- 読み込み中の分岐：読み込み済みと全リンク・クリックの本文が同じ ---------
  for (const c of FIXTURE.cases) {
    const done = run(c.landing_url);
    const loading = run(c.landing_url, { loading: true });
    eq(loading.links.map((l) => l._href), done.links.map((l) => l._href), `${c.name}: 読み込み中の分岐の全リンク`);
    const pick = (r) => r.links.find((l) => storeOf(l._href) === 'android');
    const a1 = await done.click(pick(done));
    const a2 = await loading.click(pick(loading));
    eq(a2.beaconBodies, a1.beaconBodies, `${c.name}: 読み込み中の分岐のクリックの本文`);
  }

  // --- beacon が false のとき、同じ本文で fetch を 1 回 ------------------------
  for (const c of FIXTURE.cases.filter((x) => x.ads)) {
    const r = run(c.landing_url, { beaconReturns: false });
    const play = r.links.find((l) => storeOf(l._href) === 'android');
    const res = await r.click(play);
    eq(res.fetchBodies.length, 1, `${c.name}: beacon=false で fetch 1 回`);
    eq(JSON.parse(res.fetchBodies[0]), c.web_wire_body, `${c.name}: fetch の本文`);
  }

  // --- 引き継ぎ：同じサイトの別ページへ移っても、同じ ad・cmp・src ------------
  for (const c of FIXTURE.cases.filter((x) => x.ads)) {
    const r = run(c.landing_url);
    let followed = 0;
    for (const l of r.links) {
      const h = l._href;
      if (storeOf(h)) continue;
      if (/^mailto:/i.test(h) || h.charAt(0) === '#') {
        assert.ok(!/utm_/.test(h), `${c.name}: 引き継いではいけないリンクに印 ${h}`);
        continue;
      }
      const target = new URL(h, c.landing_url);
      if (target.host !== 'blackshisa.com') {
        assert.ok(!/utm_content|gclid/.test(h), `${c.name}: 外部リンクに印 ${h}`);
        continue;
      }
      eq(target.searchParams.get('utm_content'), c.web_wire_body.ad, `${c.name}: 引き継いだ ad ${h}`);
      eq(target.searchParams.get('utm_campaign'), c.web_wire_body.cmp, `${c.name}: 引き継いだ cmp ${h}`);
      const file = pageFile(target.pathname);
      if (!fs.existsSync(file)) continue;
      const next = run(target.href);
      const play = next.links.find((x) => storeOf(x._href) === 'android');
      if (!play) continue;
      const res = await next.click(play);
      const body = JSON.parse(res.beaconBodies[0]);
      eq([body.src, body.ad, body.cmp], ['ads', c.web_wire_body.ad, c.web_wire_body.cmp], `${c.name}: 移った先 ${target.pathname} の本文`);
      eq(playReferrer(play._href), c.play_referrer, `${c.name}: 移った先 ${target.pathname} の referrer`);
      followed++;
    }
    assert.ok(followed > 0, `${c.name}: 移った先で確かめたページが 1 つも無い`);
  }

  // --- 印を付けてよいリンクと、付けてはいけないリンク --------------------------
  {
    const c = FIXTURE.cases.find((x) => x.name === 'de_app');
    const extra = [
      'https://example.com/page',
      'https://blackshisa.com.evil.example/de/',
      '//cdn.example.org/x',
      'mailto:support@blackshisa.com',
      'tel:+810000',
      '#faq',
      'https://www.blackshisa.com/de/',
      'https://blackshisa.com/es/',
      'security-light.html#top',
    ];
    const r = run(c.landing_url, { extra });
    const after = r.links.slice(r.links.length - extra.length).map((l) => l._href);
    for (let i = 0; i < 6; i++) eq(after[i], extra[i], `印を付けてはいけないリンク ${extra[i]}`);
    for (let i = 6; i < extra.length; i++) {
      const u = new URL(after[i], c.landing_url);
      eq([u.searchParams.get('utm_content'), u.searchParams.get('utm_campaign')], ['de_app', 'search_de'], `印を付けるリンク ${extra[i]}`);
    }
    eq(new URL(after[8], c.landing_url).hash, '#top', '印を付けても # は残る');
  }

  // --- 不正な値 --------------------------------------------------------------
  const base = 'https://blackshisa.com/de/parking-mode-app.html?utm_source=google&utm_medium=cpc';
  const invalid = [
    { q: '&utm_campaign=search_de&utm_content=%3Cscript%3E', ad: 'parking_mode_app', cmp: 'search_de', label: '<script>' },
    { q: '&utm_campaign=search_de&utm_content=' + 'a'.repeat(27), ad: 'parking_mode_app', cmp: 'search_de', label: '27 字' },
    { q: '&utm_campaign=search_de&utm_content=' + 'a'.repeat(26), ad: 'a'.repeat(26), cmp: 'search_de', label: '26 字ちょうど' },
    { q: '&utm_campaign=search_de&utm_content=DE_APP', ad: 'parking_mode_app', cmp: 'search_de', label: '大文字' },
    { q: '&utm_campaign=Search-DE&utm_content=de_app', ad: 'de_app', cmp: undefined, label: 'cmp だけ不正' },
  ];
  for (const t of invalid) {
    const r = run(base + t.q);
    const play = r.links.find((l) => storeOf(l._href) === 'android');
    const res = await r.click(play);
    const body = JSON.parse(res.beaconBodies[0]);
    eq([body.ad, body.cmp], [t.ad, t.cmp], `不正な値（${t.label}）の本文`);
    for (const l of r.links.filter((x) => storeOf(x._href) === 'ios')) {
      const ct = new URL(l._href).searchParams.get('ct');
      eq(ct, 'ads_' + t.ad, `不正な値（${t.label}）の ct`);
      assert.ok(ct.length <= 30, `ct が 30 字を超えた: ${ct}`);
    }
    for (const l of r.links) {
      assert.ok(!/script|DE_APP|Search-DE/.test(l._href), `不正な原文がリンクに残った（${t.label}）: ${l._href}`);
    }
    // 移った先でも、検査済みの実効値（ページ名の ad など）がそのまま使われる。
    let followed = 0;
    for (const l of r.links) {
      if (storeOf(l._href) || /^(mailto:|#)/i.test(l._href)) continue;
      const target = new URL(l._href, base + t.q);
      if (target.host !== 'blackshisa.com' || !fs.existsSync(pageFile(target.pathname))) continue;
      const next = run(target.href);
      const play = next.links.find((x) => storeOf(x._href) === 'android');
      if (!play) continue;
      const body = JSON.parse((await next.click(play)).beaconBodies[0]);
      eq([body.src, body.ad, body.cmp], ['ads', t.ad, t.cmp], `不正な値（${t.label}）で着地して ${target.pathname} へ移った先の本文`);
      for (const x of next.links.filter((y) => storeOf(y._href) === 'ios')) {
        eq(new URL(x._href).searchParams.get('ct'), 'ads_' + t.ad, `不正な値（${t.label}）の移った先の ct`);
      }
      followed++;
    }
    assert.ok(followed > 0, `不正な値（${t.label}）: 移った先で確かめたページが 1 つも無い`);
  }

  // --- ストアリンクを持つ全ページ：広告と自然流入の 2 通り --------------------
  const pages = [];
  (function walk(dir) {
    for (const name of fs.readdirSync(dir)) {
      const p = path.join(dir, name);
      if (name === 'node_modules' || name.startsWith('.')) continue;
      if (fs.statSync(p).isDirectory()) walk(p);
      else if (name.endsWith('.html')) pages.push(p);
    }
  })(ROOT);
  let storePages = 0;
  let iosTotal = 0;
  let playTotal = 0;
  for (const file of pages) {
    const { hrefs } = anchorsOf(file);
    const iosN = hrefs.filter((h) => storeOf(h) === 'ios').length;
    const playN = hrefs.filter((h) => storeOf(h) === 'android').length;
    if (iosN + playN === 0) continue;
    storePages++;
    iosTotal += iosN;
    playTotal += playN;
    let rel = '/' + path.relative(ROOT, file).split(path.sep).join('/');
    if (rel.endsWith('/index.html')) rel = rel.slice(0, -'index.html'.length);
    const ads = run(ORIGIN + rel + '?utm_source=google&utm_medium=cpc&utm_content=t_page');
    const org = run(ORIGIN + rel);
    for (const [r, isAds] of [[ads, true], [org, false]]) {
      let seenIos = 0;
      let seenPlay = 0;
      for (const l of r.links) {
        const s = storeOf(l._href);
        if (s === 'ios') {
          seenIos++;
          eq(new URL(l._href).searchParams.get('pt'), FIXTURE.pt, `${rel}: pt ${l._href}`);
          if (isAds) eq(new URL(l._href).searchParams.get('ct'), 'ads_t_page', `${rel}: 広告の ct`);
        } else if (s === 'android') {
          seenPlay++;
          const ref = playReferrer(l._href);
          if (isAds) eq(ref, 'utm_source=google_ads&utm_content=t_page', `${rel}: 広告の referrer`);
          else assert.ok(!/google_ads/.test(ref || ''), `${rel}: 自然流入に広告の印`);
        }
      }
      eq([seenIos, seenPlay], [iosN, playN], `${rel}: 全リンクを見た`);
    }
  }
  console.log(`store pages=${storePages} app_store_links=${iosTotal} play_links=${playTotal}`);
  console.log(`OK ${checks} checks`);
}

main().catch((err) => {
  console.error('FAIL:', err.message);
  process.exit(1);
});
