import Foundation

/// SBOM for exactly one retained public-build snapshot; never a closure claim.
public enum SamePublicBuildSBOM {
    public struct Descriptor: Codable, Equatable, Sendable {
        public let snapshot: BuildInputSnapshot.Descriptor
        public let originalReportSHA256: String
        public let bindingSHA256: String
        public let nativeSHA256: String
        public let symbolsSHA256: String
        public let inventorySHA256: String
        public let materialRows: Int
        public let created: String
        public let sbom: SBOMProduct.Descriptor
    }
    public enum Failure: Error { case identity, isolation, incomplete }

    public static func produce(snapshot: BuildInputSnapshot.Descriptor, snapshotStore: URL,
        originalReport: URL, created: String, output: URL) throws -> Descriptor {
        try isolate(output, from: [snapshotStore, originalReport.deletingLastPathComponent()])
        let (report, inputs) = try inputs(snapshot, snapshotStore, originalReport, created)
        let sbom = try SBOMProduct.produce(inputs: inputs, store: output)
        return try descriptor(snapshot, report, created, sbom)
    }

    public static func reopen(_ descriptor: Descriptor, snapshotStore: URL,
        originalReport: URL, output: URL) throws {
        try isolate(output, from: [snapshotStore, originalReport.deletingLastPathComponent()])
        let (report, inputs) = try inputs(descriptor.snapshot, snapshotStore, originalReport, descriptor.created)
        guard try self.descriptor(descriptor.snapshot, report, descriptor.created, descriptor.sbom) == descriptor
        else { throw Failure.identity }
        try SBOMProduct.revalidate(descriptor.sbom, inputs: inputs, store: output)
    }

    public static func requireAggregateEligible(_ descriptor: Descriptor) throws { throw Failure.incomplete }

    private static func inputs(_ snapshot: BuildInputSnapshot.Descriptor, _ store: URL,
        _ original: URL, _ created: String) throws -> (BuildInputSnapshot.Report, SBOMProduct.Inputs) {
        let report = try BuildInputSnapshot.reopen(snapshot, store: store)
        let raw = try Data(contentsOf: original)
        guard SourceDigest.sha256(raw) == report.originalParentSHA256,
              try JSONFile.data(JSONDecoder().decode(NativeBuildOutput.Report.self, from: raw)) == JSONFile.data(report.originalParent)
        else { throw Failure.identity }
        let parents = store.appendingPathComponent("parents")
        let parent = try NativeBuildOutput.reopen(store: parents)
        guard let capture = parent.nativeProduct, let inventory = parent.resourceInventory,
              capture.bindingSHA256 == report.bindingSHA256 else { throw Failure.identity }
        var materials = try BuildInputSnapshot.retainedMaterials(snapshot, store: store).map {
            SBOMProduct.Material(logicalPath: "snapshot-materials/" + $0.logicalPath,
                path: $0.path, sizeBytes: $0.sizeBytes, sha256: $0.sha256)
        }
        materials.append(.init(logicalPath: "evidence/build-input-snapshot.json",
            path: store.appendingPathComponent("snapshot.json").path, sizeBytes: snapshot.sizeBytes, sha256: snapshot.sha256))
        materials.append(.init(logicalPath: "evidence/original-native-build-report.json",
            path: original.path, sizeBytes: UInt64(raw.count), sha256: report.originalParentSHA256))
        return (report, .init(capture: capture, captureStore: parents, inventory: inventory,
            inventoryStore: parents, expectedBindingSHA256: report.bindingSHA256, materials: materials, created: created))
    }

    private static func descriptor(_ snapshot: BuildInputSnapshot.Descriptor, _ report: BuildInputSnapshot.Report,
        _ created: String, _ sbom: SBOMProduct.Descriptor) throws -> Descriptor {
        guard let capture = report.originalParent.nativeProduct, let inventory = report.originalParent.resourceInventory
        else { throw Failure.identity }
        return .init(snapshot: snapshot, originalReportSHA256: report.originalParentSHA256,
            bindingSHA256: report.bindingSHA256, nativeSHA256: capture.nativeBinary.sha256,
            symbolsSHA256: capture.debugSymbols.sha256, inventorySHA256: inventory.sha256,
            materialRows: report.materials.count, created: created, sbom: sbom)
    }

    private static func isolate(_ output: URL, from roots: [URL]) throws {
        let out = output.standardizedFileURL.path
        for root in roots {
            let input = root.standardizedFileURL.path
            guard out != input, !out.hasPrefix(input + "/"), !input.hasPrefix(out + "/")
            else { throw Failure.isolation }
        }
    }
}
