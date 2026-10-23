import Foundation
import Dispatch
import Darwin
import MixerCapabilities
import MixerExperimentalCapabilityRuntime

private struct Observation {
    let inUse: UInt64, allocated: UInt64
    let rss: Int64, cpu: Int64
    init() {
        var heap = malloc_statistics_t(), usage = rusage()
        malloc_zone_statistics(nil, &heap); _ = getrusage(RUSAGE_SELF, &usage)
        inUse = UInt64(heap.size_in_use); allocated = UInt64(heap.size_allocated); rss = Int64(usage.ru_maxrss)
        cpu = Int64(usage.ru_utime.tv_sec + usage.ru_stime.tv_sec)*1_000_000 + Int64(usage.ru_utime.tv_usec + usage.ru_stime.tv_usec)
    }
    var json: [String: Int64] { ["allocatorInUseBytes": Int64(inUse), "allocatorAllocatedBytes": Int64(allocated), "processMaximumRSSBytes": rss, "processCPUMicroseconds": cpu] }
}
private final class Sampler: @unchecked Sendable {
    private let queue = DispatchQueue(label: "mixer.verification.active-payload-sampler")
    private var timer: DispatchSourceTimer?
    private var samples = 0
    private var peakInUse: UInt64 = 0, peakAllocated: UInt64 = 0
    private var peakRSS: Int64 = 0
    private var maximumRetainedExits = 0, maximumLogicalPayloadBytes = 0
    func start(_ session: ExperimentalCapabilitySession) {
        let timer = DispatchSource.makeTimerSource(queue: queue)
        self.timer = timer
        timer.setEventHandler { [self, session] in
            let current = Observation(), status = session.status
            samples += 1; peakInUse = max(peakInUse,current.inUse); peakAllocated = max(peakAllocated,current.allocated); peakRSS = max(peakRSS,current.rss)
            maximumRetainedExits = max(maximumRetainedExits,status.retainedExits)
            maximumLogicalPayloadBytes = max(maximumLogicalPayloadBytes,status.retainedPayloadBytes)
        }
        timer.schedule(deadline: .now(), repeating: .milliseconds(1)); timer.resume()
    }
    func stop() -> [String: Int64] {
        timer?.cancel()
        return queue.sync {
            timer?.setEventHandler {}; timer = nil
            return ["samples": Int64(samples), "intervalMilliseconds": 1, "peakObservedAllocatorInUseBytes": Int64(peakInUse),
                "peakObservedAllocatorAllocatedBytes": Int64(peakAllocated), "peakObservedProcessMaximumRSSBytes": peakRSS,
                "maximumSampledRetainedExits": Int64(maximumRetainedExits), "maximumSampledLogicalPayloadBytes": Int64(maximumLogicalPayloadBytes)]
        }
    }
}
private struct ObserverFailure: Error { let code: String }
private func require(_ value: Bool, _ code: String) throws { if !value { throw ObserverFailure(code: code) } }
private func eventually(_ check: @Sendable () async throws -> Bool) async throws {
    for _ in 0..<2000 { if try await check() { return }; try await Task.sleep(for: .milliseconds(2)) }
    throw ObserverFailure(code: "bounded_observation_timeout")
}
@main struct ActivePayloadObserver {
    static func main() async throws {
        let before = Observation()
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-active-observation-"+UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = try AppPrivateKeyValueStore(directory: directory, namespaces: ["entries"])
        let expected = Data(repeating: 0xa5, count: 49152).base64EncodedString()
        _ = try await store.put(KVPutArguments(namespace: "entries", key: "large", valueBase64: expected))
        let grant = CapabilityGrant(capabilityID: CapabilitySchemas.storageID, schemaSHA256: CapabilitySchemas.storageSHA256,
            permissions: ["storage.appPrivate"], namespaces: ["entries"])
        let policy = try CapabilityPolicy(installed: [grant], manifest: [grant])
        let module = LargeGuest.build()
        let session = try await ExperimentalCapabilitySession.prepare(module: module, startupExport: "boot", policy: policy,
            adapters: InstalledCapabilityAdapters(storage: store)).create()
        defer { session.close() }
        _ = try await session.startup(); try await session.enableEffects()
        let ready = Observation(), sampler = Sampler(), start = ContinuousClock.now
        sampler.start(session)
        _ = try await session.invoke("run")
        try await eventually { try await session.invoke("stage").value == .i32(8) }
        var wrapperBytes = 0
        for index in 0..<8 {
            let word = try await session.readMemory(offset: UInt32(128+4*index), count: 4)
            let length = word.enumerated().reduce(UInt32(0)) { $0 | UInt32($1.element) << UInt32($1.offset*8) }
            try require((65536...131072).contains(length), "unexpected_wrapper_length")
            let bytes = try await session.readMemory(offset: UInt32(131072*(index+1)), count: Int(length))
            let result = try GuestCapabilityTransportCodecV1.decodeCompletion(bytes, expectedOperation: .storageGet)
            try require(result == .success(.get(KVGetResponse(found: true, valueBase64: expected))), "payload_mismatch")
            wrapperBytes += bytes.count
        }
        session.close(); try await eventually { session.status.drained }
        let sampled = sampler.stop(), drained = Observation(), status = session.status, elapsed = start.duration(to: .now)
        try require(status.acceptedCalls == 8 && status.acknowledgements == 8 && status.retainedExits == 0 && status.failure == nil, "not_drained_exactly")
        let record: [String: Any] = ["scope": "Public API, real Wasm,8 overlapping concrete storage gets, process-wide1ms sampler including probe decoding/runtime/native work",
            "before": before.json, "ready": ready.json, "drained": drained.json, "sampled": sampled,
            "payloadDecodedBytesEach": 49152, "payloadBase64BytesEach": expected.utf8.count, "guestWrapperBytesTotal": wrapperBytes,
            "elapsedSeconds": Double(elapsed.components.seconds)+Double(elapsed.components.attoseconds)/1e18,
            "acceptedCTakes": status.acceptedCalls, "acknowledgements": status.acknowledgements,
            "maximumLogicalPayloadBytesAtPumpBoundaries": status.maximumLogicalPayloadBytes, "maximumLogicalWorkersAtPumpBoundaries": status.maximumWorkers,
            "maximumCallbackNanoseconds": status.maximumCallbackNanoseconds, "maximumBatchNanoseconds": status.maximumBatchNanoseconds,
            "observedBatchOverrunNanoseconds": status.maximumBatchNanoseconds > 8_000_000 ? status.maximumBatchNanoseconds-8_000_000 : 0,
            "maximumBatchTurns": status.maximumBatchTurns, "timerTicks": status.timerTicks, "drainedConfirmed": status.drained,
            "limitations": ["Sample maximum is not an exact per-codec/transient-copy allocation peak or hardRSS bound", "Sampling includes allocator/observer/runtime/framework/native/probe work and perturbs timing", "Logical counters sample pump boundaries and exclude DTOs/backing/transient copies", "One admitted codec/C operation may overrun cooperative8ms cutoff", "No devices, no OOM/no-abort/recovery or release claim"]]
        print("ACTIVE_PAYLOAD_OBSERVATION "+String(decoding: try JSONSerialization.data(withJSONObject: record, options: [.sortedKeys]), as: UTF8.self))
        await store.close()
    }
}
