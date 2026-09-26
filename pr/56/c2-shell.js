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
    const forgetButton = document.getElementById("forget-button");
    const folderInput = document.getElementById("folder-input");
    const fileInput = document.getElementById("file-input");
    const card = document.getElementById("card");
    const detectedRow = document.getElementById("detected-row");
    const playButton = document.getElementById("play-button");
    const speechRowMain = document.getElementById("speech-row");
    const speechSelectMain = document.getElementById("speech-select-main");
    const speechRow = document.getElementById("speech-setting");
    const speechSelect = document.getElementById("speech-select");
    const exportButton = document.getElementById("export-button");
    const languageSelect = document.getElementById("language-select");
    const musicSelect = document.getElementById("music-select");
    const musicHint = document.getElementById("music-hint");
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
    const BUILD_VERSION = "pr56-24f1562d";
    /* The upload to import after the reload that follows copying it. */
    const PENDING_SOURCE = "c2.pending-source.v1";
    const SPEECH = "c2.speech.v1";
    /* Before the library the page remembered its source and where it came
     * from; these keys are read once for the migration, then removed. */
    const LEGACY_ACTIVE_SOURCE = "c2.active-source.v1";
    const LEGACY_KEYS = ["c2.active-source.v1", "c2.active-profile.v1", "c2.active-origin.v1", "c2.pending-origin.v1"];
    const THEME_CHOICE = "c2.theme.v1";
    const SCALING_MODE = "c2.scaling.v1";
    const TEXT_LANGUAGE = "c2.text-language.v1";
    const MUSIC_SOURCE = "c2.music.v1";
    const CONFIRM_CLOSE = "c2.confirm-close.v1";
    const AUTOSTART = "c2.autostart.v1";
    let runtimeReady = false;
    let gameRunning = false;
    let preparingAssets = false;
    let exporting = false;
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
    /*
     * What the game data holds is decided in C (docs/game-data-library.md):
     * every import is merged into /persistent/game-data/library and the
     * runtime writes a summary beside it, one fact per line. The page only
     * reads that summary.
     */
    const emptySummary = () => ({playable:false, languages:[], music:{dos:false, windows:false}, movies:0, enhanced:0, bytes:0});
    async function readSummary() {
      const summary = emptySummary();
      try {
        const local = await directoryAt("game-data/local", false);
        const text = await (await (await local.getFileHandle("summary")).getFile()).text();
        const lines = text.split("\n");
        if (lines[0] !== "c2-game-data 1") return summary;
        for (const line of lines.slice(1)) {
          const words = line.split(" ");
          if (words[0] === "playable") summary.playable = words[1] === "1";
          else if (words[0] === "language") {
            summary.languages.push({tag: words[1], speech: words[2] === "speech", tree: words[3],
                                    version: words.slice(4).join(" ")});
          } else if (words[0] === "music") summary.music[words[1]] = true;
          else if (words[0] === "movies") { summary.movies = +words[1]; summary.enhanced = +words[2]; }
          else if (words[0] === "bytes") summary.bytes = +words[1];
        }
      } catch {}
      return summary;
    }
    /* Game data from before the library: caches in game-data/<key>/ and a
     * folder import left in incoming/. The runtime folds them in once. */
    async function legacyGameData() {
      if (localStorage.getItem(LEGACY_ACTIVE_SOURCE)) return true;
      try {
        const dir = await directoryAt("game-data", false);
        for await (const [name] of dir.entries()) if (/^[0-9a-f]{16}$/.test(name)) return true;
      } catch {}
      return false;
    }
    const languageNames = {en:"English", de:"German", fr:"French", it:"Italian", es:"Spanish", und:"Unknown language"};
    function speechLanguages(summary) {
      return summary.languages.filter(l => l.speech);
    }
    /* The speech that plays: the choice, else the text language, else English, else the first. */
    function activeSpeech(summary) {
      const speech = speechLanguages(summary).map(l => l.tag);
      const wanted = localStorage.getItem(SPEECH) || localStorage.getItem(TEXT_LANGUAGE) || "";
      if (speech.includes(wanted)) return wanted;
      if (speech.includes("en")) return "en";
      return speech[0] || "";
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
    function showOperationError(message, title = "Import failed") {
      operationTitle.textContent = title;
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
      requestPersistence().catch(() => {});
      location.href = location.pathname + smokeQuery();
    }
    /* Same signatures the native importer sniffs: ZIP, raw CD sector,
     * ISO-9660, and the Macintosh discs' HFS behind an Apple partition map. */
    async function fileLooksImportable(file) {
      const head = new Uint8Array(await file.slice(0, 1026).arrayBuffer());
      if (head[0] === 0x50 && head[1] === 0x4b && head[2] === 3 && head[3] === 4) return "zip";
      const sync = [0, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 0];
      if (head.length >= 16 && sync.every((b, i) => head[i] === b) && (head[15] === 1 || head[15] === 2)) return "bin";
      if (head.length === 1026 && ((head[0] === 0x45 && head[1] === 0x52 && head[512] === 0x50 && head[513] === 0x4d) ||
                                   (head[1024] === 0x42 && head[1025] === 0x44))) return "hfs";
      const pvd = new Uint8Array(await file.slice(16 * 2048, 16 * 2048 + 6).arrayBuffer());
      if (String.fromCharCode(...pvd.slice(1, 6)) === "CD001") return "iso";
      if (/\.cue$/i.test(file.name)) return "cue";
      return null;
    }
    /* A smoke test's query survives the reloads of an import. */
    function smokeQuery() {
      return query.get("smoke-test") ? `?smoke-test=${encodeURIComponent(query.get("smoke-test"))}` : "";
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
        throw new Error(`${name} is not a Caesar II disc image, ZIP or .c2assets file`);
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
      requestPersistence().catch(() => {});
      location.href = location.pathname + smokeQuery();
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
        const collected = [];
        await collectEntry(directories[0], "", collected);
        await importFolder(collected);
        return;
      }
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
    /* What the game data holds, as the runtime reports it. */
    async function updateAssetsSummary() {
      const summary = await readSummary();
      const has = summary.languages.length > 0;
      assetsSummary.replaceChildren();
      assetsLoaded.hidden = !has;
      assetsEmpty.hidden = has;
      sourceDropTitle.textContent = has
        ? "Drop more game data here: what is new or better is added"
        : "Drop your Caesar II folder, disc image or ZIP here";
      exportButton.disabled = !summary.playable || gameRunning;
      if (!has) return summary;
      const rows = [];
      const speech = speechLanguages(summary);
      rows.push(["Speech", speech.length ? speech.map(l => `${languageNames[l.tag] || l.tag} (${l.version})`).join(", ") : "none"]);
      rows.push(["Music", summary.music.dos && summary.music.windows ? "DOS (1995) and Windows (1996)"
        : summary.music.dos ? "DOS (1995)" : summary.music.windows ? "Windows (1996)" : "none"]);
      rows.push(["Movies", summary.enhanced ? `${summary.movies}, ${summary.enhanced} larger than the originals` : `${summary.movies}`]);
      rows.push(["Size", formatBytes(summary.bytes)]);
      if (!summary.playable) rows.push(["Missing", "a PC installation or disc: this is not enough to play"]);
      for (const [term, value] of rows) {
        const dt = document.createElement("dt"); dt.textContent = term;
        const dd = document.createElement("dd"); dd.textContent = value;
        assetsSummary.append(dt, dd);
      }
      configureMusicChoice(summary.music);
      configureSpeechChoice(summary);
      return summary;
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
      if (pane === "assets") assetsStatus.textContent = "";
    }
    /* The dialog is as tall as its tallest pane, so the game-data summary
     * is filled in as it opens rather than when its tab is first used;
     * otherwise the dialog would grow under the player's hand. */
    function refreshSettings() {
      updateAssetsSummary().catch(error => {
        assetsStatus.textContent = `Could not inspect the loaded game data: ${error.message}`;
      });
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
      refreshSettings();
      setChromePause(true);
      if (!settingsDialog.open) settingsDialog.showModal();
    }
    function openAssetsModal() {
      openSettings("assets");
    }
    async function forgetAssets() {
      if (!confirm("Remove all game data? Saves and settings will be kept.")) return;
      settingsDialog.close();
      const root = await opfsRoot();
      beginOperation("Removing game data", 0, "Deleting…");
      for (const name of ["game-data", "incoming"]) {
        try { await root.removeEntry(name, {recursive:true}); } catch {}
      }
      for (const key of LEGACY_KEYS) localStorage.removeItem(key);
      localStorage.removeItem(SPEECH);
      await updateAssetsSummary();
      assetsStatus.textContent = "Removed the game data.";
      endOperation();
      showMainWindow(emptySummary());
      openSettings("assets");
    }
    function gameArgs() {
      const args = [];
      const speech = localStorage.getItem(SPEECH);
      if (speech) args.push("--speech", speech);
      const language = localStorage.getItem(TEXT_LANGUAGE);
      if (language) args.push("--language", language);
      const music = localStorage.getItem(MUSIC_SOURCE);
      if (music) args.push("--music", music);
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
    /*
     * The runtime runs once per page: the game, an import or an export.
     * After one of them the page reloads to run the next.
     */
    function reloadFor(key) {
      if (key) sessionStorage.setItem(key, "1");
      location.replace(location.pathname + smokeQuery());
    }
    async function startGame() {
      if (!runtimeReady || gameRunning) return;
      if (!(await readSummary()).playable) {
        showMainWindow(await readSummary(), "The game data is not enough to play yet.");
        return;
      }
      if (engineHasRun) {
        showMessage("Restarting…");
        reloadFor(AUTOSTART);
        return;
      }
      engineHasRun = true;
      gameRunning = true; panel.hidden = true;
      document.body.classList.add("playing");
      showMessage("Starting…");
      Module.callMain(gameArgs());
    }
    /*
     * Add an uploaded source to the library (or, with none, fold in game
     * data from before the library) without starting the engine, then
     * reload into the main window so the user decides when to play.
     */
    function prepareAssets(source) {
      if (!runtimeReady || gameRunning) return;
      engineHasRun = true;
      preparingAssets = true;
      panel.hidden = false;
      showMessage("Adding game data…");
      pendingImportError = undefined;
      beginOperation("Reading the game data", 0, "Reading source catalog…");
      const args = ["--prepare-assets"];
      if (source) args.unshift("--game-data", source);
      Module.callMain(args);
    }
    /* Settings > Game data > Export: the library, zipped, as a download. */
    const EXPORT_PATH = "/persistent/export/caesar2.c2assets";
    async function exportGameData() {
      if (!runtimeReady || gameRunning) return;
      if (engineHasRun) { reloadFor("c2.export.v1"); return; }
      engineHasRun = true;
      exporting = true;
      settingsDialog.close();
      pendingImportError = undefined;
      await directoryAt("export");
      beginOperation("Writing the game-data archive", 0, "Starting…");
      Module.callMain(["--export-game-data", EXPORT_PATH]);
    }
    async function downloadExport() {
      const dir = await directoryAt("export", false);
      const file = await (await dir.getFileHandle("caesar2.c2assets")).getFile();
      const url = URL.createObjectURL(file);
      const link = document.createElement("a");
      link.href = url;
      link.download = "caesar2.c2assets";
      document.body.append(link);
      link.click();
      link.remove();
      // The file stays until the next page load; the download reads it.
      setTimeout(() => URL.revokeObjectURL(url), 600_000);
    }
    /*
     * Settings > General > Text language. The game text is compiled into
     * the runtime in every language it knows; the engine detects the game
     * data's own language unless one is chosen here. Speech stays whatever
     * the game data provides. The list comes from the runtime once it is
     * ready; until then only Automatic is offered.
     */
    languageSelect.onchange = () => {
      if (languageSelect.value) localStorage.setItem(TEXT_LANGUAGE, languageSelect.value);
      else localStorage.removeItem(TEXT_LANGUAGE);
    };
    /*
     * Settings > Game data > Music. Caesar II has two soundtracks, by
     * different composers: the 1995 DOS music (Jeremy A. Bell and Jason P.
     * Rinaldi), which the game's synthesizer plays and branches with the
     * city's mood, and the 1996 Windows music (Keith Zizza), recorded from
     * hardware synthesizers. This says which the loaded data has and, with
     * both, which plays; a change while the game runs switches in place.
     */
    musicSelect.onchange = () => {
      localStorage.setItem(MUSIC_SOURCE, musicSelect.value);
      if (gameRunning) {
        try { Module._c2_browser_set_music_source(musicSelect.value === "windows" ? 1 : 0); }
        catch {}
      }
    };
    function configureMusicChoice(music) {
      const has = {dos: music.dos, windows: music.windows};
      const stored = localStorage.getItem(MUSIC_SOURCE);
      const preferred = stored === "windows" || stored === "recorded" ? "windows" : "dos";
      for (const option of musicSelect.options) option.disabled = !has[option.value];
      musicSelect.value = has[preferred] ? preferred : has.dos ? "dos" : has.windows ? "windows" : preferred;
      musicSelect.disabled = !(has.dos && has.windows);
      musicHint.textContent = has.dos && has.windows
        ? "Two different soundtracks. The 1995 one is played by a synthesizer and follows your city's mood; the 1996 one was recorded with real instruments for the Windows release and repeats three pieces."
        : has.windows ? "This game data has the 1996 Windows music only (the 1998 disc, or a Mac disc)."
        : has.dos ? "This game data has the 1995 DOS music only (discs before August 1996)."
        : "This game data has no music.";
    }
    function configureTextLanguages() {
      let listing = "";
      try { listing = Module.UTF8ToString(Module._c2_browser_text_languages()); }
      catch { return; }
      const languages = listing.split("\n").filter(Boolean).map(row => row.split("\t"));
      for (const option of [...languageSelect.options].slice(1)) option.remove();
      for (const [tag, name] of languages) {
        const option = document.createElement("option");
        option.value = tag; option.textContent = name;
        languageSelect.append(option);
      }
      const stored = localStorage.getItem(TEXT_LANGUAGE) || "";
      languageSelect.value = languages.some(([tag]) => tag === stored) ? stored : "";
    }
    /* Speech: one choice per language the game data has voices for. */
    function configureSpeechChoice(summary) {
      const speech = speechLanguages(summary);
      for (const select of [speechSelect, speechSelectMain]) {
        select.replaceChildren();
        for (const l of speech) {
          const option = document.createElement("option");
          option.value = l.tag; option.textContent = languageNames[l.tag] || l.tag;
          select.append(option);
        }
        select.value = activeSpeech(summary);
      }
      speechRow.hidden = speech.length < 2;
      speechRowMain.hidden = speech.length < 2;
    }
    /* Keep Play focusable so its tooltip can point at the assets button. */
    function setPlayEnabled(enabled) {
      playButton.setAttribute("aria-disabled", enabled ? "false" : "true");
      if (enabled) playButton.removeAttribute("data-tooltip");
      else playButton.setAttribute("data-tooltip", "Load game data first");
    }
    function playDisabled() {
      return playButton.getAttribute("aria-disabled") === "true";
    }
    function showMessage(text) {
      status.textContent = text || "";
    }
    function describeSummary(summary) {
      const parts = [];
      const speech = speechLanguages(summary);
      if (speech.length > 1) parts.push(`speech in ${speech.map(l => languageNames[l.tag] || l.tag).join(", ")}`);
      else if (speech.length) parts.push(`${languageNames[speech[0].tag] || speech[0].tag} ${speech[0].version}`);
      if (summary.music.dos && summary.music.windows) parts.push("both soundtracks");
      if (summary.enhanced) parts.push(`${summary.enhanced} larger movies`);
      return parts.join(" · ");
    }
    function missingMessage(summary) {
      if (!summary.languages.length) return "";
      if (!summary.playable) return "This game data is not enough to play: add a PC installation or disc.";
      const missing = [];
      if (!summary.music.dos && !summary.music.windows) missing.push("music");
      if (!speechLanguages(summary).length) missing.push("speech");
      if (!missing.length) return "";
      return `There are no ${missing.join(" or ")} files: the original installer left them on the CD. ` +
        "Add the disc image or the whole disc folder for sound.";
    }
    function showMainWindow(summary, message) {
      configureSpeechChoice(summary);
      setPlayEnabled(summary.playable);
      assetsButton.textContent = summary.languages.length ? "Game data" : "Load game data";
      const detected = summary.playable ? describeSummary(summary) : "";
      detectedRow.textContent = detected;
      detectedRow.hidden = !detected;
      showMessage(message || (summary.languages.length ? missingMessage(summary)
        : "Load your Caesar II game data to play, or drop it here."));
      panel.hidden = false;
    }
    async function showReady(message) {
      showMainWindow(await readSummary(), message);
    }
    async function bootstrap() {
      if (query.get("storage-check") === "1") {
        try { console.log(`browser durable files ${await storedSaveSummary()}`); }
        catch (e) { console.error(`browser durable files missing: ${e}`); }
        panel.hidden = false; showMessage("Storage check complete."); return;
      }
      // A finished export is downloaded; nothing keeps the copy afterwards.
      try { await (await opfsRoot()).removeEntry("export", {recursive:true}); } catch {}
      if (sessionStorage.getItem(AUTOSTART)) {
        sessionStorage.removeItem(AUTOSTART);
        await startGame();
        return;
      }
      if (sessionStorage.getItem("c2.export.v1")) {
        sessionStorage.removeItem("c2.export.v1");
        await exportGameData();
        return;
      }
      const pending = localStorage.getItem(PENDING_SOURCE);
      if (pending) { prepareAssets(pending); return; }
      if (await legacyGameData()) {
        // A folder imported before the library lived in incoming/: add it.
        const old = localStorage.getItem(LEGACY_ACTIVE_SOURCE);
        for (const key of LEGACY_KEYS) localStorage.removeItem(key);
        prepareAssets(old && old.startsWith("/persistent/incoming/") ? old : null);
        return;
      }
      const summary = await readSummary();
      /*
       * tools/smoke-wasm.mjs: run a smoke against whatever game data is in
       * the browser's storage; with none, the page waits at Load game data
       * for the tool to upload some (the query survives that import).
       */
      const smoke = query.get("smoke-test");
      if (smoke && summary.playable) {
        if (smoke === "prepare") prepareAssets(null);
        else if (smoke === "export") await exportGameData();
        else await startGame();
        return;
      }
      if (smoke && query.get("smoke-data")) {
        // The tool serves the game data; import it as a dropped file would
        // be, which reloads the page (query intact) once it is in storage.
        const url = query.get("smoke-data");
        const response = await fetch(url);
        if (!response.ok) throw new Error(`smoke data ${url}: ${response.status}`);
        const name = decodeURIComponent(url.split("/").pop());
        importFiles([new File([await response.blob()], name)]).catch(importFailed);
        return;
      }
      showMainWindow(summary);
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
     * A closed tab ends the session where it is. Browsers only allow a
     * generic prompt, and only when the player asked for one, so this
     * stays opt-in.
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
    /* Speech is chosen on the card and in Settings > Game data alike. */
    for (const select of [speechSelect, speechSelectMain]) {
      select.onchange = async () => {
        localStorage.setItem(SPEECH, select.value);
        configureSpeechChoice(await readSummary());
      };
    }
    exportButton.onclick = () => exportGameData().catch(importFailed);
    for (const [id, input] of [["folder-button", folderInput], ["file-button", fileInput]]) {
      document.getElementById(id).onclick = () => input.click();
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
    playButton.onclick = () => {
      if (playDisabled()) { openAssetsModal(); return; }
      startGame();
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
        configureTextLanguages();
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
      /* An import (or migration) finished: everything uploaded is in the
       * library now, so the uploads go. */
      async onLibraryChanged() {
        localStorage.removeItem(PENDING_SOURCE);
        try { await (await opfsRoot()).removeEntry("incoming", {recursive:true}); } catch {}
        // Do not await: a storage-permission prompt must not stall the shell.
        requestPersistence().catch(() => {});
        if (preparingAssets) {
          preparingAssets = false;
          if (query.get("smoke-test") === "prepare") {
            await showReady();
            const message = playDisabled()
              ? "asset preparation left play disabled"
              : "asset preparation completed without starting the game";
            endOperation();
            smokeOutput.push(message); console.log(message);
            return;
          }
          // Reload so the user returns to the main window with a fresh
          // runtime instead of going straight into the game.
          updateOperation(0, 0, "Complete");
          showMessage("Game data added.");
          location.replace(location.pathname + smokeQuery());
        }
      },
      async onExportReady(path) {
        exporting = false;
        updateOperation(0, 0, "Complete");
        await downloadExport();
        endOperation();
        showMessage(`Exported the game data as ${path.split("/").pop()}.`);
        if (query.get("smoke-test") === "export") {
          const message = "game data exported";
          smokeOutput.push(message); console.log(message);
        }
      },
      onAbort(reason) {
        const importFailure = preparingAssets || exporting;
        const message = pendingImportError || reason || "Invalid game data";
        const what = exporting ? "Export" : "Import";
        gameRunning = false; preparingAssets = false; exporting = false; panel.hidden = false;
        document.body.classList.remove("playing");
        localStorage.removeItem(PENDING_SOURCE);
        if (importFailure) {
          showOperationError(message, `${what} failed`);
          showReady(`${what} failed: ${message}. The game data you had is unchanged.`);
        } else {
          endOperation();
          showReady(`Start failed: ${message}.`);
        }
        pendingImportError = undefined;
      },
      onExit(code) {
        if (code) Module.onAbort(`exit status ${code}`);
      },
      async onGameExit() {
        gameRunning = false;
        document.body.classList.remove("playing");
        await showReady();
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
