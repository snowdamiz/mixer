import Foundation
import Testing
import MixerCapabilities

private func httpGrant(origins: Set<String> = ["https://api.example.test"], methods: Set<String> = ["GET"]) -> CapabilityGrant {
    CapabilityGrant(capabilityID: CapabilitySchemas.httpID, schemaSHA256: CapabilitySchemas.httpSHA256, permissions: ["network.https"], origins: origins, methods: methods)
}
private func storageGrant(namespaces: Set<String> = ["entries"]) -> CapabilityGrant {
    CapabilityGrant(capabilityID: CapabilitySchemas.storageID, schemaSHA256: CapabilitySchemas.storageSHA256, permissions: ["storage.appPrivate"], namespaces: namespaces)
}
private func policy() throws -> CapabilityPolicy { try CapabilityPolicy(installed: [httpGrant(),storageGrant()], manifest: [httpGrant(),storageGrant()]) }
private func request(_ id: CapabilityRequestID, url: String = "https://api.example.test/v1") -> CapabilityCall {
    CapabilityCall(identity: id, operation: .http(HTTPRequestArguments(url: url, method: "GET", headers: [], bodyBase64: "", timeoutMilliseconds: 1000)))
}
private final class Inbox: @unchecked Sendable {
    private let lock = NSLock(); private var data: [Data] = []
    func receive(_ value: Data) { lock.lock(); data.append(value); lock.unlock() }
    func values() -> [Data] { lock.lock(); defer { lock.unlock() }; return data }
}
private actor HTTPGate {
    var pending: [CheckedContinuation<HTTPResponse, Never>] = []
    func run(_ args: HTTPRequestArguments) async -> HTTPResponse { await withCheckedContinuation { pending.append($0) } }
    func started() -> Bool { !pending.isEmpty }
    func finish() { for waiter in pending { waiter.resume(returning: HTTPResponse(status: 200, headers: [], bodyBase64: "")) }; pending.removeAll() }
}
private func waitUntil(_ condition: () async throws -> Bool) async throws {
    for _ in 0..<400 { if try await condition() { return }; try await Task.sleep(nanoseconds: 5_000_000) }
    Issue.record("Timed out waiting for a bounded host transition")
}
private let fixtureID = CapabilityRequestID(session: "01234567-89ab-4cde-8fab-0123456789ab", slot: 0, generation: 1)
private func physicalNamespace(_ directory: URL) throws -> URL {
    let entry = try #require(FileManager.default.contentsOfDirectory(atPath:directory.path).first(where:{$0 != ".lock"}))
    return directory.appendingPathComponent(entry)
}
private func client(_ host: CapabilityHost) -> GuestCapabilityClient {
    GuestCapabilityClient(reserve: { try await host.issueRequestID() }, invoke: { bytes in
        try await withCheckedThrowingContinuation { continuation in
            Task {
                do { try await host.submit(bytes, deliver: { continuation.resume(returning: $0) }) }
                catch { continuation.resume(throwing: error) }
            }
        }
    }, cancel: { bytes in try? await host.submit(bytes, deliver: { _ in }) })
}

@Test func strictWireRejectsDuplicateUnicodeUnknownIntegerAndResourceAmbiguity() throws {
    let call = request(fixtureID); let good = try CapabilityCodec.encodeCall(call)
    let text = String(decoding: good, as: UTF8.self)
    for bad in [text.replacingOccurrences(of: "\"schema\":1", with: "\"schema\":1,\"schema\":1"),
                text.replacingOccurrences(of: "\"schema\":1", with: "\"schema\":1,\"\\u0073chema\":1"),
                text.replacingOccurrences(of: "\"schema\":1", with: "\"schema\":1.0"),
                text.replacingOccurrences(of: "\"schema\":1", with: "\"schema\":1e0"),
                text.replacingOccurrences(of: "\"schema\":1", with: "\"schema\":4294967296"),
                text.replacingOccurrences(of: "\"key\":", with: "\"surprise\":"),
                text.replacingOccurrences(of: "\"GET\"", with: "\"G\\ud800ET\""),
                text.replacingOccurrences(of: "\"GET\"", with: "\"GÉT\""),
                text.replacingOccurrences(of: "\"GET\"", with: "\"GET\",\"unknown\":true")].filter({ $0 != text }) {
        #expect(throws: (any Error).self) { try CapabilityCodec.decodeInbound(Data(bad.utf8)) }
    }
    #expect(throws: (any Error).self) { try CapabilityCodec.decodeInbound(Data([0xff])) }
    #expect(throws: (any Error).self) { try CapabilityCodec.decodeInbound(Data(repeating: 32, count: 524289)) }
    #expect(throws: (any Error).self) { try CapabilityCodec.decodeInbound(Data((String(repeating: "[", count: 9)+"0"+String(repeating: "]", count: 9)).utf8)) }
    #expect(try CapabilityCodec.decodeInbound(good) == .call(call))
}

