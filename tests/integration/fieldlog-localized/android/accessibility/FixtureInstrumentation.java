package dev.fieldlog.localizedax;

import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.Activity;
import android.app.Instrumentation;
import android.app.UiAutomation;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.SystemClock;
import android.text.InputType;
import android.text.TextUtils;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityNodeInfo.AccessibilityAction;
import android.view.accessibility.AccessibilityWindowInfo;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.List;

public final class FixtureInstrumentation extends Instrumentation {
    private static final String GUEST = "dev.fieldlog.generatedr90";
    private static final String TITLE = "فحص المضخة 07";
    private static final int MAX_WINDOWS = 32;
    private static final int MAX_NODES = 256;
    private static final int MAX_DEPTH = 24;
    private static final long OBSERVATION_BUDGET_MS = 2500;

    private Bundle arguments;

    @Override
    public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        this.arguments = arguments == null ? Bundle.EMPTY : arguments;
        start();
    }

    @Override
    public void onStart() {
        Bundle result = new Bundle();
        boolean success = false;
        try {
            JSONObject witness = runFixture();
            result.putString("fieldlog_ax", witness.toString());
            success = witness.getBoolean("ok");
        } catch (RuntimeException | JSONException failure) {
            result.putString("fieldlog_ax", "{\"ok\":false,\"status\":\"instrumentation_error\"}");
        }
        finish(success ? Activity.RESULT_OK : Activity.RESULT_CANCELED, result);
    }

    private JSONObject runFixture() throws JSONException {
        String mode = arguments.getString("mode");
        boolean seed = "seed".equals(mode) && arguments.size() == 1;
        Frame frame = "observe".equals(mode) && arguments.size() == 2
            ? Frame.parse(arguments.getString("frame")) : null;
        if (!seed && frame == null) {
            return result(false, "invalid_arguments");
        }
        UiAutomation automation = getUiAutomation(UiAutomation.FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES);
        if (automation == null) {
            return result(false, "automation_unavailable");
        }
        AccessibilityServiceInfo service = automation.getServiceInfo();
        if (service == null) {
            return result(false, "service_unavailable");
        }
        service.packageNames = new String[] { GUEST }; // Event filter; node scope is checked below.
        service.flags |= AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS
            | AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS;
        automation.setServiceInfo(service);

        AccessibilityNodeInfo root = activeGuestRoot(automation);
        if (root == null) {
            return result(false, "guest_window_unavailable");
        }
        return seed ? seed(automation, root) : observe(automation, root, frame);
    }

    private static JSONObject seed(UiAutomation automation, AccessibilityNodeInfo root)
            throws JSONException {
        AccessibilityNodeInfo focused = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT);
        int window = root.getWindowId();
        if (!canSeed(focused, window)) {
            return result(false, "no_eligible_input");
        }
        AccessibilityNodeInfo current = activeGuestRoot(automation);
        if (!root.equals(current)) {
            return result(false, "active_window_changed");
        }
        AccessibilityNodeInfo input = current.findFocus(AccessibilityNodeInfo.FOCUS_INPUT);
        if (!focused.equals(input) || !input.refresh() || !canSeed(input, window)) {
            return result(false, "input_focus_changed");
        }
        Bundle text = new Bundle();
        text.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, TITLE);
        if (!input.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, text)) {
            return result(false, "set_text_rejected");
        }
        boolean verified = input.refresh() && inWindow(input, window) && !isPassword(input)
            && TextUtils.equals(TITLE, input.getText());
        return result(verified, verified ? "seeded" : "set_text_accepted_readback_unavailable");
    }

    private static boolean canSeed(AccessibilityNodeInfo node, int window) {
        return inWindow(node, window) && node.isFocused() && node.isEditable() && node.isEnabled()
            && node.isVisibleToUser() && !isPassword(node)
            && node.getActionList().contains(AccessibilityAction.ACTION_SET_TEXT);
    }

    private static boolean isPassword(AccessibilityNodeInfo node) {
        int inputType = node.getInputType() & (InputType.TYPE_MASK_CLASS | InputType.TYPE_MASK_VARIATION);
        return node.isPassword()
            || inputType == (InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD)
            || inputType == (InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD)
            || inputType == (InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD)
            || inputType == (InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
    }

    private static JSONObject observe(UiAutomation automation, AccessibilityNodeInfo root, Frame frame)
            throws JSONException {
        Observation observation = new Observation(frame, root);
        boolean complete = observation.visit(root, null, 0);
        if (!root.equals(activeGuestRoot(automation))) {
            return result(false, "active_window_changed");
        }
        String status = complete ? observation.status() : "traversal_incomplete";
        JSONObject witness = result("observed".equals(status), status)
            .put("frame", frame.option)
            .put("rootBoundsPx", boundsJson(observation.rootBounds));
        for (int i = 0; i < Observation.ROLES.length; i++) {
            JSONArray matches = observation.matches[i];
            witness.put(Observation.ROLES[i], matches);
        }
        return witness;
    }

    private static final class Observation {
        private static final String[] ROLES = { "title", "statusRow", "button" };

        private final int window;
        private final Rect rootBounds;
        private final String[] expected;
        private final JSONArray[] matches = { new JSONArray(), new JSONArray(), new JSONArray() };
        private final long deadline = SystemClock.uptimeMillis() + OBSERVATION_BUDGET_MS;
        private int visited;

        Observation(Frame frame, AccessibilityNodeInfo root) {
            window = root.getWindowId();
            rootBounds = bounds(root);
            expected = new String[] { TITLE, frame.status, frame.button };
        }

        boolean visit(AccessibilityNodeInfo node, AccessibilityNodeInfo parent, int depth)
                throws JSONException {
            if (node == null) {
                return false;
            }
            visited++;
            if (!inWindow(node, window)) {
                return true;
            }
            if (!node.isEditable() && !isPassword(node)) {
                CharSequence text = node.getText();
                CharSequence description = node.getContentDescription();
                for (int i = 0; i < expected.length; i++) {
                    if (matches[i].length() < 2 && (TextUtils.equals(expected[i], text)
                            || TextUtils.equals(expected[i], description))) {
                        matches[i].put(geometry(node, parent, rootBounds));
                    }
                }
            }
            int childCount = node.getChildCount();
            if (childCount != 0 && depth == MAX_DEPTH) {
                return false;
            }
            for (int i = 0; i < childCount; i++) {
                if (visited == MAX_NODES || SystemClock.uptimeMillis() >= deadline
                        || !visit(node.getChild(i, 0), node, depth + 1)) {
                    return false;
                }
            }
            return true;
        }

        String status() {
            for (JSONArray role : matches) {
                if (role.length() != 1) {
                    return "fixture_rows_missing_or_ambiguous";
                }
            }
            return "observed";
        }
    }

    private static JSONObject geometry(AccessibilityNodeInfo node, AccessibilityNodeInfo parent,
            Rect rootBounds) throws JSONException {
        Rect parentBounds = parent == null ? new Rect() : bounds(parent);
        Rect frame = new Rect();
        boolean hasFrame = frame.setIntersect(parentBounds, rootBounds);
        return new JSONObject()
            .put("boundsPx", boundsJson(bounds(node)))
            .put("parentBoundsPx", parent == null ? JSONObject.NULL : boundsJson(parentBounds))
            .put("parentFramePx", hasFrame ? boundsJson(frame) : JSONObject.NULL)
            .put("visibleToUser", node.isVisibleToUser())
            .put("enabled", node.isEnabled())
            .put("clickable", node.isClickable())
            .put("hasActionClick", node.getActionList().contains(AccessibilityAction.ACTION_CLICK));
    }

    private static Rect bounds(AccessibilityNodeInfo node) {
        Rect result = new Rect();
        node.getBoundsInScreen(result);
        return result;
    }

    private static JSONArray boundsJson(Rect rect) {
        return new JSONArray().put(rect.left).put(rect.top).put(rect.right).put(rect.bottom);
    }

    private static JSONObject result(boolean ok, String status) throws JSONException {
        return new JSONObject().put("ok", ok).put("status", status);
    }

    private static boolean isGuest(AccessibilityNodeInfo node) {
        return node != null && TextUtils.equals(GUEST, node.getPackageName());
    }

    private static boolean inWindow(AccessibilityNodeInfo node, int window) {
        return isGuest(node) && node.getWindowId() == window;
    }

    private static AccessibilityNodeInfo activeGuestRoot(UiAutomation automation) {
        List<AccessibilityWindowInfo> windows = automation.getWindows();
        if (windows.size() > MAX_WINDOWS) {
            return null;
        }
        AccessibilityWindowInfo active = null;
        for (AccessibilityWindowInfo window : windows) {
            if (window.isActive()) {
                if (active != null || window.getType() != AccessibilityWindowInfo.TYPE_APPLICATION) {
                    return null;
                }
                active = window;
            }
        }
        if (active == null) {
            return null;
        }
        // Check package ownership on the active root before querying any descendants.
        AccessibilityNodeInfo root = active.getRoot(0);
        return inWindow(root, active.getId()) ? root : null;
    }

    private enum Frame {
        BASELINE_OPEN("baseline-open", "مفتوحة", "إكمال المهمة"),
        BASELINE_COMPLETED("baseline-completed", "مكتملة", "إعادة فتح المهمة"),
        REVIEWED_OPEN("reviewed-open", "الفحص قيد التنفيذ", "وضع علامة مكتملة"),
        REVIEWED_CONFIRM("reviewed-confirm", "الفحص بانتظار التأكيد", "تأكيد إكمال الفحص"),
        REVIEWED_COMPLETED("reviewed-completed", "اكتمل الفحص", "إعادة فتح الفحص"),
        UNAVAILABLE("unavailable", "المهمة غير متاحة", "إعادة تحميل المهمة");

        final String option;
        final String status;
        final String button;

        Frame(String option, String status, String button) {
            this.option = option;
            this.status = status;
            this.button = button;
        }

        static Frame parse(String option) {
            for (Frame frame : values()) {
                if (frame.option.equals(option)) {
                    return frame;
                }
            }
            return null;
        }
    }
}
