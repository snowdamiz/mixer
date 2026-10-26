package dev.mixer.android;
import java.nio.charset.StandardCharsets;
public final class ContractTests {
    static int checks=0;
    static void check(boolean ok){checks++;if(!ok)throw new AssertionError("check "+checks);}
    static void reject(Runnable test){boolean rejected=false;try{test.run();}catch(IllegalArgumentException expected){rejected=true;}check(rejected);}
    static byte[] bytes(String value){return value.getBytes(StandardCharsets.UTF_8);}
    static String node(String id,String kind,String props,String children,String actions){return "{\"id\":\""+id+"\",\"kind\":\""+kind+"\",\"properties\":"+props+",\"children\":"+children+",\"actions\":"+actions+"}";}
    static byte[] packet(String node,String identities,String revision){return bytes("{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":"+revision+",\"root\":"+node+"},\"identities\":"+identities+"}");}
    public static void main(String[]args){
        String identities="[{\"id\":\"root\",\"generation\":1}]";String text=node("root","text","{\"text\":\"Hello 東京 🧪\"}","[]","[]");UiPacket first=UiPacket.decode(packet(text,identities,"1"));check(first.root.text("text","").equals("Hello 東京 🧪"));
        reject(()->Json.parse(bytes("{\"x\":1,\"x\":2}")));reject(()->Json.parse(bytes("{\"x\":1,\"\\u0078\":2}")));reject(()->Json.parse(new byte[]{(byte)0xff}));reject(()->Json.parse(bytes("\"\\ud800\"")));reject(()->Json.parse(bytes("01")));reject(()->Json.parse(bytes("1e999")));reject(()->Json.parse(new byte[1048577]));reject(()->Json.parse(bytes("[".repeat(197)+"0"+"]".repeat(197))));
        reject(()->Json.parse(bytes("\"\\u００６１\"")));
        reject(()->Json.parse(bytes("{\"a\":1,\"\\u٠٠٦١\":2}")));
        reject(()->Json.parse(bytes("\"\\u00ＦＦ\"")));
        check(Json.string(Json.parse(bytes("\"\\u0061\\u00fF\""))).equals("aÿ"));
        check(Json.uint(Json.parse(bytes("18446744073709551615"))).equals("18446744073709551615"));reject(()->Json.uint(Json.parse(bytes("18446744073709551616"))));
        reject(()->UiPacket.decode(packet(text,"[]","1")));reject(()->UiPacket.decode(packet(text,identities,"-1")));reject(()->UiPacket.decode(packet(node("root","unknown","{}","[]","[]"),identities,"1")));reject(()->UiPacket.decode(packet(node("root","text","{\"text\":\"ok\",\"surprise\":true}","[]","[]"),identities,"1")));reject(()->UiPacket.decode(packet(node("root","text","{\"text\":\"ok\",\"disabled\":\"no\"}","[]","[]"),identities,"1")));
        reject(()->UiPacket.decode(packet(node("root","text","{\"text\":\"x\"}","["+text+"]","[]"),identities,"1")));reject(()->UiPacket.decode(packet(node("root","text","{\"text\":\""+"é".repeat(8193)+"\"}","[]","[]"),identities,"1")));
        String toggle=node("root","toggle","{\"label\":\"Check\",\"value\":false}","[]","[{\"id\":\"toggle\",\"event\":\"valueChange\"}]");UiPacket p=UiPacket.decode(packet(toggle,identities,"2"));check(new String(p.event("root","1","valueChange",true),StandardCharsets.UTF_8).contains("\"value\":true"));reject(()->p.event("root","1","valueChange","wrong"));reject(()->p.event("root","2","valueChange",true));reject(()->p.event("root","1","activate",null));reject(()->p.requireSuccessor(first));
        UiPacket reordered=UiPacket.decode(packet(text,identities,"3"));reordered.requireSuccessor(first);check(true);reject(()->first.requireSuccessor(reordered));
        String disabled=toggle.replace("\"value\":false","\"value\":false,\"disabled\":true");UiPacket blocked=UiPacket.decode(packet(disabled,identities,"4"));reject(()->blocked.event("root","1","valueChange",true));
        reject(()->p.event("root","1","valueChange",null));reject(()->Json.encode(Json.map("bad","\ud800")));
        reject(()->UiPacket.decode(bytes(new String(packet(text,identities,"1"),StandardCharsets.UTF_8).replaceFirst("schemaVersion\":1","schemaVersion\":2"))));
        String nested=text;String ids="{\"id\":\"root\",\"generation\":1}";for(int i=1;i<=64;i++){nested=node("level"+i,"vStack","{}","["+nested+"]","[]");ids+=",{\"id\":\"level"+i+"\",\"generation\":"+(i+1)+"}";}final String deep=nested,deepIDs="["+ids+"]";reject(()->UiPacket.decode(packet(deep,deepIDs,"1")));
        System.out.println("Android wire contract checks passed: "+checks);
    }
}
