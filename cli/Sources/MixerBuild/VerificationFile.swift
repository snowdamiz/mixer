import CryptoKit
import Darwin
import Foundation

enum VerificationFile {
    // Inspect the opened descriptor, not path metadata collected before open.
    // O_NONBLOCK prevents a concurrently substituted FIFO from hanging open.
    static func openRegular(_ url: URL) throws -> (FileHandle, Int) {
        let descriptor = Darwin.open(url.path, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)
        guard descriptor >= 0 else { throw MixerFailure("update.input-type", "Cannot open regular, non-symlink input: \(url.path)") }
        var metadata = stat()
        guard fstat(descriptor, &metadata) == 0,
              metadata.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG), metadata.st_size >= 0,
              metadata.st_nlink == 1 else {
            Darwin.close(descriptor)
            throw MixerFailure("update.input-type", "Inputs must be regular files with one link.")
        }
        return (FileHandle(fileDescriptor: descriptor, closeOnDealloc: true), Int(metadata.st_size))
    }

    static func read(_ url: URL, maximumBytes: Int) throws -> Data {
        let (handle, size) = try openRegular(url)
        defer { try? handle.close() }
        guard size <= maximumBytes else { throw MixerFailure("update.input-size", "\(url.lastPathComponent) exceeds the input limit.") }
        var result = Data()
        while true {
            let remaining = maximumBytes - result.count
            let chunk = try handle.read(upToCount: min(65_536, remaining + 1)) ?? Data()
            guard !chunk.isEmpty else { return result }
            guard chunk.count <= remaining else { throw MixerFailure("update.input-size", "Input grew beyond the configured limit.") }
            result.append(chunk)
        }
    }

    static func tool(_ path: String) throws -> VerificationToolIdentity {
        let url = URL(fileURLWithPath: path).resolvingSymlinksInPath().standardizedFileURL
        guard FileManager.default.isExecutableFile(atPath: url.path) else { throw MixerFailure("update.tools", "Trusted local verification tool is not executable.") }
        let digest = try sha256(url, maximumBytes: 512 * 1_048_576) { grew in
            MixerFailure("update.tool-size", grew ? "Verification executable grew beyond the limit." : "Verification executable exceeds 512 MiB.")
        }
        return VerificationToolIdentity(path: url.path, sha256: digest)
    }

    static func sha256(_ url: URL, maximumBytes: Int) throws -> String {
        try sha256(url, maximumBytes: maximumBytes) { grew in
            MixerFailure("update.input-size", grew ? "Verification input grew beyond its byte limit." : "Verification input exceeds its byte limit.")
        }
    }

    private static func sha256(_ url: URL, maximumBytes: Int, limitFailure: (Bool) -> MixerFailure) throws -> String {
        let (handle, size) = try openRegular(url)
        defer { try? handle.close() }
        guard size <= maximumBytes else { throw limitFailure(false) }
        var hash = SHA256(), total = 0
        while let data = try handle.read(upToCount: 65_536), !data.isEmpty {
            total += data.count
            guard total <= maximumBytes else { throw limitFailure(true) }
            hash.update(data: data)
        }
        return hash.finalize().map { String(format: "%02x", $0) }.joined()
    }
}

public struct VerificationToolIdentity: Encodable, Equatable {
    public let path: String
    public let sha256: String
}
