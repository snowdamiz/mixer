import Foundation

/// Explicit app-owned public V3 SDK consumer and Android host templates.
enum AndroidPublicHost {
    static let selection = "{\"host\":\"public-v3\",\"profile\":\"MEASURED_MULTILINE_RETIREMENT_V3\"}\n"
    static func files(_ config: ApplicationConfiguration) -> [String: String] {
        let appPackage = config.application + ".androidhost"
        let base = "Java/" + appPackage.replacingOccurrences(of: ".", with: "/") + "/"
        return ["Package.swift": package.replacingOccurrences(of: "__NAME__", with: config.name),
                "AndroidManifest.xml": manifest.replacingOccurrences(of: "__APPLICATION__", with: config.application)
                    .replacingOccurrences(of: "__PACKAGE__", with: appPackage).replacingOccurrences(of: "__NAME__", with: config.name),
                "Sources/AppAndroid/NativeEntry.swift": entry,
                "Sources/AppAndroid/PublicFactory.swift": factory,
                "Tests/AppAndroidTests/PublicHostTests.swift": tests,
                base + "PublicActivity.java": activity.replacingOccurrences(of: "__PACKAGE__", with: appPackage),
                base + "PublicBridge.java": bridge.replacingOccurrences(of: "__PACKAGE__", with: appPackage),
                "Bridge/PublicBridge.c": jni.replacingOccurrences(of: "__BRIDGE_CLASS__", with: appPackage.replacingOccurrences(of: ".", with: "/") + "/PublicBridge").replacingOccurrences(of: "__ACTIVITY_CLASS__", with: appPackage.replacingOccurrences(of: ".", with: "/") + "/PublicActivity"),
                "public-host-v3.json": selection, "README.md": readme]
    }
    private static let package = #"""
    // swift-tools-version: 6.0
    import PackageDescription
    let package = Package(name: "__NAME__Android", platforms: [.macOS(.v14)],
        products: [.library(name: "AppAndroid", type: .dynamic, targets: ["AppAndroid"])],
        dependencies: [.package(name: "Application", path: "../.."), .package(path: "../../Generated/MixerSDK")],
        targets: [
            .target(name: "AppAndroid", dependencies: [.product(name: "AppFeatures", package: "Application"),
                .product(name: "MixerAndroid", package: "MixerSDK"), .product(name: "MixerCore", package: "MixerSDK"), .product(name: "MixerUI", package: "MixerSDK")]),
            .testTarget(name: "AppAndroidTests", dependencies: ["AppAndroid", .product(name: "MixerAndroid", package: "MixerSDK"), .product(name: "MixerUI", package: "MixerSDK")])
        ], swiftLanguageModes: [.v6])
    """# + "\n"
    private static let manifest = #"""
    <manifest xmlns:android="http://schemas.android.com/apk/res/android" package="__APPLICATION__" android:versionCode="1" android:versionName="0.1.0">
      <uses-sdk android:minSdkVersion="28" android:targetSdkVersion="37" />
      <application android:theme="@android:style/Theme.Material.Light.NoActionBar" android:label="__NAME__" android:debuggable="true" android:allowBackup="false" android:extractNativeLibs="true" android:supportsRtl="true">
        <activity android:name="__PACKAGE__.PublicActivity" android:exported="true" android:windowSoftInputMode="adjustResize">
          <intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter>
        </activity>
      </application>
    </manifest>
    """# + "\n"
    private static let factory = #"""
    import Foundation
    import AppFeatures
    import MixerCore
    import MixerUI
    import MixerAndroid

