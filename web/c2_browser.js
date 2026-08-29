mergeInto(LibraryManager.library, {
  c2_browser_show_restart__proxy: "sync",
  c2_browser_show_restart: function() {
    if (Module["onGameExit"]) {
      Module["onGameExit"]();
    }
  },
  c2_browser_source_ready__deps: ["$UTF8ToString"],
  c2_browser_source_ready__proxy: "sync",
  c2_browser_source_ready: function(resolved, original) {
    if (Module["onSourceReady"]) {
      Module["onSourceReady"](UTF8ToString(resolved), UTF8ToString(original));
    }
  },
  c2_browser_import_progress__deps: ["$UTF8ToString"],
  c2_browser_import_progress__proxy: "sync",
  c2_browser_import_progress: function(phase, completed, total,
                                       completedFiles, totalFiles) {
    if (Module["onImportProgress"]) {
      Module["onImportProgress"](UTF8ToString(phase), completed, total,
                                 completedFiles, totalFiles);
    }
  },
  c2_browser_import_error__deps: ["$UTF8ToString"],
  c2_browser_import_error__proxy: "sync",
  c2_browser_import_error: function(message) {
    if (Module["onImportError"]) {
      Module["onImportError"](UTF8ToString(message));
    }
  },
});
