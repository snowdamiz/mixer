import Foundation
import Testing
import MixerCapabilities
@testable import MixerExperimentalCapabilityRuntime
#if os(macOS)
import Darwin

private struct BridgeProcessObservation {
    let allocated: UInt64
    let inUse: UInt64
    let maximumInUse: UInt64
    let maximumRSS: Int64
    let cpuMicroseconds: Int64
    init() {
        var heap = malloc_statistics_t(), usage = rusage()
        malloc_zone_statistics(nil, &heap)
        _ = getrusage(RUSAGE_SELF, &usage)
        allocated = UInt64(heap.size_allocated); inUse = UInt64(heap.size_in_use)
        maximumInUse = UInt64(heap.max_size_in_use); maximumRSS = Int64(usage.ru_maxrss)
        cpuMicroseconds = Int64(usage.ru_utime.tv_sec + usage.ru_stime.tv_sec) * 1_000_000
            + Int64(usage.ru_utime.tv_usec + usage.ru_stime.tv_usec)
    }
    var dictionary: [String: Int64] {
        ["allocatorAllocatedBytes": Int64(allocated), "allocatorInUseBytes": Int64(inUse),
         "allocatorMaximumInUseBytes": Int64(maximumInUse), "processMaximumRSSBytes": maximumRSS,
         "processCPUMicroseconds": cpuMicroseconds]
    }
}
extension ExperimentalBridgeTests {
    @Test func observationsSeparateLogicalPayloadFromAllocatorAndIdleCPU() async throws {
        // Observational process-wide measurements, not a per-owner RSS ceiling
        // or proof of allocator recovery. Run filtered in its own process too.
        let before = BridgeProcessObservation()
        let policy = try CapabilityPolicy(installed: [], manifest: [])
        let module = GuestProgram.build()
        var sessions: [ExperimentalCapabilitySession] = []
        for _ in 0..<16 {
            sessions.append(try await ExperimentalCapabilitySession.prepare(module: module, startupExport: "boot", policy: policy,
                adapters: InstalledCapabilityAdapters()).create())
        }
        let live = BridgeProcessObservation(), ticks = sessions.reduce(UInt64(0)) { $0 + $1.status.timerTicks }
        let idleStart = ContinuousClock.now
        try await Task.sleep(for: .milliseconds(250))
        let idle = BridgeProcessObservation(), elapsed = idleStart.duration(to: .now)
        let afterTicks = sessions.reduce(UInt64(0)) { $0 + $1.status.timerTicks }
        #expect(afterTicks == ticks)
        #expect(sessions.allSatisfy { $0.status.retainedPayloadBytes == 0 && $0.status.maximumWorkers == 0 })
        sessions.forEach { $0.close() }
        try await bridgeEventually { sessions.allSatisfy { $0.status.drained } }
        let drained = BridgeProcessObservation()
        let record: [String: Any] = ["scope": "macOS process-wide observational allocator/RSS/CPU,16 idle owners; no hard RSS/no-abort/recovery claim",
            "before": before.dictionary, "live16": live.dictionary, "idle": idle.dictionary, "drained": drained.dictionary,
            "idleWallSeconds": Double(elapsed.components.seconds) + Double(elapsed.components.attoseconds) / 1e18,
            "idleCPUMicroseconds": idle.cpuMicroseconds - live.cpuMicroseconds, "idleTimerTicks": afterTicks - ticks]
        print("BRIDGE_MEASUREMENT " + String(decoding: try JSONSerialization.data(withJSONObject: record, options: [.sortedKeys]), as: UTF8.self))
    }
}
#endif
