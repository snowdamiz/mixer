package dev.mixer.android;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.List;
import dev.mixer.android.AppearanceDescriptorV2.Profile;
import dev.mixer.android.AppearanceResolverV2.*;

public final class AndroidVerticalInputTests {
    private static int checks;
    private static void check(boolean ok) { checks++; if(!ok)throw new AssertionError("vertical check "+checks); }
    private static void reject(Runnable action) {
        try { action.run(); } catch(IllegalArgumentException expected) { checks++; return; }
        throw new AssertionError("expected refusal");
    }
    static byte[] packet(Object axis, String value, boolean disabled) {
        Map<String,Object> properties=Json.map("label","Task","value",value,"disabled",disabled);
        if(axis!=null)properties.put("axis",axis);
        String props=new String(Json.encode(properties),java.nio.charset.StandardCharsets.UTF_8);
        return ("{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":1,\"root\":{\"id\":\"task\",\"kind\":\"textField\",\"properties\":"+props+
            ",\"children\":[],\"actions\":[{\"id\":\"change\",\"event\":\"textChange\"}]}},\"identities\":[{\"id\":\"task\",\"generation\":1}]}").getBytes(java.nio.charset.StandardCharsets.UTF_8);
    }
    public static void main(String[] args) throws Exception {
        String value="\nCafé\r\n漢字 e\u0301 🏗️\nمسؤول";
        byte[] vertical=packet("vertical",value,false), descriptor=Files.readAllBytes(Path.of(args[0]));
        AndroidUIProfile profile=AndroidUIProfile.MEASURED_MULTILINE_V2;
        reject(()->UiPacket.decode(vertical));
        UiPacket decoded=UiPacket.decode(vertical,profile);
        check(decoded.root.text("value","").equals(value));
        check(Json.string(Json.object(Json.parse(decoded.event("task","1","textChange",value))).get("value")).equals(value));
        reject(()->decoded.event("task","2","textChange",value));
        reject(()->UiPacket.decode(packet("vertical",value,true),profile).event("task","1","textChange",value));
        for(Object bad:List.of("diagonal","Vertical","",true,new Json.Num("2")))reject(()->UiPacket.decode(packet(bad,value,false),profile));
        reject(()->UiPacket.decode(packet("vertical","é".repeat(8193),false),profile));
        Environment env=new Environment(Scheme.light,Direction.leftToRight,Profile.l,1024,new Viewport(24000,40000),new SafeArea(0,0,0,0),"en-US",new Accessibility(false,false,false),"1");
        reject(()->AppearanceResolverV2.prepare(vertical,descriptor,env,Platform.android));
        reject(()->AppearanceResolverV2.prepare(vertical,descriptor,env,Platform.iOS,profile));
        Plan plan=AppearanceResolverV2.prepare(vertical,descriptor,env,Platform.android,profile);
        FieldRecipe field=(FieldRecipe)plan.node("task").recipe();
        check(field.value().equals(value)&&field.text().value().equals(value)&&field.text().maximumLines()==null);
        byte[] horizontal=packet(null,"Zoë",false);
        check(AppearanceResolverV2.prepare(horizontal,descriptor,env,Platform.android).nodes.equals(
            AppearanceResolverV2.prepare(horizontal,descriptor,env,Platform.android,profile).nodes));
        byte[] styled=new String(vertical,java.nio.charset.StandardCharsets.UTF_8).replace("\"axis\":\"vertical\"", "\"axis\":\"vertical\",\"maxLines\":3").getBytes(java.nio.charset.StandardCharsets.UTF_8);
        reject(()->UiPacket.decode(styled,profile));
        System.out.println("PASS Android vertical data checks="+checks);
    }
}
