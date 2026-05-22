/* HealthAssist CDST — Service Worker v1  hash=01d835b3 */
'use strict';

const CACHE = 'cdst-v01d835b3';
const OFFLINE_ASSETS = [
  './', './index.html',
  './static/css/chat.css', './static/js/chat.js',
  './static/data/protocols.json', './static/data/formulary.json',
  './static/data/i18n.json', './config.json', './manifest.json',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(OFFLINE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url   = new URL(e.request.url);
  const isAPI = url.hostname !== self.location.hostname;

  if (isAPI) {
    e.respondWith(
      Promise.race([
        fetch(e.request),
        new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 10000)),
      ]).catch(() => new Response(
        JSON.stringify({error:'offline'}),
        {status:503, headers:{'Content-Type':'application/json'}}
      ))
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      }).catch(() => caches.match('./index.html'));
    })
  );
});
