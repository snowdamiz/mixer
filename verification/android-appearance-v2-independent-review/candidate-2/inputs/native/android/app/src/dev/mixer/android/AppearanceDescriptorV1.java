package dev.mixer.android;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** Closed immutable appearance data. Decoding grants no native resource, renderer,
 * installation, presentation, health, or release authority. There is no Java default
 * theme: the native bootstrap must eventually supply the same Swift-owned bytes. */
final class AppearanceDescriptorV1 {
    final String id;
    final String platformSpecificReason;
    final Map<String, Object> iOS;
    final Map<String, Object> android;
    final List<Object> resources;

    private AppearanceDescriptorV1(Map<String, Object> root) {
        id = text(root.get("id"));
        resources = list(root.get("resources"));
        if (text(root.get("mode")).equals("shared")) {
            iOS = object(root.get("theme")); android = iOS; platformSpecificReason = null;
        } else {
            iOS = object(root.get("iOS")); android = object(root.get("android"));
            platformSpecificReason = text(root.get("reason"));
        }
    }

    static AppearanceDescriptorV1 decode(byte[] source) {
        require(source != null && source.length > 0 && source.length <= 65536, "descriptor bytes");
        // Admit before copying; external mutation can no longer change the parsed bytes.
        byte[] bytes = source.clone();
        for (byte b : bytes) require(b >= 0, "ASCII descriptor");
        Reader reader = new Reader(bytes);
        Map<String, Object> root = object(reader.value(1));
        reader.take('\n');
        require(reader.cursor == bytes.length, "canonical final newline");
        String mode = choice(root.get("mode"), "shared", "platformSpecific");
        if (mode.equals("shared")) keys(root, "format", "id", "mode", "resources", "theme");
        else keys(root, "format", "id", "mode", "resources", "iOS", "android", "reason");
        require(text(root.get("format")).equals("mixer.native-appearance.1"), "format");
        identifier(root.get("id"));
        Map<String, Map<String, Object>> resourcesByID = resources(root.get("resources"));
        if (mode.equals("shared")) theme(root.get("theme"), resourcesByID);
        else {
            trimmed(root.get("reason"));
            theme(root.get("iOS"), resourcesByID); theme(root.get("android"), resourcesByID);
        }
        return new AppearanceDescriptorV1(root);
    }

    private static Map<String, Map<String, Object>> resources(Object raw) {
        List<Object> values = list(raw); require(values.size() <= 64, "resource count");
        Map<String, Map<String, Object>> byID = new LinkedHashMap<>();
        Set<String> paths = new HashSet<>(); long bytes = 0; int fonts = 0;
        for (Object value : values) {
            Map<String, Object> r = object(value);
            keys(r, "id", "kind", "path", "sha256", "bytes", "provenance", "scale", "locale", "direction");
            String id = identifier(r.get("id"));
            require(byID.put(id, r) == null, "duplicate resource ID");
            String kind = choice(r.get("kind"), "fontSFNT", "iconPNG");
            String path = boundedText(r.get("path"), 1, 256);
            for (int i = 0; i < path.length(); i++) require(idChar(path.charAt(i)) || path.charAt(i) == '/', "path character");
            for (String component : path.split("/", -1)) require(!component.isEmpty() && component.charAt(0) != '.', "path component");
            require(paths.add(path.toLowerCase(Locale.ROOT)), "duplicate folded resource path");
            String digest = boundedText(r.get("sha256"), 64, 64);
            for (int i = 0; i < digest.length(); i++) require(digit(digest.charAt(i)) || digest.charAt(i) >= 'a' && digest.charAt(i) <= 'f', "digest");
            bytes += number(r.get("bytes"), 1, 4194304); require(bytes <= 16777216, "total resource bytes");
            trimmed(r.get("provenance")); number(r.get("scale"), 1, 4);
            String locale = boundedText(r.get("locale"), 1, 64);
            for (int i = 0; i < locale.length(); i++) require(alphanumeric(locale.charAt(i)) || locale.charAt(i) == '-', "locale character");
            for (String part : locale.split("-", -1)) require(!part.isEmpty(), "locale component");
            String direction = choice(r.get("direction"), "neutral", "leftToRight", "rightToLeft");
            if (kind.equals("fontSFNT")) {
                require(++fonts <= 16 && number(r.get("scale"), 1, 4) == 1 && locale.equals("und") && direction.equals("neutral"), "font variant");
            }
        }
        return byID;
    }