@Test func typedInputsRejectNoncanonicalURLsHeadersBase64AndCrossOwnerResponses() throws {
    for url in ["http://api.example.test/", "https://API.example.test/", "https://u@api.example.test/", "https://api.example.test:443/", "https://api.example.test:0444/", "https://api.example.test/#x", "https://api.example.test/\\x", "https://api.example.test/%zz", "https://[::1]/"] {
        #expect(throws: (any Error).self) { try CapabilityCodec.encodeCall(request(fixtureID,url:url)) }
    }
    for body in ["Zg", "Zh==", String(repeating: "A", count: 87384)] {
        let operation = CapabilityOperation.put(KVPutArguments(namespace: "entries", key: "k", valueBase64: body))
        #expect(throws: (any Error).self) { try CapabilityCodec.encodeCall(CapabilityCall(identity: fixtureID, operation: operation)) }
    }
    let badHeaders = [Header(name: "x-one", value: "a"), Header(name: "x-one", value: "b")]
    #expect(throws: (any Error).self) { try CapabilityCodec.encodeCall(CapabilityCall(identity: fixtureID, operation: .http(HTTPRequestArguments(url:"https://api.example.test/",method:"GET",headers:badHeaders,bodyBase64:"",timeoutMilliseconds:1)))) }
    let call = request(fixtureID)
    let encoded = try CapabilityCodec.encodeCompletion(CapabilityCompletion(call: call, outcome: .failure(.cancelled)))
    let other = request(CapabilityRequestID(session:fixtureID.session,slot:0,generation:2))
    #expect(throws: (any Error).self) { try CapabilityCodec.decodeCompletion(encoded, expected: other) }
}

@Test func grantIntersectionDeniesExpansionAndUnavailableAdaptersFailExplicitly() async throws {
    let narrower = try CapabilityPolicy(installed:[httpGrant()], manifest:[httpGrant(origins:["https://other.example.test"])])
    let host = try CapabilityHost(policy:narrower); let inbox=Inbox(); let call=request(try await host.issueRequestID())
    try await host.submit(CapabilityCodec.encodeCall(call),deliver:inbox.receive)
    #expect(try CapabilityCodec.decodeCompletion(#require(inbox.values().first),expected:call).outcome == .failure(.permissionDenied))
    await host.close()
    let absent = try CapabilityHost(policy:policy()); let denied=request(try await absent.issueRequestID()); let second=Inbox()
    try await absent.submit(CapabilityCodec.encodeCall(denied),deliver:second.receive)
    try await waitUntil { second.values().count == 1 }
    #expect(try CapabilityCodec.decodeCompletion(#require(second.values().first),expected:denied).outcome == .failure(.unavailable))
    await absent.close()
    let unknown = CapabilityGrant(capabilityID:"native.arbitrary",schemaSHA256:String(repeating:"0",count:64),permissions:[])
    #expect(throws: (any Error).self) { try CapabilityPolicy(installed:[unknown],manifest:[unknown]) }
}

