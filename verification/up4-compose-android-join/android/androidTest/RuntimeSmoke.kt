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

class RuntimeSmoke : Instrumentation() {
    override fun onCreate(arguments: Bundle?) {
        super.onCreate(arguments)
        start()
    }

    override fun onStart() {
        val result = Bundle()
        try {
            check(Build.VERSION.SDK_INT == 28 && Build.SUPPORTED_ABIS.first() == "arm64-v8a")
            uiAutomation.serviceInfo = uiAutomation.serviceInfo.apply {
                flags = flags or AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS
            }
            val activity = startActivitySync(Intent(targetContext, RuntimeActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) as RuntimeActivity
            try {
                replay(activity)
            } finally {
                main { activity.finish() }
            }
            result.putString("stream", "\nPASS UP4 API 28 Swift/Kotlin Compose runtime join\n")
            finish(Activity.RESULT_OK, result)
        } catch (failure: Throwable) {
            result.putString("stream", "\nFAIL UP4 runtime join: ${failure.stackTraceToString()}\n")
            finish(Activity.RESULT_CANCELED, result)
        }
    }

    private fun replay(activity: RuntimeActivity) {
        val host = activity.host
        val bridge = activity.bridge
        val draft = "a界 / e\u0301 👷f"

        await("attached, focused and measured host") {
            main { Unit.takeIf { host.isAttachedToWindow && host.hasWindowFocus() && host.height > 0 } }
        }
        fun stage(step: Step): PrepareReceipt = main {
            activity.prepare(step).also { check(host.present(it)) }
        }
        fun draw(receipt: PrepareReceipt, replaces: PrepareReceipt?, admitted: Boolean = true) {
            val observed = await("PixelCopy and Swift admission for revision ${receipt.documentRevisionBits}") {
                main { bridge.draws.firstOrNull { it.receipt === receipt } }
            }
            check(observed == JoinBridge.Draw(receipt, replaces, admitted))
        }

        val initial = stage(Step.INITIAL)
        check(initial.documentRevisionBits == -4L && initial.sequenceBits == 1L)
        draw(initial, null)
        val firstSurface = main { host.getChildAt(0) as ViewGroup }
        val composeView = main { checkNotNull(firstSurface.getChildAt(0)) }
        readback("initial | Draft: abcdef | Saved: -")
        check(await("visible title") { node("title") }.performAction(AccessibilityNodeInfo.ACTION_FOCUS))
        val ime = await("focused Compose InputConnection") {
            main { composeView.onCreateInputConnection(EditorInfo()) }
        }
        main { check(ime.setComposingRegion(1, 5) && ime.setSelection(2, 4)) }
        await("Compose selection") { main { ime.getSelectedText(0)?.toString()?.takeIf { it == "cd" } } }

        fun held(step: Step, accepted: PrepareReceipt, expectedStatus: String, act: () -> Unit): JoinBridge.Input {
            var vetoes = 0
            val gate = ViewTreeObserver.OnPreDrawListener { vetoes++; false }
            val baseline = main {
                host.viewTreeObserver.addOnPreDrawListener(gate)
                bridge.draws.size to bridge.inputs.size
            }
            val pending = try {
                stage(step).also { trial ->
                    await("composed candidate while window draw is vetoed", 1_800) {
                        node("readback")?.takeIf { it.text?.toString() == expectedStatus && main { vetoes > 0 } }
                    }
                    main {
                        check(bridge.draws.size == baseline.first)
                        check(host.childCount == 1 && host.getChildAt(0) === firstSurface &&
                            firstSurface.getChildAt(0) === composeView)
                    }
                    act()
                    val input = await("held Compose input admitted by Swift", 900) {
                        main { bridge.inputs.getOrNull(baseline.second) }
                    }
                    check(input.receipt === accepted)
                    main {
                        check(bridge.draws.size == baseline.first && bridge.inputs.size == baseline.second + 1)
                        check(!host.cancel(trial))
                        check(!bridge.acknowledge(Echo(trial)))
                    }
                }
            } finally {
                main { host.viewTreeObserver.removeOnPreDrawListener(gate); host.invalidate() }
            }
            check(pending.owner == accepted.owner)
            return main { bridge.inputs[baseline.second] }
        }

        val edit = held(Step.CANCEL, initial, "cancel | Draft: abcdef | Saved: -") {
            main { check(ime.setComposingText("界 / e\u0301 👷", 1)) }
        }
        assertEvent(edit, "title", "textChange", 3L, draft, "admitted success edited")
        readback("initial | Draft: abcdef | Saved: -")
        await("retained Compose draft") { node("title")?.takeIf { it.text?.toString() == draft } }
        val save = clickSave(bridge)
        check(save.receipt === initial)
        assertEvent(save, "save", "activate", 4L, JSONObject.NULL, "admitted success save-initial/$draft")

        val promoted = stage(Step.PROMOTE)
        draw(promoted, null)
        readback("promote | Draft: $draft | Saved: $draft")
        val old = Echo(promoted)
        val foreign = old.copy(owner = UUID(old.owner.mostSignificantBits xor 1, old.owner.leastSignificantBits))
        main {
            check(bridge.send(foreign, promoted.saveEvent()) == OfferResult(false, "rejected staleOwner"))
            check(bridge.send(old.wrongOpaque(), promoted.saveEvent()) == OfferResult(false, "rejected staleReceipt"))
        }
        val failedSave = held(Step.SUPERSEDE, promoted, "supersede | Draft: $draft | Saved: $draft") {
            check(await("held Save") { node("save") }.performAction(AccessibilityNodeInfo.ACTION_CLICK))
        }
        assertEvent(failedSave, "save", "activate", 4L, JSONObject.NULL, "admitted failure unboundEvent")
        readback("promote | Draft: $draft | Saved: $draft")

        val refused = main {
            activity.prepare(Step.REPLACEMENT).also {
                check(bridge.cancel(Echo(it)))
                check(host.present(it))
            }
        }
        draw(refused, promoted, admitted = false)
        val discarded = await("renderer discards the refused candidate") {
            main { bridge.discards.firstOrNull { it.receipt === refused } }
        }
        check(!discarded.canceled)
        readback("promote | Draft: $draft | Saved: $draft")
        main { check(host.childCount == 1 && host.getChildAt(0) === firstSurface) }
        val afterRefusal = clickSave(bridge)
        check(afterRefusal.receipt === promoted && afterRefusal.result == OfferResult(true, "admitted failure unboundEvent"))

        val replacement = main {
            activity.prepare(Step.REPLACEMENT_RETRY).also {
                check(!bridge.acknowledge(Echo(it), old.wrongOpaque()))
                check(host.present(it))
            }
        }
        draw(replacement, promoted)
        main {
            check(host.childCount == 1 && host.getChildAt(0) !== firstSurface)
            check(bridge.send(old, promoted.saveEvent()) == OfferResult(false, "rejected staleOwner"))
            check(!bridge.acknowledge(Echo(refused), old))
        }
        readback("replacementRetry | Draft: replacement title | Saved: -")
        val afterReplacement = clickSave(bridge)
        check(afterReplacement.receipt === replacement)
        assertEvent(afterReplacement, "save", "activate", 4L, JSONObject.NULL,
            "admitted success save-replacementRetry/replacement title")

        val final = stage(Step.REPLACEMENT_READBACK)
        draw(final, null)
        readback("replacementReadback | Draft: replacement title | Saved: replacement title")
        main {
            activity.detachHost()
            check(bridge.retirements.single() === final)
            check(bridge.send(Echo(final), final.saveEvent()) == OfferResult(false, "rejected staleOwner"))
        }
    }

    private fun clickSave(bridge: JoinBridge): JoinBridge.Input {
        val before = main { bridge.inputs.size }
        check(await("visible Save") { node("save") }.performAction(AccessibilityNodeInfo.ACTION_CLICK))
        return await("Swift Save response") { main { bridge.inputs.getOrNull(before) } }
    }

    private fun assertEvent(input: JoinBridge.Input, id: String, event: String, generation: Long,
                            value: Any, outcome: String) {
        val envelope = JSONObject(input.envelope.decodeToString())
        check("\"revision\":${java.lang.Long.toUnsignedString(input.receipt.documentRevisionBits)}," in
            input.envelope.decodeToString())
        val identity = envelope.getJSONObject("identity")
        check(identity.getString("id") == id && identity.getLong("generation") == generation)
        check(envelope.getString("event") == event && envelope.get("value") == value)
        check(input.result == OfferResult(true, outcome))
    }

    private fun readback(expected: String) {
        await("Swift document readback: $expected") { node("readback")?.takeIf { it.text?.toString() == expected } }
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
