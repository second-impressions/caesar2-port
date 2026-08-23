/*
 * Cross-origin isolation shim for static hosts such as GitHub Pages.
 * The service worker returns same-origin resources with the headers required
 * by SharedArrayBuffer and the threaded Emscripten runtime.
 */
if (typeof window === "undefined") {
  self.addEventListener("install", () => self.skipWaiting());
  self.addEventListener("activate", event => event.waitUntil(self.clients.claim()));
  self.addEventListener("fetch", event => {
    const request = event.request;
    if (request.cache === "only-if-cached" && request.mode !== "same-origin") return;
    event.respondWith((async () => {
      const response = await fetch(request);
      if (response.status === 0) return response;
      const headers = new Headers(response.headers);
      headers.set("Cross-Origin-Opener-Policy", "same-origin");
      headers.set("Cross-Origin-Embedder-Policy", "require-corp");
      headers.set("Cross-Origin-Resource-Policy", "same-origin");
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers
      });
    })());
  });
} else {
  globalThis.coiReady = new Promise(resolve => {
    if (globalThis.crossOriginIsolated) {
      resolve(true);
      return;
    }
    if (!("serviceWorker" in navigator)) {
      resolve(false);
      return;
    }
    navigator.serviceWorker.register("./coi-serviceworker.js", {scope: "./"})
      .then(() => {
        if (navigator.serviceWorker.controller) {
          location.reload();
          resolve(false);
          return;
        }
        navigator.serviceWorker.addEventListener("controllerchange", () => {
          location.reload();
          resolve(false);
        }, {once: true});
      })
      .catch(error => {
        console.error("Could not enable cross-origin isolation", error);
        resolve(false);
      });
  });
}
