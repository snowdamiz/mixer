package dev.mixer.android;

import dev.mixer.android.AppearanceDescriptorV2.*;
import dev.mixer.android.AppearanceResolverV2.*;
import dev.mixer.android.AppearanceResolverV2.Direction;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Independent semantic expectations plus actual Swift-packet differential data.
 * Reflection is output inspection only, never product admission authority. */
public final class AppearanceResolverV2Tests {
    private static int checks;
    private static void require(boolean value, String why) { checks++; if (!value) throw new AssertionError(why); }
    private static Object tree(Object value) throws Exception {
        if (value == null || value instanceof String || value instanceof Number || value instanceof Boolean) return value;
        if (value instanceof Weight weight) return weight.value;
        if (value instanceof SystemSans) return Map.of("kind", "systemSans");
        if (value instanceof Bundled font) return Map.of("kind", "bundled", "faces", tree(font.faces()), "fallback", tree(font.fallback()));
        if (value instanceof Enum<?> enumeration) return enumeration.name();
        if (value instanceof List<?> list) { List<Object> result = new ArrayList<>(); for (Object item : list) result.add(tree(item)); return result; }
        if (value.getClass().isRecord()) {
            Map<String,Object> result = new TreeMap<>();
            for (RecordComponent component : value.getClass().getRecordComponents()) result.put(component.getName(),tree(component.getAccessor().invoke(value)));
            return result;
        }
        throw new AssertionError("unprojected type " + value.getClass());
    }
    private static String json(Object value) {
        if (value == null) return "null";
        if (value instanceof Json.Num number) return number.raw;
        if (value instanceof Number || value instanceof Boolean) return value.toString();
        if (value instanceof String string) {
            StringBuilder result = new StringBuilder("\"");
            for (int i = 0; i < string.length(); i++) {
                char c = string.charAt(i);
                if (c == '"' || c == '\\') result.append('\\').append(c);
                else if (c < 32) result.append(String.format(java.util.Locale.ROOT,"\\u%04x", (int)c));
                else result.append(c);
            }
            return result.append('"').toString();
        }
        if (value instanceof List<?> list) { List<String> values = new ArrayList<>(); for (Object item : list) values.add(json(item)); return "[" + String.join(",",values) + "]"; }
        if (value instanceof Map<?,?> map) {
            Map<String,Object> sorted = new TreeMap<>(); for (var entry : map.entrySet()) sorted.put((String)entry.getKey(),entry.getValue());
            List<String> fields = new ArrayList<>(); for (var entry : sorted.entrySet()) fields.add(json(entry.getKey()) + ":" + json(entry.getValue()));
            return "{" + String.join(",",fields) + "}";
        }
        throw new AssertionError("not JSON " + value.getClass());
    }
    private static Map<String,Object> projection(Plan plan) throws Exception {
        Map<String,Object> result = new TreeMap<>();
        for (Field field : Plan.class.getDeclaredFields()) if (!Modifier.isPrivate(field.getModifiers())) result.put(field.getName(),tree(field.get(plan)));
        List<Object> nodes = new ArrayList<>();
        for (Node node : plan.nodes) {
            Map<String,Object> value = new TreeMap<>();
            for (RecordComponent component : Node.class.getRecordComponents()) value.put(component.getName(),tree(component.getAccessor().invoke(node)));
            value.put("styles",List.of(tree(plan.style(node.identity().id(),false,false)),tree(plan.style(node.identity().id(),true,false)),
                tree(plan.style(node.identity().id(),false,true)),tree(plan.style(node.identity().id(),true,true))));
            nodes.add(value);
        }
        result.put("nodes",nodes); return result;
    }
    private static void immutable(Object value) throws Exception {
        if (value == null) return;
        if (value instanceof List<?> list) {
            try { list.clear(); throw new AssertionError("mutable list"); } catch (UnsupportedOperationException expected) { checks++; }
            for (Object child : list) immutable(child);
        } else if (value.getClass().isRecord()) {
            require(Modifier.isFinal(value.getClass().getModifiers()),"nonfinal record");
            for (RecordComponent component : value.getClass().getRecordComponents()) immutable(component.getAccessor().invoke(value));
        } else require(value instanceof String || value instanceof Number || value instanceof Boolean || value instanceof Enum<?>,"unexpected mutable leaf");
    }
    private static Environment environment(String source) {
        String[] e = source.split("\\|",-1);
        return new Environment(Scheme.valueOf(e[0]),Direction.valueOf(e[1]),Profile.valueOf(e[2]),Integer.parseInt(e[3]),
            new Viewport(Long.parseLong(e[4]),Long.parseLong(e[5])),new SafeArea(Long.parseLong(e[6]),Long.parseLong(e[7]),Long.parseLong(e[8]),Long.parseLong(e[9])),
            new String(Base64.getDecoder().decode(e[10]),StandardCharsets.UTF_8),new Accessibility(e[11].equals("1"),e[12].equals("1"),e[13].equals("1")),e[14]);
    }
    private static void metrics(Text text, Profile profile) {
        if (text == null) return;
        int[][] sizes = {{14,25,11,31},{15,26,11,32},{16,27,11,33},{17,28,12,34},{19,30,14,36},{21,32,16,38},
            {23,34,18,40},{28,38,22,44},{33,43,26,48},{40,48,32,52},{47,53,37,56},{53,58,43,60}};
        int index = switch (text.role()) { case body, headline, sectionHeader -> 0; case title -> 1; case caption -> 2; case navigationExpanded -> 3; };
        int weight = switch (text.role()) { case headline, sectionHeader -> 600; case navigationExpanded -> 700; default -> 400; };
        require(text.metrics().size64() == sizes[profile.ordinal()][index] * 64 && text.metrics().weight().value == weight,"six-role profile metric");
    }
    private static void semantics(String name, Plan plan, UiPacket packet) throws Exception {
        require(plan.revision.equals(packet.revision),"exact revision");
        require(plan.nodes.stream().map(node -> node.identity().id()).toList().equals(new ArrayList<>(packet.nodes.keySet())),"preorder");
        require(plan.node("missing") == null && plan.node(null) == null && plan.style("missing",true,true) == null,"missing node");
        for (Node node : plan.nodes) {
            UiPacket.Node original = packet.nodes.get(node.identity().id());
            require(plan.node(original.id) == node && node.identity().generation().equals(original.generation),"same exact packet identity");
            require(node.disabled() == original.disabled && node.childIDs().equals(original.children.stream().map(child -> child.id).toList()),"children/disabled");
            for (boolean pressed : new boolean[]{false,true}) for (boolean focused : new boolean[]{false,true}) {
                Style style = plan.style(original.id,pressed,focused);
                boolean control = node.recipe() instanceof ButtonRecipe || node.recipe() instanceof FieldRecipe || node.recipe() instanceof ToggleRecipe;
                require(style.disabled() == original.disabled && style.focused() == (!original.disabled && focused && control),"focus suppression");
                require(style.pressed() == (!original.disabled && pressed && (node.recipe() instanceof ButtonRecipe || node.recipe() instanceof ToggleRecipe)),"press suppression");
                immutable(style);
            }
            if (node.recipe() instanceof TextRecipe text) {
                metrics(text.text(),plan.environment.profile()); require(text.text().value().equals(original.text("text","")),"retained text");
                require(((TextPaints)plan.style(original.id,true,true).paints()).background().equals(new Color(0,0,0,0)),"explicit text clear");
            } else if (node.recipe() instanceof ButtonRecipe button) {
                metrics(button.text(),plan.environment.profile());
                if (node.disabled()) require(((ButtonPaints)plan.style(original.id,true,true).paints()).paint().background().equals(new Color(0,0,0,0)),"disabled button canonical clear");
            } else if (node.recipe() instanceof FieldRecipe field) {
                metrics(field.text(),plan.environment.profile());
                require(!plan.style(original.id,true,false).pressed(),"field ignores press");
                FieldPaint paint = ((FieldPaints)plan.style(original.id,false,false).paints()).paint();
                require(paint.outline().width64() == 0,"inactive field zero outline");
                if (node.disabled()) require(paint.caret().alpha() == 0 && paint.selection().alpha() == 0,"disabled field explicit clear");
            } else if (node.recipe() instanceof ToggleRecipe toggle) {
                metrics(toggle.text(),plan.environment.profile());
                require(toggle.metrics().trackWidth64() == 4032 && toggle.metrics().thumbWidth64() == 2368,"fixed track and rectangular thumb");
            } else if (node.recipe() instanceof NavigationRecipe navigation) {
                metrics(navigation.expandedTitle(),plan.environment.profile()); metrics(navigation.compactTitle(),plan.environment.profile());
                if (navigation.expandedTitle() != null) require(navigation.expandedTitle().role() == Role.navigationExpanded && navigation.compactTitle().role() == Role.headline && navigation.compactTitle().maximumLines() == 1,"navigation role separation");
            } else if (node.recipe() instanceof SectionRecipe section) {
                metrics(section.header(),plan.environment.profile());
                if (section.context() instanceof ListGroup) require(section.headerToContentGap64() == 0 && section.contentGaps64().isEmpty(),"structural section");
            } else if (node.recipe() instanceof VStackRecipe stack) require(stack.gaps64().size() == Math.max(0,node.childIDs().size()-1),"vstack exact gap count");
            else if (node.recipe() instanceof HStackRecipe stack) require(stack.gaps64().size() == Math.max(0,node.childIDs().size()-1),"hstack exact gap count");
            if (node.recipe() instanceof ListRecipe list) {
                for (int groupIndex = 0; groupIndex < list.groups().size(); groupIndex++) {
                    Group group = list.groups().get(groupIndex); metrics(group.header(),plan.environment.profile());
                    require(group.drawsOutline() == !group.rowIdentities().isEmpty(),"outline policy");
                    for (int row = 0; row < group.rowIdentities().size(); row++) {
                        Node record = plan.node(group.rowIdentities().get(row).id());
                        require(record != null && record.identity().equals(group.rowIdentities().get(row)),"group exact reference");
                        require(record.rowPlacement().equals(new RowPlacement(node.identity(),groupIndex,row,row+1<group.rowIdentities().size())),"interior row separator");
                    }
                }
            }
        }
        if (name.startsWith("base-")) {
            require(((VStackRecipe)plan.node("stack").recipe()).gaps64().subList(0,2).equals(List.of(128,512)),"independent body-caption gap");
            ListRecipe list = (ListRecipe)plan.node("list").recipe();
            require(list.groups().size() == 7 && !list.groups().get(0).visible() && list.groups().get(0).leadingGap64() == 0,"invisible empty group");
            require(list.groups().get(1).leadingGap64() == 640 && list.groups().get(2).leadingGap64() == 1771,"one top then headed gap");
            require(list.groups().get(2).headerToRowsGap64() == 640 && !list.groups().get(3).drawsOutline(),"header-to-row vs title-only");
            require(list.trailingPadding64() == 640,"visible bottom padding");
            ButtonPaint enabled = ((ButtonPaints)plan.style("normal",false,false).paints()).paint();
            ButtonPaint pressed = ((ButtonPaints)plan.style("normal",true,true).paints()).paint();
            require(enabled.background().alpha() == 0 && pressed.background().alpha() == 31,"independent button alpha");
            require(((FieldPaints)plan.style("field",true,true).paints()).paint().selection().alpha() == 61,"independent field selection alpha");
        }
        if (name.startsWith("custom-")) {
            Color body = ((TextPaints)plan.style("body",true,true).paints()).foreground();
            require(body.equals(new Color(18,52,86,120)),"authored RGBA neither premultiplied nor disabled-multiplied");
            require(((VStackRecipe)plan.node("stack").recipe()).gaps64().subList(0,2).equals(List.of(17,777)),"custom spacing consumed");
        }
        immutable(plan.nodes); immutable(plan.resources); immutable(plan.environment); immutable(plan.font);
        for (Field field : Plan.class.getDeclaredFields()) require(Modifier.isFinal(field.getModifiers()),"nonfinal plan field");
    }
    private static Environment changed(Environment e, String part, Object value) {
        return new Environment(part.equals("scheme") ? (Scheme)value : e.scheme(),part.equals("direction") ? (Direction)value : e.direction(),
            part.equals("profile") ? (Profile)value : e.profile(),part.equals("density") ? (Integer)value : e.density1024(),
            part.equals("viewport") ? (Viewport)value : e.viewport(),part.equals("safe") ? (SafeArea)value : e.safeArea64(),
            part.equals("locale") ? (String)value : e.localeIdentifier(),part.equals("accessibility") ? (Accessibility)value : e.accessibility(),
            part.equals("generation") ? (String)value : e.generation());
    }
    private static void rejects(byte[] packet, byte[] descriptor, Environment environment, Platform platform, String label) {
        try { AppearanceResolverV2.prepare(packet,descriptor,environment,platform); throw new AssertionError("accepted: " + label); }
        catch (AppearanceDescriptorV2.Failure expected) { checks++; }
    }
    private static Map<String,Object> node(String id, String kind, Map<String,Object> properties, List<Object> children) {
        return new LinkedHashMap<>(Map.of("id",id,"kind",kind,"properties",new LinkedHashMap<>(properties),"children",new ArrayList<>(children),"actions",new ArrayList<>()));
    }
    private static byte[] packet(Map<String,Object> root) {
        List<Object> identities = new ArrayList<>(); List<Map<String,Object>> pending = new ArrayList<>(); pending.add(root);
        int generation = 1;
        while (!pending.isEmpty()) {
            Map<String,Object> next = pending.remove(pending.size()-1); identities.add(Map.of("id",next.get("id"),"generation",generation++));
            List<Object> children = Json.array(next.get("children")); for (int i=children.size()-1;i>=0;i--) pending.add(Json.object(children.get(i)));
        }
        return json(Map.of("schemaVersion",1,"document",Map.of("schemaVersion",1,"revision",0,"root",root),"identities",identities)).getBytes(StandardCharsets.UTF_8);
    }
    private static void independent(byte[] source, byte[] descriptor, Environment environment) throws Exception {
        for (String part : List.of("scheme","direction","profile","viewport","safe","locale","accessibility","generation")) rejects(source,descriptor,changed(environment,part,null),Platform.android,"null " + part);
        rejects(source,descriptor,null,Platform.android,"null environment"); rejects(source,descriptor,environment,null,"null platform");
        for (String value : List.of("", "00", "+1", "-1", "01", "18446744073709551616", "1.0", "1e1", " 1", "١")) rejects(source,descriptor,changed(environment,"generation",value),Platform.android,"invalid generation");
        for (String value : List.of("", "a\u0000b", "a\u0085b", "a\u200Db", "\uD800", "\uDC00", "a\uD800z", "x".repeat(129), "é".repeat(65))) rejects(source,descriptor,changed(environment,"locale",value),Platform.android,"invalid locale");
        for (Object[] entry : List.of(new Object[]{"density",127},new Object[]{"density",16385},new Object[]{"density",-1},
            new Object[]{"viewport",new Viewport(-1,1)},new Object[]{"viewport",new Viewport(2147483648L,1)},
            new Object[]{"safe",new SafeArea(Long.MAX_VALUE,0,1,0)},new Object[]{"safe",new SafeArea(-1,0,0,0)},
            new Object[]{"safe",new SafeArea(0,2147483647L,0,2147483647L)})) rejects(source,descriptor,changed(environment,(String)entry[0],entry[1]),Platform.android,"invalid numeric environment");
        for (String generation : List.of("0", "18446744073709551615")) require(AppearanceResolverV2.prepare(source,descriptor,changed(environment,"generation",generation),Platform.android).environment.generation().equals(generation),"UInt64 exact generation");
        for (String locale : List.of("é".repeat(64),"😀".repeat(32),"opaque_@value")) require(AppearanceResolverV2.prepare(source,descriptor,changed(environment,"locale",locale),Platform.android).environment.localeIdentifier().equals(locale),"exact locale UTF8 boundary");
        for (int density : new int[]{128,16384}) AppearanceResolverV2.prepare(source,descriptor,changed(environment,"density",density),Platform.android);
        rejects(null,descriptor,environment,Platform.android,"null packet"); rejects(source,null,environment,Platform.android,"null descriptor");
        rejects(source,(new String(descriptor,StandardCharsets.US_ASCII).stripTrailing()+" \n").getBytes(StandardCharsets.US_ASCII),environment,Platform.android,"noncanonical descriptor");
        Map<String,Object> leaf = node("leaf","text",Map.of("text","leaf"),List.of());
        Map<String,Object> root = node("h","hStack",Map.of("alignment","firstTextBaseline"),List.of(leaf));
        rejects(packet(root),descriptor,environment,Platform.android,"explicit first baseline packet profile");
        root.put("properties",Map.of("alignment","lastTextBaseline")); rejects(packet(root),descriptor,environment,Platform.android,"explicit last baseline packet profile");
        root = node("outer","list",Map.of(),List.of(node("wrap","vStack",Map.of(),List.of(node("nested","list",Map.of(),List.of())))));
        rejects(packet(root),descriptor,environment,Platform.android,"nested list packet profile");
        root = node("stack","vStack",Map.of(),List.of(node("nav","navigation",Map.of(),List.of(leaf))));
        rejects(packet(root),descriptor,environment,Platform.android,"nonroot navigation resolver rejection");
        root = node("button","button",Map.of("label","button"),List.of()); rejects(packet(root),descriptor,environment,Platform.android,"required action packet validation");
        byte[] maximum = packet(leaf); String maximumText = new String(maximum,StandardCharsets.UTF_8).replace("\"generation\":1","\"generation\":18446744073709551615").replace("\"revision\":0","\"revision\":18446744073709551615");
        Plan maxPlan = AppearanceResolverV2.prepare(maximumText.getBytes(StandardCharsets.UTF_8),descriptor,environment,Platform.android);
        require(maxPlan.revision.equals("18446744073709551615") && maxPlan.nodes.get(0).identity().generation().equals(maxPlan.revision),"UInt64 exact packet preservation");
        for (int depth : new int[]{64,65}) {
            root = leaf; for (int i=1;i<depth;i++) root=node("d"+i,"vStack",Map.of(),List.of(root));
            if (depth==64) require(AppearanceResolverV2.prepare(packet(root),descriptor,environment,Platform.android).nodes.size()==64,"depth64 admitted");
            else rejects(packet(root),descriptor,environment,Platform.android,"depth65 rejected");
        }
        for (int total : new int[]{4096,4097}) {
            List<Object> branches = new ArrayList<>(); int remaining=total-1, id=0;
            while (remaining>0) { int count=Math.min(999,remaining-1); List<Object> children=new ArrayList<>(); for(int i=0;i<count;i++)children.add(node("n"+(id++),"text",Map.of("text","x"),List.of())); branches.add(node("b"+(id++),"vStack",Map.of(),children)); remaining-=count+1; }
            byte[] bytes=packet(node("maximum","vStack",Map.of(),branches));
            if(total==4096)require(AppearanceResolverV2.prepare(bytes,descriptor,environment,Platform.android).nodes.size()==4096,"4096 real decoded nodes");
            else rejects(bytes,descriptor,environment,Platform.android,"4097 real decoded nodes rejected");
        }
        byte[] packetCopy=source.clone(),descriptorCopy=descriptor.clone(); Plan plan=AppearanceResolverV2.prepare(packetCopy,descriptorCopy,environment,Platform.android);
        String before=json(projection(plan)); Arrays.fill(packetCopy,(byte)'X'); Arrays.fill(descriptorCopy,(byte)'X');
        require(before.equals(json(projection(plan))),"raw arrays are not retained");
        System.err.println("PASS independent semantic, raw environment, packet restrictions, exact identity, node/depth boundary, and immutable ownership checks");
    }
    public static void main(String[] args) throws Exception {
        int accepted=0,rejected=0; byte[] firstPacket=null,firstDescriptor=null; Environment firstEnvironment=null;
        UiPacket previous=null; String movingGeneration=null;
        for (String line : Files.readAllLines(Path.of(args[0]),StandardCharsets.UTF_8)) {
            String[] f=line.split("\t",-1); byte[] packet=Base64.getDecoder().decode(f[1]),descriptor=Base64.getDecoder().decode(f[2]); Environment environment=environment(f[3]);
            UiPacket decoded=UiPacket.decode(packet); decoded.requireSuccessor(previous); previous=decoded;
            if(f[0].equals("identity-0"))movingGeneration=decoded.nodes.get("moving").generation;
            if(f[0].equals("identity-1"))require(decoded.nodes.get("moving").generation.equals(movingGeneration),"reparent preserves generation");
            if(f[0].equals("identity-2"))require(!decoded.nodes.get("moving").generation.equals(movingGeneration),"kind replacement changes generation");
            String actual;
            try {
                Plan plan=AppearanceResolverV2.prepare(packet,descriptor,environment,Platform.valueOf(f[4]));
                semantics(f[0],plan,UiPacket.decode(packet)); actual=json(projection(plan)); accepted++;
                if(firstPacket==null){firstPacket=packet;firstDescriptor=descriptor;firstEnvironment=environment;}
            } catch (AppearanceDescriptorV2.Failure failure) { actual="error:"+failure.code.name(); rejected++; }
            System.out.println(f[0]+"\t"+Base64.getEncoder().encodeToString(actual.getBytes(StandardCharsets.UTF_8)));
        }
        independent(firstPacket,firstDescriptor,firstEnvironment);
        System.err.println("PASS Java resolver cases="+(accepted+rejected)+" accepted="+accepted+" rejected="+rejected+" assertions="+checks);
    }
}
