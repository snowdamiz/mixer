package dev.mixer.android;
import java.nio.charset.StandardCharsets;
import java.math.BigInteger;
import java.util.*;
/** A completely validated immutable candidate is built before touching native views. */
final class UiPacket {
    static final class Node {
        final String id,kind,generation;final Map<String,Object> properties;final List<Node> children;final Map<String,String> actions;final boolean disabled;
        Node(String id,String kind,String generation,Map<String,Object>p,List<Node>c,Map<String,String>a,boolean d){this.id=id;this.kind=kind;this.generation=generation;properties=Collections.unmodifiableMap(p);children=Collections.unmodifiableList(c);actions=Collections.unmodifiableMap(a);disabled=d;}
        String text(String key,String fallback){Object v=properties.get(key);return v==null?fallback:Json.string(v);}
        boolean flag(String key,boolean fallback){Object v=properties.get(key);return v==null?fallback:Json.bool(v);}
        double number(String key,double fallback){Object v=properties.get(key);return v==null?fallback:((Json.Num)v).number();}
    }
    final String revision;final Node root;final Map<String,Node>nodes;
    private UiPacket(String revision,Node root,Map<String,Node>nodes){this.revision=revision;this.root=root;this.nodes=Collections.unmodifiableMap(nodes);}
    static UiPacket decode(byte[] bytes){
        Map<String,Object>packet=Json.object(Json.parse(bytes));Json.keys(packet,"schemaVersion","document","identities");schema(packet.get("schemaVersion"));
        Map<String,Object>doc=Json.object(packet.get("document"));Json.keys(doc,"schemaVersion","revision","root");schema(doc.get("schemaVersion"));String revision=Json.uint(doc.get("revision"));
        List<Object>identities=Json.array(packet.get("identities"));if(identities.size()>4096)throw Json.bad("identity count");Map<String,String> generations=new HashMap<>();Set<String> unique=new HashSet<>();
        for(Object raw:identities){Map<String,Object>identity=Json.object(raw);Json.keys(identity,"id","generation");String id=identifier(identity.get("id")),generation=Json.uint(identity.get("generation"));if(generation.equals("0")||generations.put(id,generation)!=null||!unique.add(generation))throw Json.bad("duplicate/zero identity");}
        Map<String,Node> nodes=new LinkedHashMap<>();Node root=node(doc.get("root"),generations,nodes,1,false,false);if(!nodes.keySet().equals(generations.keySet()))throw Json.bad("identity coverage");return new UiPacket(revision,root,nodes);
    }
    void requireSuccessor(UiPacket previous){if(previous==null)return;if(new BigInteger(revision).compareTo(new BigInteger(previous.revision))<=0)throw Json.bad("stale document revision");for(Node n:nodes.values()){Node old=previous.nodes.get(n.id);if(old!=null&&old.kind.equals(n.kind)&&!old.generation.equals(n.generation))throw Json.bad("surviving node generation changed");if(old!=null&&!old.kind.equals(n.kind)&&old.generation.equals(n.generation))throw Json.bad("replacement reused generation");}}
    byte[] event(String id,String generation,String event,Object value){Node n=nodes.get(id);if(n==null||!n.generation.equals(generation))throw Json.bad("stale identity");if(n.disabled)throw Json.bad("disabled event");if(!n.actions.containsKey(event))throw Json.bad("unbound event");if(event.equals("textChange")){stringValue(value);}else if(event.equals("valueChange")){Json.bool(value);}else if(value!=null)throw Json.bad("event value mismatch");return Json.encode(Json.map("revision",new Json.Num(revision),"identity",Json.map("id",id,"generation",new Json.Num(generation)),"event",event,"value",value));}
    private static void schema(Object value){if(!Json.uint(value).equals("1"))throw Json.bad("unsupported schema");}
    static String identifier(Object value){String s=Json.string(value);if(s.isEmpty()||s.getBytes(StandardCharsets.UTF_8).length>128)throw Json.bad("identifier bytes");for(int i=0;i<s.length();i++)if(s.charAt(i)<32||s.charAt(i)==127)throw Json.bad("identifier control");return s;}
    static String stringValue(Object value){String s=Json.string(value);if(s.getBytes(StandardCharsets.UTF_8).length>16384)throw Json.bad("string bytes");return s;}
    static Set<String> set(String... names){return new HashSet<>(Arrays.asList(names));}
    static void optionalEnum(Map<String,Object>p,String key,String...values){if(p.containsKey(key)&&!set(values).contains(Json.string(p.get(key))))throw Json.bad("property enum: "+key);}
    private static Node node(Object raw,Map<String,String>generations,Map<String,Node>nodes,int depth,boolean ancestorDisabled,boolean inList){
        if(depth>64||nodes.size()>=4096)throw Json.bad("node/depth bounds");Map<String,Object>m=Json.object(raw);Json.keys(m,"id","kind","properties","children","actions");String id=identifier(m.get("id")),kind=Json.string(m.get("kind"));if(nodes.containsKey(id)||!generations.containsKey(id))throw Json.bad("duplicate/unowned node");
        Map<String,Object>p=new LinkedHashMap<>(Json.object(m.get("properties")));if(p.size()>16)throw Json.bad("property bound");Set<String>allowed=set("disabled","accessibilityLabel","accessibilityHint","accessibilityValue","accessibilityIdentifier");for(Map.Entry<String,Object>e:p.entrySet()){Object v=e.getValue();if(!(v instanceof String||v instanceof Boolean||v instanceof Json.Num))throw Json.bad("scalar property");if(v instanceof String)stringValue(v);if(e.getKey().startsWith("accessibility"))stringValue(v);}if(p.containsKey("disabled"))Json.bool(p.get("disabled"));
        Set<String>events=new HashSet<>(),required=new HashSet<>();boolean leaf=false;
        switch(kind){
            case "text":allowed.addAll(set("text","style","selectable","maxLines"));stringValue(p.get("text"));optionalEnum(p,"style","body","headline","title","caption");if(p.containsKey("selectable"))Json.bool(p.get("selectable"));if(p.containsKey("maxLines")){double v=number(p.get("maxLines"));if(v!=Math.rint(v)||v<1||v>100)throw Json.bad("maxLines");}leaf=true;break;
            case "button":allowed.addAll(set("label","role"));stringValue(p.get("label"));optionalEnum(p,"role","normal","destructive","cancel");events.add("activate");required.add("activate");leaf=true;break;
            case "textField":allowed.addAll(set("label","value"));stringValue(p.get("label"));stringValue(p.get("value"));events.addAll(set("textChange","submit"));required.add("textChange");leaf=true;break;
            case "toggle":allowed.addAll(set("label","value"));stringValue(p.get("label"));Json.bool(p.get("value"));events.add("valueChange");required.add("valueChange");leaf=true;break;
            case "vStack":allowed.addAll(set("spacing","alignment"));optionalEnum(p,"alignment","leading","center","trailing");spacing(p);break;
            case "hStack":allowed.addAll(set("spacing","alignment"));optionalEnum(p,"alignment","top","center","bottom");spacing(p);break;
            case "zStack":allowed.add("alignment");optionalEnum(p,"alignment","center","leading","trailing","top","bottom","topLeading","topTrailing","bottomLeading","bottomTrailing");break;
            case "list":if(inList)throw Json.bad("nested scrolling list unsupported");break;
            case "section":case "navigation":allowed.add("title");if(p.containsKey("title"))stringValue(p.get("title"));break;
            default:throw Json.bad("unsupported node: "+kind);
        }
        if(!allowed.containsAll(p.keySet()))throw Json.bad("unsupported property");
        List<Object>actionValues=Json.array(m.get("actions"));if(actionValues.size()>4)throw Json.bad("action bound");Map<String,String>actions=new LinkedHashMap<>();for(Object a:actionValues){Map<String,Object>binding=Json.object(a);Json.keys(binding,"id","event");String actionID=identifier(binding.get("id")),event=Json.string(binding.get("event"));if(!events.contains(event)||actions.put(event,actionID)!=null)throw Json.bad("unsupported/duplicate event");}if(!actions.keySet().containsAll(required))throw Json.bad("required event missing");
        List<Object>childValues=Json.array(m.get("children"));if(childValues.size()>1000||(leaf&&!childValues.isEmpty())||(kind.equals("navigation")&&childValues.size()!=1))throw Json.bad("child bounds/structure");boolean disabled=ancestorDisabled||(p.containsKey("disabled")&&Json.bool(p.get("disabled")));List<Node>children=new ArrayList<>();Node n=new Node(id,kind,generations.get(id),p,children,actions,disabled);nodes.put(id,n);for(Object child:childValues)children.add(node(child,generations,nodes,depth+1,disabled,inList||kind.equals("list")));return n;
    }
    private static double number(Object v){if(!(v instanceof Json.Num))throw Json.bad("number expected");return((Json.Num)v).number();}
    private static void spacing(Map<String,Object>p){if(p.containsKey("spacing")){double v=number(p.get("spacing"));if(v<0||v>256)throw Json.bad("spacing");}}
}
