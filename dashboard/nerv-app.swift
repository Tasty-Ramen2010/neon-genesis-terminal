import Cocoa
import WebKit

let HOME = FileManager.default.homeDirectoryForCurrentUser.path
let DASH = "\(HOME)/.config/nerv-theme/dashboard/nerv-dash"
let DASH_URL = "http://127.0.0.1:8731/"

final class WinDelegate: NSObject, NSWindowDelegate {
  func windowWillClose(_ n: Notification) { NSApp.terminate(nil) }
}

final class Nav: NSObject, WKNavigationDelegate {
  weak var web: WKWebView?
  func webView(_ w: WKWebView, didFail n: WKNavigation!, withError e: Error) { retry() }
  func webView(_ w: WKWebView, didFailProvisionalNavigation n: WKNavigation!, withError e: Error) { retry() }
  func retry() {
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
      self.web?.load(URLRequest(url: URL(string: DASH_URL)!))
    }
  }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
  var window: NSWindow!
  var web: WKWebView!
  let nav = Nav()
  let wd = WinDelegate()

  func applicationDidFinishLaunching(_ note: Notification) {
    // bring up the backend services (no browser) — the app IS the window
    let t = Process()
    t.executableURL = URL(fileURLWithPath: "/bin/bash")
    t.arguments = [DASH, "serve"]
    try? t.run()

    // open MAXIMIZED — fill the screen's visible frame (keeps menu bar)
    let vis = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1600, height: 1000)
    window = NSWindow(contentRect: vis,
      styleMask: [.titled, .closable, .resizable, .miniaturizable, .fullSizeContentView],
      backing: .buffered, defer: false)
    window.title = "NERV // MAGI"
    window.titlebarAppearsTransparent = true
    window.titleVisibility = .hidden
    window.isMovableByWindowBackground = true
    window.backgroundColor = .black
    window.setFrame(vis, display: true)
    window.delegate = wd

    let conf = WKWebViewConfiguration()
    web = WKWebView(frame: vis, configuration: conf)
    web.navigationDelegate = nav
    nav.web = web
    if #available(macOS 12.0, *) { web.underPageBackgroundColor = .black }
    window.contentView = web
    web.load(URLRequest(url: URL(string: DASH_URL)!))

    window.makeKeyAndOrderFront(nil)
    NSApp.activate(ignoringOtherApps: true)
  }

  func applicationShouldTerminateAfterLastWindowClosed(_ s: NSApplication) -> Bool { true }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
