import Cocoa
import WebKit

let HOME = FileManager.default.homeDirectoryForCurrentUser.path
let DASH = "\(HOME)/.config/nerv-theme/dashboard/nerv-dash"

// Ask nerv-dash for a free {stats ttyd shell} port triplet so multiple NERV
// windows can run at once (one per project). Falls back to the defaults.
func pickPorts() -> (stats: String, ttyd: String, shell: String) {
  let p = Process(); p.executableURL = URL(fileURLWithPath: "/bin/bash")
  p.arguments = [DASH, "ports"]
  let pipe = Pipe(); p.standardOutput = pipe
  do {
    try p.run(); p.waitUntilExit()
    let out = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
    let f = out.split(whereSeparator: { $0 == " " || $0 == "\n" }).map(String.init)
    if f.count >= 3 { return (f[0], f[1], f[2]) }
  } catch {}
  return ("8731", "7682", "7683")
}
let PORTS = pickPorts()
let DASH_URL = "http://127.0.0.1:\(PORTS.stats)/"

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
    // bring up the backend services (no browser) — the app IS the window.
    // Pass the picked ports so each app window gets its own instance.
    let t = Process()
    t.executableURL = URL(fileURLWithPath: "/bin/bash")
    t.arguments = [DASH, "serve"]
    var env = ProcessInfo.processInfo.environment
    env["NERV_PORT"] = PORTS.stats; env["NERV_TTYD_PORT"] = PORTS.ttyd; env["NERV_SHELL_PORT"] = PORTS.shell
    t.environment = env
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
