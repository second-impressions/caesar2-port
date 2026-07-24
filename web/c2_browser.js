mergeInto(LibraryManager.library, {
  c2_browser_show_restart__proxy: "sync",
  c2_browser_show_restart: function() {
    if (Module["onGameExit"]) {
      Module["onGameExit"]();
    }
  },
});
