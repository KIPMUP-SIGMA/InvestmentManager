/* Service worker KIPM-UP SIGMA: membuat aplikasi bisa dipasang dan dibuka cepat.
   Naikkan angka versi di bawah setiap kali file index.html diganti. */
const CACHE = "kipm-sigma-v1";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  // Hanya berkas milik aplikasi ini. Dokumen riset (folder riset/) tidak pernah disimpan di cache.
  if (req.method !== "GET" || url.origin !== location.origin || url.pathname.includes("/riset/")) return;

  // Halaman utama: ambil versi terbaru dari internet, cadangan dari cache bila offline.
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then(r => { if (r.ok) { const cp = r.clone(); caches.open(CACHE).then(c => c.put("index.html", cp)); } return r; })
        .catch(() => caches.match("index.html"))
    );
    return;
  }

  // Berkas lain: cache dulu, lalu internet.
  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(r => {
      if (r.ok) { const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); }
      return r;
    }))
  );
});
