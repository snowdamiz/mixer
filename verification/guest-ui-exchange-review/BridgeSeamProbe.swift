import Foundation
import CMixerVMCapability
import MixerUI
@_spi(GuestUIV1) import MixerGuest
@_spi(GuestUIV1) @testable import MixerExperimentalCapabilityRuntime

struct SeamFailure: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}
func check(_ value: Bool, _ message: String) throws { if !value { throw SeamFailure(message) } }
func required<T>(_ value: T?, _ message: String) throws -> T {
    guard let value else { throw SeamFailure(message) }; return value
}

// Original tiny Wasm fixture. Only unsigned/signed LEB, section framing and
// standard core instructions are authored here; no owner fixture is imported.
enum TinyUI {
    enum Mode { case valid, missingEvent, wrongEventType, wrongEventKind, wrongStartupType, changedBuffer, badDocument, outsideMemory }
    static let document = Data(#"{"schemaVersion":1,"revision":1,"root":{"id":"save","kind":"button","properties":{"label":"Save"},"children":[],"actions":[{"id":"sample.save","event":"activate"}]}}"#.utf8)
    static func unsigned(_ input: UInt32) -> [UInt8] {
        var value = input, out: [UInt8] = []
        repeat { let byte = UInt8(value & 127); value >>= 7; out.append(byte | (value == 0 ? 0 : 128)) } while value != 0
        return out
    }
    static func signed(_ input: Int32) -> [UInt8] {
        var value = input, out: [UInt8] = []
        while true {
            let byte = UInt8(truncatingIfNeeded: value) & 127; value >>= 7
            let last = (value == 0 && byte & 64 == 0) || (value == -1 && byte & 64 != 0)
            out.append(byte | (last ? 0 : 128)); if last { return out }
        }
    }
    static func text(_ value: String) -> [UInt8] { unsigned(UInt32(value.utf8.count)) + value.utf8 }
    static func section(_ id: UInt8, _ payload: [UInt8]) -> [UInt8] { [id] + unsigned(UInt32(payload.count)) + payload }
    static func word(_ value: UInt32) -> [UInt8] { (0..<4).map { UInt8(truncatingIfNeeded: value >> ($0 * 8)) } }
    static func header(document: UInt32 = 128, length: UInt32 = UInt32(TinyUI.document.count), event: UInt32 = 4096) -> Data {
        Data(word(0x3155494d) + word(32) + word(document) + word(length) + word(event) + word(4096) + Array(repeating: 0, count: 8))
    }
    static func build(_ mode: Mode) -> Data {
        let type: [UInt8] = [3, 0x60, 0, 1, 0x7f, 0x60, 1, 0x7f, 1, 0x7f, 0x60, 0, 0]
        let startupType: UInt8 = mode == .wrongStartupType ? 2 : 0
        let eventType: UInt8 = mode == .wrongEventType ? 0 : 1
        let names = ["mixer_guest_ui_start_v1", mode == .missingEvent ? "different_event" : "mixer_guest_ui_event_v1", "mixer_guest_capability_ready_v1"]
        var exports: [UInt8] = [3]
        for (index, name) in names.enumerated() {
            let memory = index == 1 && mode == .wrongEventKind
            exports += text(name) + [memory ? 2 : 0] + unsigned(memory ? 0 : UInt32(index))
        }
        let startup: [UInt8] = mode == .wrongStartupType ? [0, 0x0b] : [0, 0x41] + signed(mode == .outsideMemory ? 65520 : 7) + [0x0b]
        var event: [UInt8] = [0]
        if mode == .changedBuffer || mode == .badDocument {
            event += [0x41] + signed(mode == .changedBuffer ? 23 : 19)
            event += [0x41] + signed(mode == .changedBuffer ? 8192 : 3)
            event += [0x36, 2, 0] // i32.store, offset0, natural alignment
        }
        event += [0x41, 0, 0x0b]
        let bodies: [[UInt8]] = [startup, event, [0, 0x0b]]
        var code: [UInt8] = [3]
        for body in bodies { code += unsigned(UInt32(body.count)) + body }
        var data: [UInt8] = [2]
        for (offset, payload) in [(Int32(7), header()), (128, document)] {
            data += [0, 0x41] + signed(offset) + [0x0b] + unsigned(UInt32(payload.count)) + payload
        }
        return Data([0, 97, 115, 109, 1, 0, 0, 0] + section(1, type) + section(3, [3, startupType, eventType, 2])
            + section(5, [1, 1, 1, 1]) + section(7, exports) + section(10, code) + section(11, data))
    }
}

func headers() throws {
    let valid = TinyUI.header()
    _ = try GuestUIControlHeader.decode(valid, headerOffset: 7, phase: .startup)
    _ = try GuestUIControlHeader.decode(TinyUI.header(document: 39, length: 4057), headerOffset: 7, phase: .startup) // Exact adjacency.
    var checked = 0
    for index in [0, 1, 2, 3, 4, 5, 6, 7, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31] {
        var corrupted = valid; corrupted[index] ^= 1
        do { _ = try GuestUIControlHeader.decode(corrupted, headerOffset: 7, phase: .event); throw SeamFailure("invalid fixed header byte accepted") }
        catch let failure as GuestUIProtocolFailureV1 { try check(failure.phase == .event && failure.code == .header, "fixed-header wrong typed error") }
        checked += 1
    }
    for (bytes, offset) in [(TinyUI.header(document: 38, length: 1), UInt32(7)),
        (TinyUI.header(document: 4095, length: 2), 7), (TinyUI.header(document: .max - 1, length: 2), 7),
        (valid, .max - 31), (TinyUI.header(event: .max - 4095), 7)] {
        do { _ = try GuestUIControlHeader.decode(bytes, headerOffset: offset, phase: .wake); throw SeamFailure("overlap/wrap accepted") }
        catch let failure as GuestUIProtocolFailureV1 { try check(failure.phase == .wake && failure.code == .memoryRange, "range wrong typed error") }
        checked += 1
    }
    print("PASS header-corpus negative_cases=\(checked) adjacency=accepted")
}

func validationDomains() throws {
    let configuration = ExperimentalCapabilityConfiguration()
    try NativeCapabilitySession.validateGuestUI(module: TinyUI.build(.valid), configuration: configuration)
    for mode in [TinyUI.Mode.missingEvent, .wrongEventType, .wrongEventKind, .wrongStartupType] {
        do { try NativeCapabilitySession.validateGuestUI(module: TinyUI.build(mode), configuration: configuration); throw SeamFailure("invalid export admitted") }
        catch let failure as GuestUIProtocolFailureV1 { try check(failure.phase == .validation && failure.code == .requiredExport, "export wrong UI domain") }
    }
    let module = TinyUI.build(.missingEvent)
    var vm = configuration.vm, limits = configuration.capability, report = MixerVmReport()
    let status = module.withUnsafeBytes { raw in
        mixer_vm_capability_guest_ui_validate_v1(raw.bindMemory(to: UInt8.self).baseAddress, raw.count, &vm, &limits, &report)
    }
    try check(status == 1 && report.abi_version == 1 && report.status == 1 && report.function == .max && report.offset == 0 && report.value_type == 0 && report.value == 0 && report.reserved == 0 && report.fuel_used == 0 && report.host_calls_used == 0, "native exact export tuple changed")
    do { try NativeDiagnostics.check(status, report, operation: .validation, moduleLength: module.count, configuration: configuration); throw SeamFailure("error tuple accepted") }
    catch let error as ExperimentalCapabilityError { try check(error.failure.kind == .validation(.requiredDefinedExport), "generic diagnostics rewritten as UI") }
    report.reserved = 1
    do { try NativeDiagnostics.check(status, report, operation: .validation, moduleLength: module.count, configuration: configuration); throw SeamFailure("malformed report accepted") }
    catch let error as ExperimentalCapabilityError { try check(error.nativeStatus == nil && error.failure.kind == .unknown(.malformedNativeReport), "malformed report entered UI domain") }
    do { try NativeCapabilitySession.validateGuestUI(module: Data([0]), configuration: configuration); throw SeamFailure("malformed module admitted") }
    catch let error as ExperimentalCapabilityError { try check(error.failure.kind == .validation(.malformed), "malformed module entered UI domain") }
    print("PASS native-validation-domains fixed-export_cases=4 malformed_report=rejected malformed_module=bridge")
}

func composites() throws {
    for mode in [TinyUI.Mode.valid, .changedBuffer, .badDocument, .outsideMemory] {
        let native = try NativeCapabilitySession(module: TinyUI.build(mode), startup: "mixer_guest_ui_start_v1", configuration: .init())
        defer { try? native.close() }
        let exchange = try GuestUIExchangeV1(generation: 19)
        let turns = GuestUITurns(exchange: exchange)
        if mode == .outsideMemory {
            do { try turns.startup(native); throw SeamFailure("OOB header accepted") }
            catch let error as ExperimentalCapabilityError {
                try check(error.nativeStatus == 3 && error.failure.operation == .readMemory && error.failure.kind == .callerAPI(.invalidNativeArguments), "memory error domain rewritten")
                try check(exchange.snapshot().firstUIProtocolFailure == nil, "memory read fabricated UI terminal")
            }
            continue
        }
        try turns.startup(native)
        try exchange.enterEffectsIntent(generation: 19); try native.enable(); try exchange.confirmEffectsEnabled(generation: 19)
        let presentation = try required(exchange.claimPresentation(generation: 19), "no startup frame")
        var renderer = UIReconciler(); try renderer.apply(try required(presentation.frame, "no document").document.document)
        let snapshot = try renderer.currentSnapshot()
        try check(exchange.completePresentation(presentation, snapshot: snapshot) != nil, "matching native snapshot denied")
        try check(exchange.offer(UIEventEnvelope(revision: 1, identity: try required(snapshot.identity(for: "save"), "no identity"), event: .activate), generation: 19) == .accepted(sequence: 1), "input denied")
        if mode == .valid {
            try check(try turns.next(native, ready: false) == true, "event composite did not run")
            let expected = try GuestUIEventCodecV1.encode(GuestUIEventV1(sequence: 1, revision: 1, nodeID: "save", actionID: "sample.save"))
            try check(try native.read(offset: 4096, count: expected.count) == expected, "exact event not written")
            try check(turns.nativeTurns == 2 && exchange.snapshot().counters.successfulTurns == 2, "event turn counts wrong")
            try check(try turns.next(native, ready: true) == false, "empty ready check executed")
            try check(turns.nativeTurns == 2 && !exchange.snapshot().guestTurnInFlight, "noop ready counted or retained")
        } else {
            do { _ = try turns.next(native, ready: false); throw SeamFailure("invalid event harvest accepted") }
            catch let failure as GuestUIProtocolFailureV1 {
                try check(failure.phase == .event && failure.code == (mode == .changedBuffer ? .bufferChanged : .document), "event harvest wrong typed error")
                try check(turns.nativeTurns == 2 && exchange.snapshot().counters.successfulTurns == 1, "invalid UI published success")
                exchange.recordProtocolFailure(failure)
                try check(exchange.snapshot().firstUIProtocolFailure?.effectStage == .intentEntered, "event terminal lost effects stage")
            }
        }
    }
    print("PASS fixed-native-composites valid_event=noop_ready_uncharged changed_buffer=closed bad_document=closed OOB=bridge")
}

@main struct BridgeSeamProbe {
    static func main() throws { try headers(); try validationDomains(); try composites(); print("RESULT bridge_groups=3 failures=0") }
}
