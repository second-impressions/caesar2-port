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
const browserKind = process.argv[4] ?? "chromium";
const smokeResults = {
  province: "recovered province-selection smoke completed",
  city: "recovered city-loop smoke completed",
  campania: "Campania speech transition smoke completed",
  music: "music buffer smoke completed",
};
if (!(smokeKind in smokeResults)) {
  throw new Error(`unknown smoke kind '${smokeKind}'`);
}
if (!["chromium", "firefox"].includes(browserKind)) {
  throw new Error(`unknown browser '${browserKind}'`);
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
  await Promise.race([
    once(child, "exit"),
    new Promise((resolveStop) => {
      setTimeout(() => {
        if (child.exitCode === null) child.kill("SIGKILL");
        resolveStop();
      }, 5_000);
    })
  ]);
}

function waitForSocket(socket, timeoutMs = 10_000) {
  return new Promise((resolveSocket, reject) => {
    const timer = setTimeout(() => {
      reject(new Error("timed out connecting to browser debug socket"));
    }, timeoutMs);
    socket.addEventListener("open", () => {
      clearTimeout(timer);
      resolveSocket();
    }, { once: true });
    socket.addEventListener("error", () => {
      clearTimeout(timer);
      reject(new Error("browser debug socket connection failed"));
    }, { once: true });
    socket.addEventListener("close", () => {
      clearTimeout(timer);
      reject(new Error("browser debug socket closed during connection"));
    }, { once: true });
  });
}

function smokeWait(socket, navigate, getEntry) {
  return new Promise((resolveSmoke, reject) => {
    const consoleLines = [];
    const timer = setTimeout(() => {
      const suffix = consoleLines.length === 0
        ? ""
        : `\nBrowser console:\n${consoleLines.join("\n")}`;
      reject(new Error(
        `Wasm ${smokeKind} smoke timed out in ${browserKind}${suffix}`
      ));
    }, 60_000);
    socket.addEventListener("message", (event) => {
      const entry = getEntry(JSON.parse(event.data));
      if (!entry) return;
      if (entry.exception) {
        clearTimeout(timer);
        reject(new Error(entry.text));
        return;
      }
      consoleLines.push(entry.text);
      if (consoleLines.length > 40) consoleLines.shift();
      if (smokeKind === "music" && entry.text.includes("music-buffer")) {
        console.log(entry.text);
      }
      if (entry.text.includes(smokeResults[smokeKind])) {
        clearTimeout(timer);
        resolveSmoke();
      } else if (/exception|signature_mismatch|Aborted\(/i.test(entry.text)) {
        clearTimeout(timer);
        reject(new Error(entry.text));
      }
    });
    navigate();
  });
}

async function runChromium(gameUrl) {
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
  await waitForSocket(socket);
  let commandId = 0;
  const send = (method, params = {}) => {
    socket.send(JSON.stringify({ id: ++commandId, method, params }));
  };
  send("Runtime.enable");
  send("Page.enable");

  await smokeWait(
    socket,
    () => send("Page.navigate", {
      url: `${gameUrl}?smoke-test=${smokeKind}`
    }),
    (message) => {
      if (message.method === "Runtime.exceptionThrown") {
        return {
          exception: true,
          text: message.params.exceptionDetails.text
        };
      }
      if (message.method !== "Runtime.consoleAPICalled") return undefined;
      return {
        exception: false,
        text: message.params.args
          .map((arg) => arg.value ?? arg.description ?? "")
          .join(" ")
      };
    }
  );
  socket.close();
}

async function runFirefox(gameUrl) {
  browser = spawn("firefox", [
    "--headless",
    "--no-remote",
    "--profile", profile,
    "--remote-debugging-port", "0",
    "about:blank"
  ], { stdio: ["ignore", "ignore", "pipe"] });
  const webSocketUrl = await waitForLine(browser.stderr, (line) => {
    const match = line.match(/WebDriver BiDi listening on (ws:\/\/\S+)/);
    return match ? `${match[1]}/session` : undefined;
  });

  const socket = new WebSocket(webSocketUrl);
  await waitForSocket(socket);
  let commandId = 0;
  const pending = new Map();
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id === undefined) return;
    const handlers = pending.get(message.id);
    if (!handlers) return;
    pending.delete(message.id);
    if (message.type === "error") {
      handlers.reject(new Error(`${message.error}: ${message.message}`));
    } else {
      handlers.resolve(message.result);
    }
  });
  const send = (method, params = {}) => {
    const id = ++commandId;
    const result = new Promise((resolveCommand, rejectCommand) => {
      const timer = setTimeout(() => {
        pending.delete(id);
        rejectCommand(new Error(`Firefox BiDi command timed out: ${method}`));
      }, 10_000);
      pending.set(id, {
        resolve: (value) => {
          clearTimeout(timer);
          resolveCommand(value);
        },
        reject: (error) => {
          clearTimeout(timer);
          rejectCommand(error);
        }
      });
    });
    socket.send(JSON.stringify({ id, method, params }));
    return result;
  };

  await send("session.new", { capabilities: {} });
  const tree = await send("browsingContext.getTree");
  const context = tree.contexts[0]?.context;
  if (!context) throw new Error("Firefox did not expose a browsing context");
  await send("session.subscribe", {
    events: ["log.entryAdded"]
  });

  await send("browsingContext.navigate", {
    context,
    url: `${gameUrl}?smoke-test=${smokeKind}`,
    wait: "complete"
  });
  const deadline = Date.now() + 60_000;
  let consoleLines = [];
  while (Date.now() < deadline) {
    const evaluated = await send("script.evaluate", {
      expression: "JSON.stringify(globalThis.__c2SmokeOutput ?? [])",
      target: { context },
      awaitPromise: false
    });
    if (evaluated.type === "exception") {
      throw new Error(evaluated.exceptionDetails?.text ??
        "Firefox script evaluation failed");
    }
    const serialized = evaluated.result?.value;
    consoleLines = serialized ? JSON.parse(serialized) : [];
    const failure = consoleLines.find(
      (line) => /exception|signature_mismatch|Aborted\(|smoke test timed out/i
        .test(line)
    );
    if (failure) throw new Error(failure);
    if (consoleLines.some(
      (line) => line.includes(smokeResults[smokeKind])
    )) {
      socket.close();
      return;
    }
    await new Promise((resolvePoll) => setTimeout(resolvePoll, 250));
  }
  const suffix = consoleLines.length === 0
    ? ""
    : `\nBrowser output:\n${consoleLines.slice(-40).join("\n")}`;
  throw new Error(`Wasm ${smokeKind} smoke timed out in Firefox${suffix}`);
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

  if (browserKind === "firefox") {
    await runFirefox(gameUrl);
  } else {
    await runChromium(gameUrl);
  }
  console.log(`WebAssembly ${smokeKind} smoke passed in ${browserKind}`);
} finally {
  await Promise.all([stop(browser), stop(server)]);
  await rm(profile, {
    recursive: true,
    force: true,
    maxRetries: 5,
    retryDelay: 100
  });
}
