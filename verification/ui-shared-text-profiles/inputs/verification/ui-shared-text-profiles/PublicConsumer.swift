import MixerUI
for profile in UISharedTextProfileV1.allCases {
    for role in UISharedTextRoleV1.allCases {
        let metric = profile.metrics(for: role)
        print("METRIC", profile.rawValue, role.rawValue, metric.size64, metric.weight.rawValue)
    }
}
for requested in Array(UInt32(0)...UInt32(3500)) + [.max] {
    do {
        let profile = try UISharedTextProfileSelectionV1.nearest(preferredBodySize64: requested)
        print("SELECT", requested, profile.rawValue)
    } catch UISharedTextProfileErrorV1.unsupportedBodySize {
        print("SELECT", requested, "unsupported")
    } catch { fatalError("unexpected error") }
}