    @MainActor public final class ProjectPresentation: AndroidUIBatchPresentation {
        public private(set) var state = ProjectFeatureState()
        public private(set) var snapshot: UIRenderSnapshot
        private var reconciler: UIReconciler
        private var observers: [UUID: @MainActor (UIRenderSnapshot) -> Void] = [:]
        public init() throws {
            var reconciler = UIReconciler(validator: UIValidator(supportedTextFieldAxes: AndroidUIProfile.measuredMultilineRetirementV3.capabilities.textFieldAxes))
            try reconciler.apply(ProjectFeature.document(state: state, revision: 1))
            self.snapshot = try reconciler.currentSnapshot(); self.reconciler = reconciler
        }
        public func observe(_ receive: @escaping @MainActor (UIRenderSnapshot) -> Void) -> @MainActor () -> Void {
            let id = UUID(); observers[id] = receive
            return { [weak self] in self?.observers.removeValue(forKey: id) }
        }
        public func send(_ event: UIEventEnvelope) throws {
            try sendBatch([event], from: snapshot)
        }
        public func sendBatch(_ events: [UIEventEnvelope], from captured: UIRenderSnapshot) throws {
            guard !events.isEmpty, events.count <= AndroidUIHost.maximumBatchEvents,
                  try JSONEncoder().encode(events).count <= AndroidUIHost.maximumBatchBytes else { throw PublicHostError.bounds }
            guard captured.document == snapshot.document else { throw AndroidUIHostError.sourceChanged }
            let actions = try events.map { try captured.route($0) }
            guard captured.document.revision < UInt64.max else { throw PublicHostError.bounds }
            var state = self.state, reconciler = self.reconciler
            for action in actions { try ProjectFeature.handle(action, state: &state) }
            try reconciler.apply(ProjectFeature.document(state: state, revision: captured.document.revision + 1))
            let snapshot = try reconciler.currentSnapshot()
            _ = try snapshot.encodeNativePacketV1(supportedTextFieldAxes: AndroidUIProfile.measuredMultilineRetirementV3.capabilities.textFieldAxes)
            self.state = state; self.reconciler = reconciler; self.snapshot = snapshot
            for receive in Array(observers.values) { receive(snapshot) }
        }
    }
    public enum PublicHostError: Error { case bounds, surface, closed, profile, context }
    @MainActor private final class Delivery {
        weak var host: AndroidUIHost?
        var failure: (any Error)?
        func schedule() {
            Task { @MainActor [weak self] in
                guard let self, let host, host.owner != nil else { return }
                do { try host.deliverLatest() } catch { failure = error }
            }
        }
    }
    @MainActor public final class PublicAndroidApplication {
        private let delivery = Delivery()
        public let presentation: ProjectPresentation
        public let host: AndroidUIHost
        public init(surface: any AndroidUINativeSurface, selectedProfile: String) throws {
            guard selectedProfile == AndroidUIProfile.measuredMultilineRetirementV3.rawValue,
                  surface.profile == .measuredMultilineRetirementV3 else { throw PublicHostError.profile }
            presentation = try ProjectPresentation()
            host = try AndroidUIHost(surface: surface, profile: .measuredMultilineRetirementV3,
                appearance: UIAppearanceDescriptorCodecV2.mixerDefaultV2(), scheduleDelivery: { [delivery] in delivery.schedule() })
            delivery.host = host
            // Deliver synchronous reducer publications before returning the request.
            // The SDK also receives its required deferred coalesced delivery wake.
            do { try host.replace(with: presentation); try host.deliverLatest() }
            catch { host.close(); throw error }
        }
        public func send(owner: UUID, originalEnvelope: Data) throws {
            if let failure = delivery.failure { throw failure }
            guard originalEnvelope.count <= 131_072 else { throw PublicHostError.bounds }
            try JSONInputGuard.validate(originalEnvelope, limits: JSONInputLimits(maximumDepth: 8, maximumValues: 64))
            try host.send(owner: owner, event: JSONDecoder().decode(UIEventEnvelope.self, from: originalEnvelope))
            try host.deliverLatest()
        }
        public func sendBatch(owner: UUID, originalEnvelopes: Data) throws {
            if let failure = delivery.failure { throw failure }
            guard !originalEnvelopes.isEmpty, originalEnvelopes.count <= AndroidUIHost.maximumBatchBytes else { throw PublicHostError.bounds }
            try JSONInputGuard.validate(originalEnvelopes, limits: JSONInputLimits(maximumDepth: 9, maximumValues: 2049))
            let events = try JSONDecoder().decode([UIEventEnvelope].self, from: originalEnvelopes)
            try host.sendBatch(owner: owner, events: events)
            try host.deliverLatest()
        }
        public func close() { host.close() }
    }
    """# + "\n"
    private static let entry = #"""
    import Foundation
    import MixerCore
    import MixerUI
    import MixerAndroid

