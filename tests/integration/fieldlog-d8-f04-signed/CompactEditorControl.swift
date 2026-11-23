import Foundation
@testable import MixerCapabilityActivation
@_spi(GuestUIV1) @_spi(PrivateFieldLogEditor) import MixerGuest
@_spi(PrivateFieldLogEditor) import MixerRuntimeIdentity
@_spi(PrivateFieldLogEditor) import MixerUpdates

enum CompactEditorControl {
    static func deferredRefusal(identity bytes: Data) throws -> String {
        var identity = try object(bytes)
        var engine = try need(identity["engine"] as? [String: Any], "Engine identity")
        engine["ui_contract_sha256"] = FieldLogEditorDevelopment.contractSHA256
        identity["engine"] = engine
        let deferred = CapabilityInstalledExecutionMode.deferredStartupID
        let retry = FieldLogEditorDevelopment.taskRetryDependency
        var dependencies = try need(identity["dependencies"] as? [[String: String]], "Dependencies")
        dependencies.removeAll { [deferred, retry].contains($0["id"] ?? "") }
        dependencies.append(["id": FieldLogEditorDevelopment.dependency, "version": "1",
                             "artifact_sha256": FieldLogEditorDevelopment.contractSHA256])
        let milestones: Set<String> = ["feature_started", "first_screen"]
        func compactIdentity() throws -> CapabilityRuntimeIdentity {
            identity["dependencies"] = dependencies.sorted { ($0["id"] ?? "") < ($1["id"] ?? "") }
            return try CapabilityRuntimeIdentity(privateDevelopmentFieldLogEditorJSON:
                JSONSerialization.data(withJSONObject: identity))
        }
        try CapabilityInstalledExecutionMode.requireFieldLogEditor(compactIdentity(), milestones: milestones)
        let exchange = try GuestUIExchangeV1(fieldLogEditorGeneration: 1)
        try check(!exchange.allowsDeferredStartup, "F05/F06 exchange enabled deferred startup")
        dependencies.append(["id": deferred, "version": "1",
                             "artifact_sha256": CapabilityInstalledExecutionMode.deferredStartupSHA256])
        let withDeferred = try compactIdentity()
        try check(try CapabilityInstalledExecutionMode.allowsDeferredGuestUIStartup(withDeferred),
                  "Compact identity did not parse the exact deferred dependency")
        do {
            try CapabilityInstalledExecutionMode.requireFieldLogEditor(withDeferred, milestones: milestones)
        } catch let error as UpdateError where error.code == "capability.runtime.installed_mode" {
            return #"{"ordinaryCompactAdmitted":true,"exchangeAllowsDeferred":false,"deferredRefusal":"capability.runtime.installed_mode"}"#
        }
        throw UpdateError("f04.control", "F05/F06 compact mode admitted deferred startup")
    }
}