    private static void theme(Object raw, Map<String, Map<String, Object>> resources) {
        Map<String, Object> t = object(raw);
        keys(t, "recipe", "light", "dark", "typography", "layout", "controls");
        choice(t.get("recipe"), "sharedCandidate1"); palette(t.get("light")); palette(t.get("dark"));
        Map<String, Object> typography = object(t.get("typography"));
        keys(typography, "font", "body", "headline", "title", "caption");
        Set<Long> weights = new HashSet<>();
        for (String role : Arrays.asList("body", "headline", "title", "caption")) {
            Map<String, Object> metric = object(typography.get(role));
            keys(metric, "size64", "weight", "minimumLineBox64");
            long size = number(metric.get("size64"), 64, 16384);
            require(number(metric.get("minimumLineBox64"), 64, 65536) >= size, "line box");
            weights.add(weight(metric.get("weight")));
        }
        Map<String, Object> font = object(typography.get("font"));
        String kind = choice(font.get("kind"), "systemSans", "bundled");
        if (kind.equals("systemSans")) keys(font, "kind");
        else {
            keys(font, "kind", "faces", "fallback"); choice(font.get("fallback"), "none", "systemSans");
            List<Object> faces = list(font.get("faces")); require(!faces.isEmpty() && faces.size() <= 16, "font face count");
            Set<String> pairs = new HashSet<>(); Set<Long> normals = new HashSet<>();
            for (Object value : faces) {
                Map<String, Object> face = object(value); keys(face, "resourceID", "postScriptName", "weight", "style");
                Map<String, Object> resource = resources.get(identifier(face.get("resourceID")));
                require(resource != null && text(resource.get("kind")).equals("fontSFNT"), "font resource");
                String postscript = boundedText(face.get("postScriptName"), 1, 128);
                for (int i = 0; i < postscript.length(); i++) require(postscript.charAt(i) >= 33 && postscript.charAt(i) <= 126, "PostScript name");
                long weight = weight(face.get("weight")); String style = choice(face.get("style"), "normal", "italic");
                require(pairs.add(weight + ":" + style), "duplicate weight/style");
                if (style.equals("normal")) normals.add(weight);
            }
            require(normals.containsAll(weights), "missing normal weight");
        }
        Map<String, Object> layout = object(t.get("layout"));
        keys(layout, "stackGap64", "vStackAlignment", "hStackAlignment", "zStackAlignment", "list", "sectionHeaderInsets64", "navigation");
        number(layout.get("stackGap64"), 0, 65536);
        choice(layout.get("vStackAlignment"), "leading", "center", "trailing");
        choice(layout.get("hStackAlignment"), "top", "center", "bottom", "firstTextBaseline", "lastTextBaseline");
        choice(layout.get("zStackAlignment"), "center", "leading", "trailing", "top", "bottom", "topLeading", "topTrailing", "bottomLeading", "bottomTrailing");
        Map<String, Object> list = object(layout.get("list"));
        keys(list, "insets64", "minimumRow64", "rowGap64", "groupGap64", "separator64"); insets(list.get("insets64"));
        metrics(list, "minimumRow64", "rowGap64", "groupGap64", "separator64"); insets(layout.get("sectionHeaderInsets64"));
        Map<String, Object> navigation = object(layout.get("navigation"));
        keys(navigation, "titleInsets64", "minimumBarHeight64", "titleAlignment"); insets(navigation.get("titleInsets64"));
        number(navigation.get("minimumBarHeight64"), 0, 65536); choice(navigation.get("titleAlignment"), "leading", "center", "trailing");
        Map<String, Object> controls = object(t.get("controls"));
        keys(controls, "button", "field", "toggle", "focusWidth64", "focusRadius64", "pressedOpacityPermille", "selectionOpacityPermille");
        metrics(controls, "focusWidth64", "focusRadius64"); number(controls.get("pressedOpacityPermille"), 0, 1000); number(controls.get("selectionOpacityPermille"), 0, 1000);
        Map<String, Object> button = object(controls.get("button"));
        keys(button, "labelInsets64", "minimumWidth64", "minimumHeight64", "radius64"); insets(button.get("labelInsets64")); metrics(button, "minimumWidth64", "minimumHeight64", "radius64");
        Map<String, Object> field = object(controls.get("field"));
        keys(field, "insets64", "minimumHeight64", "border64"); insets(field.get("insets64")); metrics(field, "minimumHeight64", "border64");
        Map<String, Object> toggle = object(controls.get("toggle"));
        keys(toggle, "trackWidth64", "trackHeight64", "thumb64", "inset64", "labelGap64", "minimumRow64");
        metrics(toggle, "trackWidth64", "trackHeight64", "thumb64", "inset64", "labelGap64", "minimumRow64");
        long envelope = number(toggle.get("thumb64"), 0, 65536) + 2 * number(toggle.get("inset64"), 0, 65536);
        require(envelope <= number(toggle.get("trackWidth64"), 0, 65536) && envelope <= number(toggle.get("trackHeight64"), 0, 65536), "toggle envelope");
        require(number(toggle.get("minimumRow64"), 0, 65536) >= number(toggle.get("trackHeight64"), 0, 65536), "toggle row");
    }

