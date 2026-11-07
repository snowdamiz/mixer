#if canImport(UIKit)
import Foundation
import CryptoKit
import Darwin
import MixerUI

/// Only the native bundle capture routine can construct this owner. Configuration
/// and byte arrays supplied by app/guest code never confer installation authority.
@MainActor final class AppearanceInstalledV2 {
    enum Failure: Error { case missing, notRegular, changed, unsupportedResources, unsupportedFont }
    let configuration: UIAppearanceConfigurationV2
    let descriptorDigest: String
    private let descriptor: Data
    private init(_ descriptor: Data, _ configuration: UIAppearanceConfigurationV2) {
        self.descriptor = Data(descriptor)
        self.configuration = configuration
        descriptorDigest = SHA256.hash(data: descriptor).map { String(format: "%02x", $0) }.joined()
    }

    static func capture(bundle: Bundle) throws -> AppearanceInstalledV2 {
        // openat + O_NOFOLLOW checks every owned path component. No path-prefix
        // containment test, mapped mutable buffer, or later path reread is used.
        let root = open(bundle.bundleURL.path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
        guard root >= 0 else { throw Failure.missing }
        defer { close(root) }
        let folder = openat(root, "MixerAppearanceV2", O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
        guard folder >= 0 else { throw Failure.missing }
        defer { close(folder) }
        let fd = openat(folder, "descriptor.json", O_RDONLY | O_NOFOLLOW)
        guard fd >= 0 else { throw Failure.missing }
        defer { close(fd) }
        var before = stat()
        guard fstat(fd, &before) == 0, before.st_mode & S_IFMT == S_IFREG,
              before.st_size > 0, before.st_size <= 65_536 else { throw Failure.notRegular }
        var bytes = [UInt8](repeating: 0, count: Int(before.st_size))
        let count = bytes.withUnsafeMutableBytes { read(fd, $0.baseAddress, $0.count) }
        var after = stat()
        guard count == bytes.count, fstat(fd, &after) == 0,
              before.st_dev == after.st_dev, before.st_ino == after.st_ino,
              before.st_size == after.st_size,
              before.st_mtimespec.tv_sec == after.st_mtimespec.tv_sec,
              before.st_mtimespec.tv_nsec == after.st_mtimespec.tv_nsec else { throw Failure.changed }
        let data = Data(bytes)
        let configuration = try UIAppearanceDescriptorCodecV2.decode(data)
        // Deliberately reject the ENTIRE catalog, including unused entries. This
        // bounded consumer has no bundled-font/PNG support or silent fallback.
        guard configuration.resources.isEmpty else { throw Failure.unsupportedResources }
        func font(_ theme: UIThemeV2) throws {
            guard case .systemSans = theme.typography.font else { throw Failure.unsupportedFont }
        }
        switch configuration.mode {
        case let .shared(theme): try font(theme)
        case let .platformSpecific(iOS, android, _): try font(iOS); try font(android)
        }
        return AppearanceInstalledV2(data, configuration)
    }
}
#endif
