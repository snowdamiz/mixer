package dev.mixer.android;

import dev.mixer.android.AppearanceDescriptorV2.*;
import dev.mixer.android.AppearanceDescriptorV2.Error;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Pure immutable untrusted data, with no installed-resource, native-operation,
 * display, input, signing or release authority. V1 remains unchanged. */
final class AppearanceResolverV2 {
    private AppearanceResolverV2() {}
    private static final int MAXIMUM_NODES = 4096;
    private static final Color CLEAR = new Color(0, 0, 0, 0);

    enum Platform { iOS, android }
    enum Scheme { light, dark }
    enum Direction { leftToRight, rightToLeft }
    enum ButtonRole { normal, destructive, cancel }
    record Viewport(long width64, long height64) {}
    record SafeArea(long top, long leading, long bottom, long trailing) {}
    record Accessibility(boolean boldText, boolean increasedContrast, boolean reduceMotion) {}
    /** Generation is a canonical UInt64 decimal, including zero. No native
     * preference conversion or monotonic-generation enforcement is implied. */
    record Environment(Scheme scheme, Direction direction, Profile profile, int density1024,
                       Viewport viewport, SafeArea safeArea64, String localeIdentifier,
                       Accessibility accessibility, String generation) {}
    record Identity(String id, String generation) {}
    record Text(String value, Role role, Metric metrics, boolean selectable, Integer maximumLines) {}
    record RowPlacement(Identity listIdentity, int groupIndex, int rowIndex, boolean separatorAfter) {}
    sealed interface GroupSource permits SectionSource, DirectRunSource {}
    record SectionSource(Identity identity) implements GroupSource {}
    record DirectRunSource(Identity firstRow) implements GroupSource {}
    record Group(GroupSource source, Text header, List<Identity> rowIdentities, boolean visible,
                 int leadingGap64, int headerToRowsGap64) {
        Group { rowIdentities = List.copyOf(rowIdentities); }
        boolean drawsOutline() { return !rowIdentities.isEmpty(); }
    }
    sealed interface SectionContext permits OutsideList, ListGroup, WithinListRow {}
    record OutsideList() implements SectionContext {}
    record ListGroup(Identity listIdentity, int groupIndex) implements SectionContext {}
    record WithinListRow(Identity listIdentity) implements SectionContext {}
    sealed interface Recipe permits TextRecipe, ButtonRecipe, FieldRecipe, ToggleRecipe,
        VStackRecipe, HStackRecipe, ZStackRecipe, ListRecipe, SectionRecipe, NavigationRecipe {}
    record TextRecipe(Text text) implements Recipe {}
    record ButtonRecipe(ButtonRole role, Text text, ButtonMetrics metrics) implements Recipe {}
    record FieldRecipe(String label, String value, Text text, FieldMetrics metrics) implements Recipe {}
    record ToggleRecipe(Text text, boolean checked, ToggleMetrics metrics) implements Recipe {}
    record VStackRecipe(List<Integer> gaps64, HorizontalAlignment alignment) implements Recipe {
        VStackRecipe { gaps64 = List.copyOf(gaps64); }
    }
    record HStackRecipe(List<Integer> gaps64, VerticalAlignment alignment) implements Recipe {
        HStackRecipe { gaps64 = List.copyOf(gaps64); }
    }
    record ZStackRecipe(OverlayAlignment alignment) implements Recipe {}
    record ListRecipe(GroupedList metrics, int rowHeightFloor64, List<Group> groups,
                      int trailingPadding64) implements Recipe {
        ListRecipe { groups = List.copyOf(groups); }
    }
    record SectionRecipe(Text header, SectionContext context, int headerToContentGap64,
                         List<Integer> contentGaps64, HorizontalAlignment alignment) implements Recipe {
        SectionRecipe { contentGaps64 = List.copyOf(contentGaps64); }
    }
    record NavigationRecipe(Text expandedTitle, Text compactTitle, Navigation metrics) implements Recipe {}
    record Node(Identity identity, String kind, List<String> childIDs, boolean disabled,
                RowPlacement rowPlacement, Recipe recipe) {
        Node { childIDs = List.copyOf(childIDs); }
    }
    sealed interface Paints permits TextPaints, ContainerPaints, ListPaints, SectionPaints,
        NavigationPaints, ButtonPaints, FieldPaints, TogglePaints {}
    record TextPaints(Color foreground, Color background) implements Paints {}
    record ContainerPaints(Color background) implements Paints {}
    record ListPaints(Color canvas, Color surface, Color separator) implements Paints {}
    record SectionPaints(Color header, Color background) implements Paints {}
    record NavigationPaints(Color expanded, Color compact, Color background) implements Paints {}
    record ButtonPaints(ButtonPaint paint, Outline focus) implements Paints {}
    record FieldPaints(FieldPaint paint) implements Paints {}
    record TogglePaints(TogglePaint paint, Outline focus) implements Paints {}
    record Style(boolean disabled, boolean pressed, boolean focused, Paints paints) {}

