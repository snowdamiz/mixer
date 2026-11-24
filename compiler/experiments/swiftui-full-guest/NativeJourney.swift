import Foundation

enum NativeJourney {
    @MainActor
    static func run(checkpoint: (String, UInt64) -> Void) async throws {
        func emit(_ stage: String, since start: UInt64, _ result: Journey.Result) throws {
            let encoder = JSONEncoder()
            encoder.outputFormatting = .sortedKeys
            var line = try encoder.encode(result)
            checkpoint(stage, (DispatchTime.now().uptimeNanoseconds - start) / 1_000)
            line.append(0x0a)
            try FileHandle.standardOutput.write(contentsOf: line)
        }

        var start = DispatchTime.now().uptimeNanoseconds
        let journey = Journey()
        try emit("first_snapshot", since: start, journey.result)

        start = DispatchTime.now().uptimeNanoseconds
        await journey.load()
        try emit("load", since: start, journey.result)

        start = DispatchTime.now().uptimeNanoseconds
        journey.openRecord()
        try emit("open", since: start, journey.result)

        start = DispatchTime.now().uptimeNanoseconds
        journey.tryBlankSave()
        try emit("blank_save", since: start, journey.result)

        start = DispatchTime.now().uptimeNanoseconds
        journey.saveEdit()
        try emit("save", since: start, journey.result)

        start = DispatchTime.now().uptimeNanoseconds
        try journey.reopen()
        try emit("reopen", since: start, journey.result)

        #if os(iOS) || S2_MATCHED_SHELL
        try await Task.sleep(for: .seconds(1))
        withExtendedLifetime(journey) {
            checkpoint("steady", 0)
        }
        #endif
    }
}

#if S2_MATCHED_SHELL
@_cdecl("mixer_s2b_start_native")
func startNativeJourney() {
    Task { @MainActor in
        do {
            try await NativeJourney.run { stage, elapsed in
                stage.withCString { name in
                    mixer_s2b_checkpoint(name, stage.utf8.count, elapsed)
                }
            }
            mixer_s2b_finish(0)
        } catch {
            FileHandle.standardError.write(Data("native failure=\(error)\n".utf8))
            mixer_s2b_finish(20)
        }
    }
    dispatchMain()
}
#elseif os(iOS)
@_cdecl("mixer_s2a_start_native")
func startNativeJourney() {
    Task { @MainActor in
        do {
            try await NativeJourney.run { stage, elapsed in
                stage.withCString { name in
                    mixer_s2a_checkpoint(name, stage.utf8.count, elapsed)
                }
            }
            mixer_s2a_finish(0)
        } catch {
            FileHandle.standardError.write(Data("native failure=\(error)\n".utf8))
            mixer_s2a_finish(20)
        }
    }
}
#else
@main
enum NativeJourneyCommand {
    static func main() async throws {
        try await NativeJourney.run { _, _ in }
    }
}
#endif
