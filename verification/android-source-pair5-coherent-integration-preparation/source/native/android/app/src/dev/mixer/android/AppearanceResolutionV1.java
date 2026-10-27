package dev.mixer.android;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/** Pure immutable appearance data for an already decoded UI packet and canonical
 * descriptor. No native widgets, resource capture, installation, display, health,
 * signing, or release authority is established by this resolver. */
final class AppearanceResolutionV1 {
    private AppearanceResolutionV1() {}

    enum Platform { iOS, android }
    enum Scheme { light, dark }
    enum Direction { leftToRight, rightToLeft }
    enum TextRole { body, headline, title, caption }
    enum ButtonRole { normal, destructive, cancel }
    enum HorizontalAlignment { leading, center, trailing }
    enum VerticalAlignment { top, center, bottom, firstTextBaseline, lastTextBaseline }
    enum OverlayAlignment { center, leading, trailing, top, bottom, topLeading, topTrailing, bottomLeading, bottomTrailing }

    record Environment(Scheme scheme, Direction direction, int textScale1024, int density1024) {
        Environment {
            require(scheme != null && direction != null, "environment enum");
            require(textScale1024 >= 512 && textScale1024 <= 4096, "text scale");
            require(density1024 >= 128 && density1024 <= 16384, "density");
        }
    }
    /** RGBA is unpremultiplied #RRGGBBAA. Apply alpha/255 * opacity/1000 once. */
    record Paint(String color, int opacityPermille) {}
    record Insets(long top, long leading, long bottom, long trailing) {}
    record Text(TextRole role, long size64, int weight, long minimumLineBox64,
                boolean selectable, Integer maximumLines) {}
    record ButtonMetrics(Insets labelInsets64, long minimumWidth64, long minimumHeight64, long radius64) {}
    record FieldMetrics(Insets insets64, long minimumHeight64, long border64) {}
    record ToggleMetrics(long trackWidth64, long trackHeight64, long thumb64, long inset64,
                         long labelGap64, long minimumRow64) {}
    record ListMetrics(Insets insets64, long minimumRow64, long rowGap64, long groupGap64, long separator64) {}
    record NavigationMetrics(Insets titleInsets64, long minimumBarHeight64, HorizontalAlignment titleAlignment) {}
    sealed interface Recipe permits TextRecipe, ButtonRecipe, FieldRecipe, ToggleRecipe, VStackRecipe,
        HStackRecipe, ZStackRecipe, ListRecipe, SectionRecipe, NavigationRecipe {}
    record TextRecipe(Text text) implements Recipe {}
    record ButtonRecipe(ButtonRole role, Text text, ButtonMetrics metrics, long contentHeightFloor64) implements Recipe {}
    record FieldRecipe(Text text, FieldMetrics metrics, long contentHeightFloor64) implements Recipe {}
    record ToggleRecipe(Text text, boolean checked, ToggleMetrics metrics, long contentHeightFloor64) implements Recipe {}
    record VStackRecipe(long spacing64, HorizontalAlignment alignment) implements Recipe {}
    record HStackRecipe(long spacing64, VerticalAlignment alignment) implements Recipe {}
    record ZStackRecipe(OverlayAlignment alignment) implements Recipe {}
    record ListRecipe(ListMetrics metrics, long rowHeightFloor64) implements Recipe {}
    record SectionRecipe(Text header, Insets headerInsets64) implements Recipe {}
    record NavigationRecipe(Text title, NavigationMetrics metrics, long barHeightFloor64) implements Recipe {}
    /** Exact decimal UInt64 identity/revision strings are retained without signed narrowing. */
    record Identity(String id, String generation) {}
    record Node(Identity identity, String kind, boolean disabled, List<String> childIDs, Recipe recipe) {
        Node { childIDs = List.copyOf(childIDs); }
    }
    record FocusOutline(Paint paint, long width64, long radius64) {}
    record Style(boolean disabled, boolean pressed, boolean focused, Paint foreground, Paint background,
                 Paint rowBackground, Paint separator, Paint placeholder, Paint caret, Paint selection,
                 Paint border, Paint toggleTrack, Paint toggleThumb, Paint pressedOverlay, FocusOutline focusOutline) {}

    static final class Plan {
        final String revision, configurationID, recipe, platformSpecificReason;
        final Paint canvas;
        final Environment environment;
        final Platform platform;
        // These are the descriptor's bounded, recursively immutable reference data.
        // They are not installed resource bytes or a native font support receipt.
        final Map<String, Object> font;
        final List<Object> resources;
        final List<Node> nodes;
        private final Map<String, Node> byID;
        private final Map<String, Object> palette;
        private final long focusWidth64, focusRadius64;
        private final int pressedOpacityPermille, selectionOpacityPermille;