    static final class Plan {
        final String revision, configurationID, platformSpecificReason;
        final AppearanceDescriptorV2.Recipe recipe;
        final Color canvas;
        final Environment environment;
        final Platform platform;
        final Font font;
        final List<Resource> resources;
        final List<Node> nodes;
        private final Map<String, Node> byID;
        private final AppearanceDescriptorV2.Paints paints;

        private Plan(UiPacket packet, AppearanceDescriptorV2 configuration, Environment environment,
                     Platform platform, Theme theme, List<Node> nodes) {
            revision = packet.revision; configurationID = configuration.id;
            platformSpecificReason = configuration.platformSpecificReason; recipe = theme.recipe();
            this.environment = environment; this.platform = platform;
            font = theme.typography().font(); resources = List.copyOf(configuration.resources);
            this.nodes = List.copyOf(nodes);
            Map<String, Node> index = new HashMap<>();
            for (Node node : nodes) index.put(node.identity().id(), node);
            byID = Map.copyOf(index);
            paints = environment.scheme() == Scheme.light ? theme.light() : theme.dark();
            canvas = paints.canvas();
        }
        Node node(String id) { return id == null ? null : byID.get(id); }
        Style style(String id, boolean pressed, boolean focused) {
            Node node = node(id);
            if (node == null) return null;
            boolean button = node.recipe() instanceof ButtonRecipe;
            boolean field = node.recipe() instanceof FieldRecipe;
            boolean toggle = node.recipe() instanceof ToggleRecipe;
            boolean press = !node.disabled() && pressed && (button || toggle);
            boolean focus = !node.disabled() && focused && (button || field || toggle);
            Paints selected;
            if (node.recipe() instanceof TextRecipe text) {
                selected = new TextPaints(rolePaint(paints.text(), text.text().role()), CLEAR);
            } else if (node.recipe() instanceof ButtonRecipe value) {
                ButtonStates states = switch (value.role()) {
                    case normal -> paints.button().normal();
                    case destructive -> paints.button().destructive();
                    case cancel -> paints.button().cancel();
                };
                selected = new ButtonPaints(node.disabled() ? states.disabled() : press ? states.pressed() : states.enabled(),
                    focus ? states.focus() : null);
            } else if (field) {
                selected = new FieldPaints(node.disabled() ? paints.field().disabled() :
                    focus ? paints.field().focused() : paints.field().enabled());
            } else if (node.recipe() instanceof ToggleRecipe value) {
                ToggleStates states = value.checked() ? paints.toggle().on() : paints.toggle().off();
                selected = new TogglePaints(node.disabled() ? states.disabled() : press ? states.pressed() : states.enabled(),
                    focus ? states.focus() : null);
            } else if (node.recipe() instanceof ListRecipe) {
                selected = new ListPaints(paints.canvas(), paints.surface(), paints.separator());
            } else if (node.recipe() instanceof SectionRecipe value) {
                selected = new SectionPaints(value.header() == null ? null : rolePaint(paints.text(), value.header().role()), CLEAR);
            } else if (node.recipe() instanceof NavigationRecipe value) {
                selected = new NavigationPaints(value.expandedTitle() == null ? null : rolePaint(paints.text(), value.expandedTitle().role()),
                    value.compactTitle() == null ? null : rolePaint(paints.text(), value.compactTitle().role()), paints.canvas());
            } else selected = new ContainerPaints(CLEAR);
            return new Style(node.disabled(), press, focus, selected);
        }
    }

