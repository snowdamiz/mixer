package dev.mixer.compose

import android.accessibilityservice.AccessibilityServiceInfo
import android.app.Activity
import android.app.Instrumentation
import android.content.Intent
import android.graphics.Rect
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.view.View
import android.view.ViewGroup
import android.view.ViewTreeObserver
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

class ComposeSmoke : Instrumentation() {
    override fun onCreate(arguments: Bundle?) {
        super.onCreate(arguments)
        start()
    }

    override fun onStart() {
        val result = Bundle()
        try {
            uiAutomation.serviceInfo = uiAutomation.serviceInfo.apply {
                flags = flags or AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS
            }
            check(Build.VERSION.SDK_INT == 28) { "This smoke is scoped to API 28" }
            val activity = startActivitySync(Intent(targetContext, SmokeActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) as SmokeActivity
            try {
                replay(activity)
            } finally {
                onMain { activity.finish() }
            }
            result.putString("stream", "\nPASS UP4 Compose smoke: window draw, exact receipts, stable viewport, SDK events\n")
            finish(Activity.RESULT_OK, result)
        } catch (failure: Throwable) {
            result.putString("stream", "\nFAIL UP4 Compose smoke: ${failure.stackTraceToString()}\n")
            finish(Activity.RESULT_CANCELED, result)
        }
    }

    private fun replay(activity: SmokeActivity) {
        val host = activity.host
        val bridge = activity.bridge
        val owner = UUID.randomUUID()
        val stage = host.newStageOwner(owner)
        await("focused host viewport") { onMain { host.isAttachedToWindow && host.hasWindowFocus() && host.height > 0 } }

        fun frame(sequence: Long, revision: Long, status: String, disabled: Boolean = false,
                  stageOwner: StageOwner = stage, id: UUID = UUID.randomUUID()): PrepareReceipt {
            val (bytes, generations) = editorDocument(revision, status, disabled)
            return checkNotNull(host.prepare(stageOwner, sequence, revision, id, bytes, generations))
        }

        fun stageFrame(receipt: PrepareReceipt) = onMain {
            bridge.expected = receipt
            check(host.present(receipt))
        }

        val first = frame(1, 1, "Prior editor")
        val sameMetadata = frame(1, 1, "Prior editor", id = first.opaqueId)
        stageFrame(first)
        onMain { check(!host.cancel(sameMetadata)) }
        await("first exact window buffer") { onMain { bridge.selected === first } }
        check(first.owner == owner)
        val editor = onMain { host.getChildAt(0) as ViewGroup }
        val composition = onMain { checkNotNull(editor.getChildAt(0)) }
        val viewport = onMain { viewport(editor) }
        check(viewport.width() > 0 && viewport.height() > 0)
        visibleText("Editor")
        visibleText("Options")
        visibleText("Prior editor")

        click("save")
        await("initial Save") { onMain { bridge.events.size == 1 } }
        onMain { verify(bridge.events.single(), first, "save", "activate", JSONObject.NULL) }

        val title = "漢字 e\u0301 👩🏽‍💻"
        val args = Bundle().apply { putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, title) }
        withAccessibleNode("title") { check(it.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)) }
        await("V4 text event") { onMain { bridge.events.size == 2 } }
        onMain { verify(bridge.events.last(), first, "title", "textChange", title) }

        val canceled = frame(2, 2, "Never selected")
        var blocked = 0
        val gate = ViewTreeObserver.OnPreDrawListener { blocked++; false }
        onMain { host.viewTreeObserver.addOnPreDrawListener(gate) }
        try {
            stageFrame(canceled)
            await("actual pre-draw veto") { onMain { blocked > 0 } }
            onMain {
                check(bridge.draws.size == 1 && bridge.selected === first)
                check(host.cancel(canceled))
                check(host.getChildAt(0) === editor && editor.getChildAt(0) === composition && viewport(editor) == viewport)
            }
        } finally {
            onMain { host.viewTreeObserver.removeOnPreDrawListener(gate); host.invalidate() }
        }
        val refused = frame(1, 3, "Refused install", stageOwner = host.newStageOwner(UUID.randomUUID()))
        onMain { bridge.refuse = true }
        stageFrame(refused)
        await("exact Swift refusal and restored surface") { onMain { bridge.discards.lastOrNull() === refused } }
        onMain {
            check(bridge.draws.last() === refused && bridge.selected === first)
            check(host.childCount == 1 && host.getChildAt(0) === editor)
            check(editor.getChildAt(0) === composition && viewport(editor) == viewport)
            check(!host.cancel(canceled) && !host.cancel(first))
            bridge.refuse = false
        }
        withAccessibleNode("title") { check(it.text.toString() == title) }
        click("save")
        await("retained Save") { onMain { bridge.events.size == 3 } }
        onMain { verify(bridge.events.last(), first, "save", "activate", JSONObject.NULL) }

