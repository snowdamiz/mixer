package dev.mixer.android;

import dev.mixer.android.AppearanceDescriptorV2.*;
import dev.mixer.android.AppearanceDescriptorV2.Error;
import dev.mixer.android.AppearanceResolverV2.*;
import dev.mixer.android.AppearanceResolverV2.Direction;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Reviewer-owned executable oracle. Every candidate crosses actual raw decoders.
 * No product Nodes, installed bytes, support proof or native authority are fabricated. */
public final class ReviewProbe {
    private static int assertions, accepted, rejected;
    private static byte[] descriptor;
    private static final Color CLEAR = new Color(0,0,0,0);
    private static final String MAX = "18446744073709551615";
    private ReviewProbe() {}
    private static void ok(boolean value, String message) {
        assertions++; if (!value) throw new AssertionError(message);
    }
    private static void eq(Object actual, Object expected, String message) {
        ok(java.util.Objects.equals(actual, expected), message + ": actual=" + actual + " expected=" + expected);
    }
    private static Map<String,Object> map(Object... pairs) {
        Map<String,Object> out = new LinkedHashMap<>();
        for (int i=0; i<pairs.length; i+=2) out.put((String)pairs[i],pairs[i+1]);
        return out;
    }
    private static Json.Num num(String value) { return new Json.Num(value); }
    private static String json(Object value) {
        if (value == null) return "null";
        if (value instanceof Json.Num v) return v.raw;
        if (value instanceof Boolean || value instanceof Number) return value.toString();
        if (value instanceof String v) {
            StringBuilder s=new StringBuilder("\"");
            for (int i=0;i<v.length();i++) {
                char c=v.charAt(i);
                if (c=='"' || c=='\\') s.append('\\').append(c);
                else if(c<32) s.append(String.format(java.util.Locale.ROOT,"\\u%04x",(int)c));
                else s.append(c);
            }
            return s.append('"').toString();
        }
        if (value instanceof List<?> list) {
            List<String> out=new ArrayList<>(); for(Object v:list) out.add(json(v));
            return "["+String.join(",",out)+"]";
        }
        if (value instanceof Map<?,?> m) {
            Map<String,Object> sorted=new TreeMap<>();
            for(var e:m.entrySet()) sorted.put((String)e.getKey(),e.getValue());
            List<String> out=new ArrayList<>(); for(var e:sorted.entrySet())out.add(json(e.getKey())+":"+json(e.getValue()));
            return "{"+String.join(",",out)+"}";
        }
        throw new AssertionError("unknown test JSON type");
    }
    private static byte[] bytes(Object value) { return (json(value)+"\n").getBytes(StandardCharsets.UTF_8); }
    private static Map<String,Object> node(String id,String kind,Map<String,Object> props,Object... children) {
        List<Object> actions=new ArrayList<>();
        if(kind.equals("button"))actions.add(map("id",id+"Action","event","activate"));
        if(kind.equals("toggle"))actions.add(map("id",id+"Change","event","valueChange"));
        if(kind.equals("textField"))actions.add(map("id",id+"Edit","event","textChange"));
        return map("id",id,"kind",kind,"properties",props,"children",new ArrayList<>(Arrays.asList(children)),"actions",actions);
    }
    private static Map<String,Object> text(String id,String role) {
        return node(id,"text",map("text","Exact "+id+" é العربية 🙂","style",role,"selectable",true,"maxLines",100));
    }
    private static Map<String,Object> packet(Map<String,Object> root) {
        List<Object> ids=new ArrayList<>(); List<Map<String,Object>> pending=new ArrayList<>();pending.add(root);
        int generation=1;
        while(!pending.isEmpty()) {
            Map<String,Object> n=pending.remove(pending.size()-1);ids.add(map("id",n.get("id"),"generation",generation++));
            List<Object> children=Json.array(n.get("children"));
            for(int i=children.size()-1;i>=0;i--)pending.add(Json.object(children.get(i)));
        }
        return map("schemaVersion",1,"document",map("schemaVersion",1,"revision",num(MAX),"root",root),"identities",ids);
    }
    private static Environment env() {
        return new Environment(Scheme.light,Direction.leftToRight,Profile.l,128,new Viewport(2147483647L,2147483647L),
            new SafeArea(2147483647L,2147483647L,0,0),"opaque_🙂",new Accessibility(false,false,true),MAX);
    }
    private static Environment changed(Environment e,String part,Object v) {
        return new Environment(part.equals("scheme")?(Scheme)v:e.scheme(),part.equals("direction")?(Direction)v:e.direction(),
            part.equals("profile")?(Profile)v:e.profile(),part.equals("density")?(Integer)v:e.density1024(),
            part.equals("viewport")?(Viewport)v:e.viewport(),part.equals("safe")?(SafeArea)v:e.safeArea64(),
            part.equals("locale")?(String)v:e.localeIdentifier(),part.equals("accessibility")?(Accessibility)v:e.accessibility(),
            part.equals("generation")?(String)v:e.generation());
    }
    private static Plan prepare(byte[] p,byte[] d,Environment e,Platform platform) {
        Plan out=AppearanceResolverV2.prepare(p,d,e,platform);accepted++;return out;
    }
    private static void reject(byte[] p,byte[] d,Environment e,Platform platform,Error code,String why) {
        try { AppearanceResolverV2.prepare(p,d,e,platform);throw new AssertionError("accepted "+why); }
        catch(Failure failure) { rejected++;ok(code==null||failure.code==code,why+" classification "+failure.code); }
    }
    private static Map<String,Object> at(Map<String,Object> root,String path) {
        Map<String,Object> out=root;
        if(!path.isEmpty())for(String key:path.split("\\."))out=Json.object(out.get(key));
        return out;
    }
    private static Color color(Map<String,Object> p,String path) {
        int dot=path.lastIndexOf('.');String s=(String)at(p,path.substring(0,dot)).get(path.substring(dot+1));
        return new Color(Integer.parseInt(s.substring(1,3),16),Integer.parseInt(s.substring(3,5),16),
            Integer.parseInt(s.substring(5,7),16),Integer.parseInt(s.substring(7,9),16));
    }
    private static void recolor(Map<String,Object> m,int[] seed) {
        for(var e:m.entrySet()) {
            if(e.getValue() instanceof Map<?,?>)recolor(Json.object(e.getValue()),seed);
            else if(e.getValue() instanceof String s&&s.startsWith("#"))
                e.setValue(String.format(java.util.Locale.ROOT,"#%08X",0x10203001L+0x010203L*seed[0]++));
        }
    }
    private static Map<String,Object> theme(int seed) {
        Map<String,Object> t=at(Json.object(Json.parse(descriptor)),"theme");
        for(String scheme:List.of("light","dark")) {
            Map<String,Object> p=at(t,scheme);recolor(p,new int[]{seed});seed+=150;
            for(String role:List.of("normal","destructive","cancel"))at(p,"button."+role+".disabled").put("background","#00000000");
            at(p,"field.disabled").put("caret","#00000000");at(p,"field.disabled").put("selection","#00000000");
            for(String value:List.of("on","off"))at(p,"toggle."+value+".disabled").put("overlay","#00000000");
        }
        Map<String,Object> s=at(t,"stacks");s.put("defaultGap64",103);s.put("bodyCaptionGap64",17);
        s.put("vStackAlignment","trailing");s.put("hStackAlignment","firstTextBaseline");s.put("zStackAlignment","topTrailing");
        Map<String,Object> g=at(t,"groupedList");g.put("topPadding64",13);g.put("bottomPadding64",19);
        g.put("headerToGroup64",23);g.put("groupToNextHeader64",29);g.put("groupWithoutHeaderGap64",31);
        return t;
    }
    private static Map<String,Object> fullTree() {
        List<Object> controls=new ArrayList<>(),disabled=new ArrayList<>();
        for(String role:List.of("normal","destructive","cancel")) {
            controls.add(node(role,"button",map("label",role,"role",role)));
            disabled.add(node("d-"+role,"button",map("label",role,"role",role,"disabled",false)));
        }
        for(boolean value:new boolean[]{false,true}) {
            controls.add(node("toggle-"+value,"toggle",map("label","Toggle","value",value)));
            disabled.add(node("d-toggle-"+value,"toggle",map("label","Toggle","value",value)));
        }
        controls.add(node("field","textField",map("label","Placeholder","value","Value🙂")));
        disabled.add(node("d-field","textField",map("label","Placeholder","value","Disabled🙂")));
        disabled.add(text("d-text","caption"));
        controls.add(node("disabled","vStack",map("disabled",true),disabled.toArray()));
        controls.add(node("outside","section",map("title","Outside"),text("out-a","body"),text("out-b","caption")));
        controls.add(node("L","list",map(),
            node("hidden-a","section",map()),node("head-only","section",map("title","Header only")),
            node("hidden-b","section",map("title","")),text("direct-a","body"),text("direct-b","caption"),
            node("group","section",map("title","Group"),
                node("row","vStack",map(),node("deep","section",map("title","Semantic"),text("deep-a","title"),text("deep-b","body"))),
                text("group-row","body")),node("hidden-c","section",map()),text("tail","body")));
        controls.add(node("emptyL","list",map(),node("emptyGroup","section",map())));
        controls.add(node("zero","vStack",map("spacing",0),text("zero-a","body"),text("zero-b","caption")));
        controls.add(node("adjacent","vStack",map(),text("adj-a","body"),text("adj-b","caption"),
            node("wrapped","vStack",map(),text("wrapped-caption","caption")),text("adj-c","headline"),text("adj-d","caption")));
        controls.add(node("baseline","hStack",map(),text("base-a","body"),text("base-b","caption")));
        controls.add(node("overlay","zStack",map(),text("overlay-a","body"),text("overlay-b","title")));
        return node("nav","navigation",map("title","Navigation🙂"),node("root","vStack",map(),controls.toArray()));
    }
    private static void outline(Outline a,Map<String,Object> p,String path) {
        eq(a.color(),color(p,path+".color"),path+" color");
        eq(a.width64(),(int)((Json.Num)at(p,path).get("width64")).number(),path+" width");
        eq(a.radius64(),(int)((Json.Num)at(p,path).get("radius64")).number(),path+" radius");
    }
    private static void paints(Plan plan,Map<String,Object> p) {
        for(boolean disabled:new boolean[]{false,true})for(boolean pressed:new boolean[]{false,true})for(boolean focused:new boolean[]{false,true}) {
            String prefix=disabled?"d-":"";
            for(String role:List.of("normal","destructive","cancel")) {
                Style s=plan.style(prefix+role,pressed,focused);ButtonPaints paints=(ButtonPaints)s.paints();
                eq(s.disabled(),disabled,"button disabled");eq(s.pressed(),!disabled&&pressed,"button press");eq(s.focused(),!disabled&&focused,"button focus");
                String path="button."+role+"."+(disabled?"disabled":pressed?"pressed":"enabled");
                eq(paints.paint().label(),color(p,path+".label"),path+" label");eq(paints.paint().background(),color(p,path+".background"),path+" background alpha once");
                if(!disabled&&focused)outline(paints.focus(),p,"button."+role+".focus");else eq(paints.focus(),null,"button no focus");
            }
            for(boolean checked:new boolean[]{false,true}) {
                Style s=plan.style(prefix+"toggle-"+checked,pressed,focused);TogglePaints paints=(TogglePaints)s.paints();
                String path="toggle."+(checked?"on":"off")+"."+(disabled?"disabled":pressed?"pressed":"enabled");
                eq(s.disabled(),disabled,"toggle disabled");eq(s.pressed(),!disabled&&pressed,"toggle press");eq(s.focused(),!disabled&&focused,"toggle focus");
                eq(paints.paint().label(),color(p,path+".label"),path+" label");eq(paints.paint().track(),color(p,path+".track"),path+" track");
                eq(paints.paint().thumb(),color(p,path+".thumb"),path+" thumb");eq(paints.paint().overlay(),color(p,path+".overlay"),path+" overlay");
                if(!disabled&&focused)outline(paints.focus(),p,"toggle."+(checked?"on":"off")+".focus");else eq(paints.focus(),null,"toggle no focus");
            }
            Style s=plan.style(prefix+"field",pressed,focused);FieldPaint f=((FieldPaints)s.paints()).paint();
            String path="field."+(disabled?"disabled":focused?"focused":"enabled");
            eq(s.disabled(),disabled,"field disabled");eq(s.pressed(),false,"field ignores press");eq(s.focused(),!disabled&&focused,"field focus");
            eq(f.text(),color(p,path+".text"),path+" text");eq(f.placeholder(),color(p,path+".placeholder"),path+" placeholder");
            eq(f.background(),color(p,path+".background"),path+" background");eq(f.caret(),color(p,path+".caret"),path+" caret");
            eq(f.selection(),color(p,path+".selection"),path+" selection");outline(f.outline(),p,path+".outline");
        }
        for(String id:List.of("adj-a","adj-b","adj-c","overlay-b","d-text")) {
            Node n=plan.node(id);TextRecipe r=(TextRecipe)n.recipe();Style s=plan.style(id,true,true);
            eq(((TextPaints)s.paints()).foreground(),color(p,"text."+r.text().role().name()),"role paint "+id);
            eq(((TextPaints)s.paints()).background(),CLEAR,"text explicit clear");eq(s.pressed(),false,"text ignores press");eq(s.focused(),false,"text ignores focus");
        }
        eq(plan.canvas,color(p,"root.canvas"),"canvas");
    }
    private static void grouping(Plan plan) {
        eq(plan.revision,MAX,"exact revision");eq(plan.nodes.get(0).identity().id(),"nav","preorder first");
        eq(plan.node("L").childIDs(),List.of("hidden-a","head-only","hidden-b","direct-a","direct-b","group","hidden-c","tail"),"original child order");
        ListRecipe r=(ListRecipe)plan.node("L").recipe();eq(r.groups().size(),7,"group count");
        int[] gaps={0,13,0,31,29,0,31};boolean[] visible={false,true,false,true,true,false,true};
        for(int i=0;i<gaps.length;i++) {Group g=r.groups().get(i);eq(g.leadingGap64(),gaps[i],"group gap "+i);eq(g.visible(),visible[i],"visibility "+i);}
        eq(r.groups().get(1).drawsOutline(),false,"header only no outline");eq(r.groups().get(1).headerToRowsGap64(),0,"header only no row gap");
        eq(r.groups().get(4).headerToRowsGap64(),23,"header with rows gap");eq(r.trailingPadding64(),19,"visible trailing padding");
        eq(r.groups().get(3).source(),new DirectRunSource(plan.node("direct-a").identity()),"run source existing identity");
        eq(r.groups().get(4).source(),new SectionSource(plan.node("group").identity()),"section source existing identity");
        eq(plan.node("direct-a").rowPlacement(),new RowPlacement(plan.node("L").identity(),3,0,true),"run interior separator");
        eq(plan.node("direct-b").rowPlacement(),new RowPlacement(plan.node("L").identity(),3,1,false),"run final separator absent");
        eq(plan.node("row").rowPlacement(),new RowPlacement(plan.node("L").identity(),4,0,true),"group owner row");
        eq(plan.node("deep").rowPlacement(),null,"semantic section not extra row");
        SectionRecipe s=(SectionRecipe)plan.node("deep").recipe();eq(s.context(),new WithinListRow(plan.node("L").identity()),"deep ancestor context");
        eq(s.contentGaps64(),List.of(103),"semantic section gaps");eq(s.headerToContentGap64(),23,"semantic header gap");
        s=(SectionRecipe)plan.node("group").recipe();eq(s.context(),new ListGroup(plan.node("L").identity(),4),"immediate section context");
        eq(s.contentGaps64(),List.of(),"structural section no wrappers");eq(s.headerToContentGap64(),0,"structural header owned by list");
        s=(SectionRecipe)plan.node("outside").recipe();eq(s.context(),new OutsideList(),"outside context");eq(s.contentGaps64(),List.of(103),"outside gap");
        ListRecipe empty=(ListRecipe)plan.node("emptyL").recipe();eq(empty.trailingPadding64(),0,"invisible list no bottom");eq(empty.groups().get(0).leadingGap64(),0,"invisible no top");
        eq(((VStackRecipe)plan.node("zero").recipe()).gaps64(),List.of(0),"explicit zero beats pair");
        eq(((VStackRecipe)plan.node("adjacent").recipe()).gaps64(),List.of(17,103,103,103),"only direct body to caption");
        eq(((HStackRecipe)plan.node("baseline").recipe()).alignment(),VerticalAlignment.firstTextBaseline,"theme baseline retained data");
        eq(((ZStackRecipe)plan.node("overlay").recipe()).alignment(),OverlayAlignment.topTrailing,"custom overlay default");
        eq(plan.node("overlay").childIDs(),List.of("overlay-a","overlay-b"),"RTL never reverses paint order");
        eq(((VStackRecipe)plan.node("root").recipe()).alignment(),HorizontalAlignment.trailing,"custom vstack default");
        eq(((FieldRecipe)plan.node("field").recipe()).text().value(),"Value🙂","exact field value");
        NavigationRecipe nav=(NavigationRecipe)plan.node("nav").recipe();eq(nav.expandedTitle().role(),Role.navigationExpanded,"expanded role");
        eq(nav.compactTitle().role(),Role.headline,"compact role");eq(nav.compactTitle().maximumLines(),1,"compact one line");
        for(Node n:plan.nodes) {eq(plan.node(n.identity().id()),n,"index identity");if(n.identity().id().startsWith("d-"))ok(n.disabled(),"inherited disabled cannot be cleared");}
    }
    private static void matrix() {
        Map<String,Object> ios=theme(2),android=theme(1500);
        Map<String,Object> config=map("format",AppearanceDescriptorV2.FORMAT,"id","review.platform","mode","platformSpecific", "resources",List.of(),"iOS",ios,"android",android,"reason","Explicit independent palette oracle");
        byte[] d=bytes(config),p=bytes(packet(fullTree()));
        for(Platform platform:Platform.values())for(Scheme scheme:Scheme.values()) {
            Environment e=changed(changed(env(),"scheme",scheme),"direction",Direction.rightToLeft);
            Plan plan=prepare(p,d,e,platform);grouping(plan);
            // Raw expected color fields originate from the reviewer authored descriptor,
            // never the production descriptor decoder or Swift's output projection.
            Map<String,Object> selected=at(platform==Platform.iOS?ios:android,scheme.name());
            selected.put("root",map("canvas",selected.get("canvas")));paints(plan,selected);selected.remove("root");
            eq(plan.platformSpecificReason,"Explicit independent palette oracle","reason preserved");
            eq(plan.environment,e,"complete immutable environment retained");
        }
        at(ios,"typography.profiles.l.body").put("size64",1089);
        reject(p,bytes(config),env(),Platform.android,Error.unsupportedProfile,"unselected iOS full profile validation");
        at(ios,"typography.profiles.l.body").put("size64",1088);
        at(ios,"typography").put("font",map("kind","bundled","fallback","none","faces",List.of(map("resourceID","missing","postScriptName","Missing","weight",400,"style","normal"))));
        reject(p,bytes(config),env(),Platform.android,Error.fontCatalog,"unselected iOS missing font validation");
        at(ios,"typography").put("font",map("kind","systemSans"));
        at(ios,"dark.field.disabled").put("caret","#01020300");
        reject(p,bytes(config),env(),Platform.android,Error.shape,"unselected hidden noncanonical clear validation");
    }
    private static void immutableAndIdentity() {
        Map<String,Object> root=node("identity","vStack",map(),text("above53","body"),text("max64","caption"),text("exact53","headline"));
        Map<String,Object> candidate=packet(root);List<Object> ids=Json.array(candidate.get("identities"));
        String[] numbers={"9007199254740991","9007199254740993",MAX,"9007199254740992"};
        for(int i=0;i<ids.size();i++)Json.object(ids.get(i)).put("generation",num(numbers[i]));
        byte[] p=bytes(candidate),d=descriptor.clone();Plan plan=prepare(p,d,env(),Platform.android);
        for(int i=0;i<ids.size();i++)eq(plan.nodes.get(i).identity().generation(),numbers[i],"exact UInt64 above double precision");
        eq(plan.revision,MAX,"max revision unsigned");eq(plan.environment.generation(),MAX,"max env unsigned");
        Arrays.fill(p,(byte)'!');Arrays.fill(d,(byte)'!');
        eq(((TextRecipe)plan.node("max64").recipe()).text().value(),"Exact max64 é العربية 🙂","raw arrays owned");
        List<List<?>> lists=List.of(plan.nodes,plan.resources,plan.node("identity").childIDs(),((VStackRecipe)plan.node("identity").recipe()).gaps64());
        for(List<?> list:lists) {try {list.clear();throw new AssertionError("mutable plan list");}catch(UnsupportedOperationException expected){assertions++;}}
        eq(plan.node(null),null,"null lookup");eq(plan.style("missing",true,true),null,"missing style");
        List<Node> before=List.copyOf(plan.nodes);for(int i=0;i<25;i++)for(Node n:plan.nodes)plan.style(n.identity().id(),i%2==0,i%3==0);
        eq(plan.nodes,before,"style does not mutate plan");
    }
    private static void environmentBoundary() {
        byte[] p=bytes(packet(text("env","body")));Environment e=env();
        for(String key:List.of("scheme","direction","profile","viewport","safe","locale","accessibility","generation"))reject(p,descriptor,changed(e,key,null),Platform.android,Error.shape,"null "+key);
        reject(p,descriptor,null,Platform.android,Error.shape,"null environment");reject(p,descriptor,e,null,Error.shape,"null platform");
        for(String v:List.of("00","01","-0","+0","18446744073709551616","1e0","1.0"," 0","0 ","０","١","","999999999999999999999999"))reject(p,descriptor,changed(e,"generation",v),Platform.android,Error.shape,"generation "+v);
        for(String v:List.of("0","1","9007199254740993",MAX))eq(prepare(p,descriptor,changed(e,"generation",v),Platform.android).environment.generation(),v,"accepted exact env generation");
        for(String v:List.of("\uD800","\uDC00","\uDC00\uD800","\uD800\uD800\uDC00","x\uD800y","\u0000","\u007F","\u0085","\u200E","\uDB40\uDC01","😀".repeat(32)+"x","é".repeat(64)+"x"))reject(p,descriptor,changed(e,"locale",v),Platform.android,Error.shape,"malformed/forbidden/overlong locale");
        for(String v:List.of("😀".repeat(32),"é".repeat(64),"x".repeat(128),"opaque\uE000\u2028"))eq(prepare(p,descriptor,changed(e,"locale",v),Platform.android).environment.localeIdentifier(),v,"opaque locale accepted exactly");
        for(int v:new int[]{Integer.MIN_VALUE,0,127,16385,Integer.MAX_VALUE})reject(p,descriptor,changed(e,"density",v),Platform.android,Error.geometry,"density bound");
        for(Viewport v:List.of(new Viewport(0,1),new Viewport(1,0),new Viewport(-1,1),new Viewport(Long.MAX_VALUE,1),new Viewport(1,2147483648L)))reject(p,descriptor,changed(e,"viewport",v),Platform.android,Error.geometry,"viewport bound");
        for(SafeArea v:List.of(new SafeArea(-1,0,0,0),new SafeArea(Long.MAX_VALUE,0,0,0),new SafeArea(2147483647L,0,1,0),new SafeArea(0,2147483647L,0,1)))reject(p,descriptor,changed(e,"safe",v),Platform.android,Error.geometry,"safe bound/sum");
        for(Accessibility v:List.of(new Accessibility(true,false,false),new Accessibility(false,true,true),new Accessibility(true,true,false)))reject(p,descriptor,changed(e,"accessibility",v),Platform.android,Error.unsupportedNativeOperation,"visual preference fail closed");
    }
    private static void packetBoundary() {
        byte[] good=bytes(packet(text("leaf","body")));
        List<String> invalid=List.of(
            "\"schemaVersion\":1","\"generation\":1","\"revision\":"+MAX);
        for(int i=0;i<invalid.size();i++)for(String raw:List.of("-0","01","1e0","1.0","18446744073709551616","true","null","\"1\"")) {
            String key=invalid.get(i).split(":",2)[0];String s=new String(good,StandardCharsets.UTF_8).replace(invalid.get(i),key+":"+raw);
            reject(s.getBytes(StandardCharsets.UTF_8),descriptor,env(),Platform.android,Error.shape,"raw numeric token "+key+raw);
        }
        for(String kind:List.of("image","webView","Text","sectionHeader"))reject(bytes(packet(node("unknown",kind,map()))),descriptor,env(),Platform.android,Error.shape,"unknown kind");
        for(String property:List.of("theme","nativeName","fontScale","color","opacity","lineHeight","callback"))reject(bytes(packet(node("unknown","vStack",map(property,1)))),descriptor,env(),Platform.android,Error.shape,"unknown property "+property);
        reject(bytes(packet(node("leaf","text",map("text","x"),text("child","body")))),descriptor,env(),Platform.android,Error.shape,"leaf child");
        for(String baseline:List.of("firstTextBaseline","lastTextBaseline"))reject(bytes(packet(node("h","hStack",map("alignment",baseline)))),descriptor,env(),Platform.android,Error.shape,"explicit baseline packet restriction");
        reject(bytes(packet(node("outer","list",map(),node("wrap","section",map(),node("inner","list",map()))))),descriptor,env(),Platform.android,Error.shape,"nested list through section");
        reject(bytes(packet(node("wrap","vStack",map(),node("nav","navigation",map(),text("child","body"))))),descriptor,env(),Platform.android,Error.unsupportedNativeOperation,"nonroot navigation");
        Map<String,Object> bad=node("button","button",map("label","x"));bad.put("actions",List.of());reject(bytes(packet(bad)),descriptor,env(),Platform.android,Error.shape,"required control action");
        for(Object v:List.of(0,101,1.5,"1",true))reject(bytes(packet(node("t","text",map("text","x","maxLines",v)))),descriptor,env(),Platform.android,Error.shape,"maxLines bound/type");
        for(Object v:List.of(-1,257,"0",true))reject(bytes(packet(node("s","vStack",map("spacing",v)))),descriptor,env(),Platform.android,Error.shape,"spacing bound/type");
        for(double v:new double[]{0,0.0078125,0.0234375,255.999999,256}) {
            Plan p=prepare(bytes(packet(node("s","vStack",map("spacing",v),text("a","body"),text("b","caption")))),descriptor,env(),Platform.android);
            eq(((VStackRecipe)p.node("s").recipe()).gaps64(),List.of((int)Math.floor(v*64+0.5)),"explicit fractional spacing ties up");
        }
        for(int size:new int[]{16384,16385}) {
            byte[] b=bytes(packet(node("t","text",map("text","x".repeat(size)))));
            if(size==16384)eq(((TextRecipe)prepare(b,descriptor,env(),Platform.android).node("t").recipe()).text().value().length(),size,"string exact byte bound");
            else reject(b,descriptor,env(),Platform.android,Error.shape,"string over bound");
        }
        for(int n:new int[]{1000,1001}) {
            List<Object> children=new ArrayList<>();for(int i=0;i<n;i++)children.add(text("child"+i,"body"));
            byte[] b=bytes(packet(node("r","vStack",map(),children.toArray())));
            if(n==1000)eq(prepare(b,descriptor,env(),Platform.android).nodes.size(),1001,"1000 child frontier accepted");else reject(b,descriptor,env(),Platform.android,Error.shape,"1001 children rejected");
        }
        for(int n:new int[]{1048576,1048577}) {
            byte[] b=Arrays.copyOf(good,n);Arrays.fill(b,good.length,n,(byte)' ');
            if(n==1048576)prepare(b,descriptor,env(),Platform.android);else reject(b,descriptor,env(),Platform.android,Error.shape,"packet over byte bound");
        }
        reject("{\"schemaVersion\":1,\"schemaVersion\":1}".getBytes(StandardCharsets.UTF_8),descriptor,env(),Platform.android,Error.shape,"duplicate packet keys");
        reject(new byte[]{(byte)0xED,(byte)0xA0,(byte)0x80},descriptor,env(),Platform.android,Error.shape,"UTF8 surrogate packet");
        reject(new String(good,StandardCharsets.UTF_8).replace("Exact leaf", "\\uD800").getBytes(StandardCharsets.UTF_8),descriptor,env(),Platform.android,Error.shape,"escaped lone surrogate packet");
        reject(good,Arrays.copyOf(descriptor,descriptor.length-1),env(),Platform.android,Error.syntax,"descriptor missing required LF");
        reject(good,(new String(descriptor,StandardCharsets.US_ASCII)+"\n").getBytes(StandardCharsets.US_ASCII),env(),Platform.android,Error.noncanonical,"descriptor extra LF");
        Map<String,Object> doc=Json.object(Json.parse(descriptor));doc.put("nativeSupport",true);reject(good,bytes(doc),env(),Platform.android,null,"unknown descriptor support field");
        doc=Json.object(Json.parse(descriptor));doc.put("format","mixer.native-appearance.1");reject(good,bytes(doc),env(),Platform.android,Error.shape,"V1 descriptor cannot enter V2");
    }
    private static void largeGroupedFrontier() {
        List<Object> groups=new ArrayList<>();int count=0;
        for(int g=0;g<5;g++) {
            int length=g==4?90:1000;List<Object> rows=new ArrayList<>();
            for(int i=0;i<length;i++)rows.add(node("n"+(count++),"text",map("text","x")));
            groups.add(node("g"+g,"section",map("title","G"+g),rows.toArray()));
        }
        Plan p=prepare(bytes(packet(node("L","list",map(),groups.toArray()))),descriptor,env(),Platform.android);
        eq(p.nodes.size(),4096,"4096 grouped records including section identities");
        ListRecipe list=(ListRecipe)p.node("L").recipe();eq(list.groups().size(),5,"five max grouped frontiers");
        for(int g=0;g<5;g++) {
            Group group=list.groups().get(g);eq(group.rowIdentities().size(),g==4?90:1000,"row count");
            for(int r=0;r<group.rowIdentities().size();r++)eq(p.node(group.rowIdentities().get(r).id()).rowPlacement(),new RowPlacement(p.node("L").identity(),g,r,r+1<group.rowIdentities().size()),"every max row owner and separator");
        }
        List<Object> empties=new ArrayList<>();for(int i=0;i<999;i++)empties.add(node("hidden"+i,"section",map()));empties.add(text("last","body"));
        p=prepare(bytes(packet(node("L","list",map(),empties.toArray()))),descriptor,env(),Platform.android);list=(ListRecipe)p.node("L").recipe();
        eq(list.groups().size(),1000,"maximum immediate groups with invisible prefix");eq(list.groups().get(999).leadingGap64(),640,"invisible prefix cannot consume top padding");
    }
    public static void main(String[] args) throws Exception {
        descriptor=Files.readAllBytes(Path.of(args[0]));
        matrix();immutableAndIdentity();environmentBoundary();packetBoundary();largeGroupedFrontier();
        System.out.println("PASS reviewer oracle acceptedPreparations="+accepted+" explicitRejections="+rejected+" assertions="+assertions+"; host pure data only");
    }
}
