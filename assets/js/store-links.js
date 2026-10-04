/*
 * Counts clicks on App Store / Google Play links.
 *
 * Sends only {c, store, page, lang} (plus src:"ads", ad, cmp on ad landings).
 * No cookies, no identifiers, no storage.
 * Never blocks or delays navigation: errors are swallowed.
 *
 * Every App Store link gets pt=<provider token> so Apple can count campaigns.
 *
 * Ad landings (URL has gclid, or utm_source=google with utm_medium=cpc):
 *   ad  = utm_content if it matches NAME, otherwise this page's name
 *   cmp = utm_campaign if it matches NAME, otherwise absent
 *   App Store  ct=ads_<ad>
 *   Play       referrer=utm_source=google_ads&utm_campaign=<cmp>&utm_content=<ad>
 *   Links to other pages of this site carry the checked values (never the raw
 *   query), so the next page is still an ad landing with the same ad and cmp.
 * Contract: blackshisa_work/docs/quality/契約_20261004_広告の計測をキャンペーン別にする.md
 */
(function () {
  var ENDPOINT = "https://asia-northeast1-ichitap-kids.cloudfunctions.net/submitWebEvent";
  var LANGS = { en: 1, ja: 1, de: 1, es: 1 };
  var PROVIDER_TOKEN = "128814295";
  /* ct=ads_<ad> must fit App Store Connect's 30-character campaign name. */
  var NAME = /^[a-z0-9_]{1,26}$/;
  var GCLID = /^[A-Za-z0-9_-]{1,200}$/;
  var SITE_HOST = "blackshisa.com";

  function storeOf(href) {
    if (!href) return "";
    if (href.indexOf("://apps.apple.com/") !== -1) return "ios";
    if (href.indexOf("://play.google.com/store/apps/") !== -1) return "android";
    return "";
  }

  function pageLang() {
    var raw = (document.documentElement.getAttribute("lang") || "").slice(0, 2).toLowerCase();
    return LANGS[raw] ? raw : "en";
  }

  function queryParam(search, key) {
    var pairs = (search || "").replace(/^\?/, "").split("&");
    for (var i = 0; i < pairs.length; i++) {
      var eq = pairs[i].indexOf("=");
      var name = eq === -1 ? pairs[i] : pairs[i].slice(0, eq);
      if (name !== key) continue;
      var raw = eq === -1 ? "" : pairs[i].slice(eq + 1);
      try {
        return decodeURIComponent(raw.replace(/\+/g, " "));
      } catch (error) {
        return raw;
      }
    }
    return null;
  }

  function isAdLanding(search) {
    if (queryParam(search, "gclid") !== null) return true;
    return queryParam(search, "utm_source") === "google" && queryParam(search, "utm_medium") === "cpc";
  }

  function checked(value, pattern) {
    return typeof value === "string" && pattern.test(value) ? value : null;
  }

  /* The page's own name: "home" for an index, otherwise the file name. */
  function pageName(pathname) {
    var file = (pathname || "").split("/").pop() || "index.html";
    var stem = file.replace(/\.html?$/i, "").toLowerCase().replace(/[^a-z0-9_]+/g, "_");
    var name = stem === "index" || stem === "" ? "home" : stem;
    return name.slice(0, 26) || "page";
  }

  function adMarks(search, pathname) {
    return {
      ad: checked(queryParam(search, "utm_content"), NAME) || pageName(pathname),
      cmp: checked(queryParam(search, "utm_campaign"), NAME),
      gclid: checked(queryParam(search, "gclid"), GCLID)
    };
  }

  function setParam(href, key, value) {
    var hashAt = href.indexOf("#");
    var hash = hashAt === -1 ? "" : href.slice(hashAt);
    var base = hashAt === -1 ? href : href.slice(0, hashAt);
    var re = new RegExp("([?&])" + key + "=[^&]*");
    if (re.test(base)) return base.replace(re, "$1" + key + "=" + value) + hash;
    return base + (base.indexOf("?") === -1 ? "?" : "&") + key + "=" + value + hash;
  }

  /* A link to another page of this site (relative, or on blackshisa.com). */
  function isSitePage(href) {
    if (!href || href.charAt(0) === "#") return false;
    if (/^(mailto|tel|javascript|data):/i.test(href)) return false;
    var abs = /^[a-z][a-z0-9+.-]*:/i.test(href) || href.indexOf("//") === 0;
    if (!abs) return true;
    var m = /^(?:https?:)?\/\/([^/?#:]+)/i.exec(href);
    if (!m) return false;
    var host = m[1].toLowerCase();
    return host === SITE_HOST || host === "www." + SITE_HOST;
  }

  var fromAds = false;
  var marks = null;
  try {
    fromAds = isAdLanding(location.search);
    if (fromAds) marks = adMarks(location.search, location.pathname);
  } catch (error) {
    fromAds = false;
    marks = null;
  }

  function markLinks() {
    try {
      var links = document.getElementsByTagName("a");
      for (var i = 0; i < links.length; i++) {
        var href = links[i].getAttribute("href") || "";
        var store = storeOf(href);
        if (store === "ios") {
          href = setParam(href, "pt", PROVIDER_TOKEN);
          if (marks) href = setParam(href, "ct", "ads_" + marks.ad);
          links[i].setAttribute("href", href);
        } else if (store === "android") {
          if (marks) {
            var ref = "utm_source%3Dgoogle_ads";
            if (marks.cmp) ref += "%26utm_campaign%3D" + marks.cmp;
            ref += "%26utm_content%3D" + marks.ad;
            links[i].setAttribute("href", setParam(href, "referrer", ref));
          }
        } else if (marks && isSitePage(href)) {
          href = setParam(href, "utm_source", "google");
          href = setParam(href, "utm_medium", "cpc");
          if (marks.cmp) href = setParam(href, "utm_campaign", marks.cmp);
          href = setParam(href, "utm_content", marks.ad);
          if (marks.gclid) href = setParam(href, "gclid", marks.gclid);
          links[i].setAttribute("href", href);
        }
      }
    } catch (error) {
      /* ignore: marking must never stop the visitor */
    }
  }

  function post(body) {
    if (window.fetch) {
      window.fetch(ENDPOINT, {
        method: "POST",
        body: body,
        mode: "no-cors",
        keepalive: true,
        credentials: "omit",
        headers: { "Content-Type": "text/plain" }
      }).catch(function () {});
    }
  }

  function send(store) {
    try {
      var payload = { c: "bs-web-1", store: store, page: location.pathname, lang: pageLang() };
      if (marks) {
        payload.src = "ads";
        payload.ad = marks.ad;
        if (marks.cmp) payload.cmp = marks.cmp;
      }
      var body = JSON.stringify(payload);
      if (navigator.sendBeacon) {
        var queued = false;
        try {
          queued = navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "text/plain" }));
        } catch (error) {
          queued = false;
        }
        if (queued) return;
      }
      post(body);
    } catch (error) {
      /* ignore: counting must never stop the visitor */
    }
  }

  function onClick(event) {
    try {
      if (event.type === "auxclick" && event.button !== 1) return;
      var node = event.target;
      while (node && node !== document && !(node.tagName === "A" && node.href)) {
        node = node.parentNode;
      }
      if (!node || node === document) return;
      var store = storeOf(node.href);
      if (store) send(store);
    } catch (error) {
      /* ignore */
    }
  }

  document.addEventListener("click", onClick, true);
  document.addEventListener("auxclick", onClick, true);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", markLinks);
  } else {
    markLinks();
  }
})();
