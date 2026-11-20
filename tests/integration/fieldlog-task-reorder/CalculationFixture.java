package dev.fieldlog.generatedr90.androidhost;

import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

final class CalculationFixture {
    private static final String PACKAGE = "dev.fieldlog.generatedr90.calculation";
    private static final String FIRST = "976F233C-3FFB-440E-BC18-10027556C27B";
    private static final String PREDECESSOR = "D8FD094D-6A4E-4B03-930E-1C4BEE0FB8A7";
    private static final String TARGET = "91094B1F-51E9-42AD-9CF1-64055970E7CB";

    private CalculationFixture() {}

    static boolean enabled(Context context) {
        return PACKAGE.equals(context.getPackageName())
            && (context.getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
    }

    static void stageSeed(Context context) throws IOException {
        try (InputStream seed = context.getAssets().open("ChecklistRelease/calculation-seed.json")) {
            Files.copy(seed, new File(context.getFilesDir(), "calculation-seed.json").toPath(),
                StandardCopyOption.REPLACE_EXISTING);
        }
    }

    static void render(Context context, JSONObject frame, LinearLayout destination, Button action) throws JSONException {
        JSONObject root = frame.getJSONObject("root");
        require(frame.getInt("schemaVersion") == 1);
        long revision = frame.getLong("revision");
        emptyStack(root, "fieldlog-rows");
        JSONArray children = root.getJSONArray("children");
        boolean reviewed = children.length() == 4;
        require(reviewed || children.length() == 3);
        require(revision == 1 || (reviewed && revision == 2));
        if (reviewed) require("Reorder tasks".equals(text(children.getJSONObject(0), "heading", false)));

        List<String> order = new ArrayList<>(3);
        for (int i = 0; i < 3; i++) {
            JSONObject row = children.getJSONObject(i + (reviewed ? 1 : 0));
            String rowID = row.getString("id");
            require(rowID.startsWith("row-"));
            order.add(rowID.substring(4));
        }
        List<String> original = List.of(FIRST, PREDECESSOR, TARGET);
        List<String> moved = List.of(FIRST, TARGET, PREDECESSOR);
        require((revision == 1 && order.equals(original)) || order.equals(moved));

        for (int i = 0; i < order.size(); i++) {
            String task = order.get(i);
            JSONObject row = children.getJSONObject(i + (reviewed ? 1 : 0));
            emptyStack(row, "row-" + task);
            JSONArray cells = row.getJSONArray("children");
            boolean canMove = reviewed && revision == 1 && order.equals(original) && TARGET.equals(task);
            require(cells.length() == (canMove ? 2 : 1));
            String title = text(cells.getJSONObject(0), "title-" + task, true);
            TextView label = new TextView(context);
            label.setText(title);
            label.setTextSize(18);
            destination.addView(label);
            if (canMove) {
                JSONObject node = cells.getJSONObject(1);
                JSONObject props = node.getJSONObject("properties");
                JSONArray commands = node.getJSONArray("actions");
                String labelText = "Move up: " + title;
                require("toggle".equals(node.getString("id")) && "button".equals(node.getString("kind"))
                    && props.length() == 2 && ("move-" + task).equals(props.getString("accessibilityIdentifier"))
                    && labelText.equals(props.getString("label"))
                    && node.getJSONArray("children").length() == 0 && commands.length() == 1);
                JSONObject command = commands.getJSONObject(0);
                require("draft.action".equals(command.getString("id")) && "activate".equals(command.getString("event")));
                action.setText(labelText);
                action.setTag("move-" + task);
                destination.addView(action);
            }
        }
    }

    private static void emptyStack(JSONObject node, String id) throws JSONException {
        require(id.equals(node.getString("id")) && "vStack".equals(node.getString("kind"))
            && node.getJSONObject("properties").length() == 0 && node.getJSONArray("actions").length() == 0);
    }

    private static String text(JSONObject node, String id, boolean hasAccessibilityID) throws JSONException {
        JSONObject props = node.getJSONObject("properties");
        require(id.equals(node.getString("id")) && "text".equals(node.getString("kind"))
            && node.getJSONArray("children").length() == 0 && node.getJSONArray("actions").length() == 0
            && props.length() == (hasAccessibilityID ? 2 : 1)
            && (!hasAccessibilityID || id.equals(props.getString("accessibilityIdentifier"))));
        return props.getString("text");
    }

    private static void require(boolean condition) throws JSONException {
        if (!condition) throw new JSONException("Unsupported FieldLog task reorder frame");
    }
}