@Test func cancellationCompletesOnceRetainsNativeLeaseAndCannotCancelReusedGeneration() async throws {
    let gate=HTTPGate(); let inbox=Inbox()
    let host=try CapabilityHost(policy:policy(),maximumRequests:1,maximumGenerationsPerSlot:2,http:{ await gate.run($0) })
    let call=request(try await host.issueRequestID()); try await host.submit(CapabilityCodec.encodeCall(call),deliver:inbox.receive)
    try await waitUntil { await gate.started() }
    try await host.submit(CapabilityCodec.encodeCancel(call),deliver:{ _ in Issue.record("cancel stole response ownership") })
    #expect(inbox.values().count == 1)
    #expect(try CapabilityCodec.decodeCompletion(#require(inbox.values().first),expected:call).outcome == .failure(.cancelled))
    await #expect(throws:(any Error).self) { try await host.issueRequestID() }
    await gate.finish()
    var next: CapabilityRequestID?
    try await waitUntil { next = try? await host.issueRequestID(); return next != nil }
    let call2=request(try #require(next)); #expect(call2.identity.generation == 2)
    try await host.submit(CapabilityCodec.encodeCall(call2),deliver:inbox.receive)
    try await waitUntil { await gate.started() }
    await #expect(throws:(any Error).self) { try await host.submit(CapabilityCodec.encodeCancel(call),deliver:inbox.receive) }
    await gate.finish(); try await waitUntil { inbox.values().count == 2 }
    try await Task.sleep(nanoseconds:10_000_000)
    #expect(inbox.values().count == 2)
    await #expect(throws:(any Error).self) { try await host.issueRequestID() }
    await host.close()
}

@Test func sessionOwnershipDuplicateCallsAndCloseSuppressLateCallbackDelivery() async throws {
    let gate=HTTPGate(); let inbox=Inbox(); let host=try CapabilityHost(policy:policy(),http:{await gate.run($0)})
    let foreign=try CapabilityHost(policy:policy()); let call=request(try await host.issueRequestID())
    await #expect(throws:(any Error).self) { try await foreign.submit(CapabilityCodec.encodeCall(call),deliver:inbox.receive) }
    try await host.submit(CapabilityCodec.encodeCall(call),deliver:inbox.receive)
    await #expect(throws:(any Error).self) { try await host.submit(CapabilityCodec.encodeCall(call),deliver:inbox.receive) }
    try await waitUntil {await gate.started()}; await host.close(); #expect(inbox.values().count == 1)
    await gate.finish(); try await Task.sleep(nanoseconds:10_000_000); #expect(inbox.values().count == 1)
    await foreign.close()
}

@Test func deadlineAndNativeResponseValidationCannotProduceExtraSuccess() async throws {
    let gate=HTTPGate(); let inbox=Inbox(); let host=try CapabilityHost(policy:policy(),maximumRequests:1,timeoutMilliseconds:50,http:{await gate.run($0)})
    let call=request(try await host.issueRequestID()); try await host.submit(CapabilityCodec.encodeCall(call),deliver:inbox.receive)
    try await waitUntil { inbox.values().count == 1 }
    #expect(try CapabilityCodec.decodeCompletion(#require(inbox.values().first),expected:call).outcome == .failure(.deadlineExceeded))
    await gate.finish(); await host.close(); #expect(inbox.values().count == 1)
    for response in [HTTPResponse(status:302,headers:[],bodyBase64:""), HTTPResponse(status:200,headers:[],bodyBase64:Data(repeating:0,count:262145).base64EncodedString())] {
        let destination=Inbox();let h=try CapabilityHost(policy:policy(),http:{_ in response});let c=request(try await h.issueRequestID())
        try await h.submit(CapabilityCodec.encodeCall(c),deliver:destination.receive); try await waitUntil {destination.values().count==1}
        let expected:CapabilityFailure=response.status==302 ? .redirectDenied:.invalidResponse
        #expect(try CapabilityCodec.decodeCompletion(#require(destination.values().first),expected:c).outcome == .failure(expected));await h.close()
    }
}

@Test func privateStorePersistsAtomicValuesEnforcesQuotasAndRejectsPaths() async throws {
    let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-kv-\(UUID().uuidString)")
    defer {try? FileManager.default.removeItem(at:directory)}
    var store=try AppPrivateKeyValueStore(directory:directory,namespaces:["entries"],maximumTotalBytes:8,maximumEntries:1)
    let put=KVPutArguments(namespace:"entries",key:"one",valueBase64:Data("first".utf8).base64EncodedString())
    #expect(try await store.put(put).committed)
    #expect(throws:(any Error).self) { try AppPrivateKeyValueStore(directory:directory,namespaces:["entries"]) }
    await #expect(throws:CapabilityFailure.self) {try await store.put(KVPutArguments(namespace:"entries",key:"two",valueBase64:""))}
    await #expect(throws:CapabilityFailure.self) {try await store.put(KVPutArguments(namespace:"entries",key:"one",valueBase64:Data(repeating:0,count:9).base64EncodedString()))}
    await #expect(throws:(any Error).self) {try await store.get(KVGetArguments(namespace:"entries",key:"../outside"))}
    await #expect(throws:CapabilityFailure.self) {try await store.get(KVGetArguments(namespace:"other",key:"one"))}
    await store.close()
    // An abandoned private transaction never replaces the committed value.
    let orphan=try physicalNamespace(directory).appendingPathComponent(".txn-\(UUID().uuidString)");try Data("partial".utf8).write(to:orphan)
    store=try AppPrivateKeyValueStore(directory:directory,namespaces:["entries"],maximumTotalBytes:8,maximumEntries:1)
    #expect(!FileManager.default.fileExists(atPath:orphan.path))
    #expect(try await store.get(KVGetArguments(namespace:"entries",key:"one")).valueBase64 == put.valueBase64)
    #expect(try await store.delete(KVDeleteArguments(namespace:"entries",key:"one")).committed)
    #expect(try await store.get(KVGetArguments(namespace:"entries",key:"one")).found == false)
    #expect(try await store.put(KVPutArguments(namespace:"entries",key:"two",valueBase64:"" )).committed)
    await store.close()
}

@Test func actualPrivateStorageRunsThroughTypedHostPermissionBoundary() async throws {
    let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-kv-host-\(UUID().uuidString)")
    defer {try? FileManager.default.removeItem(at:directory)}
    let store=try AppPrivateKeyValueStore(directory:directory,namespaces:["entries"])
    let host=try CapabilityHost(policy:policy(),storage:store);let inbox=Inbox()
    let call=CapabilityCall(identity:try await host.issueRequestID(),operation:.put(KVPutArguments(namespace:"entries",key:"draft",valueBase64:"Zml4dHVyZQ==")))
    try await host.submit(CapabilityCodec.encodeCall(call),deliver:inbox.receive);try await waitUntil {inbox.values().count==1}
    #expect(try CapabilityCodec.decodeCompletion(#require(inbox.values().first),expected:call).outcome == .success(.put(KVMutationResponse(committed:true))))
    #expect(try await store.get(KVGetArguments(namespace:"entries",key:"draft")).valueBase64 == "Zml4dHVyZQ==")
    let guest = client(host)
    #expect(try await guest.get(KVGetArguments(namespace:"entries",key:"draft")).valueBase64 == "Zml4dHVyZQ==")
    #expect(try await guest.delete(KVDeleteArguments(namespace:"entries",key:"draft")).committed)
    #expect(try await guest.get(KVGetArguments(namespace:"entries",key:"draft")).found == false)
    await host.close();await store.close()
}

@Test func typedGuestCancellationAndUnusedReservationCannotAffectAnotherRequest() async throws {
    let gate=HTTPGate();let host=try CapabilityHost(policy:policy(),maximumRequests:1,http:{await gate.run($0)})
    let unused=request(try await host.issueRequestID())
    try await host.submit(CapabilityCodec.encodeCancel(unused),deliver:{_ in Issue.record("unused reservation completed a nonexistent call")})
    let guest=client(host)
    let work=Task {try await guest.http(HTTPRequestArguments(url:"https://api.example.test/",method:"GET",headers:[],bodyBase64:"",timeoutMilliseconds:1000))}
    try await waitUntil {await gate.started()};work.cancel()
    do {_ = try await work.value;Issue.record("Cancelled typed client returned success")}
    catch let failure as CapabilityFailure {#expect(failure == .cancelled)}
    await #expect(throws:(any Error).self) {try await host.submit(CapabilityCodec.encodeCall(unused),deliver:{_ in})}
    await gate.finish();await host.close()
}

@Test func privateStoreRejectsLinkedAndOversizedFilesWithoutTouchingExternalBytes() async throws {
    let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-kv-links-\(UUID().uuidString)")
    let external=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-kv-external-\(UUID().uuidString)")
    defer {try? FileManager.default.removeItem(at:directory);try? FileManager.default.removeItem(at:external)}
    let store=try AppPrivateKeyValueStore(directory:directory,namespaces:["entries"])
    _ = try await store.put(KVPutArguments(namespace:"entries",key:"one",valueBase64:""));await store.close()
    try Data("external sentinel".utf8).write(to:external)
    let ns=try physicalNamespace(directory)
    let key=try ns.appendingPathComponent(#require(FileManager.default.contentsOfDirectory(atPath:ns.path).first))
    try FileManager.default.removeItem(at:key)
    try FileManager.default.createSymbolicLink(at:key,withDestinationURL:external)
    #expect(throws:(any Error).self) {try AppPrivateKeyValueStore(directory:directory,namespaces:["entries"])}
    try FileManager.default.removeItem(at:key);try FileManager.default.linkItem(at:external,to:key)
    #expect(throws:(any Error).self) {try AppPrivateKeyValueStore(directory:directory,namespaces:["entries"])}
    try FileManager.default.removeItem(at:key);try Data(repeating:0,count:65537).write(to:key)
    #expect(throws:(any Error).self) {try AppPrivateKeyValueStore(directory:directory,namespaces:["entries"])}
    #expect(try Data(contentsOf:external) == Data("external sentinel".utf8))
    try FileManager.default.removeItem(at:key)
    let recovered=try AppPrivateKeyValueStore(directory:directory,namespaces:["entries"])
    #expect(try await recovered.get(KVGetArguments(namespace:"entries",key:"one")).found == false);await recovered.close()
}

@Test func cancellationWhileReservingReleasesTokenWithoutInvokingNativeAdapter() async throws {
    let reservation=HTTPGate();let host=try CapabilityHost(policy:policy(),maximumRequests:1,http:{_ in Issue.record("pre-call cancellation invoked HTTP");return HTTPResponse(status:200,headers:[],bodyBase64:"")})
    let guest=GuestCapabilityClient(reserve:{
        let id=try await host.issueRequestID()
        _ = await reservation.run(HTTPRequestArguments(url:"https://api.example.test/",method:"GET",headers:[],bodyBase64:"",timeoutMilliseconds:1))
        return id
    },invoke:{_ in Issue.record("cancelled reservation submitted a call");throw CapabilityFailure.unavailable},cancel:{bytes in try? await host.submit(bytes,deliver:{_ in})})
    let work=Task {try await guest.get(KVGetArguments(namespace:"entries",key:"one"))}
    try await waitUntil {await reservation.started()};work.cancel();await reservation.finish()
    do {_ = try await work.value;Issue.record("Cancelled reservation returned success")}
    catch let failure as CapabilityFailure {#expect(failure == .cancelled)}
    let next=try await host.issueRequestID();#expect(next.generation==2);await host.close()
}

@Test func privateStorageIdentityCannotAliasOnCaseInsensitiveFilesystems() async throws {
    let directory=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-kv-case-\(UUID().uuidString)")
    defer {try? FileManager.default.removeItem(at:directory)}
    let store=try AppPrivateKeyValueStore(directory:directory,namespaces:["entries","ENTRIES"])
    _ = try await store.put(KVPutArguments(namespace:"entries",key:"Key",valueBase64:"bG93ZXI="))
    _ = try await store.put(KVPutArguments(namespace:"entries",key:"key",valueBase64:"dXBwZXI="))
    _ = try await store.put(KVPutArguments(namespace:"ENTRIES",key:"Key",valueBase64:"b3RoZXI="))
    #expect(try await store.get(KVGetArguments(namespace:"entries",key:"Key")).valueBase64 == "bG93ZXI=")
    #expect(try await store.get(KVGetArguments(namespace:"entries",key:"key")).valueBase64 == "dXBwZXI=")
    #expect(try await store.get(KVGetArguments(namespace:"ENTRIES",key:"Key")).valueBase64 == "b3RoZXI=")
    let maximum=String(repeating:"X",count:128)
    _ = try await store.put(KVPutArguments(namespace:"entries",key:maximum,valueBase64:"Zg=="))
    #expect(try await store.get(KVGetArguments(namespace:"entries",key:maximum)).valueBase64 == "Zg==")
    await store.close()
}
