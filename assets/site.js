/* assets/site.js -- three jobs, no framework.
 *  1. theme: follow the OS unless the reader chose; remember the choice
 *  2. language: show one translation at a time; remember the choice
 *  3. legacy anchors: every Telegram link ever sent points at the site root
 *     as #s{storyId}-{MMDDHHMM}. Editions now live on their own pages, so
 *     the root resolves the anchor via editions.json and forwards.
 */
(function () {
  var root = document.documentElement;
  var store = { get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
                set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
  // ?theme=dark&lang=zh in the URL wins for this visit and is remembered
  var q = new URLSearchParams(location.search);
  if (q.get("theme") === "dark" || q.get("theme") === "light") store.set("theme", q.get("theme"));
  if (q.get("lang") && /^(en|zh|ja|ko|es|de)$/.test(q.get("lang"))) store.set("lang", q.get("lang"));

  // 1. theme
  var mq = window.matchMedia("(prefers-color-scheme: dark)");
  function applyTheme(t) {
    root.setAttribute("data-theme", t);
    var b = document.getElementById("theme");
    if (b) { b.setAttribute("aria-pressed", t === "dark" ? "true" : "false"); b.textContent = t === "dark" ? "Day" : "Night"; b.setAttribute("aria-label", t === "dark" ? "Switch to the day theme" : "Switch to the night theme"); }
  }
  applyTheme(store.get("theme") || (mq.matches ? "dark" : "light"));
  mq.addEventListener && mq.addEventListener("change", function (e) { if (!store.get("theme")) applyTheme(e.matches ? "dark" : "light"); });
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("#theme");
    if (!b) return;
    var t = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    store.set("theme", t); applyTheme(t);
  });

  // 2. language
  function applyLang(l) { root.setAttribute("data-lang", l); var s = document.getElementById("lang"); if (s) s.value = l; }
  applyLang(store.get("lang") || "en");
  document.addEventListener("change", function (e) {
    if (e.target && e.target.id === "lang") { store.set("lang", e.target.value); applyLang(e.target.value); }
  });

  // 3. legacy anchors on the root page
  var m = /^#s(\d+)-(\d{2})(\d{2})(\d{2})(\d{2})$/.exec(location.hash);
  if (!m || !root.hasAttribute("data-root")) return;
  if (document.getElementById(location.hash.slice(1))) return; // it is on this page
  var id = m[1], mmdd = m[2] + "/" + m[3], hhmm = m[4] + m[5];
  fetch("editions.json").then(function (r) { return r.json(); }).then(function (eds) {
    var hits = eds.filter(function (e) { return e.p.indexOf("/" + mmdd + "-" + hhmm + ".html") > 0; });
    var best = hits.filter(function (e) { return e.ids.indexOf(id) >= 0; })[0] || hits[hits.length - 1];
    if (best) location.replace(best.p + location.hash);
  }).catch(function () {});
})();
