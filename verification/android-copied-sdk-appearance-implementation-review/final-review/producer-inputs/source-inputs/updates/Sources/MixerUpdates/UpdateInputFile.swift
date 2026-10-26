import Foundation
#if canImport(Darwin)
import Darwin
#elseif canImport(Android)
import Android
#else
import Glibc
#endif

/// Bounds allocation while reading. File metadata is only an early rejection;
/// the actual stream is limited even if a regular file grows after that check.
/// Open nonblocking before inspecting the descriptor so path replacement cannot
/// turn the metadata check into a blocking FIFO/device read. Final symlinks reject.
public enum UpdateInputFile {
    public static func read(_ url: URL, maximumBytes: Int = 1_048_576) throws -> Data {
        try validateMaximum(maximumBytes)
        guard url.isFileURL, url.path.hasPrefix("/"), !url.path.utf8.contains(0), url.path.utf8.count <= 4096 else {
            throw UpdateError("file.kind", "Input must be an absolute local file URL")
        }
        let descriptor = url.withUnsafeFileSystemRepresentation { path in
            guard let path else { return Int32(-1) }
            return open(path, O_RDONLY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW)
        }
        guard descriptor >= 0 else {
            throw UpdateError(errno == ELOOP ? "file.kind" : "file.open", "Cannot open input as a regular non-symlink file")
        }
        let handle = FileHandle(fileDescriptor: descriptor, closeOnDealloc: true)
        defer { try? handle.close() }
        var status = stat()
        guard fstat(descriptor, &status) == 0 else { throw UpdateError("file.stat", "Cannot inspect input descriptor") }
        guard status.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG) else { throw UpdateError("file.kind", "Input must be a regular file") }
        guard status.st_size >= 0, status.st_size <= maximumBytes else {
            throw UpdateError("file.size", "Input file exceeds configured limit")
        }
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
