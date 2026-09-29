/*
 * Counts clicks on App Store / Google Play links.
 *
 * Sends only {c, store, page, lang} (plus src:"ads" on ad landings).
 * No cookies, no identifiers, no storage.
 * Never blocks or delays navigation: errors are swallowed.
 *
 * Ad landings (URL has gclid, or utm_source=google with utm_medium=cpc):
 * the store links on this page are re-marked so installs from ads can be
 * told apart from organic ones.
 *   App Store  ct=ads_<name>
 *   Play       referrer=utm_source=google_ads&utm_campaign=<name>
 * <name> is utm_content (its first word) or, without it, this page's name.
 * The mark lives only on this page view; nothing is stored.
 */
(function () {
  var ENDPOINT = "https://asia-northeast1-ichitap-kids.cloudfunctions.net/submitWebEvent";
  var LANGS = { en: 1, ja: 1, de: 1, es: 1 };

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

  function cleanName(raw) {
    return (raw || "").toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "");
  }

  function adName(search, pathname) {
    var content = (queryParam(search, "utm_content") || "").replace(/^\s+/, "").split(/\s+/)[0];
    var name = cleanName(content);
    if (!name) {
      var file = (pathname || "").split("/").pop() || "index.html";
      var stem = file.replace(/\.html?$/i, "");
      name = stem === "index" || stem === "" ? "home" : cleanName(stem);
    }
    return (name || "page").slice(0, 36); /* "ads_" + name stays within ct's 40 chars */
  }

  function setParam(href, key, value) {
    var hashAt = href.indexOf("#");
    var hash = hashAt === -1 ? "" : href.slice(hashAt);
    var base = hashAt === -1 ? href : href.slice(0, hashAt);
    var re = new RegExp("([?&])" + key + "=[^&]*");
    if (re.test(base)) return base.replace(re, "$1" + key + "=" + value) + hash;
    return base + (base.indexOf("?") === -1 ? "?" : "&") + key + "=" + value + hash;
  }

  function markAdLinks() {
    try {
      var name = adName(location.search, location.pathname);
      var links = document.getElementsByTagName("a");
      for (var i = 0; i < links.length; i++) {
        var href = links[i].getAttribute("href") || "";
        var store = storeOf(href);
        if (store === "ios") {
          links[i].setAttribute("href", setParam(href, "ct", "ads_" + name));
        } else if (store === "android") {
          links[i].setAttribute(
            "href",
            setParam(href, "referrer", "utm_source%3Dgoogle_ads%26utm_campaign%3D" + name)
          );
        }
      }
    } catch (error) {
      /* ignore: marking must never stop the visitor */
    }
  }

  var fromAds = false;
  try {
    fromAds = isAdLanding(location.search);
  } catch (error) {
    fromAds = false;
  }

  function send(store) {
    try {
      var payload = { c: "bs-web-1", store: store, page: location.pathname, lang: pageLang() };
      if (fromAds) payload.src = "ads";
      var body = JSON.stringify(payload);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "text/plain" }));
        return;
      }
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

  if (fromAds) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", markAdLinks);
    } else {
      markAdLinks();
    }
  }
})();
