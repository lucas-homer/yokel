// Render decisive-mark regions of MS notice forms into one labelled PNG per review item.
// usage: render-marks <spec.json>
// spec: {"out": path, "scale": 1.8, "parts": [{"label": str, "pdf": path, "page": 1,
//        "crops": [[x0, y0, x1, y1], ...]}]}  (crop fractions, top-left origin)
// Renders are derivatives for owner viewing; they are written outside git.
import AppKit
import Foundation
import PDFKit

let spec = try! JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))) as! [String: Any]
let scale = CGFloat(spec["scale"] as! Double)
var tiles: [CGImage] = []

func label(_ text: String, width: Int) -> CGImage {
    let h = 30
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: h, bitsPerSample: 8, samplesPerPixel: 4,
                               hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    let g = NSGraphicsContext(bitmapImageRep: rep)!
    NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = g
    NSColor(calibratedWhite: 0.15, alpha: 1).setFill(); NSRect(x: 0, y: 0, width: width, height: h).fill()
    (text as NSString).draw(at: NSPoint(x: 8, y: 6), withAttributes: [.font: NSFont.boldSystemFont(ofSize: 17), .foregroundColor: NSColor.white])
    NSGraphicsContext.restoreGraphicsState()
    return rep.cgImage!
}

for part in spec["parts"] as! [[String: Any]] {
    guard let pdf = PDFDocument(url: URL(fileURLWithPath: part["pdf"] as! String)),
          let page = pdf.page(at: (part["page"] as! Int) - 1) else { fatalError("Cannot read \(part["label"]!)") }
    let box = page.bounds(for: .mediaBox)
    let rotated = page.rotation % 180 != 0
    let w = Int((rotated ? box.height : box.width) * scale), h = Int((rotated ? box.width : box.height) * scale)
    let full = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8, samplesPerPixel: 4,
                                hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    let g = NSGraphicsContext(bitmapImageRep: full)!
    NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = g
    g.cgContext.setFillColor(NSColor.white.cgColor); g.cgContext.fill(CGRect(x: 0, y: 0, width: w, height: h))
    g.cgContext.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: g.cgContext)
    NSGraphicsContext.restoreGraphicsState()
    let cg = full.cgImage!
    tiles.append(label(part["label"] as! String, width: w))
    for c in part["crops"] as! [[Double]] {
        let r = CGRect(x: c[0] * Double(w), y: c[1] * Double(h), width: (c[2] - c[0]) * Double(w), height: (c[3] - c[1]) * Double(h)).integral
        tiles.append(cg.cropping(to: r)!)
    }
}
let gap = 4
let outW = tiles.map { $0.width }.max()!
let outH = tiles.map { $0.height }.reduce(0, +) + gap * (tiles.count - 1)
let out = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: outW, pixelsHigh: outH, bitsPerSample: 8, samplesPerPixel: 4,
                           hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
let og = NSGraphicsContext(bitmapImageRep: out)!
NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = og
og.cgContext.setFillColor(NSColor(calibratedRed: 0.8, green: 0.1, blue: 0.1, alpha: 1).cgColor)
og.cgContext.fill(CGRect(x: 0, y: 0, width: outW, height: outH))
var y = outH
for t in tiles {
    y -= t.height
    og.cgContext.draw(t, in: CGRect(x: 0, y: y, width: t.width, height: t.height))
    y -= gap
}
NSGraphicsContext.restoreGraphicsState()
try! out.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: spec["out"] as! String))
