mergeInto(LibraryManager.library, {
  c2_browser_show_restart__proxy: "sync",
  c2_browser_show_restart: function() {
    if (Module["onGameExit"]) {
      Module["onGameExit"]();
    }
  },
  c2_browser_library_changed__proxy: "sync",
  c2_browser_library_changed: function() {
    if (Module["onLibraryChanged"]) Module["onLibraryChanged"]();
  },
  c2_browser_export_ready__deps: ["$UTF8ToString"],
  c2_browser_export_ready__proxy: "sync",
  c2_browser_export_ready: function(path) {
    if (Module["onExportReady"]) Module["onExportReady"](UTF8ToString(path));
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
