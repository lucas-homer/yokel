import Foundation
import PDFKit
import CoreGraphics
// usage: pdfpages <file>... ; JSON per file: pages, chars per page, images per page (direct XObject images incl. one form level)
func countImages(_ res: CGPDFDictionaryRef?, depth: Int) -> Int {
  guard let res = res, depth < 3 else { return 0 }
  var xobj: CGPDFDictionaryRef? = nil
  guard CGPDFDictionaryGetDictionary(res, "XObject", &xobj), let xo = xobj else { return 0 }
  var n = 0
  CGPDFDictionaryApplyBlock(xo, { _, obj, _ in
    var s: CGPDFStreamRef? = nil
    if CGPDFObjectGetValue(obj, .stream, &s), let st = s, let d = CGPDFStreamGetDictionary(st) {
      var name: UnsafePointer<Int8>? = nil
      if CGPDFDictionaryGetName(d, "Subtype", &name), let nm = name {
        let sub = String(cString: nm)
        if sub == "Image" { n += 1 }
        else if sub == "Form" { var r: CGPDFDictionaryRef? = nil; if CGPDFDictionaryGetDictionary(d, "Resources", &r) { n += countImages(r, depth: depth + 1) } }
      }
    }
    return true
  }, nil)
  return n
}
for path in CommandLine.arguments.dropFirst() {
  guard let doc = PDFDocument(url: URL(fileURLWithPath: path)) else {
    print("{\"path\":\"\(path)\",\"error\":\"unreadable\"}"); continue }
  var chars: [Int] = []; var imgs: [Int] = []
  for i in 0..<doc.pageCount {
    let p = doc.page(at: i)
    chars.append((p?.string ?? "").trimmingCharacters(in: .whitespacesAndNewlines).count)
    var res: CGPDFDictionaryRef? = nil
    if let cg = p?.pageRef, let dict = cg.dictionary { CGPDFDictionaryGetDictionary(dict, "Resources", &res) }
    imgs.append(countImages(res, depth: 0))
  }
  print("{\"path\":\"\(path)\",\"pages\":\(doc.pageCount),\"chars\":\(chars),\"images\":\(imgs)}")
}
