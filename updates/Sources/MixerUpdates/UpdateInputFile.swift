import Foundation

/// Bounds allocation while reading. File metadata is only an early rejection;
/// the actual stream is limited even if a regular file grows after that check.
public enum UpdateInputFile {
    public static func read(_ url: URL, maximumBytes: Int = 1_048_576) throws -> Data {
        try validateMaximum(maximumBytes)
        let metadata = try url.resourceValues(forKeys: [.fileSizeKey, .isRegularFileKey])
        guard metadata.isRegularFile == true else { throw UpdateError("file.kind", "Input must be a regular file") }
        guard let size = metadata.fileSize, size >= 0, size <= maximumBytes else {
            throw UpdateError("file.size", "Input file exceeds configured limit")
        }
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        return try read(handle, maximumBytes: maximumBytes)
    }

    static func read(_ handle: FileHandle, maximumBytes: Int) throws -> Data {
        try validateMaximum(maximumBytes)
        var result = Data()
        while true {
            let remaining = maximumBytes - result.count
            let chunk = try handle.read(upToCount: min(65_536, remaining + 1)) ?? Data()
            guard !chunk.isEmpty else { return result }
            guard chunk.count <= remaining else { throw UpdateError("file.size", "Input file grew beyond configured limit") }
            result.append(chunk)
        }
    }

    private static func validateMaximum(_ maximum: Int) throws {
        guard maximum > 0, maximum <= 16 * 1_048_576 else { throw UpdateError("file.limit", "Invalid input byte limit") }
    }
}
