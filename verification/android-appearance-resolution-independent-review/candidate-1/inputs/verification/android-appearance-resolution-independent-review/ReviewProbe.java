package dev.mixer.android;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;
import java.util.HexFormat;
import java.util.IdentityHashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;

/** Review-owned full output transport and deep immutable graph/alias probes. */
public final class ReviewProbe {
    private ReviewProbe() {}
    private static long assertions, containers, finalFields, accepted, rejected, boundary, nodes, styles, packets;
    private static final Set<Object> visited = Collections.newSetFromMap(new IdentityHashMap<>());
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("oracle.tsv actual.jsonl");
        List<String> actual = new ArrayList<>();
        for (String line : Files.readAllLines(Path.of(args[0]), StandardCharsets.UTF_8)) {
            String[] f = line.split("\t", -1);
            check(f.length == 8, "TSV fields");
            AppearanceResolutionV1.Plan plan = null;
            AppearanceDescriptorV1 descriptor = null;
            UiPacket packet = null;
            byte[] descriptorBytes = Base64.getDecoder().decode(f[2]);
            byte[] packetBytes = Base64.getDecoder().decode(f[5]);
            try {
                descriptor = AppearanceDescriptorV1.decode(descriptorBytes);
                Map<String,Object> e = Json.object(Json.parse(Base64.getDecoder().decode(f[3])));
                AppearanceResolutionV1.Environment env = new AppearanceResolutionV1.Environment(
                    AppearanceResolutionV1.Scheme.valueOf(Json.string(e.get("scheme"))),
                    AppearanceResolutionV1.Direction.valueOf(Json.string(e.get("direction"))),
                    Integer.parseInt(Json.uint(e.get("textScale1024"))), Integer.parseInt(Json.uint(e.get("density1024"))));
                packet = UiPacket.decode(packetBytes);
                plan = AppearanceResolutionV1.prepare(packet, descriptor, env, AppearanceResolutionV1.Platform.valueOf(f[4]));
            } catch (IllegalArgumentException expected) {
                check(!f[1].equals("accepted") || f[7].equals("packet-baseline-rejected"), f[0]+" unexpected rejection: "+expected);
                if (f[7].isEmpty()) rejected++; else boundary++;
                actual.add("null"); continue;
            }
            check(f[1].equals("accepted") && f[7].isEmpty(), f[0]+" unexpected acceptance");
            accepted++;
            String output = normalized(plan);
            check(sha(output).equals(f[6]), f[0]+" complete resolved data digest mismatch");
            equal(packet.revision,plan.revision,"revision");
            equal(null,plan.node("absent"),"missing node");
            equal(null,plan.style("absent",true,true),"missing style");
            check(plan.nodes.size()==packet.nodes.size(),"one output for each input");
            List<String> expectedPreorder = new ArrayList<>(); preorder(packet.root, expectedPreorder);
            equal(expectedPreorder,plan.nodes.stream().map(n->n.identity().id()).toList(),"original preorder");
            UiPacket eventPacket=packet;
            for (AppearanceResolutionV1.Node node : plan.nodes) {
                UiPacket.Node source = packet.nodes.get(node.identity().id());
                check(plan.node(source.id)==node,"index returns original plan object");
                equal(source.generation,node.identity().generation(),"exact generation");
                equal(source.kind,node.kind(),"kind");equal(source.disabled,node.disabled(),"inherited disabled");
                equal(source.children.stream().map(n->n.id).toList(),node.childIDs(),"child order");
                for (String event : source.actions.keySet()) {
                    Object value=event.equals("textChange")?"Edited العربية 🧪":event.equals("valueChange")?Boolean.TRUE:null;
                    if (source.disabled) reject(()->eventPacket.event(source.id,source.generation,event,value));
                    else {
                        byte[] before=packet.event(source.id,source.generation,event,value);
                        plan.style(source.id,true,true);
                        check(Arrays.equals(before,packet.event(source.id,source.generation,event,value)),"unchanged event");
                    }
                }
                nodes++;
            }
            // Walk the complete graph including private index/palette and both unselected
            // descriptor branches, not just the publicly retained maps at depth one.
            visited.clear();immutable(plan);immutable(descriptor);immutable(packet);
            for (AppearanceResolutionV1.Node node : plan.nodes) for(int state=0;state<4;state++) {
                immutable(plan.style(node.identity().id(),(state&1)!=0,(state&2)!=0));styles++;
            }
            Arrays.fill(descriptorBytes,(byte)'!');Arrays.fill(packetBytes,(byte)'!');
            equal(output,normalized(plan),"decoded arrays have no retained mutable alias");
            AppearanceResolutionV1.Plan saved=plan;
            UiPacket savedPacket=packet;AppearanceDescriptorV1 savedDescriptor=descriptor;
            reject(()->AppearanceResolutionV1.prepare(null,savedDescriptor,saved.environment,saved.platform));
            reject(()->AppearanceResolutionV1.prepare(savedPacket,null,saved.environment,saved.platform));
            reject(()->AppearanceResolutionV1.prepare(savedPacket,savedDescriptor,null,saved.platform));
            reject(()->AppearanceResolutionV1.prepare(savedPacket,savedDescriptor,saved.environment,null));
            if (accepted==1) packetProbes(f[5],descriptor,plan.environment,plan.platform);
            actual.add(output);
        }
        for (var c : UiPacket.class.getDeclaredConstructors()) check(Modifier.isPrivate(c.getModifiers()),"packet constructor private");
        for (var c : AppearanceDescriptorV1.class.getDeclaredConstructors()) check(Modifier.isPrivate(c.getModifiers()),"descriptor constructor private");
        Files.write(Path.of(args[1]),actual,StandardCharsets.UTF_8);
        System.out.println("review cases="+actual.size()+" accepted="+accepted+" rejected="+rejected+" knownPacketBoundary="+boundary+" nodes="+nodes+" styles="+styles+" immutableContainers="+containers+" finalFields="+finalFields+" extraPacketProbes="+packets+" assertions="+assertions);
    }
    private static void preorder(UiPacket.Node n,List<String> ids) { ids.add(n.id);for(UiPacket.Node c:n.children)preorder(c,ids); }
    private static String normalized(AppearanceResolutionV1.Plan p) throws Exception {
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("revision",p.revision);result.put("configurationID",p.configurationID);result.put("recipe",p.recipe);result.put("platformSpecificReason",p.platformSpecificReason);
        result.put("canvas",p.canvas);result.put("environment",p.environment);result.put("platform",p.platform);result.put("font",p.font);result.put("resources",p.resources);
        List<Object> ns=new ArrayList<>();
        for(AppearanceResolutionV1.Node n:p.nodes) {
            Map<String,Object> v=record(n),r=record(n.recipe());r.put("case",n.recipe().getClass().getSimpleName());v.put("recipe",r);
            List<Object> ss=new ArrayList<>();for(int state=0;state<4;state++)ss.add(p.style(n.identity().id(),(state&1)!=0,(state&2)!=0));v.put("styles",ss);ns.add(v);
        }
        result.put("nodes",ns);return canonical(result);
    }
    private static Map<String,Object> record(Object o) throws Exception {
        Map<String,Object> v=new TreeMap<>();for(RecordComponent c:o.getClass().getRecordComponents())v.put(c.getName(),c.getAccessor().invoke(o));return v;
    }
    private static String canonical(Object o) throws Exception {
        if(o!=null&&o.getClass().isRecord())return canonical(record(o));
        if(o instanceof Enum<?> e)return canonical(e.name());
        if(o instanceof Number)return canonical(o.toString());
        if(o instanceof Map<?,?> m) {
            TreeMap<String,Object> v=new TreeMap<>();for(var e:m.entrySet())v.put((String)e.getKey(),e.getValue());
            List<String> entries=new ArrayList<>();for(var e:v.entrySet())entries.add(canonical(e.getKey())+":"+canonical(e.getValue()));return "{"+String.join(",",entries)+"}";
        }
        if(o instanceof List<?> l){List<String> entries=new ArrayList<>();for(Object v:l)entries.add(canonical(v));return "["+String.join(",",entries)+"]";}
        StringBuilder b=new StringBuilder();Json.write(b,o);return b.toString();
    }
    @SuppressWarnings({"unchecked","rawtypes"})
    private static void immutable(Object o) throws Exception {
        if(o==null||o instanceof String||o instanceof Number||o instanceof Boolean||o instanceof Enum<?>||!visited.add(o))return;
        if(o instanceof Map<?,?> m) {
            containers++;unsupported(()->((Map)m).put("__review__","mutation"));unsupported(m::clear);
            if(!m.isEmpty()) {
                var e=m.entrySet().iterator().next();unsupported(()->((Map.Entry)e).setValue("mutation"));
                Iterator<?> it=m.keySet().iterator();it.next();unsupported(it::remove);
            }
            for(var e:m.entrySet()){immutable(e.getKey());immutable(e.getValue());}return;
        }
        if(o instanceof List<?> l) {
            containers++;unsupported(()->((List)l).add("mutation"));unsupported(l::clear);
            if(!l.isEmpty())unsupported(()->((List)l).set(0,"mutation"));
            for(Object v:l)immutable(v);return;
        }
        check(o.getClass().getName().startsWith("dev.mixer.android."),"unexpected mutable graph type "+o.getClass());
        for(Field f:o.getClass().getDeclaredFields()) {
            if(Modifier.isStatic(f.getModifiers()))continue;
            check(Modifier.isFinal(f.getModifiers()),"non-final field "+f);finalFields++;
            f.setAccessible(true);immutable(f.get(o));
        }
    }
    private static String wire(Object o) {
        if(o instanceof Map<?,?> m){List<String> es=new ArrayList<>();for(var e:m.entrySet())es.add(wire(e.getKey())+":"+wire(e.getValue()));return "{"+String.join(",",es)+"}";}
        if(o instanceof List<?> l){List<String> es=new ArrayList<>();for(Object v:l)es.add(wire(v));return "["+String.join(",",es)+"]";}
        StringBuilder b=new StringBuilder();Json.write(b,o);return b.toString();
    }
    private static UiPacket decodeWire(Object o){return UiPacket.decode(wire(o).getBytes(StandardCharsets.UTF_8));}
    private static void packetProbes(String encoded,AppearanceDescriptorV1 d,AppearanceResolutionV1.Environment env,AppearanceResolutionV1.Platform platform) {
        Map<String,Object> root=Json.object(Json.parse(Base64.getDecoder().decode(encoded)));
        List<Object> ids=Json.array(root.get("identities"));
        java.math.BigInteger high=new java.math.BigInteger("18446744073709551615");
        Map<String,String> exact=new LinkedHashMap<>();
        for(int i=0;i<ids.size();i++) {
            Map<String,Object> id=Json.object(ids.get(i));String value=high.subtract(java.math.BigInteger.valueOf(i)).toString();id.put("generation",new Json.Num(value));exact.put(Json.string(id.get("id")),value);
        }
        UiPacket p=decodeWire(root);var plan=AppearanceResolutionV1.prepare(p,d,env,platform);packets++;
        for(var n:plan.nodes)equal(exact.get(n.identity().id()),n.identity().generation(),"exact high UInt64 generation");
        for(String malformed:new String[]{"0","-1","1.5","18446744073709551616"}) {
            Json.object(ids.get(0)).put("generation",new Json.Num(malformed));reject(()->decodeWire(root));packets++;
        }
        Json.object(ids.get(0)).put("generation",new Json.Num(Json.uint(Json.object(ids.get(1)).get("generation"))));reject(()->decodeWire(root));packets++;
        // All prior decoded values remain unchanged when raw parser builders change.
        equal(exact.get(plan.nodes.get(0).identity().id()),plan.nodes.get(0).identity().generation(),"external builder detached");
    }
    private static void unsupported(Runnable r){assertions++;try{r.run();}catch(UnsupportedOperationException expected){return;}throw new AssertionError("mutable retained collection");}
    private static void reject(Runnable r){assertions++;try{r.run();}catch(IllegalArgumentException expected){return;}throw new AssertionError("invalid input accepted");}
    private static void check(boolean value,String reason){assertions++;if(!value)throw new AssertionError(reason);}
    private static void equal(Object a,Object b,String reason){check(Objects.equals(a,b),reason+" expected="+a+" actual="+b);}
    private static String sha(String v) throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(v.getBytes(StandardCharsets.UTF_8)));}
}
