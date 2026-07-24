#!/usr/bin/env node

import { mkdtemp, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { createInterface } from "node:readline";

const root = resolve(import.meta.dirname, "..");
const build = resolve(process.argv[2] ?? `${root}/build/port/wasm-debug`);
const smokeKind = process.argv[3] ?? "province";
const smokeResults = {
  province: "recovered province-selection smoke completed",
  city: "recovered city-loop smoke completed",
  campania: "Campania speech transition smoke completed",
  music: "music buffer smoke completed",
};
if (!(smokeKind in smokeResults)) {
  throw new Error(`unknown smoke kind '${smokeKind}'`);
}
const profile = await mkdtemp(`${tmpdir()}/caesar2-wasm-smoke-`);
let server;
let browser;

function waitForLine(stream, predicate, timeoutMs = 15_000) {
  return new Promise((resolveLine, reject) => {
    const lines = createInterface({ input: stream });
    const timer = setTimeout(() => {
      lines.close();
      reject(new Error("timed out waiting for child-process output"));
    }, timeoutMs);
    lines.on("line", (line) => {
      const result = predicate(line);
      if (result !== undefined) {
        clearTimeout(timer);
        lines.close();
        resolveLine(result);
      }
    });
  });
}

async function stop(child) {
  if (!child || child.exitCode !== null) return;
  child.kill("SIGTERM");
  await once(child, "exit");
}

try {
  const entries = (await readdir(build)).filter(
    (name) => /^caesar2-[a-z]{2}\.html$/.test(name)
  );
  if (entries.length !== 1) {
    throw new Error(`${build} must contain exactly one language build`);
  }
  server = spawn("python3", [
    `${root}/tools/serve-wasm.py`, build, "--entry", entries[0],
    "--port", "0"
  ], { stdio: ["ignore", "pipe", "inherit"] });
  const gameUrl = await waitForLine(server.stdout, (line) => {
    const match = line.match(/Serving (http:\/\/\S+\.html)/);
    return match?.[1];
  });

  browser = spawn("chromium", [
    "--headless=new",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--enable-unsafe-swiftshader",
    ...(smokeKind === "music"
      ? ["--autoplay-policy=no-user-gesture-required"]
      : []),
    `--user-data-dir=${profile}`,
    "--remote-debugging-address=127.0.0.1",
    "--remote-debugging-port=0",
    "about:blank"
  ], { stdio: ["ignore", "ignore", "pipe"] });
  const devtoolsPort = await waitForLine(browser.stderr, (line) => {
    const match = line.match(/DevTools listening on ws:\/\/127\.0\.0\.1:(\d+)/);
    return match ? Number(match[1]) : undefined;
  });

  const pages = await fetch(`http://127.0.0.1:${devtoolsPort}/json`).then(
    (response) => response.json()
  );
  const page = pages.find((entry) => entry.type === "page");
  if (!page) throw new Error("Chromium did not expose a page target");

  const socket = new WebSocket(page.webSocketDebuggerUrl);
  await once(socket, "open");
  let commandId = 0;
  const send = (method, params = {}) => {
    socket.send(JSON.stringify({ id: ++commandId, method, params }));
  };
  send("Runtime.enable");
  send("Page.enable");

  await new Promise((resolveSmoke, reject) => {
    const consoleLines = [];
    const timer = setTimeout(() => {
      const suffix = consoleLines.length === 0
        ? ""
        : `\nBrowser console:\n${consoleLines.join("\n")}`;
      reject(new Error(`Wasm ${smokeKind} smoke timed out${suffix}`));
    }, 60_000);
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") {
        clearTimeout(timer);
        reject(new Error(message.params.exceptionDetails.text));
        return;
      }
      if (message.method !== "Runtime.consoleAPICalled") return;
      const text = message.params.args
        .map((arg) => arg.value ?? arg.description ?? "")
        .join(" ");
      consoleLines.push(text);
      if (consoleLines.length > 40) consoleLines.shift();
      if (smokeKind === "music" && text.includes("music-buffer")) {
        console.log(text);
      }
      if (text.includes(smokeResults[smokeKind])) {
        clearTimeout(timer);
        resolveSmoke();
      } else if (/exception|signature_mismatch|Aborted\(/i.test(text)) {
        clearTimeout(timer);
        reject(new Error(text));
      }
    });
    send("Page.navigate", { url: `${gameUrl}?smoke-test=${smokeKind}` });
  });
  socket.close();
  console.log(`WebAssembly ${smokeKind} smoke passed`);
} finally {
  await Promise.all([stop(browser), stop(server)]);
  await rm(profile, {
    recursive: true,
    force: true,
    maxRetries: 5,
    retryDelay: 100
  });
}