    /** Both raw inputs are admitted afresh. There is no alternate constructor
     * accepting fabricated packet Nodes or app-supplied native support. */
    static Plan prepare(byte[] packetBytes, byte[] canonicalDescriptorBytes,
                        Environment environment, Platform platform) {
        AppearanceDescriptorV2 configuration = AppearanceDescriptorV2.decode(canonicalDescriptorBytes);
        validate(environment); admit(platform != null, Error.shape);
        UiPacket packet;
        try { packet = UiPacket.decode(packetBytes); }
        catch (IllegalArgumentException failure) {
            Failure rejected = new Failure(Error.shape); rejected.initCause(failure); throw rejected;
        }
        preflight(packet);
        Theme theme = platform == Platform.iOS ? configuration.iOS : configuration.android;
        Resolver resolver = new Resolver(packet, theme, environment.profile());
        resolver.placements();
        List<Node> nodes = new ArrayList<>(packet.nodes.size());
        ArrayDeque<Pending> pending = new ArrayDeque<>();
        pending.push(new Pending(packet.root, null, false, true));
        while (!pending.isEmpty()) {
            Pending item = pending.pop(); UiPacket.Node node = item.node();
            boolean disabled = item.disabled() || node.flag("disabled", false);
            List<String> children = new ArrayList<>(node.children.size());
            for (UiPacket.Node child : node.children) children.add(child.id);
            nodes.add(new Node(identity(node), node.kind, children, disabled, resolver.rows.get(node.id),
                resolver.recipe(node, item.listAncestor())));
            Identity list = node.kind.equals("list") ? identity(node) : item.listAncestor();
            for (int i = node.children.size() - 1; i >= 0; i--)
                pending.push(new Pending(node.children.get(i), list, disabled, false));
        }
        return new Plan(packet, configuration, environment, platform, theme, nodes);
    }

    private static void validate(Environment environment) {
        admit(environment != null && environment.scheme() != null && environment.direction() != null &&
            environment.profile() != null && environment.viewport() != null && environment.safeArea64() != null &&
            environment.accessibility() != null, Error.shape);
        admit(environment.density1024() >= 128 && environment.density1024() <= 16384, Error.geometry);
        Viewport viewport = environment.viewport(); SafeArea safe = environment.safeArea64();
        admit(viewport.width64() > 0 && viewport.width64() <= AppearanceGeometryV2.MAXIMUM_EXTENT64 &&
            viewport.height64() > 0 && viewport.height64() <= AppearanceGeometryV2.MAXIMUM_EXTENT64 &&
            inset(safe.top()) && inset(safe.leading()) && inset(safe.bottom()) && inset(safe.trailing()), Error.geometry);
        // Each operand is <= Int32.max, so these sums cannot overflow long.
        admit(safe.leading() + safe.trailing() <= viewport.width64() &&
            safe.top() + safe.bottom() <= viewport.height64(), Error.geometry);
        String locale = environment.localeIdentifier();
        admit(locale != null && !locale.isEmpty() && locale.length() <= 128, Error.shape);
        for (int i = 0; i < locale.length(); i++) {
            char c = locale.charAt(i);
            if (Character.isHighSurrogate(c)) {
                admit(i + 1 < locale.length() && Character.isLowSurrogate(locale.charAt(i + 1)), Error.shape);
                i++;
            } else admit(!Character.isLowSurrogate(c), Error.shape);
        }
        admit(locale.getBytes(StandardCharsets.UTF_8).length <= 128, Error.shape);
        for (int i = 0; i < locale.length();) {
            int codepoint = locale.codePointAt(i); int category = Character.getType(codepoint);
            admit(category != Character.CONTROL && category != Character.FORMAT, Error.shape);
            i += Character.charCount(codepoint);
        }
        admit(unsigned(environment.generation()), Error.shape);
        admit(!environment.accessibility().boldText() && !environment.accessibility().increasedContrast(),
            Error.unsupportedNativeOperation);
    }
    private static boolean inset(long value) { return value >= 0 && value <= AppearanceGeometryV2.MAXIMUM_EXTENT64; }
    private static boolean unsigned(String value) {
        if (value == null || value.isEmpty() || value.length() > 20 || value.length() > 1 && value.charAt(0) == '0') return false;
        for (int i = 0; i < value.length(); i++) if (value.charAt(i) < '0' || value.charAt(i) > '9') return false;
        return new BigInteger(value).bitLength() <= 64;
    }
    private record Pending(UiPacket.Node node, Identity listAncestor, boolean disabled, boolean root) {}
    private static void preflight(UiPacket packet) {
        int visited = 0, children = 0, groups = 0, rows = 0, gaps = 0;
        ArrayDeque<Pending> pending = new ArrayDeque<>(); pending.push(new Pending(packet.root, null, false, true));
        while (!pending.isEmpty()) {
            Pending item = pending.pop(); UiPacket.Node node = item.node();
            admit(visited < MAXIMUM_NODES && packet.nodes.get(node.id) == node, Error.shape);
            admit(!(node.kind.equals("list") && item.listAncestor() != null) &&
                !(node.kind.equals("navigation") && !item.root()), Error.unsupportedNativeOperation);
            visited++; children += node.children.size();
            if (node.kind.equals("vStack") || node.kind.equals("hStack") || node.kind.equals("section"))
                gaps += Math.max(0, node.children.size() - 1);
            if (node.kind.equals("list")) {
                boolean run = false;
                for (UiPacket.Node child : node.children) {
                    if (child.kind.equals("section")) { groups++; rows += child.children.size(); run = false; }
                    else { if (!run) groups++; rows++; run = true; }
                }
            }
            admit(children < MAXIMUM_NODES && groups <= MAXIMUM_NODES && rows < MAXIMUM_NODES && gaps < MAXIMUM_NODES &&
                node.children.size() <= MAXIMUM_NODES - visited - pending.size(), Error.valueLimit);
            Identity list = node.kind.equals("list") ? identity(node) : item.listAncestor();
            for (int i = node.children.size() - 1; i >= 0; i--)
                pending.push(new Pending(node.children.get(i), list, false, false));
        }
        long references = (long)visited + children + groups + 2L * rows;
        admit(visited == packet.nodes.size() && references <= 5L * MAXIMUM_NODES, Error.valueLimit);
    }

