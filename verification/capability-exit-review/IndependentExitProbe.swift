import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import Testing
@testable import MixerCapabilities

private final class Locked<Value: Sendable>: @unchecked Sendable {
    private let lock=NSLock(); private var value:Value
    init(_ value:Value){self.value=value}
    func read()->Value{lock.lock();defer{lock.unlock()};return value}
    func change(_ body:(inout Value)->Void){lock.lock();body(&value);lock.unlock()}
}
private struct Record:Sendable {var deliveries:[Data]=[];var exits=0;var activeAtExit:[Int]=[]}
private actor InvocationGate {
    private(set) var entered=false
    private var continuation:CheckedContinuation<Void,Never>?
    func hold() async {await withCheckedContinuation{entered=true;continuation=$0}}
    func release(){continuation?.resume();continuation=nil}
}
private final class InvalidationGate:@unchecked Sendable {
    private let condition=NSCondition();private var opened=false;private var began=false;private var expired=false
    func hold(){condition.lock();began=true;let limit=Date().addingTimeInterval(8);while !opened{if !condition.wait(until:limit){expired=true;break}};condition.unlock()}
    func release(){condition.lock();opened=true;condition.broadcast();condition.unlock()}
    var entered:Bool{condition.lock();defer{condition.unlock()};return began}
    var timedOut:Bool{condition.lock();defer{condition.unlock()};return expired}
}
private final class FixtureProtocol:URLProtocol,@unchecked Sendable {
    static let starts=Locked<[String:Int]>([:])
    override class func canInit(with request:URLRequest)->Bool{true}
    override class func canonicalRequest(for request:URLRequest)->URLRequest{request}
    override func startLoading(){
        guard let url=request.url else{return}
        Self.starts.change{$0[url.absoluteString,default:0]+=1}
        client?.urlProtocol(self,didReceive:HTTPURLResponse(url:url,statusCode:200,httpVersion:"HTTP/1.1",headerFields:["Content-Length":"0"])!,cacheStoragePolicy:.notAllowed)
        if !url.path.contains("stall"){client?.urlProtocolDidFinishLoading(self)}
    }
    override func stopLoading(){}
}
private final class WeakHost:@unchecked Sendable{weak var value:CapabilityHost?;init(_ value:CapabilityHost?){self.value=value}}
private func eventually(_ predicate:() async throws->Bool)async throws {
    for _ in 0..<800 {if try await predicate(){return};try await Task.sleep(nanoseconds:5_000_000)}
    try #require(try await predicate(),"Independent exit condition did not arrive")
}
private func policy(allow:Bool=true)throws->CapabilityPolicy {
    let http=CapabilityGrant(capabilityID:CapabilitySchemas.httpID,schemaSHA256:CapabilitySchemas.httpSHA256,permissions:["network.https"],origins:["https://exit.review.test"],methods:["GET"])
    let storage=CapabilityGrant(capabilityID:CapabilitySchemas.storageID,schemaSHA256:CapabilitySchemas.storageSHA256,permissions:["storage.appPrivate"],namespaces:["records"])
    return try CapabilityPolicy(installed:[http,storage],manifest:allow ? [http,storage]:[])
}
private func call(_ id:CapabilityRequestID,stall:Bool=false)->CapabilityCall {
    CapabilityCall(identity:id,operation:.http(HTTPRequestArguments(url:"https://exit.review.test/"+(stall ? "stall-":"ok-")+UUID().uuidString,method:"GET",headers:[],bodyBase64:"",timeoutMilliseconds:3000)))
}
private func nextID(_ host:CapabilityHost)async throws->CapabilityRequestID {
    var id:CapabilityRequestID?
    try await eventually{id=try? await host.issueRequestID();return id != nil}
    return try #require(id)
}