    private typealias SurfaceCall = @convention(c) @Sendable (Int64, Int32, UnsafePointer<UInt8>?, Int, UnsafePointer<UInt8>?, Int, UnsafePointer<UInt8>?, Int) -> Int32
    @MainActor private final class BridgeSurface: AndroidUINativeSurface {
        let context: Int64
        let callback: SurfaceCall
        var failure = false
        let profile = AndroidUIProfile.measuredMultilineRetirementV3
        var capabilities: AndroidUICapabilities { profile.capabilities }
        init(_ context: Int64, _ callback: @escaping SurfaceCall) { self.context = context; self.callback = callback }
        func call(_ operation: Int32, _ owner: UUID, _ packet: Data = Data(), _ appearance: Data = Data()) throws {
            guard !failure else { throw PublicHostError.surface }
            let owner = Data(owner.uuidString.utf8)
            let status = owner.withUnsafeBytes { o in packet.withUnsafeBytes { p in appearance.withUnsafeBytes { a in
                callback(context, operation, o.bindMemory(to: UInt8.self).baseAddress, o.count,
                    p.bindMemory(to: UInt8.self).baseAddress, p.count, a.bindMemory(to: UInt8.self).baseAddress, a.count)
            } } }
            guard status == 0 else { failure = true; throw PublicHostError.surface }
        }
        func activate(owner: UUID) throws { try call(0, owner) }
        func install(_ frame: AndroidUIFrame) throws {
            guard frame.profile == profile else { throw PublicHostError.profile }
            try call(1, frame.owner, frame.packet, frame.appearanceDescriptorV2)
        }
        func revoke(owner: UUID) {
            // Cleanup must still run after a rejected install. Preserve any earlier
            // failure and never report a failed native lifetime as accepted.
            let previous = failure; failure = false
            do { try call(2, owner) } catch { failure = true }
            failure = failure || previous
        }
    }
    private final class Replies: @unchecked Sendable {
        private let lock = NSLock()
        private var values: [Int64: Int32] = [:]
        func reserve(_ id: Int64) -> Bool {
            lock.lock(); defer { lock.unlock() }
            guard values[id] == nil, values.count < 16 else { return false }; values[id] = 0; return true
        }
        func complete(_ id: Int64, _ result: Int32) { lock.lock(); defer { lock.unlock() }; values[id] = result }
        func take(_ id: Int64) -> Int32 {
            lock.lock(); defer { lock.unlock() }
            guard let result = values[id] else { return -1 }
            if result != 0 { values.removeValue(forKey: id) }; return result
        }
    }
    private let replies = Replies()
    @MainActor private enum Applications {
        static var values: [Int64: (PublicAndroidApplication, BridgeSurface)] = [:]
        static func execute(_ id: Int64, _ operation: Int32, _ profile: String, _ owner: Data, _ event: Data, _ callback: @escaping SurfaceCall) -> Int32 {
            do {
                switch operation {
                case 0:
                    guard values[id] == nil, values.count < 16 else { throw PublicHostError.context }
                    let surface = BridgeSurface(id, callback)
                    let application = try PublicAndroidApplication(surface: surface, selectedProfile: profile)
                    values[id] = (application, surface)
                case 1:
                    guard let (application, surface) = values[id], !surface.failure,
                          let text = String(data: owner, encoding: .utf8), let token = UUID(uuidString: text),
                          Data(token.uuidString.utf8) == owner else { throw PublicHostError.context }
                    // Array payload opts into atomic batch admission; scalar ABI
                    // clients retain the existing strict single-event path.
                    if event.first(where: { ![9, 10, 13, 32].contains($0) }) == 91 {
                        try application.sendBatch(owner: token, originalEnvelopes: event)
                    } else {
                        try application.send(owner: token, originalEnvelope: event)
                    }
                case 2:
                    guard let (application, surface) = values[id] else { throw PublicHostError.context }
                    application.close()
                    guard !surface.failure else { throw PublicHostError.surface }
                    values.removeValue(forKey: id)
                default: throw PublicHostError.context
                }
                return 1
            } catch { return 2 }
        }
    }
    @_cdecl("mixer_public_android_submit")
    public func publicAndroidSubmit(_ context: Int64, _ operation: Int32,
        _ profile: UnsafePointer<UInt8>?, _ profileCount: Int,
        _ owner: UnsafePointer<UInt8>?, _ ownerCount: Int,
        _ event: UnsafePointer<UInt8>?, _ eventCount: Int,
        _ callback: @convention(c) @Sendable @escaping (Int64, Int32, UnsafePointer<UInt8>?, Int, UnsafePointer<UInt8>?, Int, UnsafePointer<UInt8>?, Int) -> Int32) -> Int32 {
        guard context > 0, (0...2).contains(operation), (0...64).contains(profileCount),
              (0...64).contains(ownerCount), (0...131_072).contains(eventCount),
              (profileCount == 0 || profile != nil), (ownerCount == 0 || owner != nil), (eventCount == 0 || event != nil) else { return 1 }
        let profile = profile.map { Data(bytes: $0, count: profileCount) } ?? Data()
        let owner = owner.map { Data(bytes: $0, count: ownerCount) } ?? Data()
        let event = event.map { Data(bytes: $0, count: eventCount) } ?? Data()
        guard let selected = String(data: profile, encoding: .utf8), replies.reserve(context) else { return 1 }
        Task { @MainActor in replies.complete(context, Applications.execute(context, operation, selected, owner, event, callback)) }
        return 0
    }
    @_cdecl("mixer_public_android_poll")
    public func publicAndroidPoll(_ context: Int64) -> Int32 {
        guard Thread.isMainThread else { return -1 }
        _ = RunLoop.main.run(mode: .default, before: Date(timeIntervalSinceNow: 0.001))
        return replies.take(context)
    }
    """# + "\n"
    private static let activity = #"""
    package __PACKAGE__;
    import android.app.Activity;
    import android.os.Bundle;
    import android.os.Handler;
    import android.os.Looper;
    import android.widget.FrameLayout;
    import dev.mixer.android.AndroidUIProfile;
    import dev.mixer.android.AndroidUINativeSurface;
    import java.util.Arrays;
    import java.util.ArrayDeque;

