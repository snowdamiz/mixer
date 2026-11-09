import Foundation

// Captured Apple InternalBetaState / ExternalBetaState contracts are attributed in CONTRACT.md.
public struct StoreTestingValue: Codable, Sendable {
    public let expired: Bool?
    public let internalBuildState: String?
    public let externalBuildState: String?
    var rawStates: [String] { [internalBuildState, externalBuildState].compactMap { $0 } }
    static func validState(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 128 && !value.unicodeScalars.contains { CharacterSet.controlCharacters.contains($0) }
    }
    var valid: Bool { rawStates.allSatisfy(Self.validState) }
}

public struct StoreTestingReconciliationReport: Encodable, Sendable {
    public let reconciliation: StoreReconciliationReport
    public let testLinks = "unverified"
    public let appStoreReviewApproval = "unverified"
    public let releasedAvailability = "unverified"
    public var observationFreshness: String {
        if reconciliation.query == "observed" && reconciliation.observationUpdated { return "current-provider-observation" }
        return reconciliation.observation == nil ? "no-observation" : "retained-previous-observation"
    }
    private var current: StoreBuildObservation? {
        observationFreshness == "current-provider-observation" ? reconciliation.observation : nil
    }
    public var internalReadiness: String { readiness(external: false) }
    public var externalReadiness: String { readiness(external: true) }
    private func readiness(external: Bool) -> String {
        guard let observation = current, let testing = observation.providerValue.testing else { return "unresolved" }
        let state = external ? testing.externalBuildState : testing.internalBuildState
        if testing.expired == true { return "expired" }
        if testing.rawStates.contains("EXPIRED") { return testing.expired == false ? "contradictory" : "expired" }
        guard let state else { return "unresolved" }
        let known = ["PROCESSING", "PROCESSING_EXCEPTION", "MISSING_EXPORT_COMPLIANCE", "READY_FOR_BETA_TESTING", "IN_BETA_TESTING", "IN_EXPORT_COMPLIANCE_REVIEW"] + (external ? ["READY_FOR_BETA_SUBMISSION", "WAITING_FOR_BETA_REVIEW", "IN_BETA_REVIEW", "BETA_REJECTED", "BETA_APPROVED", "NOT_APPLICABLE"] : [])
        guard known.contains(state) else { return "unresolved" }
        let ready = state == "READY_FOR_BETA_TESTING" || state == "IN_BETA_TESTING"
        let anyReady = testing.rawStates.contains("READY_FOR_BETA_TESTING") || testing.rawStates.contains("IN_BETA_TESTING")
        if anyReady && (observation.processingState != "VALID" || testing.rawStates.contains("PROCESSING") || testing.rawStates.contains("PROCESSING_EXCEPTION")) { return "contradictory" }
        guard ["VALID", "PROCESSING", "FAILED", "INVALID"].contains(observation.processingState) else { return "unresolved" }
        if ready {
            guard testing.expired == false else { return "unresolved" }
            return state == "IN_BETA_TESTING" ? "in-testing" : "ready-for-testing"
        }
        return "not-ready"
    }
    public var exitCode: Int32 {
        if [internalReadiness, externalReadiness].allSatisfy({ ["ready-for-testing", "in-testing"].contains($0) }) { return 0 }
        return reconciliation.query == "observed" && ![internalReadiness, externalReadiness].contains(where: { ["unresolved", "contradictory", "expired"].contains($0) }) ? 2 : 1
    }
    public var nextStep: String {
        if reconciliation.code != nil { return reconciliation.nextStep }
        if observationFreshness != "current-provider-observation" { return "Query this existing build again for a current provider observation; retained states are historical." }
        let states = current?.providerValue.testing?.rawStates ?? []
        if states.contains("MISSING_EXPORT_COMPLIANCE") || states.contains("IN_EXPORT_COMPLIANCE_REVIEW") { return "Inspect this build's export compliance information in App Store Connect; no compliance or account classification is inferred." }
        if states.contains("BETA_REJECTED") { return "Inspect this build's beta review information in App Store Connect; beta review is separate from App Store review." }
        if states.contains("BETA_APPROVED") { return "Beta review approval alone does not establish testing readiness, App Store approval, or released availability. Inspect this build in App Store Connect." }
        if states.contains("READY_FOR_BETA_SUBMISSION") || states.contains("WAITING_FOR_BETA_REVIEW") || states.contains("IN_BETA_REVIEW") { return "Inspect this build's beta review state in App Store Connect; this command does not submit it for review." }
        return "Inspect the separate internal and external provider observations. Tester access, testing links, App Store approval and release require separate evidence."
    }
    enum CodingKeys: String, CodingKey {
        case provider, qualification, buildID, appID, bundleID, query, code, observation, observationUpdated, observationFreshness, internalReadiness, externalReadiness, testLinks, appStoreReviewApproval, releasedAvailability, nextStep
    }
    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(reconciliation.provider, forKey: .provider); try c.encode(reconciliation.qualification, forKey: .qualification)
        try c.encode(reconciliation.buildID, forKey: .buildID); try c.encode(reconciliation.appID, forKey: .appID); try c.encode(reconciliation.bundleID, forKey: .bundleID)
        try c.encode(reconciliation.query, forKey: .query); try c.encodeIfPresent(reconciliation.code, forKey: .code)
        try c.encodeIfPresent(reconciliation.observation, forKey: .observation); try c.encode(reconciliation.observationUpdated, forKey: .observationUpdated)
        try c.encode(observationFreshness, forKey: .observationFreshness); try c.encode(internalReadiness, forKey: .internalReadiness); try c.encode(externalReadiness, forKey: .externalReadiness)
        try c.encode(testLinks, forKey: .testLinks); try c.encode(appStoreReviewApproval, forKey: .appStoreReviewApproval); try c.encode(releasedAvailability, forKey: .releasedAvailability); try c.encode(nextStep, forKey: .nextStep)
    }
}