@Suite(.serialized) struct IndependentExitProbe {
    @Test func leaseReentrantCallbackAndConcurrentDuplicateFactsEmitOnce()async {
        for firstInvocation in [false,true]{
            let count=Locked(0)
            let lease=CapabilityExitLease{lease in
                count.change{$0+=1}
                lease.invocationReturned();lease.adapterExited()
            }
            if firstInvocation{lease.invocationReturned()}else{lease.adapterExited()}
            #expect(count.read()==0)
            await withTaskGroup(of:Void.self){group in
                for index in 0..<256 {group.addTask{for _ in 0..<16{if index.isMultiple(of:2){lease.adapterExited()}else{lease.invocationReturned()}}}}
            }
            #expect(count.read()==1)
        }
    }
    @Test func rejectedLegacyObservationPreservesReservationAndOrdinaryAPI()async throws {
        let record=Locked(Record()),invoked=Locked(0)
        let host=try CapabilityHost(policy:policy(),maximumRequests:1,http:{_ in invoked.change{$0+=1};return HTTPResponse(status:204,headers:[],bodyBase64:"")})
        let request=call(try await host.issueRequestID())
        await #expect(throws:CapabilityWireError.self){try await host.submitObserved(CapabilityCodec.encodeCall(request),deliver:{data in record.change{$0.deliveries.append(data)}},didExit:{record.change{$0.exits+=1}})}
        #expect(record.read().exits==0 && invoked.read()==0)
        try await host.submit(CapabilityCodec.encodeCall(request),deliver:{data in record.change{$0.deliveries.append(data)}})
        try await eventually{record.read().deliveries.count==1}
        #expect(invoked.read()==1 && record.read().exits==0)
        #expect(try CapabilityCodec.decodeCompletion(#require(record.read().deliveries.first),expected:request).outcome == .success(.http(HTTPResponse(status:204,headers:[],bodyBase64:""))))
        _=try await nextID(host);await host.close()
    }
    @Test func hostDeinitBeforeInvocationRetainsNoIOExitAndSuppressesDelivery()async throws {
        let gate=InvocationGate(),record=Locked(Record())
        defer{Task{await gate.release()}}
        let adapters=InstalledCapabilityAdapters(hooks:InstalledCapabilityExecutionHooks(beforeInvocation:{await gate.hold()}))
        var host:CapabilityHost?=try CapabilityHost(policy:policy(),maximumRequests:1,installedAdapters:adapters)
        let weakHost=WeakHost(host),request=call(try await #require(host).issueRequestID())
        try await #require(host).submitObserved(CapabilityCodec.encodeCall(request),deliver:{data in record.change{$0.deliveries.append(data)}},didExit:{record.change{$0.exits+=1}})
        try await eventually{await gate.entered}
        host=nil
        try await eventually{weakHost.value==nil}
        #expect(record.read().exits==0 && record.read().deliveries.isEmpty)
        await gate.release();try await eventually{record.read().exits==1}
        #expect(record.read().deliveries.isEmpty)
    }
    @Test func committedStorageCancellationAndCloseJoinAfterWorkerReturn()async throws {
        let folder=FileManager.default.temporaryDirectory.appendingPathComponent("mixer-independent-exit-"+UUID().uuidString)
        defer{try? FileManager.default.removeItem(at:folder)}
        let store=try AppPrivateKeyValueStore(directory:folder,namespaces:["records"])
        let gate=InvocationGate(),record=Locked(Record())
        defer{Task{await gate.release()}}
        let adapters=InstalledCapabilityAdapters(storage:store,hooks:InstalledCapabilityExecutionHooks(afterInvocation:{await gate.hold()}))
        let host=try CapabilityHost(policy:policy(),maximumRequests:1,installedAdapters:adapters)
        let value=Data("committed before cancellation".utf8).base64EncodedString()
        let request=CapabilityCall(identity:try await host.issueRequestID(),operation:.put(KVPutArguments(namespace:"records",key:"one",valueBase64:value)))
        try await host.submitObserved(CapabilityCodec.encodeCall(request),deliver:{data in record.change{$0.deliveries.append(data)}},didExit:{record.change{$0.exits+=1}})
        try await eventually{await gate.entered}
        #expect(try await store.get(KVGetArguments(namespace:"records",key:"one")).valueBase64==value)
        #expect(record.read().exits==0 && record.read().deliveries.isEmpty)
        await #expect(throws:CapabilityWireError.self){try await host.issueRequestID()}
        try await host.submit(CapabilityCodec.encodeCancel(request),deliver:{_ in Issue.record("Cancellation stole original delivery")})
        #expect(record.read().deliveries.count==1 && record.read().exits==0)
        #expect(try CapabilityCodec.decodeCompletion(#require(record.read().deliveries.first),expected:request).outcome == .failure(.cancelled))
        await host.close();await gate.release()
        try await eventually{record.read().exits==1}
        #expect(record.read().deliveries.count==1)
        #expect(try await store.get(KVGetArguments(namespace:"records",key:"one")).valueBase64==value)
        _=try await store.delete(KVDeleteArguments(namespace:"records",key:"one"));await store.close()
        let reopened=try AppPrivateKeyValueStore(directory:folder,namespaces:["records"])
        #expect(try await reopened.get(KVGetArguments(namespace:"records",key:"one")).found==false)
        await reopened.close()
    }
    @Test func httpTerminalAndOrdinarySubmitCannotReleaseBeforeNativeCounter()async throws {
        for observed in [false,true]{
            let gate=InvalidationGate(),record=Locked(Record());defer{gate.release()}
            let transport=try URLSessionHTTPTransport(maximumConcurrentRequests:1,protocolClasses:[FixtureProtocol.self],beforeInvalidation:{gate.hold()})
            let host=try CapabilityHost(policy:policy(),maximumRequests:1,installedAdapters:InstalledCapabilityAdapters(http:transport))
            let request=call(try await host.issueRequestID())
            if observed{try await host.submitObserved(CapabilityCodec.encodeCall(request),deliver:{data in record.change{$0.deliveries.append(data)}},didExit:{record.change{$0.exits+=1;$0.activeAtExit.append(transport.activeRequests)}})}
            else{try await host.submit(CapabilityCodec.encodeCall(request),deliver:{data in record.change{$0.deliveries.append(data)}})}
            try await eventually{gate.entered && record.read().deliveries.count==1}
            #expect(record.read().exits==0 && transport.activeRequests==1)
            await #expect(throws:CapabilityWireError.self){try await host.issueRequestID()}
            try await host.submit(CapabilityCodec.encodeCancel(request),deliver:{_ in Issue.record("Late cancellation replaced delivery")})
            #expect(record.read().deliveries.count==1 && record.read().exits==0)
            gate.release();let next=try await nextID(host)
            #expect(next.generation==2 && transport.activeRequests==0)
            #expect(record.read().exits==(observed ? 1:0));#expect(record.read().activeAtExit==(observed ? [0]:[]))
            #expect(!gate.timedOut);await host.close()
        }
    }
    @Test func httpExitBeforeWorkerReturnAndDeinitStillNeedsSecondFact()async throws {
        let gate=InvocationGate(),record=Locked(Record());defer{Task{await gate.release()}}
        let transport=try URLSessionHTTPTransport(maximumConcurrentRequests:1,protocolClasses:[FixtureProtocol.self])
        let adapters=InstalledCapabilityAdapters(http:transport,hooks:InstalledCapabilityExecutionHooks(afterInvocation:{await gate.hold()}))
        var host:CapabilityHost?=try CapabilityHost(policy:policy(),maximumRequests:1,installedAdapters:adapters)
        let weakHost=WeakHost(host),request=call(try await #require(host).issueRequestID())
        try await #require(host).submitObserved(CapabilityCodec.encodeCall(request),deliver:{data in record.change{$0.deliveries.append(data)}},didExit:{record.change{$0.exits+=1;$0.activeAtExit.append(transport.activeRequests)}})
        try await eventually{await gate.entered && transport.activeRequests==0}
        #expect(record.read().exits==0 && record.read().deliveries.isEmpty)
        await #expect(throws:CapabilityWireError.self){try await #require(host).issueRequestID()}
        host=nil;try await eventually{weakHost.value==nil}
        #expect(record.read().exits==0)
        await gate.release();try await eventually{record.read().exits==1}
        #expect(record.read().deliveries.isEmpty && record.read().activeAtExit==[0])
    }
}
