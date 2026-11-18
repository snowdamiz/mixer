import CoreGraphics
import CryptoKit
import Foundation
import ImageIO

struct Workspace: Decodable {
    struct Entry: Decodable {
        let id: UUID
        let title: String
        let attachmentIDs: [UUID]
    }
    struct Attachment: Decodable {
        let id: UUID
        let filename: String
        let byteCount: Int
    }
    let entries: [Entry]
    let drafts: [Entry]
    let attachments: [Attachment]
}

struct EvidenceError: Error, CustomStringConvertible {
    let description: String
}

func openImage(_ data: Data, type: String) throws -> CGImage {
    guard let source = CGImageSourceCreateWithData(data as CFData, nil),
          CGImageSourceGetType(source) as String? == type,
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil)
    else { throw EvidenceError(description: "Could not decode \(type)") }
    return image
}

func samples(_ image: CGImage) throws -> [[Int]] {
    let colorSpace = CGColorSpace(name: CGColorSpace.sRGB)!
    return try [(1, 1), (3, 1), (1, 3), (3, 3)].map { x, y in
        let pixelBounds = CGRect(x: image.width * x / 4, y: image.height * y / 4,
                                 width: 1, height: 1)
        guard let pixel = image.cropping(to: pixelBounds) else {
            throw EvidenceError(description: "Could not sample \(pixelBounds)")
        }
        var rgba = [UInt8](repeating: 0, count: 4)
        return try rgba.withUnsafeMutableBytes { bytes in
            guard let context = CGContext(
                data: bytes.baseAddress, width: 1, height: 1, bitsPerComponent: 8,
                bytesPerRow: 4, space: colorSpace,
                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
                    | CGBitmapInfo.byteOrder32Big.rawValue
            ) else { throw EvidenceError(description: "Could not create RGB sample buffer") }
            context.draw(pixel, in: CGRect(x: 0, y: 0, width: 1, height: 1))
            return bytes.prefix(3).map(Int.init)
        }
    }
}

func sha256(_ data: Data) -> String {
    SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
}

func verify() throws {
    guard CommandLine.arguments.count == 4,
          ["draft", "entry"].contains(CommandLine.arguments[3])
    else {
        throw EvidenceError(description: "Usage: verify-draft-photo WORKSPACE_DIRECTORY SEED_PNG draft|entry")
    }
    let isDraft = CommandLine.arguments[3] == "draft"
    let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
    let seed = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[2]))
    let snapshot = try Data(contentsOf: directory.appendingPathComponent("workspace.json"))
    let workspace = try JSONDecoder().decode(Workspace.self, from: snapshot)
    let records = isDraft ? workspace.drafts : workspace.entries
    guard records.count == 1, let entry = records.first,
          entry.title == "Migration photo draft",
          (isDraft ? workspace.entries : workspace.drafts).isEmpty,
          entry.attachmentIDs.count == 1, let id = entry.attachmentIDs.first,
          workspace.attachments.count == 1, let attachment = workspace.attachments.first,
          attachment.id == id, attachment.filename == id.uuidString.lowercased() + ".jpg"
    else { throw EvidenceError(description: "Expected one record in the requested phase linked to one photo") }

    let photoDirectory = directory.appendingPathComponent("photos", isDirectory: true)
    let photo = photoDirectory.appendingPathComponent(attachment.filename)
    guard try FileManager.default.contentsOfDirectory(atPath: photoDirectory.path) == [attachment.filename],
          try photo.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey]).isRegularFile == true,
          try photo.resourceValues(forKeys: [.isSymbolicLinkKey]).isSymbolicLink == false
    else { throw EvidenceError(description: "Expected a single regular file at the saved attachment path") }
    let jpeg = try Data(contentsOf: photo)
    guard !jpeg.isEmpty, jpeg.count == attachment.byteCount else {
        throw EvidenceError(description: "JPEG length differs from the saved attachment record")
    }
    let image = try openImage(jpeg, type: "public.jpeg")
    let original = try openImage(seed, type: "public.png")
    guard original.width == 1920, original.height == 1280,
          image.width == 1600, abs(image.height - 1067) <= 1 else {
        throw EvidenceError(description: "Unexpected seed or resized JPEG dimensions")
    }
    let originalColors = try samples(original)
    let actualColors = try samples(image)
    let maxChannelError = zip(originalColors.flatMap { $0 }, actualColors.flatMap { $0 })
        .map { abs($0 - $1) }.max()!
    guard maxChannelError <= 18 else {
        throw EvidenceError(description: "Saved JPEG does not match the seeded photo's four swatches")
    }
    let evidence: [String: Any] = [
        "workspaceDirectory": directory.lastPathComponent,
        "snapshotSHA256": sha256(snapshot),
        "entryID": entry.id.uuidString, "entryTitle": entry.title,
        "attachmentID": id.uuidString, "file": attachment.filename,
        "jpegBytes": jpeg.count, "jpegSHA256": sha256(jpeg),
        "jpegDimensions": [image.width, image.height], "seedSHA256": sha256(seed),
        "seedSamplesRGB": originalColors, "jpegSamplesRGB": actualColors,
        "maxSampleChannelDifference": maxChannelError,
    ]
    let json = try JSONSerialization.data(withJSONObject: evidence, options: [.prettyPrinted, .sortedKeys])
    print(String(decoding: json, as: UTF8.self))
}

do {
    try verify()
} catch {
    FileHandle.standardError.write(Data("Photo evidence failed: \(error)\n".utf8))
    exit(1)
}
