package dev.mixer.android;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
public final class IndependentPairProbe {
    static int checks=0;
    interface Task { void run() throws Exception; }
    static void ok(String name,boolean value){if(!value)throw new AssertionError(name);checks++;System.out.println("PASS "+name);}
    static void reject(String name,Task body) throws Exception {
        boolean refused=false;try{body.run();}catch(IllegalArgumentException expected){refused=true;}
        ok(name,refused);
    }
    static byte[] encoded(Map<String,Object> value){return Json.encode(value);}
    static Map<String,Object> object(byte[] value){return Json.object(Json.parse(value));}
    static String text(byte[] value){return new String(value,StandardCharsets.UTF_8);}
    public static void main(String[] args) throws Exception {
        Path input=Path.of(args[0]),output=Path.of(args[1]);Files.createDirectories(output);
        byte[] initial=Files.readAllBytes(input.resolve("app-initial.json"));
        byte[] successor=Files.readAllBytes(input.resolve("app-successor.json"));
        byte[] previousFull=Files.readAllBytes(input.resolve("full-previous.json"));
        byte[] nextFull=Files.readAllBytes(input.resolve("full-next.json"));
        byte[] descriptor=Files.readAllBytes(input.resolve("descriptor.json"));
        UiPacket a=UiPacket.decode(initial),b=UiPacket.decode(successor);
        ok("actual application initial revision",a.revision.equals("1"));
        ok("actual application successor revision",b.revision.equals("2"));
        b.requireSuccessor(a);ok("actual application successor accepted",true);
        UiPacket highA=UiPacket.decode(previousFull),highB=UiPacket.decode(nextFull);
        ok("actual UInt64 previous revision",highA.revision.equals("18446744073709551614"));
        ok("actual UInt64 max revision",highB.revision.equals("18446744073709551615"));
        ok("actual UInt64 max generation",highB.root.generation.equals("18446744073709551615"));
        highB.requireSuccessor(highA);ok("UInt64 successor comparison",true);
        byte[] event=highB.event("full","18446744073709551615","activate",null);
        Files.write(output.resolve("full-event.json"),event);
        ok("UInt64 event numeric spelling",text(event).contains("18446744073709551615"));
        AppearanceDescriptorV2.decode(descriptor);ok("actual copied Swift descriptor decoded",true);
        reject("packet unsupported schema",()->{var v=object(initial);v.put("schemaVersion",new Json.Num("2"));UiPacket.decode(encoded(v));});
        reject("document unsupported schema",()->{var v=object(initial);Json.object(v.get("document")).put("schemaVersion",new Json.Num("2"));UiPacket.decode(encoded(v));});
        reject("packet unknown field",()->{var v=object(initial);v.put("unknown",true);UiPacket.decode(encoded(v));});
        reject("packet duplicate field",()->UiPacket.decode(text(initial).replaceFirst("\\{","{\"schemaVersion\":1,").getBytes(StandardCharsets.UTF_8)));
        reject("packet malformed JSON",()->UiPacket.decode(Arrays.copyOf(initial,initial.length-1)));
        reject("packet missing identity",()->{var v=object(initial);Json.array(v.get("identities")).remove(0);UiPacket.decode(encoded(v));});
        reject("packet duplicate identity",()->{var v=object(initial);var ids=Json.array(v.get("identities"));ids.add(ids.get(0));UiPacket.decode(encoded(v));});
        reject("packet extra identity",()->{var v=object(initial);Json.array(v.get("identities")).add(Json.map("id","not-in-document","generation",new Json.Num("99999")));UiPacket.decode(encoded(v));});
        reject("packet zero generation",()->{var v=object(nextFull);Json.object(Json.array(v.get("identities")).get(0)).put("generation",new Json.Num("0"));UiPacket.decode(encoded(v));});
        reject("packet generation UInt64 overflow",()->{var v=object(nextFull);Json.object(Json.array(v.get("identities")).get(0)).put("generation",new Json.Num("18446744073709551616"));UiPacket.decode(encoded(v));});
        reject("packet revision UInt64 overflow",()->{var v=object(nextFull);Json.object(v.get("document")).put("revision",new Json.Num("18446744073709551616"));UiPacket.decode(encoded(v));});
        reject("successor stale revision",()->a.requireSuccessor(b));
        reject("successor same revision",()->highB.requireSuccessor(highB));
        reject("surviving node generation drift",()->{var v=object(nextFull);Json.object(Json.array(v.get("identities")).get(0)).put("generation",new Json.Num("18446744073709551614"));UiPacket.decode(encoded(v)).requireSuccessor(highA);});
        reject("event stale generation",()->highB.event("full","9007199254740993","activate",null));
        reject("event unsupported binding",()->highB.event("full",highB.root.generation,"textChange","bad"));
        reject("descriptor unsupported format",()->AppearanceDescriptorV2.decode(text(descriptor).replace("mixer.native-appearance.2","mixer.native-appearance.9").getBytes(StandardCharsets.UTF_8)));
        reject("descriptor unsupported recipe",()->AppearanceDescriptorV2.decode(text(descriptor).replace("measuredShared2","unreviewed").getBytes(StandardCharsets.UTF_8)));
        reject("descriptor unknown field",()->AppearanceDescriptorV2.decode(text(descriptor).replaceFirst("\\{","{\"a\":1,").getBytes(StandardCharsets.UTF_8)));
        reject("descriptor duplicate field",()->AppearanceDescriptorV2.decode(text(descriptor).replaceFirst("\\{","{\"format\":\"mixer.native-appearance.2\",").getBytes(StandardCharsets.UTF_8)));
        reject("descriptor malformed JSON",()->AppearanceDescriptorV2.decode(Arrays.copyOf(descriptor,descriptor.length-1)));
        System.out.println("INDEPENDENT_JAVA_CHECKS="+checks);
    }
}
