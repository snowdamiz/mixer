package dev.mixer.compose

import android.accessibilityservice.AccessibilityServiceInfo
import android.app.Activity
import android.app.Instrumentation
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.view.ViewGroup
import android.view.ViewTreeObserver
import android.view.accessibility.AccessibilityNodeInfo
import android.view.inputmethod.EditorInfo
import org.json.JSONObject
import java.util.UUID

class HeldInputSmoke : Instrumentation() {
    override fun onCreate(arguments: Bundle?) {
        super.onCreate(arguments)
        start()
    }

    override fun onStart() {
        val result = Bundle()
        try {
            check(Build.VERSION.SDK_INT == 28)
            uiAutomation.serviceInfo = uiAutomation.serviceInfo.apply {
                flags = flags or AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS
            }
            val activity = startActivitySync(Intent(targetContext, SmokeActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) as SmokeActivity
            try {
                replay(activity)
            } finally {
                main { activity.finish() }
            }
            result.putString("stream", "\nPASS UP4 held input: Save, composition, consecutive edits and submit on one API 28 surface\n")
            finish(Activity.RESULT_OK, result)
        } catch (failure: Throwable) {
            result.putString("stream", "\nFAIL UP4 held input: ${failure.stackTraceToString()}\n")
            finish(Activity.RESULT_CANCELED, result)
        }
    }

    private fun replay(activity: SmokeActivity) {
        val host = activity.host
        val bridge = activity.bridge
        val stage = host.newStageOwner(UUID.randomUUID())
        var revision = 0L
        val initialText = "abcdef"
        fun frame(status: String, value: String): PrepareReceipt {
            val current = ++revision
            val wire = """{"schemaVersion":1,"revision":$current,"root":{
              "id":"form","kind":"vStack","properties":{"alignment":"leading"},"actions":[],"children":[
                {"id":"readback","kind":"text","properties":{"text":${JSONObject.quote(status)}},"actions":[],"children":[]},
                {"id":"title","kind":"textField","properties":{"label":"Title","value":${JSONObject.quote(value)},"axis":"horizontal"},
                  "actions":[{"id":"edit","event":"textChange"},{"id":"submit","event":"submit"}],"children":[]},
                {"id":"save","kind":"button","properties":{"label":"Save"},"actions":[{"id":"save","event":"activate"}],"children":[]}
              ]}}"""
            return checkNotNull(host.prepare(stage, current, current, UUID.randomUUID(), wire.toByteArray(),
                longArrayOf(1, 2, 3, 4)))
        }
        fun install(receipt: PrepareReceipt) = main {
            bridge.expected = receipt
            check(host.present(receipt))
        }
        await("focused host") { main { (host.hasWindowFocus() && host.height > 0).takeIf { it } } }
        val initial = frame("Initial frame", initialText)
        install(initial)
        await("first exact PixelCopy") { main { bridge.selected?.takeIf { it === initial } } }
        val surface = main { host.getChildAt(0) as ViewGroup }
        val composeView = main { checkNotNull(surface.getChildAt(0)) }
        check(await("visible title") { node("title") }.performAction(AccessibilityNodeInfo.ACTION_FOCUS))
        val ime = await("focused Compose input connection") { main { composeView.onCreateInputConnection(EditorInfo()) } }
        main { check(ime.setSelection(0, 0)) }

        fun held(status: String, draft: String, nodeId: String, vararg events: Pair<String, Any>, input: () -> Unit) {
            val proposal = frame(status, draft)
            val eventCount = main { bridge.events.size }
            var vetoes = 0
            val gate = ViewTreeObserver.OnPreDrawListener { vetoes++; false }
            main { host.viewTreeObserver.addOnPreDrawListener(gate) }
            try {
                install(proposal)
                await("veto and applied candidate semantics for $status", 1_800) {
                    node("readback")?.takeIf { it.text?.toString() == status && main { vetoes > 0 } }
                }
                main {
                    check(bridge.draws.single() === initial && bridge.selected === initial)
                    check(host.childCount == 1 && host.getChildAt(0) === surface && surface.getChildAt(0) === composeView)
                }
                input()
                for ((index, expected) in events.withIndex()) {
                    val (event, value) = expected
                    val record = await("accepted $event #${index + 1} during veto", 900) {
                        main { bridge.events.getOrNull(eventCount + index) }
                    }
                    check(record.first === initial)
                    val envelope = record.second
                    check(envelope.getLong("revision") == initial.documentRevisionBits)
                    check(envelope.getString("event") == event && envelope.get("value") == value)
                    val identity = envelope.getJSONObject("identity")
                    val generation = if (nodeId == "title") 3L else 4L
                    check(identity.getString("id") == nodeId && identity.getLong("generation") == generation)
                }
                main {
                    check(bridge.events.size == eventCount + events.size && bridge.draws.single() === initial)
                    check(!host.cancel(proposal))
                }
            } finally {
                main { host.viewTreeObserver.removeOnPreDrawListener(gate); host.invalidate() }
            }
            await("restored accepted semantics after $status") {
                node("readback")?.takeIf { it.text?.toString() == "Initial frame" }
            }
        }

        held("Trial for Save", initialText, "save", "activate" to JSONObject.NULL) {
            main { check(ime.setComposingRegion(1, 5) && ime.setSelection(2, 4)) }
            await("selection through held composition", 450) {
                main { ime.getSelectedText(0)?.toString()?.takeIf { it == "cd" } }
            }
            check(checkNotNull(node("save")).performAction(AccessibilityNodeInfo.ACTION_CLICK))
        }
        val firstEdit = "a界f"
        val edited = "a語f"
        held("Trial for consecutive input", initialText, "title",
            "textChange" to firstEdit, "textChange" to edited, "submit" to JSONObject.NULL) {
            main {
                val before = bridge.events.size
                check(ime.setComposingText("界", 1))
                check(bridge.events.size == before + 1)
                check(ime.setComposingText("語", 1))
                check(ime.finishComposingText())
                check(ime.performEditorAction(EditorInfo.IME_ACTION_DONE))
                check(bridge.events.size == before + 3) { "Consecutive IME input must route before recomposition" }
            }
        }
        held("Trial for submit", edited, "title", "submit" to JSONObject.NULL) {
            main { check(ime.performEditorAction(EditorInfo.IME_ACTION_DONE)) }
        }
        check(await("retained text draft") { node("title")?.text?.toString()?.takeIf { it == edited } } == edited)

        val next = frame("Next accepted frame", edited)
        install(next)
        await("new exact PixelCopy without stale acknowledgment") { main { bridge.selected?.takeIf { it === next } } }
        main {
            check(bridge.draws == listOf(initial, next) && bridge.discards.isEmpty())
            check(host.getChildAt(0) === surface && surface.getChildAt(0) === composeView)
        }
        check(await("fresh Save") { node("save") }.performAction(AccessibilityNodeInfo.ACTION_CLICK))
        await("Save carries new receipt") { main { bridge.events.lastOrNull()?.takeIf { it.first === next } } }
    }

    private fun node(tag: String): AccessibilityNodeInfo? {
        val root = uiAutomation.rootInActiveWindow ?: return null
        val pending = ArrayDeque(listOf(root))
        val matches = mutableListOf<AccessibilityNodeInfo>()
        while (pending.isNotEmpty()) {
            val current = pending.removeLast()
            val id = current.viewIdResourceName
            if (current.isVisibleToUser && (id == tag || id == "${targetContext.packageName}:id/$tag")) matches += current
            for (index in 0 until current.childCount) current.getChild(index)?.let(pending::addLast)
        }
        check(matches.size <= 1) { "More than one visible $tag" }
        return matches.singleOrNull()?.takeIf { it.refresh() }
    }

    private fun <T : Any> await(description: String, timeout: Long = 5_000, value: () -> T?): T {
        val deadline = SystemClock.uptimeMillis() + timeout
        do {
            value()?.let { return it }
            SystemClock.sleep(20)
        } while (SystemClock.uptimeMillis() < deadline)
        error("Timed out waiting for $description")
    }

    private fun <T> main(action: () -> T): T {
        var result: Result<T>? = null
        runOnMainSync { result = runCatching(action) }
        return checkNotNull(result).getOrThrow()
    }
}
