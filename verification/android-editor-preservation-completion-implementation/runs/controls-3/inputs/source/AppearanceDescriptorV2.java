package dev.mixer.android;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** Immutable untrusted measuredShared2 data. No default theme, native support,
 * resource loading, display health, signed authority, or release qualification. */
final class AppearanceDescriptorV2 {
    static final String FORMAT = "mixer.native-appearance.2";
    final String id;
    final Mode mode;
    final Theme iOS;
    final Theme android;
    final String platformSpecificReason;
    final List<Resource> resources;

    enum Error { byteLimit, invalidEncoding, syntax, duplicateKey, depthLimit, valueLimit,
        arrayLimit, noncanonical, shape, number, resourceCatalog, fontCatalog,
        unsupportedProfile, geometry, unsupportedNativeOperation, layout, nativeAttachment }
    static final class Failure extends IllegalArgumentException {
        private static final long serialVersionUID = 1L;
        final Error code;
        Failure(Error code) { super(code.name()); this.code = code; }
    }
    enum Mode { shared, platformSpecific }
    enum Recipe { measuredShared2 }
    enum PreferencePolicy { nearestBody64TiesUpRejectOutside }
    enum MissingVStackGap { bodyThenCaptionPairOtherwiseDefault }
    enum RowPolicy { maxProfileFloorSemanticContentPlusInsets }
    enum SeparatorPolicy { interiorRowsOnly }
    enum CheckedEnd { logicalTrailing }
    enum Collapse { snapAtExpandedOverflow }
    enum TitleWrap { growExpandedEllipsizeCompactOneLine }
    enum HorizontalAlignment { leading, center, trailing }
    enum VerticalAlignment { top, center, bottom, firstTextBaseline, lastTextBaseline }
    enum OverlayAlignment { center, leading, trailing, top, bottom, topLeading, topTrailing, bottomLeading, bottomTrailing }
    enum Role { body, headline, title, caption, sectionHeader, navigationExpanded }
    enum Profile { xs, s, m, l, xl, xxl, xxxl, a1, a2, a3, a4, a5 }
    enum FontKind { systemSans, bundled }
    enum FontFallback { none, systemSans }
    enum FontStyle { normal, italic }
    enum ResourceKind { fontSFNT, iconPNG }
    enum Direction { neutral, leftToRight, rightToLeft }
    enum Weight {
        w400(400), w500(500), w600(600), w700(700);
        final int value;
        Weight(int value) { this.value = value; }
    }
    record Color(int red, int green, int blue, int alpha) {}
    record Insets(int top, int leading, int bottom, int trailing) {}
    record Resource(String id, ResourceKind kind, String path, String sha256, int bytes,
                    String provenance, int scale, String locale, Direction direction) {}
    record FontFace(String resourceID, String postScriptName, Weight weight, FontStyle style) {}
    sealed interface Font permits SystemSans, Bundled {}
    record SystemSans() implements Font {}
    record Bundled(List<FontFace> faces, FontFallback fallback) implements Font {
        Bundled { faces = List.copyOf(faces); }
    }
    record Metric(int size64, Weight weight) {}
    record Roles(Metric body, Metric headline, Metric title, Metric caption,
                 Metric sectionHeader, Metric navigationExpanded) {}
    record Profiles(Roles xs, Roles s, Roles m, Roles l, Roles xl, Roles xxl,
                    Roles xxxl, Roles a1, Roles a2, Roles a3, Roles a4, Roles a5) {}
    record Floors(int xs, int s, int m, int l, int xl, int xxl,
                  int xxxl, int a1, int a2, int a3, int a4, int a5) {}
    record Typography(Font font, Profiles profiles, Profile defaultProfile, PreferencePolicy preferencePolicy) {}
    record RolePaints(Color body, Color headline, Color title, Color caption,
                      Color sectionHeader, Color navigationExpanded) {}
    record Outline(Color color, int width64, int radius64) {}
    record ButtonPaint(Color label, Color background) {}
    record ButtonStates(ButtonPaint enabled, ButtonPaint pressed, ButtonPaint disabled, Outline focus) {}
    record ButtonRoles(ButtonStates normal, ButtonStates destructive, ButtonStates cancel) {}
    record FieldPaint(Color text, Color placeholder, Color background, Color caret, Color selection, Outline outline) {}
    record FieldStates(FieldPaint enabled, FieldPaint focused, FieldPaint disabled) {}
    record TogglePaint(Color label, Color track, Color thumb, Color overlay) {}
    record ToggleStates(TogglePaint enabled, TogglePaint pressed, TogglePaint disabled, Outline focus) {}
    record ToggleValues(ToggleStates on, ToggleStates off) {}
    record Paints(Color canvas, Color surface, Color separator, RolePaints text,
                  ButtonRoles button, FieldStates field, ToggleValues toggle) {}
    record Stacks(int defaultGap64, int bodyCaptionGap64, MissingVStackGap missingVStackGap,
                  HorizontalAlignment vStackAlignment, VerticalAlignment hStackAlignment, OverlayAlignment zStackAlignment) {}
    record GroupedList(int outerHorizontal64, Insets contentInsets64, int topPadding64, int bottomPadding64,
                       int headerToGroup64, int groupToNextHeader64, int groupWithoutHeaderGap64,
                       Floors profileFloors64, int separatorInset64, int separatorThickness64,
                       AppearanceGeometryV2.Shape outline, int radius64, RowPolicy rowPolicy, SeparatorPolicy separatorPolicy) {}
    record ButtonMetrics(Insets labelInsets64, int minimumHitWidth64, int minimumHitHeight64, int overlayRadius64) {}
    record FieldMetrics(Insets insets64, int minimumContentHeight64, int minimumHitHeight64) {}
    record ToggleMetrics(AppearanceGeometryV2.Shape track, AppearanceGeometryV2.Shape thumb,
                         int trackWidth64, int trackHeight64, int thumbWidth64, int thumbHeight64,
                         int trackAuthoringRadius64, int thumbAuthoringRadius64, int thumbInset64,
                         int labelGap64, int minimumHitWidth64, int minimumHitHeight64, CheckedEnd checkedEnd) {}
    record Navigation(Role expandedRole, Role compactRole, HorizontalAlignment expandedAlignment,
                      HorizontalAlignment compactAlignment, Insets expandedInsets64, Insets compactInsets64,
                      int minimumExpandedBar64, int minimumCompactBar64, Collapse collapse, TitleWrap titleWrap) {}
    record Theme(Recipe recipe, Typography typography, Paints light, Paints dark, Stacks stacks,
                 GroupedList groupedList, ButtonMetrics button, FieldMetrics field,
                 ToggleMetrics toggle, Navigation navigation) {}