    public final class PublicActivity extends Activity {
        private final Handler handler = new Handler(Looper.getMainLooper());
        private FrameLayout root;
        private AndroidUINativeSurface surface;
        private byte[] owner;
        private long context;
        private boolean destroyed, failed, drainScheduled, draining;
        private static final int MAX_EVENTS = 32, MAX_BYTES = 131072;
        private static final class CapturedEvent {
            final long context; final AndroidUINativeSurface surface; final byte[] owner, envelope;
            CapturedEvent(long context, AndroidUINativeSurface surface, byte[] owner, byte[] envelope) {
                this.context = context; this.surface = surface; this.owner = owner.clone(); this.envelope = envelope.clone();
            }
        }
        private final ArrayDeque<CapturedEvent> events = new ArrayDeque<>();
        private int eventBytes = 2; // JSON array delimiters, plus comma per subsequent event.
        private int readiness;
        @Override public void onCreate(Bundle state) {
            super.onCreate(state); root = new FrameLayout(this); setContentView(root);
            if (!handler.post(this::openWhenReady)) throw new IllegalStateException("host queue unavailable");
        }
        private void openWhenReady() {
            if (destroyed || failed) return;
            if (root.getWidth() <= 0 || root.getHeight() <= 0 || root.getRootWindowInsets() == null || !root.hasWindowFocus()) {
                if (++readiness > 625 || !handler.postDelayed(this::openWhenReady, 16)) fail();
                return;
            }
            surface = new AndroidUINativeSurface(this, root, AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3, this::enqueue);
            context = PublicBridge.open(this, surface.profile().name());
            if (context <= 0) fail();
        }
        private void enqueue(byte[] capturedOwner, byte[] envelope) {
            if (Looper.myLooper() != Looper.getMainLooper() || destroyed || failed || draining || context <= 0 || surface == null ||
                owner == null || capturedOwner == null || !Arrays.equals(capturedOwner, owner) || envelope == null ||
                envelope.length == 0 || envelope.length > MAX_BYTES || events.size() >= MAX_EVENTS ||
                eventBytes + envelope.length + (events.isEmpty() ? 0 : 1) > MAX_BYTES) {
                deferQueueFailure(); throw new IllegalStateException("native event queue unavailable");
            }
            CapturedEvent first = events.peekFirst();
            if (first != null && (first.context != context || first.surface != surface || !Arrays.equals(first.owner, capturedOwner))) {
                deferQueueFailure(); throw new IllegalStateException("native event authority changed");
            }
            eventBytes += envelope.length + (events.isEmpty() ? 0 : 1);
            events.addLast(new CapturedEvent(context, surface, capturedOwner, envelope));
            if (!drainScheduled) {
                drainScheduled = true;
                if (!handler.post(this::drainEvents)) {
                    deferQueueFailure(); throw new IllegalStateException("host queue unavailable");
                }
            }
        }
        private void drainEvents() {
            drainScheduled = false;
            if (destroyed || failed) { invalidateEvents(); return; }
            if (events.isEmpty()) return;
            draining = true;
            try {
                surface.gateInput();
                CapturedEvent first = events.peekFirst();
                for (CapturedEvent event : events) {
                    if (event.context != context || event.surface != surface || !Arrays.equals(event.owner, owner) ||
                        event.context != first.context || event.surface != first.surface || !Arrays.equals(event.owner, first.owner)) {
                        fail(); return;
                    }
                }
                byte[] batch = new byte[eventBytes]; int offset = 0; batch[offset++] = '[';
                for (CapturedEvent event : events) {
                    if (offset > 1) batch[offset++] = ',';
                    System.arraycopy(event.envelope, 0, batch, offset, event.envelope.length); offset += event.envelope.length;
                }
                batch[offset++] = ']';
                if (offset != batch.length) { fail(); return; }
                invalidateEvents();
                if (PublicBridge.event(first.context, first.owner, batch) != 0) fail();
                // Only the ensuing validated surface.install reopens native input.
            } catch (RuntimeException error) {
                fail(); throw error;
            } finally { draining = false; }
        }
        // Native callbacks only record/copy and post. Even rejected input must
        // unwind its editor lease before the app asks the surface to gate.
        private void deferQueueFailure() {
            boolean first = !failed;
            failed = true; invalidateEvents();
            if (first) handler.post(this::fail);
        }
        private void invalidateEvents() { events.clear(); eventBytes = 2; }
        public int surface(long capturedContext, int operation, byte[] token, byte[] packet, byte[] descriptor) {
            if (Looper.myLooper() != Looper.getMainLooper()) return 1;
            // During open, the native bridge has not returned this lifetime's id.
            if (context == 0 && operation == 0 && !destroyed && !failed) context = capturedContext;
            if (capturedContext != context || surface == null || (destroyed && operation != 2)) return 1;
            try {
                switch (operation) {
                    case 0: if (owner != null) return 1; surface.activate(token); owner = token.clone(); break;
                    case 1: surface.install(new AndroidUINativeSurface.Frame(token, packet, descriptor)); break;
                    case 2: invalidateEvents(); surface.revoke(token); owner = null; break;
                    default: return 1;
                }
                return 0;
            } catch (RuntimeException error) { android.util.Log.e("MixerAndroidHost", "Native surface operation failed: " + operation, error); fail(); return 1; }
        }
        private void fail() { failed = true; invalidateEvents(); if (surface != null) surface.gateInput(); }
        @Override public void onResume() { super.onResume(); if (surface != null) surface.onResume(); }
        @Override public void onPause() { if (surface != null) surface.onPause(); super.onPause(); }
        @Override public void onStop() { if (surface != null) surface.onStop(); super.onStop(); }
        @Override public void onDestroy() {
            destroyed = true; invalidateEvents(); handler.removeCallbacksAndMessages(null);
            if (context > 0 && PublicBridge.close(context) != 0) failed = true;
            if (surface != null) surface.close(); super.onDestroy();
        }
    }
    """# + "\n"
    private static let bridge = #"""
    package __PACKAGE__;
    public final class PublicBridge {
        static { System.loadLibrary("mixer_public_android_jni"); }
        private PublicBridge() {}
        public static long open(PublicActivity receiver, String profile) { requireMain(); return openNative(receiver, profile); }
        public static int event(long context, byte[] owner, byte[] envelope) { requireMain(); return eventNative(context, owner, envelope); }
        public static int close(long context) { requireMain(); return closeNative(context); }
        private static native long openNative(PublicActivity receiver, String profile);
        private static native int eventNative(long context, byte[] originalOwner, byte[] originalEnvelope);
        private static native int closeNative(long context);
        private static void requireMain() {
            if (android.os.Looper.myLooper() != android.os.Looper.getMainLooper()) throw new IllegalStateException("Android main thread required");
        }
    }
    """# + "\n"
    private static let jni = #"""
    #include <jni.h>
    #include <stdint.h>
    #include <stdlib.h>
    #include <string.h>
    typedef int32_t (*surface_callback)(int64_t,int32_t,const uint8_t*,intptr_t,const uint8_t*,intptr_t,const uint8_t*,intptr_t);
    extern int32_t mixer_public_android_submit(int64_t,int32_t,const uint8_t*,intptr_t,const uint8_t*,intptr_t,const uint8_t*,intptr_t,surface_callback);
    extern int32_t mixer_public_android_poll(int64_t);
    typedef struct Context { int64_t id; jobject receiver; int busy, failed; struct Context *next; } Context;
    static Context *contexts;
    static int64_t next_id;
    static _Thread_local JNIEnv *pump_env;
    static Context *find(int64_t id) { for(Context *p=contexts;p;p=p->next) if(p->id==id) return p; return NULL; }
    static jbyteArray bytes(JNIEnv *e,const uint8_t *p,intptr_t n) {
        if(n<0||n>1048576||(n&&!p)) return NULL;
        jbyteArray a=(*e)->NewByteArray(e,(jsize)n);
        if(a&&n) (*e)->SetByteArrayRegion(e,a,0,(jsize)n,(const jbyte*)p);
        return a;
    }
    static int32_t surface(int64_t id,int32_t op,const uint8_t *o,intptr_t on,const uint8_t *p,intptr_t pn,const uint8_t *a,intptr_t an) {
        JNIEnv *e=pump_env; Context *c=find(id); if(!e||!c||!c->busy) return 1;
        jclass type=(*e)->GetObjectClass(e,c->receiver); if(!type) return 1;
        jmethodID method=(*e)->GetMethodID(e,type,"surface","(JI[B[B[B)I");
        jbyteArray owner=bytes(e,o,on),packet=bytes(e,p,pn),appearance=bytes(e,a,an);
        jint result=1;
        if(method&&owner&&packet&&appearance&&!(*e)->ExceptionCheck(e)) result=(*e)->CallIntMethod(e,c->receiver,method,(jlong)id,(jint)op,owner,packet,appearance);
        if((*e)->ExceptionCheck(e)) { (*e)->ExceptionClear(e); result=1; }
        if(owner) (*e)->DeleteLocalRef(e,owner);
        if(packet) (*e)->DeleteLocalRef(e,packet);
        if(appearance) (*e)->DeleteLocalRef(e,appearance);
        (*e)->DeleteLocalRef(e,type); return result;
    }
    static int execute(JNIEnv *e,Context *c,int op,const uint8_t *profile,intptr_t profile_n,const uint8_t *owner,intptr_t owner_n,const uint8_t *event,intptr_t event_n) {
        if(!c||c->busy||pump_env||(c->failed&&op!=2)) return 1;
        c->busy=1;
        int result=mixer_public_android_submit(c->id,op,profile,profile_n,owner,owner_n,event,event_n,surface);
        if(result==0) {
            pump_env=e; int status=0;
            for(int i=0;i<1000&&status==0;i++) status=mixer_public_android_poll(c->id);
            pump_env=NULL; result=status==1?0:1;
            if(status==0) c->failed=1; /* Unknown queued work: retain, never retry. */
        }
        c->busy=0; return result;
    }
    static jlong open_host(JNIEnv *e,jclass ignored,jobject receiver,jstring profile) {
        (void)ignored; if(!receiver||!profile||next_id==INT64_MAX) return 0;
        int count=0; for(Context *p=contexts;p;p=p->next) count++;
        if(count>=16) return 0;
        jsize n=(*e)->GetStringUTFLength(e,profile); if(n<=0||n>64) return 0;
        const char *text=(*e)->GetStringUTFChars(e,profile,NULL); if(!text) return 0;
        if(n!=(jsize)strlen("MEASURED_MULTILINE_RETIREMENT_V3")||memcmp(text,"MEASURED_MULTILINE_RETIREMENT_V3",(size_t)n)!=0) { (*e)->ReleaseStringUTFChars(e,profile,text); return 0; }
        Context *c=calloc(1,sizeof(*c)); if(!c) { (*e)->ReleaseStringUTFChars(e,profile,text); return 0; }
        c->id=++next_id; c->receiver=(*e)->NewGlobalRef(e,receiver);
        if(!c->receiver) { free(c); (*e)->ReleaseStringUTFChars(e,profile,text); return 0; }
        c->next=contexts; contexts=c;
        int result=execute(e,c,0,(const uint8_t*)text,n,NULL,0,NULL,0);
        (*e)->ReleaseStringUTFChars(e,profile,text);
        if(result) { c->failed=1; return 0; } /* Keep uncertain activation cleanup visible. */
        return c->id;
    }
    static jint event_host(JNIEnv *e,jclass ignored,jlong id,jbyteArray owner,jbyteArray event) {
        (void)ignored; Context *c=find(id); if(!c||!owner||!event) return 1;
        jsize on=(*e)->GetArrayLength(e,owner),en=(*e)->GetArrayLength(e,event);
        if(on<=0||on>64||en<=0||en>131072) return 1;
        jbyte *o=(*e)->GetByteArrayElements(e,owner,NULL); if(!o) return 1;
        jbyte *v=(*e)->GetByteArrayElements(e,event,NULL); if(!v) { (*e)->ReleaseByteArrayElements(e,owner,o,JNI_ABORT); return 1; }
        int result=execute(e,c,1,NULL,0,(const uint8_t*)o,on,(const uint8_t*)v,en);
        (*e)->ReleaseByteArrayElements(e,event,v,JNI_ABORT); (*e)->ReleaseByteArrayElements(e,owner,o,JNI_ABORT); return result;
    }
    static jint close_host(JNIEnv *e,jclass ignored,jlong id) {
        (void)ignored; Context *c=find(id); if(!c||c->failed) return 1;
        if(execute(e,c,2,NULL,0,NULL,0,NULL,0)) { c->failed=1; return 1; }
        Context **link=&contexts; while(*link!=c) link=&(*link)->next;
        *link=c->next; (*e)->DeleteGlobalRef(e,c->receiver); free(c); return 0;
    }
    /* Package-specific names are supplied at build time without JNI name escaping.
       RegisterNatives requires the exact generated PublicBridge class. */
    JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm,void *reserved) {
        (void)reserved; JNIEnv *e=NULL;
        if((*vm)->GetEnv(vm,(void**)&e,JNI_VERSION_1_6)!=JNI_OK) return JNI_ERR;
        jclass type=(*e)->FindClass(e,"__BRIDGE_CLASS__"); if(!type) return JNI_ERR;
        JNINativeMethod methods[]={{"openNative","(L__ACTIVITY_CLASS__;Ljava/lang/String;)J",(void*)open_host},
            {"eventNative","(J[B[B)I",(void*)event_host},{"closeNative","(J)I",(void*)close_host}};
        jint status=(*e)->RegisterNatives(e,type,methods,3); (*e)->DeleteLocalRef(e,type);
        return status==0?JNI_VERSION_1_6:JNI_ERR;
    }
    """# + "\n"
    private static let readme = #"""
    # Public Android V3 development host

    Selected explicitly by `mixer create NAME --platform android --android-host public-v3`.
    The app-owned external-package Activity consumes only public facade/profile APIs.
    Shared Swift uses public MixerAndroid/MixerUI/MixerCore. Original owner, native
    packet, appearance and event bytes cross the app JNI glue without JSON rebasing.
    Each Activity has an independent bounded context and receiver; no global current
    callback context exists. Callbacks execute only during the Android-main pump.
    Queued native events retain original bytes and authority in a 32-event,
    131072-byte FIFO. A deferred drain submits one JSON array without numeric
    decoding/re-encoding. The optional public batch presentation validates every
    member against the same installed snapshot and publishes one app-owned atomic
    transaction; scalar operation-1 payloads keep strict legacy admission.
    The starter
    has process-local value state and synchronous reducers; it has no persistence
    or asynchronous app effects. Changing config does not migrate an existing host.

    `swift test --package-path Platforms/Android -j 2` executes the exact public
    factory, open/edit/add/toggle/close, original-frame and refusal tests on macOS.
    These controlled native surface tests do not establish Android JNI execution.
    `mixer build --platform android` packages this explicit public host with its
    app-owned JNI and external Activity. Native input batches retain original
    envelopes and publish one app transaction per originating installed frame.
    No fallback to staged-v2 is supported. Immutable published-package, Android
    runtime/device, signing/store, cleanup on Android and GA qualification remain pending.
    """# + "\n"
    private static let tests = #"""
    import Foundation
    import Testing
    import MixerUI
    import MixerAndroid
    @testable import AppAndroid

    @MainActor private final class Surface: AndroidUINativeSurface {
        var profile = AndroidUIProfile.measuredMultilineRetirementV3
        var capabilities: AndroidUICapabilities { profile.capabilities }
        var owner: UUID?
        var frames: [AndroidUIFrame] = []
        var revocations = 0
        func activate(owner: UUID) throws { #expect(self.owner == nil); self.owner = owner }
        func install(_ frame: AndroidUIFrame) throws {
            #expect(frame.owner == owner); #expect(frame.profile == profile)
            #expect(try frame.snapshot.encodeNativePacketV1(supportedTextFieldAxes: profile.capabilities.textFieldAxes) == frame.packet)
            #expect(try UIAppearanceDescriptorCodecV2.canonicalData(UIAppearanceDescriptorCodecV2.mixerDefaultV2()) == frame.appearanceDescriptorV2)
            frames.append(frame)
        }
        func revoke(owner: UUID) { #expect(self.owner == owner); self.owner = nil; revocations += 1 }
    }
    @MainActor @Test func publicFactoryOpenEditAddToggleCloseAndRefusals() throws {
        let surface = Surface()
        let app = try PublicAndroidApplication(surface: surface, selectedProfile: AndroidUIProfile.measuredMultilineRetirementV3.rawValue)
        let initial = try #require(surface.frames.last), owner = try #require(app.host.owner)
        func event(_ id: String, _ kind: UIEventKind, _ value: UIValue) throws -> Data {
            let frame = try #require(surface.frames.last)
            return try JSONEncoder().encode(UIEventEnvelope(revision: frame.snapshot.document.revision,
                identity: #require(frame.snapshot.identity(for: id)), event: kind, value: value))
        }
        let edit = try event("draft", .textChange, .string("Café 東京 🧪\noriginal"))
        #expect(throws: (any Error).self) { try app.send(owner: UUID(), originalEnvelope: edit) }
        #expect(surface.frames.count == 1)
        try app.send(owner: owner, originalEnvelope: edit)
        #expect(app.presentation.state.draft == "Café 東京 🧪\noriginal")
        #expect(throws: (any Error).self) { try app.send(owner: owner, originalEnvelope: edit) }
        try app.send(owner: owner, originalEnvelope: event("add", .activate, .null))
        #expect(app.presentation.state.entries.count == 1)
        #expect(app.presentation.state.entries[0].title == "Café 東京 🧪\noriginal")
        #expect(app.presentation.state.draft.isEmpty)
        let id = "entry." + app.presentation.state.entries[0].id.uuidString
        try app.send(owner: owner, originalEnvelope: event(id, .valueChange, .bool(true)))
        #expect(app.presentation.state.entries[0].completed)
        #expect(String(decoding: try #require(surface.frames.last).packet, as: UTF8.self).contains("1 of 1 completed"))
        #expect(throws: (any Error).self) { try app.send(owner: owner, originalEnvelope: Data("{}".utf8)) }
        #expect(throws: (any Error).self) { try app.send(owner: owner, originalEnvelope: Data(repeating: 32, count: 131_073)) }
        #expect(surface.frames.count == 4)
        #expect(initial.packet != surface.frames.last?.packet)
        app.close(); app.close(); #expect(surface.revocations == 1); #expect(app.host.owner == nil)
        #expect(throws: (any Error).self) { try app.send(owner: owner, originalEnvelope: edit) }
        let successor = Surface()
        let next = try PublicAndroidApplication(surface: successor, selectedProfile: AndroidUIProfile.measuredMultilineRetirementV3.rawValue)
        #expect(next.host.owner != owner); #expect(next.presentation.state.entries.isEmpty)
        next.close(); #expect(successor.revocations == 1)
    }
    @MainActor @Test func bothSidesMustSelectPublicV3() throws {
        let surface = Surface()
        #expect(throws: (any Error).self) { _ = try PublicAndroidApplication(surface: surface, selectedProfile: "LEGACY_HORIZONTAL") }
        #expect(surface.frames.isEmpty); #expect(surface.owner == nil)
        surface.profile = .measuredMultilineV2
        #expect(throws: (any Error).self) { _ = try PublicAndroidApplication(surface: surface, selectedProfile: "MEASURED_MULTILINE_RETIREMENT_V3") }
        #expect(surface.frames.isEmpty)
    }

    @MainActor @Test func publicBatchOrdersTextSubmitTextAndPublishesOnce() throws {
        let surface = Surface()
        let app = try PublicAndroidApplication(surface: surface, selectedProfile: surface.profile.rawValue)
        defer { app.close() }
        let owner = try #require(app.host.owner), original = app.presentation.snapshot
        let identity = try #require(original.identity(for: "draft"))
        let events = [UIEventEnvelope(revision: original.document.revision, identity: identity, event: .textChange, value: .string("first 🧪")),
                      UIEventEnvelope(revision: original.document.revision, identity: identity, event: .submit),
                      UIEventEnvelope(revision: original.document.revision, identity: identity, event: .textChange, value: .string("tail"))]
        var publications = 0
        let cancel = app.presentation.observe { _ in publications += 1 }; defer { cancel() }
        try app.sendBatch(owner: owner, originalEnvelopes: JSONEncoder().encode(events))
        #expect(app.presentation.state.entries.map(\.title) == ["first 🧪"])
        #expect(app.presentation.state.draft == "tail")
        #expect(publications == 1 && surface.frames.count == 2)
        #expect(app.presentation.snapshot.document.revision == original.document.revision + 1)
        #expect(throws: UIRoutingError.staleRevision) { try app.sendBatch(owner: owner, originalEnvelopes: JSONEncoder().encode(events)) }
        #expect(publications == 1)
    }
    @MainActor @Test func publicBatchInvalidSecondAndReducerFailureAreAtomic() throws {
        let surface = Surface()
        let app = try PublicAndroidApplication(surface: surface, selectedProfile: surface.profile.rawValue)
        defer { app.close() }
        let owner = try #require(app.host.owner), original = app.presentation.snapshot
        let identity = try #require(original.identity(for: "draft"))
        let first = UIEventEnvelope(revision: original.document.revision, identity: identity, event: .textChange, value: .string("first"))
        let invalid = UIEventEnvelope(revision: original.document.revision, identity: identity, event: .textChange, value: .bool(true))
        let reducerInvalid = UIEventEnvelope(revision: original.document.revision, identity: identity, event: .textChange, value: .string(String(repeating: "a", count: 16_385)))
        // First two valid actions would allocate an entry in local copied state.
        let submit = UIEventEnvelope(revision: original.document.revision, identity: identity, event: .submit)
        var publications = 0
        let cancel = app.presentation.observe { _ in publications += 1 }; defer { cancel() }
        for events in [[first, invalid], [first, submit, reducerInvalid], [first, submit, submit]] {
            #expect(throws: (any Error).self) { try app.sendBatch(owner: owner, originalEnvelopes: JSONEncoder().encode(events)) }
            #expect(app.presentation.state.draft.isEmpty && app.presentation.state.entries.isEmpty)
            #expect(app.presentation.snapshot.document == original.document)
            #expect(publications == 0 && surface.frames.count == 1)
        }
        let valid = try JSONEncoder().encode([first])
        #expect(throws: AndroidUIHostError.staleOwner) { try app.sendBatch(owner: UUID(), originalEnvelopes: valid) }
        for data in [Data("[]".utf8), Data("[{},{}]".utf8), Data("[null]".utf8), try JSONEncoder().encode(Array(repeating: first, count: 33)), Data(repeating: 32, count: 131_073)] {
            #expect(throws: (any Error).self) { try app.sendBatch(owner: owner, originalEnvelopes: data) }
            #expect(app.presentation.snapshot.document == original.document)
        }
        try app.send(owner: owner, originalEnvelope: JSONEncoder().encode(first))
        #expect(app.presentation.state.draft == "first" && publications == 1)
        #expect(throws: UIRoutingError.staleRevision) { try app.send(owner: owner, originalEnvelope: JSONEncoder().encode(first)) }
    }
    """# + "\n"
}
