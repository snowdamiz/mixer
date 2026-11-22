#!/usr/bin/env python3
"""Execute the prepared FieldLog launcher guard against a minimal task model."""

import argparse
from pathlib import Path
import re
import subprocess
import tempfile

ANDROID = Path("Integrations/GeneratedReport/Platforms/Android/Java/dev/fieldlog/generatedr90/androidhost")
MODEL = """
import java.util.ArrayList;
import java.util.List;

class LauncherModel {
    record ComponentName(String name) {
        ComponentName(PublicActivity activity, Class<?> type) { this(type.getSimpleName()); }
    }
    record Intent(String action, String category, Object data, int flags, ComponentName component) {
        static final String ACTION_MAIN = "android.intent.action.MAIN";
        static final String CATEGORY_LAUNCHER = "android.intent.category.LAUNCHER";
        static final int FLAG_ACTIVITY_NEW_TASK = 0x10000000;
        String getAction() { return action; }
        boolean hasCategory(String requested) { return requested.equals(category); }
        Object getData() { return data; }
        int getFlags() { return flags; }
        ComponentName getComponent() { return component; }
    }
    static final ComponentName PUBLIC = new ComponentName("PublicActivity");
    static final ComponentName ALIAS = new ComponentName("__ALIAS__");
    static final ComponentName OTHER = new ComponentName("Other");
    static final Intent LAUNCHER = new Intent(Intent.ACTION_MAIN, Intent.CATEGORY_LAUNCHER, null, 0x10200000, PUBLIC);
    static final Intent ASSIGNMENT = new Intent("dev.fieldlog.generatedr90.OPEN_ASSIGNMENT", null, "route", 0x10020000, ALIAS);
    static class AssignmentNotifications {
        static ComponentName tapComponent(PublicActivity context) { return ALIAS; }
    }

    static class ActivityManager {
        record AppTask(RecentTaskInfo info, boolean removed) {
            RecentTaskInfo getTaskInfo() {
                if (removed) throw new IllegalArgumentException("removed task");
                return info;
            }
        }
        static class RecentTaskInfo {
            final int taskId, numActivities;
            final ComponentName baseActivity;
            RecentTaskInfo(int taskId, int numActivities, ComponentName baseActivity) {
                this.taskId = taskId;
                this.numActivities = numActivities;
                this.baseActivity = baseActivity;
            }
        }
        final List<AppTask> tasks = new ArrayList<>();
        List<AppTask> getAppTasks() { return tasks; }
        void add(int taskId, int count, ComponentName base) {
            tasks.add(new AppTask(new RecentTaskInfo(taskId, count, base), false));
        }
    }

    static class Task {
        final ActivityManager manager = new ActivityManager();
        final List<String> stack = new ArrayList<>(List.of("original record", "Camera2"));
        final int id = 9;
        final String resultRecipient = stack.getFirst();
        String result;
        Task(ComponentName base) { manager.add(id, 3, base); }
        void cameraResult(String response) {
            check(stack.equals(List.of(resultRecipient, "Camera2")), "camera must be immediately above its recipient");
            stack.removeLast();
            result = resultRecipient + ": " + response;
        }
    }

    static class PublicActivity {
        final Task task;
        final Intent intent;
        final boolean root;
        boolean finishAllowed = true, finished, enteredNormalCreate;
        int finishCalls;
        PublicActivity(Task task, Intent intent, boolean root) { this.task = task; this.intent = intent; this.root = root; }
        boolean isTaskRoot() { return root; }
        int getTaskId() { return task.id; }
        Intent getIntent() { return intent; }
        <T> T getSystemService(Class<T> type) { return type.cast(task.manager); }
        void finish() {
            finishCalls++;
            if (finishAllowed) {
                check(task.stack.getLast().equals("launcher duplicate"), "finish must target only the new record");
                task.stack.removeLast();
                finished = true;
            }
        }
        boolean isFinishing() { return finished; }

__GUARD__

        void create(Object state) {
__GATE__
            enteredNormalCreate = true;
        }
    }

    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    static void continues(String label, Task task, Intent intent, boolean root, Object state) {
        PublicActivity activity = new PublicActivity(task, intent, root);
        activity.create(state);
        check(activity.enteredNormalCreate && activity.finishCalls == 0, label);
    }
    static void modal(ComponentName base, String result) {
        Task task = new Task(base);
        task.manager.tasks.addFirst(new ActivityManager.AppTask(null, true));
        task.stack.add("launcher duplicate");
        PublicActivity activity = new PublicActivity(task, LAUNCHER, false);
        activity.create(null);
        check(activity.finished && !activity.enteredNormalCreate && activity.finishCalls == 1,
            "fresh duplicate must finish before workspace startup");
        task.cameraResult(result);
        check(task.result.equals("original record: " + result), "modal result must go to original record");
    }
    public static void main(String[] args) {
        modal(ALIAS, "cancelled by Back");
        modal(ALIAS, "capture confirmed");
        modal(PUBLIC, "capture confirmed");
        continues("ordinary cold root", new Task(PUBLIC), LAUNCHER, true, null);
        continues("cold shade", new Task(ALIAS), ASSIGNMENT, true, null);
        continues("assignment intent never retired by launcher guard", new Task(PUBLIC), ASSIGNMENT, false, null);
        continues("restored alias root", new Task(ALIAS), ASSIGNMENT, true, new Object());
        continues("restored launcher recipient and Settings recreation", new Task(PUBLIC), LAUNCHER, false, new Object());
        continues("unrelated action", new Task(ALIAS), new Intent("other", Intent.CATEGORY_LAUNCHER, null, 0x10200000, PUBLIC), false, null);
        continues("no launcher category", new Task(ALIAS), new Intent(Intent.ACTION_MAIN, null, null, 0x10200000, PUBLIC), false, null);
        continues("launcher with data", new Task(ALIAS), new Intent(Intent.ACTION_MAIN, Intent.CATEGORY_LAUNCHER, "uri", 0x10200000, PUBLIC), false, null);
        continues("caller-task launch", new Task(ALIAS), new Intent(Intent.ACTION_MAIN, Intent.CATEGORY_LAUNCHER, null, 0, PUBLIC), false, null);
        continues("foreign task root", new Task(OTHER), LAUNCHER, false, null);
        Task differentTask = new Task(OTHER);
        differentTask.manager.add(8, 3, ALIAS);
        continues("FieldLog root only in a different task", differentTask, LAUNCHER, false, null);
        Task solo = new Task(PUBLIC);
        solo.manager.tasks.clear();
        solo.manager.add(solo.id, 1, PUBLIC);
        continues("task snapshot has no second Activity", solo, LAUNCHER, false, null);
        PublicActivity blocked = new PublicActivity(new Task(ALIAS), LAUNCHER, false);
        blocked.finishAllowed = false;
        blocked.create(null);
        check(blocked.finishCalls == 1 && blocked.enteredNormalCreate, "finish refusal must not leave an empty Activity");
        System.out.println("PASS: 16 cases (launcher record, modal result target, ordinary/assignment entry, restoration, and scope controls)");
    }
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fieldlog", type=Path)
    parser.add_argument("--java", default="java")
    parser.add_argument("--scratch", type=Path, default=Path.cwd())
    args = parser.parse_args()
    android = args.fieldlog / ANDROID
    public = (android / "PublicActivity.java").read_text()
    assignment = (android / "AssignmentNotifications.java").read_text()
    alias = re.search(r'private static final String ALIAS = "([^"]+)";', assignment)[1]
    create = public.index("    @Override public void onCreate(Bundle state)")
    guard_start = public.rfind("    private boolean isDuplicateLauncher(Intent intent)", 0, create)
    guard = "" if guard_start == -1 else public[guard_start:create]
    entry = public[create:].split("        super.onCreate(state);\n", 1)[1]
    gate = entry.split("        if (state == null) pendingAssignment =", 1)[0]
    assert "content =" not in gate, "launcher gate must run before view and workspace initialization"
    model = MODEL.replace("__ALIAS__", alias).replace("__GUARD__", guard).replace("__GATE__", gate)
    with tempfile.TemporaryDirectory(prefix="launcher-model-", dir=args.scratch) as directory:
        source = Path(directory) / "LauncherModel.java"
        source.write_text(model)
        subprocess.run([args.java, str(source)], check=True, timeout=20)


if __name__ == "__main__":
    main()
