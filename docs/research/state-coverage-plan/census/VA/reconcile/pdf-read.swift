import Foundation
import PDFKit
import AppKit
let args = CommandLine.arguments
let url = URL(fileURLWithPath: args[1])
guard let pdf = PDFDocument(url: url) else { fatalError("Cannot read PDF") }
let pageNo = Int(args[2])!
guard let page = pdf.page(at: pageNo - 1) else { fatalError("No such page") }
if args.count > 3 {
    let rect = page.bounds(for: .mediaBox)
    let scale: CGFloat = 1.5
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(rect.width * scale), pixelsHigh: Int(rect.height * scale), bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    let graphics = NSGraphicsContext(bitmapImageRep: bitmap)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = graphics
    graphics.cgContext.setFillColor(NSColor.white.cgColor)
    graphics.cgContext.fill(CGRect(x:0,y:0,width:rect.width*scale,height:rect.height*scale))
    graphics.cgContext.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: graphics.cgContext)
    NSGraphicsContext.restoreGraphicsState()
    try bitmap.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: args[3]))
} else {
    print(page.string ?? "[no text]")
}