    private AppearanceDescriptorV2(String id, Mode mode, Theme iOS, Theme android,
                                   String reason, List<Resource> resources) {
        this.id = id; this.mode = mode; this.iOS = iOS; this.android = android;
        this.platformSpecificReason = reason; this.resources = List.copyOf(resources);
    }

    static AppearanceDescriptorV2 decode(byte[] source) {
        admit(source != null && source.length >= 1 && source.length <= 65536, Error.byteLimit);
        // Admission precedes copying; no raw input or raw JSON graph escapes this method.
        byte[] bytes = source.clone();
        for (byte b : bytes) admit(b >= 0, Error.invalidEncoding);
        Reader reader = new Reader(bytes);
        Map<String, Object> root = object(reader.value(1));
        reader.take(10, Error.noncanonical);
        admit(reader.cursor == bytes.length, Error.noncanonical);
        Mode mode = enumeration(root.get("mode"), Mode.class);
        if (mode == Mode.shared) keys(root, "format", "id", "mode", "resources", "theme");
        else keys(root, "format", "id", "mode", "resources", "iOS", "android", "reason");
        constant(root.get("format"), FORMAT);
        String id = identifier(root.get("id"));
        List<Resource> resources = resources(root.get("resources"));
        Theme ios, android; String reason = null;
        if (mode == Mode.shared) { ios = theme(root.get("theme")); android = ios; }
        else {
            ios = theme(root.get("iOS")); android = theme(root.get("android"));
            reason = trimmed(root.get("reason"), Error.shape);
        }
        semantics(ios, resources);
        if (mode == Mode.platformSpecific) semantics(android, resources);
        return new AppearanceDescriptorV2(id, mode, ios, android, reason, resources);
    }