        private Plan(UiPacket packet, AppearanceDescriptorV1 descriptor, Environment environment,
                     Platform platform, Map<String, Object> theme, List<Node> nodes) {
            revision = packet.revision; configurationID = descriptor.id;
            recipe = text(theme, "recipe"); platformSpecificReason = descriptor.platformSpecificReason;
            this.environment = environment; this.platform = platform;
            palette = object(theme.get(environment.scheme().name()));
            canvas = paint("canvas");
            font = object(object(theme.get("typography")).get("font"));
            resources = descriptor.resources;
            this.nodes = List.copyOf(nodes);
            Map<String, Node> index = new LinkedHashMap<>();
            for (Node node : nodes) index.put(node.identity().id(), node);
            byID = Collections.unmodifiableMap(index);
            Map<String, Object> controls = object(theme.get("controls"));
            focusWidth64 = metric(controls, "focusWidth64"); focusRadius64 = metric(controls, "focusRadius64");
            pressedOpacityPermille = (int)metric(controls, "pressedOpacityPermille");
            selectionOpacityPermille = (int)metric(controls, "selectionOpacityPermille");
        }

        Node node(String nodeID) { return byID.get(nodeID); }
        Style style(String nodeID) { return style(nodeID, false, false); }
        Style style(String nodeID, boolean pressed, boolean focused) {
            Node node = node(nodeID);
            if (node == null) return null;
            boolean field = node.kind().equals("textField"), list = node.kind().equals("list");
            boolean toggle = node.kind().equals("toggle"), button = node.kind().equals("button");
            boolean interactive = field || toggle || button;
            pressed = interactive && !node.disabled() && pressed;
            focused = interactive && !node.disabled() && focused;
            String roleColor = node.recipe() instanceof ButtonRecipe value && value.role() == ButtonRole.destructive
                ? "destructive" : "accent";
            Paint track = node.recipe() instanceof ToggleRecipe value
                ? paint(node.disabled() ? "separator" : value.checked() ? "accent" : "toggleOff") : null;
            return new Style(node.disabled(), pressed, focused,
                paint(node.disabled() ? "disabledText" : button ? roleColor : "primaryText"),
                list || node.kind().equals("navigation") ? paint("canvas") : new Paint("#00000000", 1000),
                list ? paint("surface") : null, list ? paint("separator") : null,
                field ? paint(node.disabled() ? "disabledText" : "secondaryText") : null,
                field && !node.disabled() ? paint("accent") : null,
                field && !node.disabled() ? paint("accent", selectionOpacityPermille) : null,
                field ? paint("separator") : null, track, toggle ? paint("toggleThumb") : null,
                pressed ? paint(roleColor, pressedOpacityPermille) : null,
                focused ? new FocusOutline(paint("focus"), focusWidth64, focusRadius64) : null);
        }
        private Paint paint(String name) { return paint(name, 1000); }
        private Paint paint(String name, int opacity) { return new Paint(text(palette, name), opacity); }
    }

    static Plan prepare(UiPacket packet, AppearanceDescriptorV1 descriptor, Environment environment, Platform platform) {
        require(packet != null && descriptor != null && environment != null && platform != null, "resolution input");
        // UiPacket and AppearanceDescriptorV1 have private outer constructors. Their
        // decoders validate full input before returning and expose no mutable aliases.
        // Resolve only actual packet nodes; no IDs or generations are synthesized.
        require(packet.nodes.size() > 0 && packet.nodes.size() <= 4096, "packet node bound");
        Map<String, Object> theme = platform == Platform.iOS ? descriptor.iOS : descriptor.android;
        Metrics metrics = new Metrics(theme, environment.textScale1024());
        List<Node> nodes = new ArrayList<>(packet.nodes.size());
        ArrayDeque<UiPacket.Node> pending = new ArrayDeque<>(); pending.push(packet.root);
        while (!pending.isEmpty()) {
            UiPacket.Node node = pending.pop();
            require(nodes.size() < 4096 && packet.nodes.get(node.id) == node, "packet identity");
            List<String> childIDs = new ArrayList<>(node.children.size());
            for (UiPacket.Node child : node.children) childIDs.add(child.id);
            nodes.add(new Node(new Identity(node.id, node.generation), node.kind, node.disabled,
                childIDs, metrics.resolve(node)));
            require(node.children.size() <= 4096 - nodes.size() - pending.size(), "packet frontier");
            for (int i = node.children.size() - 1; i >= 0; i--) pending.push(node.children.get(i));
        }
        require(nodes.size() == packet.nodes.size(), "packet coverage");
        return new Plan(packet, descriptor, environment, platform, theme, nodes);
    }

