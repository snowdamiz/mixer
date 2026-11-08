
extension StoreSubmissionReconciliationTests {
    @Test func freshEveryByteMaximumJournalRefusesWithoutSideEffectsThenRestores() throws {
        try reviewProject { root in
            let secret = String(repeating: "J", count: 256)
            try reviewRecognize(root, "prior-recognition")
            let file = try reviewFile(root); defer { file.close() }
            let stale = try file.reserve(), retained = try file.reserve()
            _ = try file.commit(reviewValue(retained, secret))
            let record = reviewRecord(root), index = reviewIndex(root)
            let priorRecord = try Data(contentsOf: record)
            let pending = index.appendingPathComponent("pending")
            let body = Data("mixer-credential-v2\n256-\(SHA256.hash(data: Data(secret.utf8)).map { String(format: "%02x", $0) }.joined())\n".utf8)
            let intact = body + Data((SHA256.hash(data: body).map { String(format: "%02x", $0) }.joined() + "\n").utf8)
            try #require(intact.count == 154)
            for offset in intact.indices {
                var corrupt = intact; corrupt[offset] ^= 1
                try #require(zip(corrupt, intact).filter { $0.0 != $0.1 }.count == 1)
                try corrupt.write(to: pending)
                let before = try reviewIndexSnapshot(index)
                let reopened = try reviewFile(root); defer { reopened.close() }
                for operation in 0..<3 {
                    do {
                        switch operation {
                        case 0: _ = try reopened.observation()
                        case 1: _ = try reopened.reserve()
                        default: _ = try reopened.commit(reviewValue(stale, "stale-safe-value"))
                        }
                        Issue.record("Mutated maximum journal accepted at byte \(offset), operation \(operation)")
                    } catch let failure as MixerFailure {
                        #expect(failure.code == "store.credential-index")
                        #expect(!String(describing: failure).contains(secret))
                    }
                    #expect(try Data(contentsOf: record) == priorRecord)
                    #expect(try reviewIndexSnapshot(index) == before)
                }
            }
            try intact.write(to: pending)
            #expect(try file.observation() == nil)
            #expect(!FileManager.default.fileExists(atPath: pending.path))
            let old = try file.commit(reviewValue(stale, "stale-safe-value"))
            #expect(old.0 == nil && !old.1)
            try reviewReject(file, secret)
            try reviewReject(file, "prior-recognition")
            let json = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: record)) as? [String: Any])
            #expect((json["discardedThrough"] as? NSNumber)?.uint64Value == retained)
            print("FRESH everyByteMaximum bytes=154 refusalOperations=462 preserved=true exactRestore=true tombstone=true")
        }
    }

    @Test func freshChecksumConsistentSyntaxAndLegacyRefuseBeforeStatusDispatch() throws {
        try reviewProject { root in
            let secret = "fresh-syntax-secret"
            let file = try reviewFile(root); defer { file.close() }
            let generation = try file.reserve()
            _ = try file.commit(reviewValue(generation, secret))
            let index = reviewIndex(root), pending = index.appendingPathComponent("pending")
            let priorRecord = try Data(contentsOf: reviewRecord(root))
            let hash = SHA256.hash(data: Data(secret.utf8)).map { String(format: "%02x", $0) }.joined()
            let length = secret.utf8.count
            let bodies = [
                "mixer-credential-v2\n+\(length)-\(hash)\n",
                "mixer-credential-v2\n-\(length)-\(hash)\n",
                "mixer-credential-v2\n\(length)--\(hash)\n",
                "mixer-credential-v2\n\(length)-\(hash)\r\n",
                "mixer-credential-v2\r\n\(length)-\(hash)\n",
                "mixer-credential-v1\n\(length)-\(hash)\n",
                "mixer-credential-v0\n\(length)-\(hash)\n",
                "mixer-credential-v2\n\(length)-\(hash)\nextra\n"
            ]
            var variants = bodies.map { text -> Data in
                let body = Data(text.utf8)
                return body + Data((SHA256.hash(data: body).map { String(format: "%02x", $0) }.joined() + "\n").utf8)
            }
            variants += [Data(), Data("mixer-credential-v1\n\(length)-\(hash)\n".utf8)]
            try #require(variants.count == 10 && Set(variants).count == 10)
            for damaged in variants {
                try damaged.write(to: pending)
                let before = try reviewIndexSnapshot(index)
                ScriptedASC.script.set([Reply()])
                for token in ["", dummyToken] {
                    do { _ = try query(root, token: token); Issue.record("Malformed pending permitted status dispatch") }
                    catch let failure as MixerFailure {
                        #expect(failure.code == "store.credential-index")
                        #expect(!String(describing: failure).contains(secret))
                        #expect(!String(describing: failure).contains(dummyToken))
                    }
                    #expect(ScriptedASC.script.requests().isEmpty)
                    #expect(try Data(contentsOf: reviewRecord(root)) == priorRecord)
                    #expect(try reviewIndexSnapshot(index) == before)
                }
            }
            try reviewPendingData(secret).write(to: pending)
            #expect(try file.observation() == nil)
            print("FRESH syntaxAndLegacy variants=10 statusRefusals=20 providerRequests=0 preserved=true")
        }
    }
}
