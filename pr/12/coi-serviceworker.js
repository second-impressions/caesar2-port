/*
 * Cross-origin isolation shim for static hosts such as GitHub Pages.
 * The service worker returns same-origin resources with the headers required
 * by SharedArrayBuffer and the threaded Emscripten runtime.
 *
 * The build version below is what makes this file change between builds. A
 * byte-identical worker is never reinstalled, so the first worker a visitor
 * ever received would keep serving them forever.
 */
const C2_BUILD_VERSION = "1.0.0-52-71064b4b";
if (typeof window === "undefined") {
  self.addEventListener("install", () => self.skipWaiting());
  self.addEventListener("activate", event => event.waitUntil((async () => {
    await self.clients.claim();
    for (const client of await self.clients.matchAll({type: "window"})) {
      client.postMessage({type: "c2-build", version: C2_BUILD_VERSION});
    }
  })()));
  self.addEventListener("fetch", event => {
    const request = event.request;
    if (request.cache === "only-if-cached" && request.mode !== "same-origin") return;
    event.respondWith((async () => {
      // Always revalidate: the page, its runtime and the wasm module are
      // published under fixed names, so a cached mix of two builds would load.
      const response = await fetch(request, {cache: "no-cache"});
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
    if (!("serviceWorker" in navigator)) {
      resolve(globalThis.crossOriginIsolated);
      return;
    }
    // Native COOP/COEP headers need no shim. A controlled, isolated page does:
    // it must still ask for worker updates instead of returning early forever.
    if (globalThis.crossOriginIsolated && !navigator.serviceWorker.controller) {
      resolve(true);
      return;
    }
    let reloading = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (reloading) return;
      // Never destroy an unsaved city for a background deployment. The active
      // runtime is self-contained; its next normal navigation will use the new
      // controller.
      if (document.body?.classList.contains("playing")) return;
      reloading = true;
      location.reload();
    });
    navigator.serviceWorker.register("./coi-serviceworker.js", {
      scope: "./", updateViaCache: "none"
    }).then(registration => {
      registration.update().catch(() => {});
      if (globalThis.crossOriginIsolated) {
        resolve(true);
        return;
      }
      if (navigator.serviceWorker.controller) {
        location.reload();
        resolve(false);
        return;
      }
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        resolve(false);
      }, {once: true});
    }).catch(error => {
      console.error("Could not enable cross-origin isolation", error);
      resolve(false);
    });
  });
}