    private static final class Metrics {
        final Map<String, Object> layout;
        final Map<TextRole, Text> types;
        final ButtonMetrics button;
        final FieldMetrics field;
        final ToggleMetrics toggle;
        final ListMetrics list;
        final Insets sectionHeaderInsets64;
        final NavigationMetrics navigation;
        final long buttonFloor, fieldFloor, toggleFloor, rowFloor, barFloor;
        Metrics(Map<String, Object> theme, int scale) {
            Map<String, Object> typography = object(theme.get("typography"));
            Map<TextRole, Text> resolved = new LinkedHashMap<>();
            for (TextRole role : TextRole.values()) {
                Map<String, Object> value = object(typography.get(role.name()));
                resolved.put(role, new Text(role, scaled(metric(value, "size64"), scale),
                    (int)metric(value, "weight"), scaled(metric(value, "minimumLineBox64"), scale), false, null));
            }
            types = Collections.unmodifiableMap(resolved);
            Map<String, Object> controls = object(theme.get("controls"));
            Map<String, Object> b = object(controls.get("button")), f = object(controls.get("field")), t = object(controls.get("toggle"));
            button = new ButtonMetrics(insets(b.get("labelInsets64")), metric(b, "minimumWidth64"), metric(b, "minimumHeight64"), metric(b, "radius64"));
            field = new FieldMetrics(insets(f.get("insets64")), metric(f, "minimumHeight64"), metric(f, "border64"));
            toggle = new ToggleMetrics(metric(t, "trackWidth64"), metric(t, "trackHeight64"), metric(t, "thumb64"),
                metric(t, "inset64"), metric(t, "labelGap64"), metric(t, "minimumRow64"));
            layout = object(theme.get("layout"));
            Map<String, Object> l = object(layout.get("list")), n = object(layout.get("navigation"));
            list = new ListMetrics(insets(l.get("insets64")), metric(l, "minimumRow64"), metric(l, "rowGap64"), metric(l, "groupGap64"), metric(l, "separator64"));
            sectionHeaderInsets64 = insets(layout.get("sectionHeaderInsets64"));
            navigation = new NavigationMetrics(insets(n.get("titleInsets64")), metric(n, "minimumBarHeight64"),
                HorizontalAlignment.valueOf(text(n, "titleAlignment")));
            long body = types.get(TextRole.body).minimumLineBox64();
            buttonFloor = height(button.minimumHeight64(), body, button.labelInsets64());
            fieldFloor = height(field.minimumHeight64(), body, field.insets64());
            toggleFloor = Math.max(Math.max(toggle.minimumRow64(), toggle.trackHeight64()), body);
            rowFloor = Math.max(list.minimumRow64(), body);
            barFloor = height(navigation.minimumBarHeight64(), types.get(TextRole.title).minimumLineBox64(), navigation.titleInsets64());
        }
        Recipe resolve(UiPacket.Node node) {
            return switch (node.kind) {
                case "text" -> {
                    Text source = types.get(TextRole.valueOf(node.text("style", "body")));
                    yield new TextRecipe(new Text(source.role(), source.size64(), source.weight(), source.minimumLineBox64(),
                        node.flag("selectable", false), node.properties.containsKey("maxLines") ? (int)node.number("maxLines", 0) : null));
                }
                case "button" -> new ButtonRecipe(ButtonRole.valueOf(node.text("role", "normal")), types.get(TextRole.body), button, buttonFloor);
                case "textField" -> new FieldRecipe(types.get(TextRole.body), field, fieldFloor);
                case "toggle" -> new ToggleRecipe(types.get(TextRole.body), node.flag("value", false), toggle, toggleFloor);
                case "vStack" -> new VStackRecipe(spacing(node), HorizontalAlignment.valueOf(node.text("alignment", text(layout, "vStackAlignment"))));
                case "hStack" -> new HStackRecipe(spacing(node), VerticalAlignment.valueOf(node.text("alignment", text(layout, "hStackAlignment"))));
                case "zStack" -> new ZStackRecipe(OverlayAlignment.valueOf(node.text("alignment", text(layout, "zStackAlignment"))));
                case "list" -> new ListRecipe(list, rowFloor);
                case "section" -> new SectionRecipe(node.properties.containsKey("title") ? types.get(TextRole.caption) : null, sectionHeaderInsets64);
                case "navigation" -> new NavigationRecipe(node.properties.containsKey("title") ? types.get(TextRole.title) : null,
                    navigation, node.properties.containsKey("title") ? barFloor : navigation.minimumBarHeight64());
                default -> throw new IllegalArgumentException("unsupported node");
            };
        }
        private long spacing(UiPacket.Node node) {
            if (!node.properties.containsKey("spacing")) return metric(layout, "stackGap64");
            double value = node.number("spacing", 0);
            require(Double.isFinite(value) && value >= 0 && value <= 256, "spacing");
            return (long)Math.floor(value * 64 + 0.5);
        }
    }
    private static long scaled(long metric, int scale) {
        require(metric >= 0 && metric <= 65536, "scaled metric");
        return (metric * scale + 512) / 1024;
    }
    private static long height(long minimum, long line, Insets insets) {
        long content = Math.addExact(Math.addExact(line, insets.top()), insets.bottom());
        require(content <= 0xffff_ffffL, "aggregate height");
        return Math.max(minimum, content);
    }
    private static Insets insets(Object raw) {
        Map<String, Object> value = object(raw);
        return new Insets(metric(value, "top"), metric(value, "leading"), metric(value, "bottom"), metric(value, "trailing"));
    }
    @SuppressWarnings("unchecked") private static Map<String, Object> object(Object value) {
        return (Map<String, Object>)Objects.requireNonNull(value);
    }
    private static long metric(Map<String, Object> object, String key) { return (Long)Objects.requireNonNull(object.get(key)); }
    private static String text(Map<String, Object> object, String key) { return (String)Objects.requireNonNull(object.get(key)); }
    private static void require(boolean admitted, String reason) { if (!admitted) throw new IllegalArgumentException(reason); }
}