        val next = frame(4, 4, "Selected editor", disabled = true)
        stageFrame(next)
        await("new selected revision") { onMain { bridge.selected === next } }
        onMain { check(host.getChildAt(0) === editor && editor.getChildAt(0) === composition && viewport(editor) == viewport) }
        withAccessibleNode("save") {
            check(!it.isEnabled)
            it.performAction(AccessibilityNodeInfo.ACTION_CLICK)
        }
        val editCount = onMain { bridge.events.size }
        click("flag")
        await("toggle event at new revision") { onMain { bridge.events.size == editCount + 1 } }
        onMain {
            check(editCount == 3)
            verify(bridge.events.last(), next, "flag", "valueChange", true)
            activity.setContentView(android.widget.FrameLayout(activity))
            check(bridge.selected == null && !host.present(next) && !host.cancel(next))
        }
    }

    private fun verify(record: Pair<PrepareReceipt, JSONObject>, receipt: PrepareReceipt,
                       node: String, event: String, value: Any) {
        val (issued, envelope) = record
        check(issued === receipt)
        check(envelope.keys().asSequence().toSet() == setOf("revision", "identity", "event", "value"))
        check(envelope.getLong("revision") == receipt.documentRevisionBits && envelope.getString("event") == event)
        check(envelope.getJSONObject("identity").getString("id") == node && envelope.get("value") == value)
        val generation = when (node) { "title" -> 5L; "save" -> 6L; "flag" -> 7L; else -> error(node) }
        check(envelope.getJSONObject("identity").getLong("generation") == generation)
    }

    private fun click(id: String) {
        withAccessibleNode(id) {
            check(it.performAction(AccessibilityNodeInfo.ACTION_CLICK)) { "Cannot click $id" }
        }
    }

    @Suppress("DEPRECATION") // API 28 pools accessibility nodes.
    private fun visibleText(text: String) {
        awaitVisibleNode("text '$text'") { it.text?.toString() == text }.recycle()
    }

    @Suppress("DEPRECATION")
    private fun withAccessibleNode(id: String, action: (AccessibilityNodeInfo) -> Unit) {
        val resourcePrefix = "${targetContext.packageName}:id/"
        val node = awaitVisibleNode("test tag '$id'") {
            it.viewIdResourceName?.removePrefix(resourcePrefix) == id
        }
        try {
            action(node)
        } finally {
            node.recycle()
        }
    }

    private fun awaitVisibleNode(description: String, matches: (AccessibilityNodeInfo) -> Boolean): AccessibilityNodeInfo {
        var found: AccessibilityNodeInfo? = null
        await("visible $description") {
            found = uiAutomation.rootInActiveWindow?.let { uniqueVisibleNode(it, description, matches) }
            found != null
        }
        return checkNotNull(found)
    }

    private fun viewport(view: View): Rect {
        val location = IntArray(2)
        view.getLocationInWindow(location)
        return Rect(location[0], location[1], location[0] + view.width, location[1] + view.height)
    }

    private fun await(description: String, predicate: () -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + 5_000
        while (SystemClock.uptimeMillis() < deadline) {
            if (predicate()) return
            SystemClock.sleep(20)
        }
        error("Timed out waiting for $description")
    }

    private fun <T> onMain(action: () -> T): T {
        var outcome: Result<T>? = null
        runOnMainSync { outcome = runCatching(action) }
        return checkNotNull(outcome).getOrThrow()
    }
}

// Android 9's virtual provider can return null from its by-text search.
@Suppress("DEPRECATION")
private fun uniqueVisibleNode(root: AccessibilityNodeInfo, description: String,
                              matches: (AccessibilityNodeInfo) -> Boolean): AccessibilityNodeInfo? {
    var found: AccessibilityNodeInfo? = null

    fun visit(node: AccessibilityNodeInfo) {
        try {
            if (node.isVisibleToUser && matches(node)) {
                check(found == null) { "Multiple visible accessibility nodes match $description" }
                found = node
            }
            for (index in 0 until node.childCount) {
                node.getChild(index)?.let(::visit)
            }
        } finally {
            if (node !== found) node.recycle()
        }
    }

    try {
        visit(root)
        return found
    } catch (failure: Throwable) {
        found?.recycle()
        throw failure
    }
}

private fun editorDocument(revision: Long, status: String, disabled: Boolean): Pair<ByteArray, LongArray> {
    fun props(vararg values: Pair<String, Any>) = JSONObject(values.toMap())
    fun node(id: String, kind: String, properties: JSONObject = JSONObject(),
             children: List<JSONObject> = emptyList(), vararg events: String) = JSONObject()
        .put("id", id).put("kind", kind).put("properties", properties).put("children", JSONArray(children))
        .put("actions", JSONArray(events.map { props("id" to "$id.$it", "event" to it) }))
    val form = node("form", "vStack", props("alignment" to "leading"), listOf(
        node("title", "textField", props("label" to "Title", "value" to "", "axis" to "vertical"),
            emptyList(), "textChange", "submit"),
        node("save", "button", props("label" to "Save", "disabled" to disabled), emptyList(), "activate"),
        node("flag", "toggle", props("label" to "Flag", "value" to false), emptyList(), "valueChange"),
        node("row", "hStack", props("alignment" to "firstTextBaseline"), listOf(
            node("readback", "text", props("text" to status, "style" to "headline", "maxLines" to 1)),
            node("overlay", "zStack", props("alignment" to "bottomTrailing"), listOf(
                node("caption", "text", props("text" to "✍🏽", "style" to "caption", "selectable" to true)),
            )),
        )),
    ))
    val nested = node("nested", "vStack", children = listOf(node("nested-text", "text", props("text" to "Nested row"))))
    val section = node("section", "section", props("title" to "Options"), listOf(form, nested))
    val rows = (0 until 100).map { node("row-$it", "text", props("text" to "Row $it")) }
    val root = node("nav", "navigation", props("title" to "Editor"),
        listOf(node("rows", "list", children = listOf(section) + rows)))
    val bytes = JSONObject().put("schemaVersion", 1).put("revision", revision).put("root", root)
        .toString().toByteArray()
    return bytes to LongArray(13 + rows.size) { it + 1L }
}
