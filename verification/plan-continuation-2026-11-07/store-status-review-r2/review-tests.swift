
// Independent R2 review additions. Synthetic credentials; scripted transport only.
import CryptoKit

@Suite(.serialized) struct StoreR2IndependentReviewTests {
    private func compact(_ data: Data) -> String {
        data.base64EncodedString().replacingOccurrences(of: "+", with: "-").replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "")
    }
    private func jwt(_ index: Int, key: P256.Signing.PrivateKey, team: Bool = false) throws -> String {
        let header = Data(#"{"alg":"ES256","kid":"TESTKEY123","typ":"JWT"}"#.utf8)
        let identity = team ? #""iss":"00000000-0000-0000-0000-000000000000""# : #""sub":"user""#
        let body = Data("{\(identity),\"iat\":\(1794099600 + index),\"exp\":\(1794100800 + index),\"aud\":\"appstoreconnect-v1\"}".utf8)
        let message = compact(header) + "." + compact(body)
        let signature = try key.signature(for: Data(message.utf8))
        #expect(key.publicKey.isValidSignature(signature, for: Data(message.utf8)))
        return message + "." + compact(signature.rawRepresentation)
    }
    @Test func ordinaryIndividualJWTRotationMustContinueUpdating() throws {
        try project { root in
            let key = P256.Signing.PrivateKey()
            var tokens: [String] = []
            for i in 0..<17 { tokens.append(try jwt(i, key: key)) }
            #expect(tokens.allSatisfy { $0.utf8.count == 250 })
            #expect(Set(tokens).count == 17)
            for i in 0..<16 {
                ScriptedASC.script.set([Reply(body: payload("PROCESSING", version: "\(i)"))])
                let result = try query(root, token: tokens[i])
                try #require(result.observationUpdated && result.observation?.version == "\(i)")
            }
            ScriptedASC.script.set([Reply(body: payload("VALID", version: "16"))])
            let seventeenth = try query(root, token: tokens[16])
            #expect(seventeenth.observationUpdated && seventeenth.observation?.processingState == "VALID")
            ScriptedASC.script.set([Reply(body: payload("VALID", version: "17"))])
            let reused = try query(root, token: tokens[0])
            #expect(reused.observationUpdated && reused.observation?.version == "17")
            let longToken = try jwt(18, key: key, team: true)
            #expect(longToken.utf8.count == 293)
            ScriptedASC.script.set([Reply(body: payload("VALID", version: "18"))])
            let long = try query(root, token: longToken)
            #expect(long.observationUpdated && long.observation?.version == "18")
            print("REVIEW rotation individualBytes=250 first16Updated=16 seventeenth=\(seventeenth.code?.rawValue ?? "nil") reused=\(reused.code?.rawValue ?? "nil") teamBytes=293 teamRecovery=\(long.code?.rawValue ?? "nil") retainedVersion=\(long.observation?.version ?? "nil")")
        }
    }
    @Test func repeatedSameCredentialAndLongJWTRotationRemainOpen() throws {
        for long in [false, true] {
            try project { root in
                let key = P256.Signing.PrivateKey(), same = try jwt(0, key: key)
                for i in 0..<20 {
                    ScriptedASC.script.set([Reply(body: payload("VALID", version: "\(i)"))])
                    let result = try query(root, token: long ? jwt(i, key: key, team: true) : same)
                    #expect(result.observationUpdated && result.observation?.version == "\(i)")
                }
                print("REVIEW rotationControl long=\(long) successfulQueries=20")
            }
        }
    }
    @Test func schemaOneMigrationAndMaximumFieldBytesRemoveKnownSecret() throws {
        for bytes in [128, 256] {
            try project { root in
                let future = String(repeating: "Z", count: bytes)
                ScriptedASC.script.set([Reply(body: payload("VALID", version: future)), Reply(status: 401)])
                _ = try query(root)
                let dir = root.appendingPathComponent(".mixer/store")
                let path = try #require(FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil).first { $0.pathExtension == "json" })
                var legacy = try #require(JSONSerialization.jsonObject(with: record(root)) as? [String: Any])
                for key in ["redactions", "redactionsExhausted", "discardedThrough"] { legacy.removeValue(forKey: key) }
                try JSONSerialization.data(withJSONObject: legacy, options: [.sortedKeys]).write(to: path)
                #expect(try query(root, token: future).observation == nil)
                #expect(try query(root, token: "").observation == nil)
                let saved = try record(root)
                #expect(!String(decoding: saved, as: UTF8.self).contains(future))
                let migrated = try #require(JSONSerialization.jsonObject(with: saved) as? [String: Any])
                #expect((migrated["discardedThrough"] as? NSNumber)?.intValue == 1)
                print("REVIEW migration credentialBytes=\(bytes) durableRemoval=true tombstone=1")
            }
        }
    }
    @Test func crossProcessCredentialRecognitionFencesOlderWriter() throws {
        try project { root in
            let secret = "synthetic credential with spaces", gate = Gate(), done = DispatchSemaphore(value: 0), result = ResultBox()
            ScriptedASC.script.set([Reply(body: payload("VALID", version: secret), gate: gate)])
            DispatchQueue.global().async { result.set(Result { try query(root) }); done.signal() }
            guard gate.started.wait(timeout: .now() + 5) == .success else { gate.release.signal(); Issue.record("Old request did not start"); return }
            defer { gate.release.signal() }
            let process = Process(), pipe = Pipe()
            process.executableURL = URL(fileURLWithPath: try #require(ProcessInfo.processInfo.environment["MIXER_STORE_TEST_CLI"]))
            process.arguments = ["submit", "status", "--provider", "app-store-connect", "--build-id", "build-1", "--app-id", "12345", "--directory", root.path]
            var environment = ProcessInfo.processInfo.environment
            environment["MIXER_ASC_BEARER_TOKEN"] = secret
            process.environment = environment; process.standardOutput = pipe; process.standardError = pipe
            try process.run()
            let data = pipe.fileHandleForReading.readDataToEndOfFile(); process.waitUntilExit()
            #expect(process.terminationStatus == 1 && String(decoding: data, as: UTF8.self).contains("store.credential-required"))
            gate.release.signal()
            try #require(done.wait(timeout: .now() + 5) == .success)
            let older = try #require(result.get()).get()
            #expect(older.code == .redactedResponse && older.observation == nil)
            #expect(try query(root, token: "").observation == nil)
            #expect(!String(decoding: try record(root), as: UTF8.self).contains(secret))
            print("REVIEW crossProcess childExit=\(process.terminationStatus) oldWriter=\(older.code?.rawValue ?? "nil") noReemission=true")
        }
    }
}
