package mixer.capabilities;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Qualification executable only; not a native transport or dispatch surface. */
public final class CapabilityProbe {
    private CapabilityProbe() {}
    public static void main(String[] args) throws IOException {
        try {
            ByteArrayOutputStream bytes=new ByteArrayOutputStream(); byte[] buffer=new byte[8192]; int count;
            while((count=System.in.read(buffer))!=-1) { if(bytes.size()+count>524288) throw CapabilityJSON.bad("probe bound");bytes.write(buffer,0,count); }
            String mode=args.length==0?"roundtrip":args[0]; byte[] output;
            if(mode.equals("decode-completion")) {
                if(args.length!=2) throw CapabilityJSON.bad("probe expected");
                CapabilityCodec.Inbound expected=CapabilityCodec.decodeInbound(Files.readAllBytes(Paths.get(args[1])));
                output=CapabilityCodec.encodeCompletion(CapabilityCodec.decodeCompletion(bytes.toByteArray(),expected));
            } else {
                CapabilityCodec.Inbound call=CapabilityCodec.decodeInbound(bytes.toByteArray());
                if(mode.equals("complete")&&call.kind.equals("call")) {
                    CapabilityModels.Model result;
                    if(call.capability.equals("network.http.v1"))result=new CapabilityModels.HTTPResponse(200,Collections.emptyList(),"Zml4dHVyZQ==");
                    else if(call.operation.equals("get"))result=new CapabilityModels.KVGetResponse(true,"Zml4dHVyZQ==");
                    else result=new CapabilityModels.KVMutationResponse(true);
                    output=CapabilityCodec.encodeCompletion(new CapabilityCodec.Completion(call,result,null));
                } else if(mode.equals("roundtrip"))output=CapabilityCodec.encodeInbound(call);
                else throw CapabilityJSON.bad("probe mode");
            }
            System.out.write(output);
        } catch(IllegalArgumentException e) { System.err.println("capability probe rejected input");System.exit(1); }
    }
}
