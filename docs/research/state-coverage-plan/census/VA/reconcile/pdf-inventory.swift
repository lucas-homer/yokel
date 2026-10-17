import Foundation
import PDFKit
let args = CommandLine.arguments
guard let pdf = PDFDocument(url: URL(fileURLWithPath: args[1])) else { fatalError("Unreadable PDF") }
let pages = (0..<pdf.pageCount).map { pdf.page(at: $0)?.string ?? "" }
let data = try JSONSerialization.data(withJSONObject: pages, options: [.sortedKeys])
try data.write(to: URL(fileURLWithPath: args[2]))
