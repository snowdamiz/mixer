package mixer.capabilities;
import java.util.*;
import java.nio.charset.StandardCharsets;

/** Dependency-free hostile API tests; no Android/JNI/device claim. */
public final class CapabilityCodecTests {
    private static int checks;
    private CapabilityCodecTests() {}
    private static void check(boolean value) { checks++;if(!value)throw new AssertionError("capability codec check "+checks); }
    private static void rejects(Runnable operation) { boolean rejected=false;try{operation.run();}catch(IllegalArgumentException expected){rejected=true;}check(rejected); }
    public static void main(String[] args) {
        CapabilityCodec.Identity id=new CapabilityCodec.Identity("01234567-89ab-4cde-8fab-0123456789ab",0,1);
        CapabilityCodec.Inbound call=new CapabilityCodec.Inbound("call",id,"storage.keyValue.v1","get",new CapabilityModels.KVGetArguments("entries","one"));
        byte[] bytes=CapabilityCodec.encodeInbound(call);check(CapabilityCodec.decodeInbound(bytes).identity.equals(id));
        Arrays.fill(bytes,(byte)'x');check(call.identity.equals(id));
        rejects(()->CapabilityCodec.decodeInbound(null));
        rejects(()->CapabilityCodec.decodeInbound(new byte[]{(byte)0xc0,(byte)0x80}));
        rejects(()->CapabilityCodec.decodeInbound("{\"a\":1,\"\\u0061\":2}".getBytes(StandardCharsets.UTF_8)));
        for(String failure:new String[]{"permissionDenied","unavailable","cancelled","deadlineExceeded","invalidResponse","redirectDenied","quotaExceeded","ioFailure"}) {
            byte[] encoded=CapabilityCodec.encodeCompletion(new CapabilityCodec.Completion(call,null,failure));
            check(CapabilityCodec.decodeCompletion(encoded,call).failure.equals(failure));
        }
        rejects(()->CapabilityCodec.encodeCompletion(new CapabilityCodec.Completion(call,null,"nativeException: secret")));
        rejects(()->CapabilityCodec.encodeCompletion(new CapabilityCodec.Completion(call,new CapabilityModels.KVGetResponse(false,""),"cancelled")));
        final int[] invocations={0};
        CapabilityModels.Model changing=()->{invocations[0]++;return invocations[0]==1?new CapabilityModels.KVGetResponse(true,"Zg==").wire():CapabilityJSON.map("arbitrary",true);};
        byte[] snapshot=CapabilityCodec.encodeCompletion(new CapabilityCodec.Completion(call,changing,null));
        check(invocations[0]==1);check(CapabilityCodec.decodeCompletion(snapshot,call).value instanceof CapabilityModels.KVGetResponse);
        List<CapabilityModels.Header> headers=new ArrayList<>();headers.add(new CapabilityModels.Header("x-one","v"));
        CapabilityModels.HTTPRequestArguments request=new CapabilityModels.HTTPRequestArguments("https://api.example.test/","GET",headers,"",1);headers.clear();check(request.headers.size()==1);
        rejects(()->CapabilityCodec.encodeInbound(new CapabilityCodec.Inbound("call",id,"network.http.v1","request",new CapabilityModels.HTTPRequestArguments("https://api.example.test/","GET",Collections.singletonList(new CapabilityModels.Header("cookie","s")),"",1))));
        CapabilityCodec.Inbound foreign=new CapabilityCodec.Inbound("call",new CapabilityCodec.Identity(id.session,0,2),call.capability,call.operation,call.arguments);
        rejects(()->CapabilityCodec.decodeCompletion(snapshot,foreign));
        System.out.println("{\"checks\":"+checks+",\"passed\":true,\"scope\":\"Java codec host only\"}");
    }
}
