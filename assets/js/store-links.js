/*
 * Counts clicks on App Store / Google Play links.
 *
 * Sends only {c, store, page, lang}. No cookies, no identifiers, no storage.
 * Never blocks or delays navigation: errors are swallowed.
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

  function send(store) {
    try {
      var body = JSON.stringify({ c: "bs-web-1", store: store, page: location.pathname, lang: pageLang() });
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
})();
