const CACHE_NAME = "uga-stove-field-v1";

const APP_SHELL = [
    "./",
    "./index.html",
    "./styles.css",
    "./app.js",
    "./manifest.webmanifest",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
    );

    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) =>
            Promise.all(
                cacheNames
                    .filter((cacheName) => cacheName !== CACHE_NAME)
                    .map((cacheName) => caches.delete(cacheName))
            )
        )
    );

    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    if (event.request.method !== "GET") {
        return;
    }

    const requestUrl = new URL(event.request.url);

    if (
        requestUrl.origin === self.location.origin
        && requestUrl.pathname.startsWith("/api/")
    ) {
        return;
    }

    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }

            return fetch(event.request)
                .then((networkResponse) => {
                    const responseCopy = networkResponse.clone();

                    if (
                        requestUrl.origin === self.location.origin
                        && requestUrl.pathname.startsWith("/field/")
                    ) {
                        caches
                            .open(CACHE_NAME)
                            .then((cache) => cache.put(event.request, responseCopy));
                    }

                    return networkResponse;
                })
                .catch(() => caches.match("./index.html"));
        })
    );
});