    private static List<Resource> resources(Object raw) {
        List<Object> items = array(raw, 0, 64); List<Resource> resources = new ArrayList<>();
        Set<String> ids = new HashSet<>(), paths = new HashSet<>(); long total = 0; int fonts = 0;
        for (Object item : items) {
            Map<String, Object> r = object(item);
            keys(r, "id", "kind", "path", "sha256", "bytes", "provenance", "scale", "locale", "direction");
            String id = identifier(r.get("id"));
            ResourceKind kind = enumeration(r.get("kind"), ResourceKind.class);
            String path = bounded(r.get("path"), 1, 256);
            boolean first = true;
            for (int i = 0; i < path.length(); i++) {
                char c = path.charAt(i); admit(idChar(c) || c == '/', Error.shape);
                if (c == '/') { admit(!first, Error.shape); first = true; }
                else { admit(!first || c != '.', Error.shape); first = false; }
            }
            admit(!first, Error.shape);
            String sha = bounded(r.get("sha256"), 64, 64);
            for (int i = 0; i < sha.length(); i++) admit(digit(sha.charAt(i)) || sha.charAt(i) >= 'a' && sha.charAt(i) <= 'f', Error.shape);
            int bytes = number(r.get("bytes"), 1, 4194304);
            String provenance = trimmed(r.get("provenance"), Error.resourceCatalog);
            int scale = number(r.get("scale"), 1, 4);
            String locale = bounded(r.get("locale"), 1, 64); first = true;
            for (int i = 0; i < locale.length(); i++) {
                char c = locale.charAt(i); admit(alphanumeric(c) || c == '-', Error.shape);
                if (c == '-') { admit(!first, Error.shape); first = true; } else first = false;
            }
            admit(!first, Error.shape);
            Direction direction = enumeration(r.get("direction"), Direction.class);
            admit(ids.add(id) && paths.add(path.toLowerCase(Locale.ROOT)), Error.resourceCatalog);
            total += bytes; admit(total <= 16777216, Error.resourceCatalog);
            if (kind == ResourceKind.fontSFNT) {
                admit(++fonts <= 16 && scale == 1 && locale.equals("und") && direction == Direction.neutral, Error.fontCatalog);
            }
            resources.add(new Resource(id, kind, path, sha, bytes, provenance, scale, locale, direction));
        }
        return List.copyOf(resources);
    }

