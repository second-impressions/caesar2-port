    const canvas = document.getElementById("canvas");
    const panel = document.getElementById("panel");
    const status = document.getElementById("status");
    const operationDialog = document.getElementById("operation-dialog");
    const operationTitle = document.getElementById("operation-title");
    const operationProgress = document.getElementById("operation-progress");
    const operationDetail = document.getElementById("operation-detail");
    const operationClose = document.getElementById("operation-close");
    const toolbar = document.getElementById("toolbar");
    const assetsButton = document.getElementById("assets-button");
    const bundledButton = document.getElementById("bundled-button");
    const forgetButton = document.getElementById("forget-button");
    const folderInput = document.getElementById("folder-input");
    const fileInput = document.getElementById("file-input");
    const card = document.getElementById("card");
    const detectedRow = document.getElementById("detected-row");
    const playButton = document.getElementById("play-button");
    const profileRow = document.getElementById("profile-row");
    const profileSelect = document.getElementById("profile-select");
    const settingsDialog = document.getElementById("settings-dialog");
    const assetsSummary = document.getElementById("assets-summary");
    const assetsLoaded = document.getElementById("assets-loaded");
    const assetsStatus = document.getElementById("assets-status");
    const assetsEmpty = document.getElementById("assets-empty");
    const sourceDrop = document.getElementById("source-drop");
    const sourceDropTitle = document.getElementById("source-drop-title");
    const aboutDialog = document.getElementById("about-dialog");
    const userDataStatus = document.getElementById("userdata-status");
    const userDataInput = document.getElementById("userdata-input");
    const userDataDrop = document.getElementById("userdata-drop");
    const query = new URLSearchParams(location.search);
    const smokeOutput = query.has("smoke-test") ? [] : null;
    const BUILD_VERSION = "1.0.0-40-a343c39d";
    const HAS_BUNDLED_ASSETS = 0 === 1;
    const ACTIVE_SOURCE = "c2.active-source.v1";
    const PENDING_SOURCE = "c2.pending-source.v1";
    const ACTIVE_PROFILE = "c2.active-profile.v1";
    const ACTIVE_ORIGIN = "c2.active-origin.v1";
    const THEME_CHOICE = "c2.theme.v1";
    const SCALING_MODE = "c2.scaling.v1";
    const CONFIRM_CLOSE = "c2.confirm-close.v1";
    const AUTOSTART_SOURCE = "c2.autostart.v1";
    const PENDING_ORIGIN = "c2.pending-origin.v1";
    let runtimeReady = false;
    let gameRunning = false;
    let preparingAssets = false;
    let chosenSourceLabel = "";
    let scalingMode = localStorage.getItem(SCALING_MODE) === "fractional" ? "fractional" : "integer";
    let pausedByChrome = false;
    let engineHasRun = false;
    let pendingImportError;

    function resizeCanvasToIntegerScale() {
      const density = devicePixelRatio || 1;
      const fit = Math.min(innerWidth * density / 640, innerHeight * density / 480);
      // Integer scaling keeps square pixels; fractional fills the window and
      // leaves bars on the short axis.
      const scale = scalingMode === "fractional" ? Math.max(1, fit) : Math.max(1, Math.floor(fit));
      // Round down: a box wider than the viewport keeps the renderer letterboxing
      // into space the browser no longer offers.
      const cssWidth = Math.floor(640 * scale / density);
      const cssHeight = Math.floor(480 * scale / density);
      canvas.style.setProperty("--c2-canvas-width", `${cssWidth}px`);
      canvas.style.setProperty("--c2-canvas-height", `${cssHeight}px`);
      // SDL detects the CSS size at startup, but CSS changes do not emit a
      // browser resize event. Keep its window/backing store in lockstep too.
      if (gameRunning) {
        try { Module._c2_browser_set_canvas_size(cssWidth, cssHeight); }
        catch {}
      }
    }
    /*
     * Leaving fullscreen reports the old viewport for a frame or two, so the
     * first measurement would keep the fullscreen-sized canvas and letterbox it
     * with black. Settle the size over the following frames instead.
     */
    function scheduleCanvasResize() {
      resizeCanvasToIntegerScale();
      requestAnimationFrame(() => {
        resizeCanvasToIntegerScale();
        requestAnimationFrame(resizeCanvasToIntegerScale);
      });
    }
    resizeCanvasToIntegerScale(); addEventListener("resize", scheduleCanvasResize);
    /*
     * Right-click is a game input while the game is running. Everywhere else
     * the page keeps the browser's normal context menu.
     */
    canvas.addEventListener("contextmenu", e => {
      if (!gameRunning) return;
      e.preventDefault();
      if (query.get("smoke-test") === "contextmenu") {
        const message = "browser context menu suppressed";
        smokeOutput.push(message); console.log(message);
      }
    });
    if (query.get("smoke-test") === "canvas") {
      requestAnimationFrame(() => {
        canvas.focus(); const style = getComputedStyle(canvas);
        if (document.activeElement === canvas && style.userSelect === "none" &&
            style.outlineStyle === "none" && !canvas.draggable) {
          const message = "canvas focus styling suppressed";
          smokeOutput.push(message); console.log(message);
        }
      });
    }

    async function opfsRoot() { return navigator.storage.getDirectory(); }
    async function directoryAt(path, create = true) {
      let dir = await opfsRoot();
      for (const part of path.split("/").filter(Boolean)) dir = await dir.getDirectoryHandle(part, {create});
      return dir;
    }
    async function clearDirectory(dir) {
      for await (const [name] of dir.entries()) await dir.removeEntry(name, {recursive:true});
    }
    async function childCaseInsensitive(dir, wanted, kind) {
      for await (const [name, handle] of dir.entries()) {
        if (name.toLowerCase() === wanted.toLowerCase() && (!kind || handle.kind === kind)) return handle;
      }
      return null;
    }
    async function descendCaseInsensitive(root, parts) {
      let dir = root;
      for (const part of parts) {
        dir = await childCaseInsensitive(dir, part, "directory");
        if (!dir) return null;
      }
      return dir;
    }
    async function hasFileWithExtension(dir, extension) {
      if (!dir) return false;
      for await (const [name, handle] of dir.entries()) {
        if (handle.kind === "file" && name.toLowerCase().endsWith(extension)) return true;
      }
      return false;
    }
    /*
     * The original installer copied only the HD tree; XMI music, RAW speech
     * and the movies stayed on the CD. Report what a source lacks so silence
     * is explained rather than mysterious.
     */
    async function missingMedia(root, base) {
      const missing = [];
      const music = await descendCaseInsensitive(root, ["XMI"]);
      const speech = await descendCaseInsensitive(root, ["RAW"]);
      if (!(await hasFileWithExtension(music, ".xmi")) && !(await hasFileWithExtension(base, ".xmi"))) missing.push("music");
      if (!(await hasFileWithExtension(speech, ".raw")) && !(await hasFileWithExtension(base, ".raw"))) missing.push("speech");
      return missing;
    }
    async function hashFile(file) {
      const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
      return [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, "0")).join("");
    }
    const languageNames = {en:"English", de:"German", fr:"French", it:"Italian", es:"Spanish"};
    /*
     * C2.ENG differs per release, so its digest identifies both the language
     * and the release group the loaded data came from.
     */
    const knownEditions = {
      "581da6ed8e43630ba074ddbada2b269448c729159739e951aa29cbf714b6c6bd":
        {language:"English", edition:"Europe/OEM and 1995–1996 rerelease"},
      "3c448a3caba887a0a9f792af070aa058d13b1f678d74b06f09d1f5cfd92252c3":
        {language:"English", edition:"1996–1997 rerelease"},
      "d1a7af206a1c9e0beed6fa6f3cd67992585539de2583e8044c3a29eaa51bcf8c":
        {language:"English", edition:"Europe original"},
      "9f54949256035951c815ca347e52fbba410b565867afc478a1f9254e8f0288d5":
        {language:"French", edition:"France"},
      "93d435839b253e4fea9bda74211bef18072dcbd23f2ebed5fc10dff459bd248b":
        {language:"German", edition:"Germany rerelease"},
      "0c0f5a4a6ba9ff9e986a9cea8a748db83e323eab24a83b7a2de86fff53d3b0f5":
        {language:"German", edition:"Germany original"},
      "e26ac14fd8ff64860cc0b78b55373bd20ea7c2e6fa81558e4393b1a5165a7219":
        {language:"German", edition:"Germany, Windows 95 tree"}
    };
    async function sourceInfo(source) {
      if (source === "/assets") {
        return {
          available: HAS_BUNDLED_ASSETS,
          profiles: [],
          language: languageNames["en"] || "en"
        };
      }
      if (!source?.startsWith("/persistent/")) return {available:false, profiles:[]};
      try {
        const root = await descendCaseInsensitive(await opfsRoot(), source.slice(12).split("/").filter(Boolean));
        if (!root) return {available:false, profiles:[]};
        const packIndex = await childCaseInsensitive(root, "C2PACK.IDX", "file");
        if (packIndex) {
          const text = await (await packIndex.getFile()).text();
          const rows = [...text.matchAll(/^PROFILE\t([^\t\r\n]+)\t?([^\r\n]*)/gm)];
          const components = new Set();
          for (const row of rows) {
            for (const part of (row[2] || "").split(",")) if (part) components.add(part);
          }
          return {
            available: rows.length > 0,
            profiles: rows.map(row => row[1]),
            components: [...components]
          };
        }
        const direct = await descendCaseInsensitive(root, []);
        const dos = await descendCaseInsensitive(root, ["HD"]);
        const win = await descendCaseInsensitive(root, ["C2WIN95", "HD"]);
        const candidates = [
          [direct, "Installed game directory"],
          [dos, win ? "DOS/Win95 hybrid · DOS assets" : "DOS CD layout"],
          [win, "Windows 95 CD layout"],
        ];
        for (const [base, layout] of candidates) {
          if (!base) continue;
          const text = await childCaseInsensitive(base, "C2.ENG", "file");
          const help = await childCaseInsensitive(base, "HELP.ENG", "file");
          if (text && help) {
            const known = knownEditions[await hashFile(await text.getFile())];
            return {
              available: true,
              profiles: [],
              language: known?.language || "Unrecognised text data",
              edition: known?.edition || "Unrecognised release",
              layout,
              missing: await missingMedia(root, base)
            };
          }
        }
      } catch {}
      return {available:false, profiles:[]};
    }
    function formatBytes(bytes) {
      if (bytes < 1024) return `${bytes} B`;
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
      return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
    }
    function beginOperation(title, total = 0, detail = "Starting…") {
      operationTitle.textContent = title;
      operationClose.hidden = true;
      operationProgress.hidden = false;
      if (total > 0) {
        operationProgress.max = total;
        operationProgress.value = 0;
      } else {
        operationProgress.removeAttribute("max");
        operationProgress.removeAttribute("value");
      }
      operationDetail.textContent = total ? `0 B / ${formatBytes(total)}` : detail;
      if (!operationDialog.open) operationDialog.showModal();
    }
    function updateOperation(value, total, suffix = "") {
      if (total > 0) {
        operationProgress.hidden = false;
        operationProgress.max = total;
        operationProgress.value = Math.min(value, total);
        operationDetail.textContent = `${formatBytes(value)} / ${formatBytes(total)}${suffix}`;
      } else if (suffix) {
        operationDetail.textContent = suffix;
      }
    }
    function showOperationError(message) {
      operationTitle.textContent = "Import failed";
      operationProgress.hidden = true;
      operationDetail.textContent = message;
      operationClose.hidden = false;
      if (!operationDialog.open) operationDialog.showModal();
    }
    function endOperation() {
      if (operationDialog.open) operationDialog.close();
    }
    async function writeBrowserFile(root, relative, file, onBytes) {
      const parts = relative.replaceAll("\\", "/").split("/").filter(Boolean);
      if (!parts.length || parts.some(p => p === "." || p === "..")) throw new Error("Unsafe input path");
      let dir = root;
      for (const part of parts.slice(0, -1)) dir = await dir.getDirectoryHandle(part, {create:true});
      const handle = await dir.getFileHandle(parts.at(-1), {create:true});
      const writable = await handle.createWritable();
      const progress = new TransformStream({
        transform(chunk, controller) {
          onBytes?.(chunk.byteLength);
          controller.enqueue(chunk);
        }
      });
      // Keep the browser's optimized stream-to-OPFS path; awaiting one write
      // per chunk makes large BIN images orders of magnitude slower.
      await file.stream().pipeThrough(progress).pipeTo(writable);
    }
    async function requestPersistence() {
      if (!navigator.storage?.persist) return false;
      if (await navigator.storage.persisted()) return true;
      return navigator.storage.persist();
    }
    function folderName(entries) {
      return entries[0]?.path.split("/")[0] || "";
    }
    /* The origin is the label of the choice the user pressed, nothing invented. */
    function rememberOrigin(name) {
      localStorage.setItem(PENDING_ORIGIN, JSON.stringify({kind: chosenSourceLabel, name}));
    }
    function inputEntries(files) {
      return [...files].map(file => ({file, path: file.webkitRelativePath || file.name}));
    }
    /*
     * The importer classifies content itself (ZIP, ISO or raw-sector
     * signatures, installation layouts), so the page only has to get the
     * bytes into OPFS: a folder is copied whole, files are copied as-is.
     */
    async function importFolder(entries) {
      if (!entries.length) throw new Error("The folder is empty");
      const total = entries.reduce((sum, entry) => sum + entry.file.size, 0);
      let loaded = 0;
      let done = 0;
      showMessage("Importing installation folder…");
      beginOperation("Copying installation folder", total);
      const generation = `folder-${Date.now()}`;
      const incoming = await directoryAt(`incoming/${generation}`);
      for (const {file, path} of entries) {
        const slash = path.indexOf("/");
        await writeBrowserFile(incoming,
          slash >= 0 ? path.slice(slash + 1) : path, file,
          bytes => { loaded += bytes; updateOperation(loaded, total,
            ` · ${done}/${entries.length} files`); });
        done++;
        updateOperation(loaded, total, ` · ${done}/${entries.length} files`);
      }
      localStorage.setItem(PENDING_SOURCE, `/persistent/incoming/${generation}`);
      rememberOrigin(folderName(entries));
      requestPersistence().catch(() => {});
      location.href = location.pathname;
    }
    /* Same signatures the native importer sniffs: ZIP, raw CD sector, ISO-9660. */
    async function fileLooksImportable(file) {
      const head = new Uint8Array(await file.slice(0, 16).arrayBuffer());
      if (head[0] === 0x50 && head[1] === 0x4b && head[2] === 3 && head[3] === 4) return "zip";
      const sync = [0, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 0];
      if (head.length === 16 && sync.every((b, i) => head[i] === b) && (head[15] === 1 || head[15] === 2)) return "bin";
      const pvd = new Uint8Array(await file.slice(16 * 2048, 16 * 2048 + 6).arrayBuffer());
      if (String.fromCharCode(...pvd.slice(1, 6)) === "CD001") return "iso";
      if (/\.cue$/i.test(file.name)) return "cue";
      return null;
    }
    async function importFiles(files) {
      const selected = [...files];
      if (!selected.length) throw new Error("No file selected");
      const kinds = await Promise.all(selected.map(fileLooksImportable));
      const unknown = selected.filter((_, i) => !kinds[i]);
      if (unknown.length) {
        const name = unknown[0].name;
        if (/\.(eng|exe|dat|pl8|raw|xmi|smk)$/i.test(name) || unknown.length > 1) {
          throw new Error(`${name} is part of an installation; use Browse folder or drop the whole folder`);
        }
        throw new Error(`${name} is not a Caesar II disc image, ZIP or asset pack`);
      }
      // A BIN is enough on its own; a CUE beside it is copied but not required.
      let primary = selected.find((_, i) => kinds[i] === "bin")
                 || selected.find((_, i) => kinds[i] !== "cue");
      if (!primary) throw new Error("A CUE sheet needs its BIN image; select the BIN file");
      if (selected.filter((_, i) => kinds[i] !== "cue").length > 1) {
        throw new Error("Select one disc image, ZIP or pack at a time");
      }
      const total = selected.reduce((sum, file) => sum + file.size, 0);
      let loaded = 0;
      let done = 0;
      beginOperation("Copying game data", total);
      const generation = `files-${Date.now()}`;
      const incoming = await directoryAt(`incoming/${generation}`);
      for (const file of selected) {
        showMessage(`Importing source… ${done + 1}/${selected.length}`);
        await writeBrowserFile(incoming, file.name, file,
          bytes => { loaded += bytes; updateOperation(loaded, total,
            ` · ${done}/${selected.length} files`); });
        done++;
        updateOperation(loaded, total, ` · ${done}/${selected.length} files`);
      }
      localStorage.setItem(PENDING_SOURCE, `/persistent/incoming/${generation}/${primary.name}`);
      rememberOrigin(selected.map(f => f.name).join(", "));
      requestPersistence().catch(() => {});
      location.href = location.pathname;
    }
    /* Dropped folders arrive as directory entries; flatten them to files. */
    function readEntries(reader) {
      return new Promise((resolve, reject) => reader.readEntries(resolve, reject));
    }
    function entryFile(entry) {
      return new Promise((resolve, reject) => entry.file(resolve, reject));
    }
    async function collectEntry(entry, prefix, out) {
      if (entry.isFile) {
        out.push({file: await entryFile(entry), path: prefix + entry.name});
        return;
      }
      const reader = entry.createReader();
      for (;;) {
        const batch = await readEntries(reader);
        if (!batch.length) break;
        for (const child of batch) await collectEntry(child, `${prefix}${entry.name}/`, out);
      }
    }
    async function importDrop(dataTransfer) {
      const items = [...dataTransfer.items || []];
      const entries = items.map(item => item.webkitGetAsEntry?.()).filter(Boolean);
      const directories = entries.filter(entry => entry.isDirectory);
      if (directories.length > 1) throw new Error("Drop one folder at a time");
      if (directories.length === 1) {
        if (entries.length > 1) throw new Error("Drop either a folder or files, not both");
        chosenSourceLabel = "Dropped folder";
        const collected = [];
        await collectEntry(directories[0], "", collected);
        await importFolder(collected);
        return;
      }
      chosenSourceLabel = "Dropped file";
      await importFiles(dataTransfer.files);
    }
    function zipStore(files) {
      const encoder = new TextEncoder();
      const table = new Uint32Array(256);
      for (let n = 0; n < 256; n++) {
        let c = n;
        for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
        table[n] = c >>> 0;
      }
      const u16 = (view, offset, value) => view.setUint16(offset, value, true);
      const u32 = (view, offset, value) => view.setUint32(offset, value >>> 0, true);
      const parts = [], central = [];
      let offset = 0;
      for (const item of files) {
        const name = encoder.encode(item.name);
        const data = item.data;
        let crc = 0xffffffff;
        for (const byte of data) crc = table[(crc ^ byte) & 255] ^ (crc >>> 8);
        crc = (crc ^ 0xffffffff) >>> 0;
        const local = new Uint8Array(30 + name.length);
        const lv = new DataView(local.buffer);
        u32(lv, 0, 0x04034b50); u16(lv, 4, 20); u16(lv, 6, 0x0800);
        u32(lv, 14, crc); u32(lv, 18, data.length); u32(lv, 22, data.length);
        u16(lv, 26, name.length); local.set(name, 30);
        parts.push(local, data);
        const cd = new Uint8Array(46 + name.length); const cv = new DataView(cd.buffer);
        u32(cv, 0, 0x02014b50); u16(cv, 4, 20); u16(cv, 6, 20); u16(cv, 8, 0x0800);
        u32(cv, 16, crc); u32(cv, 20, data.length); u32(cv, 24, data.length);
        u16(cv, 28, name.length); u32(cv, 42, offset); cd.set(name, 46);
        central.push(cd); offset += local.length + data.length;
      }
      const centralSize = central.reduce((sum, part) => sum + part.length, 0);
      const end = new Uint8Array(22); const ev = new DataView(end.buffer);
      u32(ev, 0, 0x06054b50); u16(ev, 8, files.length); u16(ev, 10, files.length);
      u32(ev, 12, centralSize); u32(ev, 16, offset);
      return new Blob([...parts, ...central, end], {type:"application/zip"});
    }
    async function storedSaveSummary() {
      const dir = await directoryAt("user-data", false);
      const result = [];
      for (const name of ["c2smoke.sav", "caesar2.sav", "lastyear.sav", "history.dat"]) {
        try { result.push(`${name}:${(await (await dir.getFileHandle(name)).getFile()).size}`); } catch {}
      }
      return result;
    }
    async function exportUserData() {
      let dir;
      try { dir = await directoryAt("user-data", false); }
      catch { userDataStatus.textContent = "No saves, history, or settings stored yet."; return; }
      const archiveFiles = [];
      for await (const [name, handle] of dir.entries()) {
        if (handle.kind !== "file" ||
            (!/\.sav$/i.test(name) && name.toLowerCase() !== "history.dat" &&
             name.toLowerCase() !== "caesar2.inf")) continue;
        const file = await handle.getFile();
        archiveFiles.push({name, data:new Uint8Array(await file.arrayBuffer())});
      }
      if (!archiveFiles.length) {
        userDataStatus.textContent = "No saves, history, or settings stored yet.";
        return;
      }
      archiveFiles.sort((a, b) => a.name.localeCompare(b.name));
      const url = URL.createObjectURL(zipStore(archiveFiles));
      const link = document.createElement("a");
      link.href = url;
      link.download = "caesar2-user-data.zip";
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
      userDataStatus.textContent = `Exported ${archiveFiles.length} user-data file${archiveFiles.length === 1 ? "" : "s"}.`;
    }
    function canonicalUserDataName(name) {
      const base = name.replaceAll("\\", "/").split("/").at(-1);
      if (/\.sav$/i.test(base)) return base;
      if (base.toLowerCase() === "history.dat") return "history.dat";
      if (base.toLowerCase() === "caesar2.inf") return "caesar2.inf";
      throw new Error(`Unsupported user-data file: ${name}`);
    }
    async function writeUserData(name, data) {
      name = canonicalUserDataName(name);
      if (/\.sav$/i.test(name) && data.byteLength !== 225745) throw new Error(`${name} is not a 225745-byte Caesar II save`);
      if (name === "history.dat" && data.byteLength !== 4000) throw new Error("history.dat must be 4000 bytes");
      if (name === "caesar2.inf" && (data.byteLength < 64 || data.byteLength > 1048576)) throw new Error("caesar2.inf has an invalid size");
      const dir = await directoryAt("user-data");
      const handle = await dir.getFileHandle(name, {create:true});
      const writable = await handle.createWritable();
      await writable.write(data);
      await writable.close();
    }
    async function importUserFiles(files) {
      let count = 0;
      for (const file of files) {
        await writeUserData(file.name, new Uint8Array(await file.arrayBuffer()));
        userDataStatus.textContent = `Imported ${++count}/${files.length} user-data files…`;
      }
    }
    function findZipEnd(data) {
      const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
      for (let i = data.length - 22; i >= Math.max(0, data.length - 65557); i--) {
        if (view.getUint32(i, true) === 0x06054b50) return i;
      }
      return -1;
    }
    async function inflateZipEntry(bytes, limit) {
      if (!("DecompressionStream" in globalThis)) throw new Error("This browser cannot decompress ZIP entries");
      const reader = new Blob([bytes]).stream()
        .pipeThrough(new DecompressionStream("deflate-raw")).getReader();
      const chunks = [];
      let size = 0;
      for (;;) {
        const {done, value} = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > limit) {
          await reader.cancel();
          throw new Error("ZIP user-data entry exceeds limits");
        }
        chunks.push(value);
      }
      const result = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.byteLength; }
      return result;
    }
    async function importUserZip(file) {
      if (!file || file.size > 8 * 1024 * 1024) throw new Error("User-data ZIP exceeds the 8 MiB limit");
      const data = new Uint8Array(await file.arrayBuffer());
      const view = new DataView(data.buffer);
      const end = findZipEnd(data);
      if (end < 0) throw new Error("ZIP end record not found");
      const entries = view.getUint16(end + 10, true);
      let cursor = view.getUint32(end + 16, true);
      if (!entries || entries > 256) throw new Error("ZIP contains an invalid number of files");
      let imported = 0;
      const decoder = new TextDecoder("utf-8", {fatal:true});
      for (let index = 0; index < entries; index++) {
        if (cursor + 46 > data.length || view.getUint32(cursor, true) !== 0x02014b50) throw new Error("Invalid ZIP directory");
        const flags = view.getUint16(cursor + 8, true);
        const method = view.getUint16(cursor + 10, true);
        const compressedSize = view.getUint32(cursor + 20, true);
        const uncompressedSize = view.getUint32(cursor + 24, true);
        const nameLength = view.getUint16(cursor + 28, true);
        const extraLength = view.getUint16(cursor + 30, true);
        const commentLength = view.getUint16(cursor + 32, true);
        const localOffset = view.getUint32(cursor + 42, true);
        const next = cursor + 46 + nameLength + extraLength + commentLength;
        if (next > data.length) throw new Error("Invalid ZIP directory entry");
        const name = decoder.decode(data.subarray(cursor + 46, cursor + 46 + nameLength));
        if (name.includes("/") || name.includes("\\")) throw new Error(`ZIP paths are not valid user-data names: ${name}`);
        cursor = next;
        if (flags & 1) throw new Error("Encrypted ZIP user data is not supported");
        if (localOffset + 30 > data.length || view.getUint32(localOffset, true) !== 0x04034b50) throw new Error("Invalid ZIP local header");
        const localName = view.getUint16(localOffset + 26, true);
        const localExtra = view.getUint16(localOffset + 28, true);
        const start = localOffset + 30 + localName + localExtra;
        if (start + compressedSize > data.length || uncompressedSize > 2 * 1024 * 1024) throw new Error("ZIP user-data entry exceeds limits");
        let content;
        if (method === 0) content = data.slice(start, start + compressedSize);
        else if (method === 8) content = await inflateZipEntry(
          data.slice(start, start + compressedSize), 2 * 1024 * 1024);
        else throw new Error(`Unsupported ZIP compression method ${method}`);
        if (content.byteLength !== uncompressedSize) throw new Error(`ZIP size mismatch for ${name}`);
        await writeUserData(name, content);
        imported++;
      }
      return imported;
    }
    /* One entry point: exported ZIPs (by signature, not name) are unpacked,
     * everything else is written as a user-data file. */
    async function importUserData(files) {
      const selected = [...files];
      if (!selected.length) throw new Error("No file selected");
      const zips = [];
      const plain = [];
      for (const file of selected) {
        const head = new Uint8Array(await file.slice(0, 4).arrayBuffer());
        (head[0] === 0x50 && head[1] === 0x4b && head[2] === 3 && head[3] === 4 ? zips : plain).push(file);
      }
      for (const file of plain) canonicalUserDataName(file.name);
      let count = 0;
      if (plain.length) {
        await importUserFiles(plain);
        count += plain.length;
      }
      for (const zip of zips) count += await importUserZip(zip);
      requestPersistence().catch(() => {});
      userDataStatus.textContent = `Imported ${count} user-data file${count === 1 ? "" : "s"}.`;
    }
    function originLabel() {
      try {
        const stored = JSON.parse(localStorage.getItem(ACTIVE_ORIGIN) || "null");
        if (stored?.kind) return stored.name ? `${stored.kind} · ${stored.name}` : stored.kind;
      } catch {}
      return null;
    }
    /* Show what the loader actually recognised in the currently loaded data. */
    async function updateAssetsSummary() {
      const source = localStorage.getItem(ACTIVE_SOURCE);
      const info = source ? await sourceInfo(source) : {available:false, profiles:[]};
      assetsSummary.replaceChildren();
      // Loading a second set only makes sense once the current one is removed.
      assetsLoaded.hidden = !info.available;
      assetsEmpty.hidden = info.available;
      sourceDropTitle.textContent = info.available
        ? "Drop new game data here to replace the current set"
        : "Drop your Caesar II folder, disc image or ZIP here";
      if (!info.available) return;
      const rows = [];
      const origin = originLabel();
      if (origin) rows.push(["Loaded", origin]);
      if (info.profiles?.length) {
        rows.push(["Languages", info.profiles.map(name => languageNames[name] || name).join(", ")]);
        if (info.components?.length) rows.push(["Contents", info.components.sort().join(", ")]);
      } else if (info.language) {
        rows.push(["Language", info.language]);
      }
      if (info.edition) rows.push(["Edition", info.edition]);
      if (info.layout) rows.push(["Layout", info.layout]);
      for (const [term, value] of rows) {
        const dt = document.createElement("dt"); dt.textContent = term;
        const dd = document.createElement("dd"); dd.textContent = value;
        assetsSummary.append(dt, dd);
      }
    }
    const settingsTabs = [...document.querySelectorAll(".c2-settings-tab")];
    function selectSettingsPane(pane, focus = false) {
      for (const tab of settingsTabs) {
        const active = tab.dataset.pane === pane;
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
        document.getElementById(`pane-${tab.dataset.pane}`).hidden = !active;
        if (active && focus) tab.focus();
      }
      if (pane === "assets") {
        assetsStatus.textContent = "";
        updateAssetsSummary().catch(error => {
          assetsStatus.textContent = `Could not inspect loaded assets: ${error.message}`;
        });
      }
    }
    selectSettingsPane("general");
    for (const tab of settingsTabs) {
      tab.addEventListener("keydown", event => {
        let index = settingsTabs.indexOf(tab);
        if (event.key === "ArrowDown" || event.key === "ArrowRight") index++;
        else if (event.key === "ArrowUp" || event.key === "ArrowLeft") index--;
        else if (event.key === "Home") index = 0;
        else if (event.key === "End") index = settingsTabs.length - 1;
        else return;
        event.preventDefault();
        const next = settingsTabs[(index + settingsTabs.length) % settingsTabs.length];
        selectSettingsPane(next.dataset.pane, true);
      });
    }
    function openSettings(pane) {
      selectSettingsPane(pane);
      setChromePause(true);
      if (!settingsDialog.open) settingsDialog.showModal();
    }
    function openAssetsModal() {
      openSettings("assets");
    }
    async function forgetAssets() {
      if (!confirm("Delete cached/imported game data? Saves and settings will be kept.")) return;
      settingsDialog.close();
      const root = await opfsRoot();
      const targets = [];
      for (const name of ["game-data", "incoming"]) {
        try {
          const dir = await root.getDirectoryHandle(name);
          for await (const [child] of dir.entries()) targets.push([name, child]);
        } catch {}
      }
      let removed = 0;
      beginOperation("Removing cached assets", targets.length);
      updateOperation(0, targets.length, ` · 0/${targets.length} items`);
      for (const [parent, child] of targets) {
        try {
          const dir = await root.getDirectoryHandle(parent);
          await dir.removeEntry(child, {recursive:true});
        } catch {}
        removed++;
        updateOperation(removed, targets.length,
          ` · ${removed}/${targets.length} items`);
      }
      for (const name of ["game-data", "incoming"]) {
        try { await root.removeEntry(name, {recursive:true}); } catch {}
      }
      localStorage.removeItem(ACTIVE_SOURCE);
      localStorage.removeItem(ACTIVE_PROFILE);
      localStorage.removeItem(ACTIVE_ORIGIN);
      await updateAssetsSummary();
      assetsStatus.textContent = removed === 1
        ? "Removed 1 cached asset set."
        : `Removed ${removed} cached asset sets.`;
      endOperation();
      showMainWindow({available:false, profiles:[]});
      openSettings("assets");
    }
    function gameArgs(source) {
      const args = ["--game-data", source];
      const profile = localStorage.getItem(ACTIVE_PROFILE);
      if (profile) args.push("--asset-profile", profile);
      if (scalingMode === "fractional") args.push("--fractional-scaling");
      if (query.get("mouse-lock") === "1") args.push("--mouse-lock");
      const smoke = query.get("smoke-test");
      if (smoke === "province" || smoke === "restart") args.push("--smoke-test");
      if (smoke === "city") args.push("--city-smoke-test");
      if (smoke === "campania") args.push("--campania-transition-smoke-test");
      if (smoke === "build") args.push("--province-build-smoke-test");
      if (smoke === "citybuild") args.push("--city-build-smoke-test");
      if (smoke === "music") args.push("--music-buffer-smoke-test");
      if (smoke === "save") args.push("--save-load-smoke-test");
      return args;
    }
    async function startGame(source, skipValidation = false) {
      if (!runtimeReady || gameRunning) return;
      if (!skipValidation && !(await sourceInfo(source)).available) {
        localStorage.removeItem(ACTIVE_SOURCE);
        showMainWindow({available:false, profiles:[]}, "Cached game data is no longer available.");
        return;
      }
      if (engineHasRun) {
        // The recovered engine initialises its globals once and SDL is shut
        // down when it exits, so a second run needs a fresh runtime.
        sessionStorage.setItem(AUTOSTART_SOURCE, source);
        showMessage("Restarting…");
        location.reload();
        return;
      }
      engineHasRun = true;
      gameRunning = true; panel.hidden = true;
      document.body.classList.add("playing");
      showMessage("Starting…");
      Module.callMain(gameArgs(source));
    }
    /*
     * Import and cache an uploaded source without starting the engine, then
     * reload into the main window so the user decides when to play.
     */
    function prepareAssets(source) {
      if (!runtimeReady || gameRunning) return;
      preparingAssets = true;
      panel.hidden = false;
      showMessage("Checking game data…");
      pendingImportError = undefined;
      beginOperation("Checking game data", 0, "Reading source catalog…");
      const args = ["--game-data", source, "--prepare-assets"];
      const profile = localStorage.getItem(ACTIVE_PROFILE);
      if (profile) args.push("--asset-profile", profile);
      Module.callMain(args);
    }
    function configureAssetChoices(info) {
      profileSelect.replaceChildren();
      profileRow.hidden = true;
      if (info.profiles?.length) {
        const stored = localStorage.getItem(ACTIVE_PROFILE);
        for (const name of info.profiles) {
          const option = document.createElement("option");
          option.value = name; option.textContent = languageNames[name] || name;
          profileSelect.append(option);
        }
        profileSelect.value = info.profiles.includes(stored) ? stored : info.profiles[0];
        localStorage.setItem(ACTIVE_PROFILE, profileSelect.value);
        if (info.profiles.length > 1) profileRow.hidden = false;
      } else {
        localStorage.removeItem(ACTIVE_PROFILE);
      }
    }
    /* Keep Play focusable so its tooltip can point at the assets button. */
    function setPlayEnabled(enabled) {
      playButton.setAttribute("aria-disabled", enabled ? "false" : "true");
      if (enabled) playButton.removeAttribute("data-tooltip");
      else playButton.setAttribute("data-tooltip", "Load assets first");
    }
    function playDisabled() {
      return playButton.getAttribute("aria-disabled") === "true";
    }
    function showMessage(text) {
      status.textContent = text || "";
    }
    function describeInfo(info) {
      const parts = [];
      if (info.profiles?.length > 1) parts.push(`${info.profiles.length} languages`);
      else if (info.language) parts.push(info.language);
      if (info.edition) parts.push(info.edition);
      else if (info.layout) parts.push(info.layout);
      if (info.missing?.length) parts.push(`no ${info.missing.join(" or ")} files`);
      return parts.join(" · ");
    }
    function missingMediaMessage(info) {
      if (!info.missing?.length) return "";
      return `This installation has no ${info.missing.join(" or ")} files: the original ` +
        "installer left them on the CD. Load the disc image or the whole disc folder for sound.";
    }
    function showMainWindow(info, message) {
      configureAssetChoices(info);
      setPlayEnabled(info.available);
      assetsButton.textContent = info.available ? "Replace game data" : "Load game data";
      const detected = info.available ? describeInfo(info) : "";
      detectedRow.textContent = detected;
      detectedRow.hidden = !detected;
      showMessage(message || (info.available ? missingMediaMessage(info)
        : "Load your Caesar II game data to play, or drop it here."));
      panel.hidden = false;
    }
    async function showReady(source, message) {
      const info = source ? await sourceInfo(source) : {available:false, profiles:[]};
      if (!info.available) {
        localStorage.removeItem(ACTIVE_SOURCE);
        showMainWindow({available:false, profiles:[]},
          source ? "Cached game data is no longer available." : undefined);
        return;
      }
      showMainWindow(info, message);
    }
    /*
     * Play must work whenever usable data exists: the remembered source, any
     * previously imported cache directory, or data bundled with the build.
     */
    async function discoverSource() {
      const remembered = localStorage.getItem(ACTIVE_SOURCE);
      if (remembered && (await sourceInfo(remembered)).available) return remembered;
      try {
        const cache = await (await opfsRoot()).getDirectoryHandle("game-data");
        for await (const [name, handle] of cache.entries()) {
          if (handle.kind !== "directory") continue;
          const candidate = `/persistent/game-data/${name}`;
          if ((await sourceInfo(candidate)).available) return candidate;
        }
      } catch {}
      if (HAS_BUNDLED_ASSETS && (await sourceInfo("/assets")).available) return "/assets";
      return null;
    }
    async function bootstrap() {
      if (query.get("storage-check") === "1") {
        try { console.log(`browser durable files ${await storedSaveSummary()}`); }
        catch (e) { console.error(`browser durable files missing: ${e}`); }
        panel.hidden = false; showMessage("Storage check complete."); return;
      }
      const autostart = sessionStorage.getItem(AUTOSTART_SOURCE);
      if (autostart) {
        sessionStorage.removeItem(AUTOSTART_SOURCE);
        await startGame(autostart);
        return;
      }
      if (query.get("smoke-test") === "prepare") { prepareAssets("/assets"); return; }
      if (query.get("smoke-test")) { await startGame("/assets", true); return; }
      const pending = localStorage.getItem(PENDING_SOURCE);
      if (pending) { prepareAssets(pending); return; }
      const source = await discoverSource();
      if (source) localStorage.setItem(ACTIVE_SOURCE, source);
      else localStorage.removeItem(ACTIVE_SOURCE);
      await showReady(source);
      if (query.has("choose-data")) openAssetsModal();
    }

    const themeInputs = [...settingsDialog.querySelectorAll("input[name=c2-theme]")];
    const systemDark = matchMedia("(prefers-color-scheme: dark)");
    /* "system" leaves the choice to the OS; light and dark pin it. */
    function applyTheme(choice) {
      if (choice === "light" || choice === "dark") document.documentElement.dataset.theme = choice;
      else delete document.documentElement.dataset.theme;
      for (const input of themeInputs) input.checked = input.value === choice;
    }
    applyTheme(localStorage.getItem(THEME_CHOICE) || "system");
    systemDark.addEventListener("change", () => {
      if (!localStorage.getItem(THEME_CHOICE)) applyTheme("system");
    });
    const scalingInputs = [...settingsDialog.querySelectorAll("input[name=c2-scaling]")];
    const fullscreenToggle = document.getElementById("fullscreen-toggle");
    function applyScaling(mode) {
      scalingMode = mode === "fractional" ? "fractional" : "integer";
      for (const input of scalingInputs) input.checked = input.value === scalingMode;
      // CSS chooses the canvas box; SDL must use the matching logical
      // presentation or it will integer-letterbox inside a fractional box.
      if (gameRunning) {
        try { Module._c2_browser_set_fractional_scaling(scalingMode === "fractional" ? 1 : 0); }
        catch {}
      }
      scheduleCanvasResize();
    }
    applyScaling(scalingMode);
    for (const input of scalingInputs) {
      input.onchange = () => {
        localStorage.setItem(SCALING_MODE, input.value);
        applyScaling(input.value);
      };
    }
    /*
     * The recovered game has no autosave, so a closed tab loses the session.
     * Browsers only allow a generic prompt, and only when the player asked for
     * one, so this stays opt-in.
     */
    const confirmCloseToggle = document.getElementById("confirm-close-toggle");
    confirmCloseToggle.checked = localStorage.getItem(CONFIRM_CLOSE) === "1";
    confirmCloseToggle.onchange = () => {
      if (confirmCloseToggle.checked) localStorage.setItem(CONFIRM_CLOSE, "1");
      else localStorage.removeItem(CONFIRM_CLOSE);
    };
    addEventListener("beforeunload", event => {
      if (!gameRunning || !confirmCloseToggle.checked) return;
      event.preventDefault();
      event.returnValue = "";
    });
    fullscreenToggle.onchange = async () => {
      try {
        if (fullscreenToggle.checked) await document.documentElement.requestFullscreen();
        else if (document.fullscreenElement) await document.exitFullscreen();
      } catch {}
      fullscreenToggle.checked = !!document.fullscreenElement;
    };
    document.addEventListener("fullscreenchange", () => {
      fullscreenToggle.checked = !!document.fullscreenElement;
      if (gameRunning) {
        try { Module._c2_browser_set_fractional_scaling(scalingMode === "fractional" ? 1 : 0); }
        catch {}
      }
      scheduleCanvasResize();
    });
    /* Host chrome must not run over a live city: pause while it is open. */
    function setChromePause(paused) {
      if (!gameRunning || !runtimeReady) return;
      if (paused === pausedByChrome) return;
      try { Module._c2_browser_set_pause(paused ? 1 : 0); } catch { return; }
      pausedByChrome = paused;
    }
    for (const input of themeInputs) {
      input.onchange = () => {
        if (input.value === "system") localStorage.removeItem(THEME_CHOICE);
        else localStorage.setItem(THEME_CHOICE, input.value);
        applyTheme(input.value);
      };
    }
    profileSelect.onchange = () => localStorage.setItem(ACTIVE_PROFILE, profileSelect.value);
    bundledButton.hidden = !HAS_BUNDLED_ASSETS;
    /* Remember the choice label so the assets summary can repeat it verbatim. */
    function choiceLabel(button) {
      return button.childNodes[0].textContent.trim();
    }
    for (const [id, input, label] of [["folder-button", folderInput, "Folder"],
                                     ["file-button", fileInput, "File"]]) {
      document.getElementById(id).onclick = () => { chosenSourceLabel = label; input.click(); };
    }
    /* Anything can be dropped on the splash card or the settings drop zone. */
    for (const target of [card, sourceDrop]) {
      target.addEventListener("dragover", event => {
        if (gameRunning) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "copy";
        target.classList.add("is-over");
      });
      target.addEventListener("dragleave", () => target.classList.remove("is-over"));
      target.addEventListener("drop", event => {
        target.classList.remove("is-over");
        if (gameRunning) return;
        event.preventDefault();
        settingsDialog.close();
        importDrop(event.dataTransfer).catch(importFailed);
      });
    }
    bundledButton.onclick = async () => {
      if (!HAS_BUNDLED_ASSETS) return;
      settingsDialog.close();
      localStorage.setItem(ACTIVE_SOURCE, "/assets");
      localStorage.setItem(ACTIVE_ORIGIN, JSON.stringify({kind: choiceLabel(bundledButton), name: ""}));
      await showReady("/assets");
    };
    playButton.onclick = () => {
      const source = localStorage.getItem(ACTIVE_SOURCE);
      if (playDisabled()) { openAssetsModal(); return; }
      if (source) startGame(source);
    };
    assetsButton.onclick = openAssetsModal;
    document.getElementById("about-button").onclick = () => { setChromePause(true); aboutDialog.showModal(); };
    document.getElementById("about-close").onclick = () => aboutDialog.close();
    document.getElementById("settings-button").onclick = () => openSettings("general");
    document.getElementById("settings-close").onclick = () => settingsDialog.close();
    operationClose.onclick = () => {
      operationDialog.close();
      openSettings("assets");
    };
    for (const tab of settingsTabs) tab.onclick = () => selectSettingsPane(tab.dataset.pane);
    for (const dialog of [settingsDialog, aboutDialog]) {
      dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close(); });
      // Esc, the close button and backdrop clicks all end up here.
      dialog.addEventListener("close", () => {
        if (!settingsDialog.open && !aboutDialog.open) setChromePause(false);
      });
    }
    document.getElementById("userdata-export").onclick = exportUserData;
    document.getElementById("userdata-import").onclick = () => userDataInput.click();
    userDataDrop.addEventListener("dragover", event => {
      event.preventDefault();
      event.stopPropagation();
      event.dataTransfer.dropEffect = "copy";
      userDataDrop.classList.add("is-over");
    });
    userDataDrop.addEventListener("dragleave", () => userDataDrop.classList.remove("is-over"));
    userDataDrop.addEventListener("drop", event => {
      event.preventDefault();
      event.stopPropagation();
      userDataDrop.classList.remove("is-over");
      importUserData(event.dataTransfer.files).catch(e => userDataStatus.textContent = `Import failed: ${e.message}`);
    });
    forgetButton.onclick = forgetAssets;
    const importFailed = e => {
      settingsDialog.close();
      showOperationError(e.message);
      showMessage(`Import failed: ${e.message}`);
    };
    folderInput.onchange = () => { settingsDialog.close(); importFolder(inputEntries(folderInput.files)).catch(importFailed); };
    fileInput.onchange = () => { settingsDialog.close(); importFiles(fileInput.files).catch(importFailed); };
    userDataInput.onchange = () => {
      importUserData(userDataInput.files).catch(e => userDataStatus.textContent = `Import failed: ${e.message}`);
      userDataInput.value = "";
    };
    for (const link of document.querySelectorAll(".nav-action")) {
      link.addEventListener("click", event => event.preventDefault());
    }
    console.log(`Caesar II ${BUILD_VERSION}`);
    if (smokeOutput) globalThis.__c2SmokeOutput = smokeOutput;

    var Module = {
      noInitialRun: true,
      canvas,
      locateFile: (path, prefix) =>
        `${prefix}${path}?v=${encodeURIComponent(BUILD_VERSION)}`,
      print(text) { if (smokeOutput) smokeOutput.push(String(text)); console.log(text); },
      printErr(text) { if (smokeOutput) smokeOutput.push(String(text)); console.error(text); },
      setStatus(text) { if (gameRunning) status.textContent = text || ""; },
      monitorRunDependencies() {},
      onRuntimeInitialized() {
        runtimeReady = true;
        console.log(`cross-origin isolated ${globalThis.crossOriginIsolated}`);
        if (!globalThis.crossOriginIsolated) {
          showMessage("Cross-origin isolation is unavailable; threaded WebAssembly cannot start.");
          panel.hidden = false;
          return;
        }
        bootstrap();
      },
      onImportError(message) {
        pendingImportError = message;
      },
      onImportProgress(phase, completedKiB, totalKiB,
                       completedFiles, totalFiles) {
        operationTitle.textContent = phase;
        const suffix = totalFiles > 0
          ? ` · ${completedFiles}/${totalFiles} files`
          : "";
        updateOperation(completedKiB * 1024, totalKiB * 1024, suffix);
      },
      async onSourceReady(resolved, original) {
        const active = resolved.replace(/\/ACTIVE-[^/]+$/, "");
        localStorage.setItem(ACTIVE_SOURCE, active);
        localStorage.removeItem(PENDING_SOURCE);
        const origin = localStorage.getItem(PENDING_ORIGIN);
        if (origin) localStorage.setItem(ACTIVE_ORIGIN, origin);
        else localStorage.removeItem(ACTIVE_ORIGIN);
        localStorage.removeItem(PENDING_ORIGIN);
        if (original.startsWith("/persistent/incoming/files-")) {
          try {
            const generation = original.slice("/persistent/incoming/".length).split("/")[0];
            const incoming = await (await opfsRoot()).getDirectoryHandle("incoming");
            await incoming.removeEntry(generation, {recursive:true});
          } catch {}
        }
        // Do not await: a storage-permission prompt must not stall the shell.
        requestPersistence().catch(() => {});
        if (preparingAssets) {
          preparingAssets = false;
          if (query.get("smoke-test") === "prepare") {
            await showReady(active);
            const message = playDisabled()
              ? "asset preparation left play disabled"
              : "asset preparation completed without starting the game";
            endOperation();
            smokeOutput.push(message); console.log(message);
            return;
          }
          // Reload so the imported data is served by a fresh runtime and the
          // user returns to the main window instead of straight into the game.
          updateOperation(0, 0, "Complete");
          showMessage("Game data imported.");
          location.replace(location.pathname);
        }
      },
      onAbort(reason) {
        const importFailure = preparingAssets;
        const message = pendingImportError || reason || "Invalid game data";
        gameRunning = false; preparingAssets = false; panel.hidden = false;
        document.body.classList.remove("playing");
        localStorage.removeItem(PENDING_SOURCE);
        localStorage.removeItem(PENDING_ORIGIN);
        const previous = localStorage.getItem(ACTIVE_SOURCE);
        if (importFailure) {
          showOperationError(message);
          showReady(previous, `Import failed: ${message}.` +
            (previous ? " Your previous game data is still available." : ""));
        } else {
          endOperation();
          showReady(previous, `Start failed: ${message}.`);
        }
        pendingImportError = undefined;
      },
      onExit(code) {
        if (code) Module.onAbort(`exit status ${code}`);
      },
      async onGameExit() {
        gameRunning = false;
        document.body.classList.remove("playing");
        await showReady(localStorage.getItem(ACTIVE_SOURCE));
        if (query.get("smoke-test") === "restart") {
          const key = "c2.restart-smoke.v1";
          if (sessionStorage.getItem(key)) {
            sessionStorage.removeItem(key);
            const message = "restart after exit completed";
            smokeOutput.push(message); console.log(message);
          } else {
            sessionStorage.setItem(key, "1");
            playButton.click();
          }
        }
        if (query.get("smoke-test") === "save") {
          try { console.log(`browser save persistence ${await storedSaveSummary()}`); }
          catch (e) { console.error(`browser save persistence failed: ${e}`); }
        }
      }
    };
