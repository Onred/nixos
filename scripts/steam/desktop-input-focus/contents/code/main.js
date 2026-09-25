function reportFocusedWindow(window) {
    const pid = window && !window.deleted ? window.pid : 0;
    const desktopFileName = window ? window.desktopFileName : "";

    callDBus(
        "org.onred.SteamDesktopInput",
        "/org/onred/SteamDesktopInput",
        "org.onred.SteamDesktopInput",
        "SetFocusedWindow",
        pid,
        desktopFileName || ""
    );
}

workspace.windowActivated.connect(reportFocusedWindow);
reportFocusedWindow(workspace.activeWindow);
