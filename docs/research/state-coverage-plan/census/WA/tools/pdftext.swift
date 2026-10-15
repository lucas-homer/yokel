import Foundation
import PDFKit
// usage: pdftext <file> [maxpages] ; prints text with form-feed between pages
let a = CommandLine.arguments
guard let doc = PDFDocument(url: URL(fileURLWithPath: a[1])) else { exit(2) }
let n = a.count > 2 ? min(Int(a[2])!, doc.pageCount) : doc.pageCount
for i in 0..<n { print(doc.page(at: i)?.string ?? "", terminator: "\u{0C}") }
