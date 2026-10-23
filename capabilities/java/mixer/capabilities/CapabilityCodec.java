package mixer.capabilities;
import java.util.*;

/** JNI-facing boundary is bounded byte[] plus explicit value records, never pointers. */
public final class CapabilityCodec {
    private CapabilityCodec() {}
    public static final class Identity {
        public final String session; public final int slot; public final long generation;
        public Identity(String session,int slot,long generation) { this.session=session;this.slot=slot;this.generation=generation; }
        Map<String,Object> wire() { return CapabilityJSON.map("session",session,"slot",(long)slot,"generation",generation); }
        @Override public boolean equals(Object raw) { return raw instanceof Identity && ((Identity)raw).session.equals(session)&&((Identity)raw).slot==slot&&((Identity)raw).generation==generation; }
        @Override public int hashCode() { return Objects.hash(session,slot,generation); }
    }
    public static final class Inbound {
        public final String kind,capability,operation; public final Identity identity; public final CapabilityModels.Model arguments;
        public Inbound(String kind,Identity identity,String capability,String operation,CapabilityModels.Model arguments) { this.kind=kind;this.identity=identity;this.capability=capability;this.operation=operation;this.arguments=arguments; }
    }
    public static final class Completion {
        public final Inbound call; public final CapabilityModels.Model value; public final String failure;
        public Completion(Inbound call,CapabilityModels.Model value,String failure) { this.call=call;this.value=value;this.failure=failure; }
    }
    private static final Set<String> FAILURES=CapabilityJSON.keys("permissionDenied","unavailable","cancelled","deadlineExceeded","invalidResponse","redirectDenied","quotaExceeded","ioFailure");
    private static Identity identity(Object raw) { Map<String,Object> m=CapabilityJSON.object(raw); CapabilityJSON.exact(m,CapabilityJSON.keys("session","slot","generation"));return new Identity(CapabilityJSON.text(m,"session","uuid",36),(int)CapabilityJSON.number(m,"slot",0,65535),CapabilityJSON.number(m,"generation",1,4294967295L)); }
    private static String[] metadata(Map<String,Object> m) {
        CapabilityJSON.number(m,"schema",1,1); String cap=CapabilityJSON.text(m,"capability","ascii",64),op=CapabilityJSON.text(m,"operation","ascii",16);
        String[] descriptor=CapabilityModels.descriptor(cap,op);
        if(!CapabilityJSON.text(m,"schemaHash","ascii",64).equals(descriptor[0])) throw CapabilityJSON.bad("schema hash");return descriptor;
    }
    public static Inbound decodeInbound(byte[] bytes) {
        Map<String,Object> m=CapabilityJSON.parse(bytes);String kind=CapabilityJSON.text(m,"kind","ascii",16);
        if(!CapabilityJSON.keys("call","cancel").contains(kind)) throw CapabilityJSON.bad("kind");
        CapabilityJSON.exact(m,kind.equals("call")?CapabilityJSON.keys("schema","kind","identity","capability","schemaHash","operation","arguments"):CapabilityJSON.keys("schema","kind","identity","capability","schemaHash","operation"));
        String[] descriptor=metadata(m);return new Inbound(kind,identity(m.get("identity")),(String)m.get("capability"),(String)m.get("operation"),kind.equals("call")?CapabilityModels.decode(descriptor[1],CapabilityJSON.object(m.get("arguments"))):null);
    }
    private static Map<String,Object> envelope(Inbound call,String kind) {
        String[] descriptor=CapabilityModels.descriptor(call.capability,call.operation);identity(call.identity.wire());
        Map<String,Object> m=new LinkedHashMap<>();m.put("schema",1L);m.put("kind",kind);m.put("identity",call.identity.wire());m.put("capability",call.capability);m.put("schemaHash",descriptor[0]);m.put("operation",call.operation);return m;
    }
    public static byte[] encodeInbound(Inbound call) {
        Map<String,Object> m=envelope(call,call.kind);
        if(call.kind.equals("call")) { if(call.arguments==null)throw CapabilityJSON.bad("arguments");CapabilityModels.Model owned=CapabilityModels.decode(CapabilityModels.descriptor(call.capability,call.operation)[1],call.arguments.wire());m.put("arguments",owned.wire()); }
        else if(!call.kind.equals("cancel")||call.arguments!=null) throw CapabilityJSON.bad("cancel arguments");
        byte[] bytes=CapabilityJSON.encode(m);decodeInbound(bytes);return bytes;
    }
    public static byte[] encodeCompletion(Completion completion) {
        Map<String,Object> m=envelope(completion.call,"completion");
        if(completion.failure!=null) { if(completion.value!=null||!FAILURES.contains(completion.failure))throw CapabilityJSON.bad("failure");m.put("outcome",CapabilityJSON.map("kind","failure","code",completion.failure)); }
        else { if(completion.value==null)throw CapabilityJSON.bad("value");CapabilityModels.Model owned=CapabilityModels.decode(CapabilityModels.descriptor(completion.call.capability,completion.call.operation)[2],completion.value.wire());m.put("outcome",CapabilityJSON.map("kind","success","value",owned.wire())); }
        return CapabilityJSON.encode(m);
    }
    public static Completion decodeCompletion(byte[] bytes,Inbound expected) {
        Map<String,Object> m=CapabilityJSON.parse(bytes);CapabilityJSON.exact(m,CapabilityJSON.keys("schema","kind","identity","capability","schemaHash","operation","outcome"));String[] descriptor=metadata(m);
        if(!"completion".equals(m.get("kind"))||!identity(m.get("identity")).equals(expected.identity)||!expected.capability.equals(m.get("capability"))||!expected.operation.equals(m.get("operation")))throw CapabilityJSON.bad("completion owner");
        Map<String,Object> o=CapabilityJSON.object(m.get("outcome"));String kind=CapabilityJSON.text(o,"kind","ascii",16);
        if(kind.equals("success")) { CapabilityJSON.exact(o,CapabilityJSON.keys("kind","value"));return new Completion(expected,CapabilityModels.decode(descriptor[2],CapabilityJSON.object(o.get("value"))),null); }
        if(kind.equals("failure")) { CapabilityJSON.exact(o,CapabilityJSON.keys("kind","code"));String code=CapabilityJSON.text(o,"code","ascii",32);if(!FAILURES.contains(code))throw CapabilityJSON.bad("failure code");return new Completion(expected,null,code); }
        throw CapabilityJSON.bad("outcome");
    }
}