    private static Theme theme(Object raw) {
        Map<String, Object> t = object(raw);
        keys(t, "recipe", "typography", "light", "dark", "stacks", "groupedList", "button", "field", "toggle", "navigation");
        return new Theme(enumeration(t.get("recipe"), Recipe.class), typography(t.get("typography")),
            paints(t.get("light")), paints(t.get("dark")), stacks(t.get("stacks")), grouped(t.get("groupedList")),
            buttonMetrics(t.get("button")), fieldMetrics(t.get("field")), toggleMetrics(t.get("toggle")), navigation(t.get("navigation")));
    }
    private static Typography typography(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "font", "profiles", "defaultProfile", "preferencePolicy");
        return new Typography(font(f.get("font")), profiles(f.get("profiles")), enumeration(f.get("defaultProfile"), Profile.class),
            enumeration(f.get("preferencePolicy"), PreferencePolicy.class));
    }
    private static Font font(Object raw) {
        Map<String, Object> f = object(raw); FontKind kind = enumeration(f.get("kind"), FontKind.class);
        if (kind == FontKind.systemSans) { keys(f, "kind"); return new SystemSans(); }
        keys(f, "kind", "faces", "fallback"); List<FontFace> faces = new ArrayList<>();
        for (Object item : array(f.get("faces"), 1, 16)) {
            Map<String, Object> face = object(item); keys(face, "resourceID", "postScriptName", "weight", "style");
            String postscript = bounded(face.get("postScriptName"), 1, 128);
            admit(postscript.indexOf(' ') < 0, Error.shape);
            faces.add(new FontFace(identifier(face.get("resourceID")), postscript, weight(face.get("weight")), enumeration(face.get("style"), FontStyle.class)));
        }
        return new Bundled(faces, enumeration(f.get("fallback"), FontFallback.class));
    }
    private static Profiles profiles(Object raw) {
        Map<String, Object> f = object(raw); profileKeys(f);
        return new Profiles(roles(f.get("xs")), roles(f.get("s")), roles(f.get("m")), roles(f.get("l")),
            roles(f.get("xl")), roles(f.get("xxl")), roles(f.get("xxxl")), roles(f.get("a1")),
            roles(f.get("a2")), roles(f.get("a3")), roles(f.get("a4")), roles(f.get("a5")));
    }
    private static Roles roles(Object raw) {
        Map<String, Object> f = object(raw); roleKeys(f);
        return new Roles(metric(f.get("body")), metric(f.get("headline")), metric(f.get("title")), metric(f.get("caption")),
            metric(f.get("sectionHeader")), metric(f.get("navigationExpanded")));
    }
    private static Metric metric(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "size64", "weight");
        return new Metric(number(f.get("size64"), 64, 16384), weight(f.get("weight")));
    }
    private static Floors floors(Object raw) {
        Map<String, Object> f = object(raw); profileKeys(f);
        return new Floors(positive(f,"xs"), positive(f,"s"), positive(f,"m"), positive(f,"l"),
            positive(f,"xl"), positive(f,"xxl"), positive(f,"xxxl"), positive(f,"a1"), positive(f,"a2"), positive(f,"a3"), positive(f,"a4"), positive(f,"a5"));
    }
    private static Paints paints(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "canvas", "surface", "separator", "text", "button", "field", "toggle");
        Map<String, Object> b = object(f.get("button")); keys(b, "normal", "destructive", "cancel");
        Map<String, Object> v = object(f.get("toggle")); keys(v, "on", "off");
        return new Paints(color(f.get("canvas")), color(f.get("surface")), color(f.get("separator")), rolePaints(f.get("text")),
            new ButtonRoles(buttonStates(b.get("normal")), buttonStates(b.get("destructive")), buttonStates(b.get("cancel"))),
            fieldStates(f.get("field")), new ToggleValues(toggleStates(v.get("on")), toggleStates(v.get("off"))));
    }
    private static RolePaints rolePaints(Object raw) {
        Map<String, Object> f = object(raw); roleKeys(f);
        return new RolePaints(color(f.get("body")), color(f.get("headline")), color(f.get("title")), color(f.get("caption")),
            color(f.get("sectionHeader")), color(f.get("navigationExpanded")));
    }
    private static Outline outline(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "color", "width64", "radius64");
        return new Outline(color(f.get("color")), scalar(f,"width64"), scalar(f,"radius64"));
    }
    private static ButtonPaint buttonPaint(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "label", "background");
        return new ButtonPaint(color(f.get("label")), color(f.get("background")));
    }
    private static ButtonStates buttonStates(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "enabled", "pressed", "disabled", "focus");
        return new ButtonStates(buttonPaint(f.get("enabled")), buttonPaint(f.get("pressed")), buttonPaint(f.get("disabled")), outline(f.get("focus")));
    }
    private static FieldPaint fieldPaint(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "text", "placeholder", "background", "caret", "selection", "outline");
        return new FieldPaint(color(f.get("text")), color(f.get("placeholder")), color(f.get("background")), color(f.get("caret")),
            color(f.get("selection")), outline(f.get("outline")));
    }
    private static FieldStates fieldStates(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "enabled", "focused", "disabled");
        return new FieldStates(fieldPaint(f.get("enabled")), fieldPaint(f.get("focused")), fieldPaint(f.get("disabled")));
    }
    private static TogglePaint togglePaint(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "label", "track", "thumb", "overlay");
        return new TogglePaint(color(f.get("label")), color(f.get("track")), color(f.get("thumb")), color(f.get("overlay")));
    }
    private static ToggleStates toggleStates(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "enabled", "pressed", "disabled", "focus");
        return new ToggleStates(togglePaint(f.get("enabled")), togglePaint(f.get("pressed")), togglePaint(f.get("disabled")), outline(f.get("focus")));
    }
    private static Stacks stacks(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "defaultGap64", "bodyCaptionGap64", "missingVStackGap", "vStackAlignment", "hStackAlignment", "zStackAlignment");
        return new Stacks(scalar(f,"defaultGap64"), scalar(f,"bodyCaptionGap64"), enumeration(f.get("missingVStackGap"), MissingVStackGap.class),
            enumeration(f.get("vStackAlignment"), HorizontalAlignment.class), enumeration(f.get("hStackAlignment"), VerticalAlignment.class),
            enumeration(f.get("zStackAlignment"), OverlayAlignment.class));
    }
    private static GroupedList grouped(Object raw) {
        Map<String, Object> f = object(raw);
        keys(f, "outerHorizontal64", "contentInsets64", "topPadding64", "bottomPadding64", "headerToGroup64", "groupToNextHeader64",
            "groupWithoutHeaderGap64", "profileFloors64", "separatorInset64", "separatorThickness64", "outline", "radius64", "rowPolicy", "separatorPolicy");
        constant(f.get("outline"), "fullGroupContinuousCubic2");
        return new GroupedList(scalar(f,"outerHorizontal64"), insets(f.get("contentInsets64")), scalar(f,"topPadding64"), scalar(f,"bottomPadding64"),
            scalar(f,"headerToGroup64"), scalar(f,"groupToNextHeader64"), scalar(f,"groupWithoutHeaderGap64"), floors(f.get("profileFloors64")),
            scalar(f,"separatorInset64"), scalar(f,"separatorThickness64"), AppearanceGeometryV2.Shape.fullGroupContinuousCubic2,
            scalar(f,"radius64"), enumeration(f.get("rowPolicy"), RowPolicy.class), enumeration(f.get("separatorPolicy"), SeparatorPolicy.class));
    }
    private static ButtonMetrics buttonMetrics(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "labelInsets64", "minimumHitWidth64", "minimumHitHeight64", "overlayRadius64");
        return new ButtonMetrics(insets(f.get("labelInsets64")), positive(f,"minimumHitWidth64"), positive(f,"minimumHitHeight64"), scalar(f,"overlayRadius64"));
    }
    private static FieldMetrics fieldMetrics(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "insets64", "minimumContentHeight64", "minimumHitHeight64");
        return new FieldMetrics(insets(f.get("insets64")), positive(f,"minimumContentHeight64"), positive(f,"minimumHitHeight64"));
    }
    private static ToggleMetrics toggleMetrics(Object raw) {
        Map<String, Object> f = object(raw);
        keys(f, "track", "thumb", "trackWidth64", "trackHeight64", "thumbWidth64", "thumbHeight64", "trackAuthoringRadius64",
            "thumbAuthoringRadius64", "thumbInset64", "labelGap64", "minimumHitWidth64", "minimumHitHeight64", "checkedEnd");
        constant(f.get("track"), "track63x28Continuous2"); constant(f.get("thumb"), "thumb37x24Continuous2");
        return new ToggleMetrics(AppearanceGeometryV2.Shape.track63x28Continuous2, AppearanceGeometryV2.Shape.thumb37x24Continuous2,
            fixed(f,"trackWidth64",4032), fixed(f,"trackHeight64",1792), fixed(f,"thumbWidth64",2368), fixed(f,"thumbHeight64",1536),
            fixed(f,"trackAuthoringRadius64",896), fixed(f,"thumbAuthoringRadius64",768), fixed(f,"thumbInset64",128),
            scalar(f,"labelGap64"), positive(f,"minimumHitWidth64"), positive(f,"minimumHitHeight64"), enumeration(f.get("checkedEnd"), CheckedEnd.class));
    }
    private static Navigation navigation(Object raw) {
        Map<String, Object> f = object(raw);
        keys(f, "expandedRole", "compactRole", "expandedAlignment", "compactAlignment", "expandedInsets64", "compactInsets64",
            "minimumExpandedBar64", "minimumCompactBar64", "collapse", "titleWrap");
        constant(f.get("expandedRole"), "navigationExpanded"); constant(f.get("compactRole"), "headline");
        constant(f.get("expandedAlignment"), "leading"); constant(f.get("compactAlignment"), "center");
        return new Navigation(Role.navigationExpanded, Role.headline, HorizontalAlignment.leading, HorizontalAlignment.center,
            insets(f.get("expandedInsets64")), insets(f.get("compactInsets64")), positive(f,"minimumExpandedBar64"), positive(f,"minimumCompactBar64"),
            enumeration(f.get("collapse"), Collapse.class), enumeration(f.get("titleWrap"), TitleWrap.class));
    }
    private static Insets insets(Object raw) {
        Map<String, Object> f = object(raw); keys(f, "top", "leading", "bottom", "trailing");
        return new Insets(scalar(f,"top"), scalar(f,"leading"), scalar(f,"bottom"), scalar(f,"trailing"));
    }
    private static Color color(Object raw) {
        String value = bounded(raw, 9, 9); admit(value.charAt(0) == '#', Error.shape);
        for (int i = 1; i < 9; i++) admit(digit(value.charAt(i)) || value.charAt(i) >= 'A' && value.charAt(i) <= 'F', Error.shape);
        return new Color(hex(value,1), hex(value,3), hex(value,5), hex(value,7));
    }
    private static int hex(String value, int start) { return Integer.parseInt(value.substring(start,start + 2), 16); }

    private static void semantics(Theme t, List<Resource> resources) {
        // This table is the closed recipe's admissible profile family, never a
        // substitute/default theme. Every decoded metric is retained and compared.
        int[][] family = {{14,25,11,31},{15,26,11,32},{16,27,11,33},{17,28,12,34},
            {19,30,14,36},{21,32,16,38},{23,34,18,40},{28,38,22,44},
            {33,43,26,48},{40,48,32,52},{47,53,37,56},{53,58,43,60}};
        Profiles p = t.typography.profiles;
        Roles[] rows = {p.xs,p.s,p.m,p.l,p.xl,p.xxl,p.xxxl,p.a1,p.a2,p.a3,p.a4,p.a5};
        for (int i = 0; i < rows.length; i++) {
            Roles r = rows[i]; int[] f = family[i];
            metricIs(r.body,f[0],Weight.w400); metricIs(r.headline,f[0],Weight.w600);
            metricIs(r.title,f[1],Weight.w400); metricIs(r.caption,f[2],Weight.w400);
            metricIs(r.sectionHeader,f[0],Weight.w600); metricIs(r.navigationExpanded,f[3],Weight.w700);
        }
        if (t.typography.font instanceof Bundled b) {
            Map<String,Resource> byID = new HashMap<>(); for (Resource r : resources) byID.put(r.id,r);
            Set<String> pairs = new HashSet<>(); Set<Weight> normals = new HashSet<>();
            for (FontFace f : b.faces) {
                Resource r = byID.get(f.resourceID);
                admit(pairs.add(f.weight.name() + ":" + f.style.name()) && r != null && r.kind == ResourceKind.fontSFNT, Error.fontCatalog);
                if (f.style == FontStyle.normal) normals.add(f.weight);
            }
            admit(normals.containsAll(List.of(Weight.w400,Weight.w600,Weight.w700)), Error.fontCatalog);
            for (FontFace f : b.faces) admit(normals.contains(f.weight), Error.fontCatalog);
        }
        Floors f = t.groupedList.profileFloors64;
        int[] floors = {f.xs,f.s,f.m,f.l,f.xl,f.xxl,f.xxxl,f.a1,f.a2,f.a3,f.a4,f.a5};
        for (int i = 0; i < floors.length; i++) admit(floors[i] >= t.toggle.trackHeight64 && (i == 0 || floors[i] >= floors[i - 1]), Error.geometry);
        admit(t.navigation.minimumExpandedBar64 >= t.navigation.minimumCompactBar64, Error.geometry);
        admit((long)t.toggle.thumbWidth64 + 2L * t.toggle.thumbInset64 <= t.toggle.trackWidth64 &&
            (long)t.toggle.thumbHeight64 + 2L * t.toggle.thumbInset64 == t.toggle.trackHeight64, Error.geometry);
        Color clear = new Color(0,0,0,0);
        for (Paints paint : List.of(t.light,t.dark)) {
            for (ButtonStates button : List.of(paint.button.normal,paint.button.destructive,paint.button.cancel)) admit(button.disabled.background.equals(clear), Error.shape);
            admit(paint.field.disabled.caret.equals(clear) && paint.field.disabled.selection.equals(clear) &&
                paint.field.enabled.outline.width64 == 0 && paint.field.disabled.outline.width64 == 0 &&
                paint.toggle.on.disabled.overlay.equals(clear) && paint.toggle.off.disabled.overlay.equals(clear), Error.shape);
        }
    }
    private static void metricIs(Metric m, int units, Weight weight) { admit(m.size64 == units * 64 && m.weight == weight, Error.unsupportedProfile); }
    private static void profileKeys(Map<String,Object> f) { keys(f,"xs","s","m","l","xl","xxl","xxxl","a1","a2","a3","a4","a5"); }
    private static void roleKeys(Map<String,Object> f) { keys(f,"body","headline","title","caption","sectionHeader","navigationExpanded"); }
    private static int scalar(Map<String,Object> f, String key) { return number(f.get(key),0,65536); }
    private static int positive(Map<String,Object> f, String key) { return number(f.get(key),1,65536); }
    private static int fixed(Map<String,Object> f, String key, int expected) { int value = scalar(f,key); admit(value == expected, Error.shape); return value; }
    private static Weight weight(Object raw) {
        int value = number(raw,400,700); for (Weight w : Weight.values()) if (w.value == value) return w;
        throw new Failure(Error.number);
    }
    private static int number(Object raw, int low, int high) {
        admit(raw instanceof Long, Error.shape); long n = (Long)raw;
        admit(n >= low && n <= high, Error.number); return (int)n;
    }
    private static String text(Object raw) { admit(raw instanceof String, Error.shape); return (String)raw; }
    private static String bounded(Object raw, int low, int high) {
        String value = text(raw); admit(value.length() >= low && value.length() <= high, Error.shape);
        for (int i = 0; i < value.length(); i++) admit(value.charAt(i) >= 32 && value.charAt(i) <= 126, Error.shape);
        return value;
    }
    private static String trimmed(Object raw, Error error) {
        String value = bounded(raw,1,512); admit(value.charAt(0) != ' ' && value.charAt(value.length() - 1) != ' ', error); return value;
    }
    private static String identifier(Object raw) {
        String value = bounded(raw,1,128); for (int i = 0; i < value.length(); i++) admit(idChar(value.charAt(i)), Error.shape); return value;
    }
    private static boolean digit(char c) { return c >= '0' && c <= '9'; }
    private static boolean alphanumeric(char c) { return digit(c) || c >= 'A' && c <= 'Z' || c >= 'a' && c <= 'z'; }
    private static boolean idChar(char c) { return alphanumeric(c) || c == '_' || c == '.' || c == '-'; }
    private static void constant(Object raw, String expected) { admit(text(raw).equals(expected), Error.shape); }
    private static <T extends Enum<T>> T enumeration(Object raw, Class<T> type) {
        String value = text(raw);
        try { return Enum.valueOf(type,value); } catch (IllegalArgumentException error) { throw new Failure(Error.shape); }
    }
    @SuppressWarnings("unchecked") private static Map<String,Object> object(Object raw) { admit(raw instanceof Map, Error.shape); return (Map<String,Object>)raw; }
    @SuppressWarnings("unchecked") private static List<Object> array(Object raw, int low, int high) {
        admit(raw instanceof List, Error.shape); List<Object> values = (List<Object>)raw;
        admit(values.size() >= low && values.size() <= high, Error.shape); return values;
    }
    private static void keys(Map<String,Object> value, String... names) { admit(value.keySet().equals(new HashSet<>(Arrays.asList(names))), Error.shape); }
    private static void admit(boolean condition, Error code) { if (!condition) throw new Failure(code); }

    /** Bounded streaming canonical grammar. Each value, array slot and container
     * depth is admitted before its child is constructed or retained. All schema
     * strings are printable ASCII, so only quote/backslash escapes are canonical. */
    private static final class Reader {
        private final byte[] bytes;
        private int cursor, values;
        Reader(byte[] bytes) { this.bytes = bytes; }
        private int peek() { admit(cursor < bytes.length, Error.syntax); return bytes[cursor]; }
        private void take(int expected, Error error) { admit(peek() == expected, error); cursor++; }
        private Object value(int depth) {
            admit(values < 8192, Error.valueLimit); values++;
            int next = peek();
            if (next == '{') {
                admit(depth <= 20, Error.depthLimit); cursor++;
                Map<String,Object> map = new LinkedHashMap<>(); String prior = null;
                if (peek() == '}') { cursor++; return map; }
                while (true) {
                    String key = string();
                    admit(!map.containsKey(key), Error.duplicateKey);
                    admit(prior == null || prior.compareTo(key) < 0, Error.noncanonical); prior = key;
                    take(':',Error.syntax); Object child = value(depth + 1); map.put(key,child);
                    if (peek() == '}') { cursor++; return map; } take(',',Error.syntax);
                }
            }
            if (next == '[') {
                admit(depth <= 20, Error.depthLimit); cursor++; List<Object> list = new ArrayList<>();
                if (peek() == ']') { cursor++; return list; }
                while (true) {
                    admit(list.size() < 64, Error.arrayLimit); Object child = value(depth + 1); list.add(child);
                    if (peek() == ']') { cursor++; return list; } take(',',Error.syntax);
                }
            }
            if (next == '"') return string();
            admit(next >= '0' && next <= '9', Error.syntax); long n = 0; int start = cursor;
            while (cursor < bytes.length && digit((char)bytes[cursor])) {
                admit(cursor == start || bytes[start] != '0', Error.number);
                int digit = bytes[cursor++] - '0'; admit(n <= (Long.MAX_VALUE - digit) / 10, Error.number); n = n * 10 + digit;
            }
            return n;
        }
        private String string() {
            take('"',Error.syntax); StringBuilder out = new StringBuilder();
            while (true) {
                int c = peek(); cursor++; if (c == '"') return out.toString();
                admit(out.length() < 512, Error.shape); admit(c >= 32 && c <= 126, Error.syntax);
                if (c == '\\') { c = peek(); cursor++; admit(c == '"' || c == '\\', Error.noncanonical); }
                out.append((char)c);
            }
        }
    }
}