    private static void palette(Object raw) {
        Map<String, Object> palette = object(raw);
        keys(palette, "canvas", "surface", "primaryText", "secondaryText", "accent", "destructive", "disabledText", "separator", "focus", "toggleOff", "toggleThumb");
        for (Object color : palette.values()) {
            String s = boundedText(color, 9, 9); require(s.charAt(0) == '#', "color prefix");
            for (int i = 1; i < s.length(); i++) require(digit(s.charAt(i)) || s.charAt(i) >= 'A' && s.charAt(i) <= 'F', "RGBA8 color");
        }
    }
    private static void insets(Object raw) {
        Map<String, Object> value = object(raw); keys(value, "top", "leading", "bottom", "trailing"); metrics(value, "top", "leading", "bottom", "trailing");
    }
    private static void metrics(Map<String, Object> value, String... names) { for (String name : names) number(value.get(name), 0, 65536); }
    private static long weight(Object value) { long n = number(value, 400, 700); require(n % 100 == 0, "weight"); return n; }
    private static String trimmed(Object value) { String s = boundedText(value, 1, 512); require(s.charAt(0) != ' ' && s.charAt(s.length() - 1) != ' ', "trimmed text"); return s; }
    private static String identifier(Object value) {
        String s = boundedText(value, 1, 128); for (int i = 0; i < s.length(); i++) require(idChar(s.charAt(i)), "identifier"); return s;
    }
    private static boolean digit(char c) { return c >= '0' && c <= '9'; }
    private static boolean alphanumeric(char c) { return digit(c) || c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z'; }
    private static boolean idChar(char c) { return alphanumeric(c) || c == '_' || c == '.' || c == '-'; }
    private static String boundedText(Object value, int low, int high) {
        String s = text(value); require(s.length() >= low && s.length() <= high, "string bound");
        for (int i = 0; i < s.length(); i++) require(s.charAt(i) >= 32 && s.charAt(i) <= 126, "printable ASCII"); return s;
    }
    private static String choice(Object value, String... choices) { String s = text(value); require(Arrays.asList(choices).contains(s), "enum"); return s; }
    private static String text(Object value) { require(value instanceof String, "string"); return (String)value; }
    private static long number(Object value, long low, long high) { require(value instanceof Long, "integer"); long n = (Long)value; require(n >= low && n <= high, "integer range"); return n; }
    @SuppressWarnings("unchecked") private static Map<String, Object> object(Object value) { require(value instanceof Map, "object"); return (Map<String, Object>)value; }
    @SuppressWarnings("unchecked") private static List<Object> list(Object value) { require(value instanceof List, "array"); return (List<Object>)value; }
    private static void keys(Map<String, Object> value, String... names) { require(value.keySet().equals(new HashSet<>(Arrays.asList(names))), "closed fields"); }
    private static void require(boolean value, String reason) { if (!value) throw new IllegalArgumentException(reason); }

    /** Canonical grammar is enforced while reading, before a schema graph exists.
     * Keys are ASCII sorted and unique, integers have no alternate spellings, only
     * quote/backslash escapes are canonical for the printable string domain. */
    private static final class Reader {
        final byte[] bytes; int cursor; int values;
        Reader(byte[] bytes) { this.bytes = bytes; }
        int peek() { require(cursor < bytes.length, "truncated JSON"); return bytes[cursor]; }
        void take(int expected) { require(peek() == expected, "canonical JSON"); cursor++; }
        Object value(int depth) {
            require(depth <= 16 && ++values <= 4096, "JSON construction bounds"); int next = peek();
            if (next == '{') {
                cursor++; Map<String, Object> map = new LinkedHashMap<>(); String prior = null;
                if (peek() == '}') { cursor++; return Collections.unmodifiableMap(map); }
                while (true) {
                    String key = string(); require(prior == null || prior.compareTo(key) < 0, "sorted unique keys"); prior = key; take(':');
                    Object child = value(depth + 1); map.put(key, child);
                    if (peek() == '}') { cursor++; return Collections.unmodifiableMap(map); } take(',');
                }
            }
            if (next == '[') {
                cursor++; List<Object> list = new ArrayList<>();
                if (peek() == ']') { cursor++; return Collections.unmodifiableList(list); }
                while (true) {
                    require(list.size() < 64, "array bound"); Object child = value(depth + 1); list.add(child);
                    if (peek() == ']') { cursor++; return Collections.unmodifiableList(list); } take(',');
                }
            }
            if (next == '"') return string();
            require(next >= '0' && next <= '9', "unsigned integer"); long n = 0; int start = cursor;
            while (cursor < bytes.length && digit((char)bytes[cursor])) {
                require(cursor == start || bytes[start] != '0', "leading zero");
                int digit = bytes[cursor++] - '0'; require(n <= (Long.MAX_VALUE - digit) / 10, "integer overflow"); n = n * 10 + digit;
            }
            return n;
        }
        String string() {
            take('"'); StringBuilder out = new StringBuilder();
            while (true) {
                int c = peek(); cursor++; if (c == '"') return out.toString();
                require(out.length() < 512 && c >= 32 && c <= 126, "string bounds");
                if (c == '\\') { c = peek(); cursor++; require(c == '"' || c == '\\', "noncanonical escape"); }
                out.append((char)c);
            }
        }
    }
}