    private static final class Resolver {
        private final UiPacket packet;
        private final Theme theme;
        private final Profile profile;
        private final Roles roles;
        private final Map<String, List<Group>> groups = new HashMap<>();
        private final Map<String, SectionContext> sections = new HashMap<>();
        private final Map<String, RowPlacement> rows = new HashMap<>();
        Resolver(UiPacket packet, Theme theme, Profile profile) {
            this.packet = packet; this.theme = theme; this.profile = profile;
            Profiles p = theme.typography().profiles();
            roles = switch (profile) {
                case xs -> p.xs(); case s -> p.s(); case m -> p.m(); case l -> p.l();
                case xl -> p.xl(); case xxl -> p.xxl(); case xxxl -> p.xxxl();
                case a1 -> p.a1(); case a2 -> p.a2(); case a3 -> p.a3(); case a4 -> p.a4(); case a5 -> p.a5();
            };
        }
        Text text(String value, Role role) { return text(value, role, false, null); }
        Text text(String value, Role role, boolean selectable, Integer maximumLines) {
            Metric metric = switch (role) {
                case body -> roles.body(); case headline -> roles.headline(); case title -> roles.title();
                case caption -> roles.caption(); case sectionHeader -> roles.sectionHeader();
                case navigationExpanded -> roles.navigationExpanded();
            };
            return new Text(value, role, metric, selectable, maximumLines);
        }
        Text header(UiPacket.Node node) {
            String title = node.text("title", ""); return title.isEmpty() ? null : text(title, Role.sectionHeader);
        }
        void placements() {
            for (UiPacket.Node node : packet.nodes.values()) {
                if (!node.kind.equals("list")) continue;
                List<Group> list = new ArrayList<>(); List<UiPacket.Node> run = new ArrayList<>();
                for (UiPacket.Node child : node.children) {
                    if (child.kind.equals("section")) {
                        if (!run.isEmpty()) { append(list, run, null, node); run.clear(); }
                        append(list, child.children, child, node);
                    } else run.add(child);
                }
                if (!run.isEmpty()) append(list, run, null, node);
                groups.put(node.id, List.copyOf(list));
            }
        }
        void append(List<Group> list, List<UiPacket.Node> children, UiPacket.Node section, UiPacket.Node owner) {
            Identity source = identity(section == null ? children.get(0) : section), listID = identity(owner);
            Text title = section == null ? null : header(section);
            boolean visible = title != null || !children.isEmpty(), previous = false;
            for (Group group : list) previous |= group.visible();
            GroupedList metrics = theme.groupedList();
            int gap = !visible ? 0 : !previous ? metrics.topPadding64() :
                title == null ? metrics.groupWithoutHeaderGap64() : metrics.groupToNextHeader64();
            int index = list.size();
            if (section != null) sections.put(section.id, new ListGroup(listID, index));
            List<Identity> identities = new ArrayList<>(children.size());
            for (int i = 0; i < children.size(); i++) {
                UiPacket.Node child = children.get(i); identities.add(identity(child));
                rows.put(child.id, new RowPlacement(listID, index, i, i + 1 < children.size()));
            }
            list.add(new Group(section == null ? new DirectRunSource(source) : new SectionSource(source), title, identities,
                visible, gap, title != null && !children.isEmpty() ? metrics.headerToGroup64() : 0));
        }
        Recipe recipe(UiPacket.Node node, Identity listAncestor) {
            String label = node.text("label", "");
            return switch (node.kind) {
                case "text" -> new TextRecipe(text(node.text("text", ""), Role.valueOf(node.text("style", "body")),
                    node.flag("selectable", false), node.properties.containsKey("maxLines") ? (int)node.number("maxLines", 0) : null));
                case "button" -> new ButtonRecipe(ButtonRole.valueOf(node.text("role", "normal")), text(label, Role.body), theme.button());
                case "textField" -> new FieldRecipe(label, node.text("value", ""), text(node.text("value", ""), Role.body), theme.field());
                case "toggle" -> new ToggleRecipe(text(label, Role.body), node.flag("value", false), theme.toggle());
                case "vStack" -> {
                    List<Integer> gaps = new ArrayList<>();
                    for (int i = 0; i + 1 < node.children.size(); i++) {
                        UiPacket.Node first = node.children.get(i), second = node.children.get(i + 1);
                        boolean pair = first.kind.equals("text") && second.kind.equals("text") &&
                            first.text("style", "body").equals("body") && second.text("style", "").equals("caption");
                        gaps.add(node.properties.containsKey("spacing") ? AppearanceGeometryV2.spacing64(node.number("spacing", 0)) :
                            pair ? theme.stacks().bodyCaptionGap64() : theme.stacks().defaultGap64());
                    }
                    yield new VStackRecipe(gaps, HorizontalAlignment.valueOf(node.text("alignment", theme.stacks().vStackAlignment().name())));
                }
                case "hStack" -> new HStackRecipe(gaps(node), VerticalAlignment.valueOf(node.text("alignment", theme.stacks().hStackAlignment().name())));
                case "zStack" -> new ZStackRecipe(OverlayAlignment.valueOf(node.text("alignment", theme.stacks().zStackAlignment().name())));
                case "list" -> {
                    Floors f = theme.groupedList().profileFloors64();
                    int floor = switch (profile) {
                        case xs -> f.xs(); case s -> f.s(); case m -> f.m(); case l -> f.l(); case xl -> f.xl();
                        case xxl -> f.xxl(); case xxxl -> f.xxxl(); case a1 -> f.a1(); case a2 -> f.a2();
                        case a3 -> f.a3(); case a4 -> f.a4(); case a5 -> f.a5();
                    };
                    List<Group> list = groups.get(node.id); boolean visible = false;
                    for (Group group : list) visible |= group.visible();
                    yield new ListRecipe(theme.groupedList(), floor, list, visible ? theme.groupedList().bottomPadding64() : 0);
                }
                case "section" -> {
                    Text title = header(node); SectionContext context = sections.get(node.id);
                    if (context == null) context = listAncestor == null ? new OutsideList() : new WithinListRow(listAncestor);
                    boolean grouped = context instanceof ListGroup;
                    yield new SectionRecipe(title, context, !grouped && title != null && !node.children.isEmpty() ? theme.groupedList().headerToGroup64() : 0,
                        grouped ? List.of() : repeated(theme.stacks().defaultGap64(), node.children.size()), HorizontalAlignment.leading);
                }
                case "navigation" -> {
                    String title = node.text("title", "");
                    yield new NavigationRecipe(title.isEmpty() ? null : text(title, Role.navigationExpanded),
                        title.isEmpty() ? null : text(title, Role.headline, false, 1), theme.navigation());
                }
                default -> throw new Failure(Error.unsupportedNativeOperation);
            };
        }
        List<Integer> gaps(UiPacket.Node node) {
            int gap = node.properties.containsKey("spacing") ? AppearanceGeometryV2.spacing64(node.number("spacing", 0)) : theme.stacks().defaultGap64();
            return repeated(gap, node.children.size());
        }
    }
    private static List<Integer> repeated(int value, int childCount) {
        List<Integer> result = new ArrayList<>(Math.max(0, childCount - 1));
        for (int i = 1; i < childCount; i++) result.add(value);
        return result;
    }
    private static Identity identity(UiPacket.Node node) { return new Identity(node.id, node.generation); }
    private static Color rolePaint(RolePaints paints, Role role) {
        return switch (role) {
            case body -> paints.body(); case headline -> paints.headline(); case title -> paints.title();
            case caption -> paints.caption(); case sectionHeader -> paints.sectionHeader(); case navigationExpanded -> paints.navigationExpanded();
        };
    }
    private static void admit(boolean condition, Error error) { if (!condition) throw new Failure(error); }
}
