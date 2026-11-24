package dev.mixer.compose

import android.content.res.Configuration
import android.graphics.Bitmap
import android.graphics.Rect
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.view.PixelCopy
import android.view.View
import android.view.Window
import android.widget.FrameLayout
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.ViewCompositionStrategy
import org.json.JSONObject
import java.util.UUID
import java.util.concurrent.Executors

/**
 * Implemented by the Swift/JNI embedding. Calls run on the UI thread and must return
 * immediately, without reentering the host. Guest work runs on its own executor.
 */
public interface ComposeSwiftBridge {
    /**
     * Acknowledge the staged Swift snapshot and handlers for this exact receipt first.
     * Return false on refusal, preserving the prior Swift snapshot and its handlers.
     * For a successful cross-owner replacement, retire [replacing]'s Swift owner
     * synchronously before returning true. The host then exposes the new controls.
     * [replacing] is null on the first draw and on same-owner updates.
     */
    public fun didDraw(receipt: PrepareReceipt, replacing: PrepareReceipt?): Boolean

    /** Drop the Swift proposal identified by this receipt. The accepted snapshot remains selected. */
    public fun discard(receipt: PrepareReceipt)

    /**
     * Offer the SDK UIEventEnvelope to the accepted Swift snapshot. True means
     * admitted to dispatch, even if the app handler's result signals failure.
     */
    public fun offer(receipt: PrepareReceipt, envelopeUtf8: ByteArray): Boolean

    /** Retire the accepted Swift owner on detach. Replacement retirement is part of [didDraw]. */
    public fun retire(receipt: PrepareReceipt)
}

/** One native window lifetime. Detach retires all of its stage owners and receipts. */
public class ComposeDocumentHost(
    private val window: Window,
    private val bridge: ComposeSwiftBridge,
) : FrameLayout(window.context) {
    private class EditorMount(var mountedDuringTrial: Boolean = false)

    private inner class Surface(initial: RenderFrame, val theme: SharedTheme) {
        var frame by mutableStateOf(initial)
        var trial by mutableStateOf<Candidate?>(null)
        val editorValues = mutableMapOf<Long, EditorValue>()
        val view = ComposeView(context).apply {
            setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnDetachedFromWindow)
            setContent {
                val shown = frame
                DocumentSurface(shown.receipt.document.root, theme, editorValues,
                    bindControl = { node ->
                        val binding = shown.binding(node)
                        val mount = if (node.kind == Kind.textField) {
                            val editor = remember(binding) { EditorMount() }
                            DisposableEffect(editor) {
                                editor.mountedDuringTrial = authority.isPending(shown)
                                onDispose { editor.mountedDuringTrial = false }
                            }
                            editor
                        } else null
                        ControlInput(
                            emit = { event, value ->
                                offer(this@Surface, binding, event, value, shown.takeIf { mount?.mountedDuringTrial == true })
                            },
                            canEditLocally = {
                                val mounted = shown.takeIf { mount?.mountedDuringTrial == true }
                                inputAvailable(this@Surface) && authority.target(binding, Event.textChange, mounted) != null
                            },
                        )
                    },
                    drawMarker = { canvas ->
                        val next = trial
                        if (next != null && next.receipt === shown.receipt) {
                            val bounds = viewport(this@Surface)
                            if (bounds != null && canvas.size.width == bounds.width().toFloat() &&
                                canvas.size.height == bounds.height().toFloat()) {
                                next.marker.draw(canvas)
                                next.drawnViewport = bounds
                            }
                        }
                    },
                )
            }
        }
    }

    private class Candidate(
        val receipt: PrepareReceipt,
        val surface: Surface,
        val marker: BufferMarker,
    ) {
        var drawnViewport: Rect? = null
    }

    private val authority = FrameAuthority()
    private val main = Handler(Looper.getMainLooper())
    private val probe = Runnable { checkBuffer() }
    private val expiry = Runnable { pending?.let { cancel(it.receipt) } }
    private val worker = Executors.newSingleThreadExecutor { task -> Thread(task, "Mixer-frame-copy") }
    private var copying = false
    private var pending: Candidate? = null
    private var acceptedSurface: Surface? = null
    private var inBridge = false
    private var closed = false

    /** Swift associates this opaque owner with one native session or signed activation lifetime. */
    public fun newStageOwner(owner: UUID): StageOwner = authority.newStage(owner)

    /**
     * Thread-safe. Decode away from the UI thread. Generations are the Swift
     * UIRenderSnapshot identities in root-first depth-first document order.
     */
    public fun prepare(owner: StageOwner, sequenceBits: Long, revisionBits: Long, opaqueId: UUID,
                       documentUtf8: ByteArray, generations: LongArray): PrepareReceipt? =
        DocumentReader.decode(documentUtf8, generations)?.let {
            authority.prepare(owner, sequenceBits, revisionBits, opaqueId, it)
        }

    /** Install a prepared proposal on the main thread. A false result leaves it with Swift. */
    public fun present(receipt: PrepareReceipt): Boolean {
        requireMain()
        if (closed || inBridge || !isAttachedToWindow || !isShown || !hasWindowFocus() || !isHardwareAccelerated) {
            return false
        }
        val theme = SharedTheme.capture(resources) ?: return false
        val current = acceptedSurface
        val previous = authority.accepted
        val reusable = current?.takeIf {
            it.theme == theme && previous?.receipt?.stageOwner === receipt.stageOwner &&
                canReuse(previous.receipt.document.root, receipt.document.root, it.editorValues)
        }
        val frame = if (reusable == null) RenderFrame(receipt) else {
            RenderFrame(receipt, checkNotNull(previous), reusable.editorValues.mapValues { it.value.value.text })
        }
        if (!authority.stage(frame)) return false
        val surface = reusable ?: Surface(frame, theme)
        val next = Candidate(receipt, surface, BufferMarker(theme.canvasArgb))
        pending = next
        if (surface !== current) {
            current?.view?.importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS
            surface.view.importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS
            addView(surface.view, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
        }
        surface.frame = frame
        surface.trial = next
        main.postDelayed(expiry, 3_000)
        scheduleProbe()
        return true
    }

    /** Cancel one exact provisional install. Late receipts leave the current selection alone. */
    public fun cancel(receipt: PrepareReceipt): Boolean {
        requireMain()
        if (inBridge || !authority.cancel(receipt)) return false
        restoreAccepted(checkNotNull(pending))
        notifyBridge { bridge.discard(receipt) }
        return true
    }

    private fun restoreAccepted(rejected: Candidate) {
        finishProbe()
        val current = acceptedSurface
        if (rejected.surface === current) {
            rejected.surface.frame = checkNotNull(authority.accepted)
        } else {
            removeView(rejected.surface.view)
            current?.view?.importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_AUTO
        }
    }

    private fun finishProbe() {
        main.removeCallbacks(probe)
        main.removeCallbacks(expiry)
        pending?.surface?.trial = null
        pending = null
    }

    override fun onWindowFocusChanged(hasWindowFocus: Boolean) {
        super.onWindowFocusChanged(hasWindowFocus)
        if (!hasWindowFocus) pending?.let { cancel(it.receipt) }
    }

    override fun onVisibilityAggregated(isVisible: Boolean) {
        super.onVisibilityAggregated(isVisible)
        if (!isVisible) pending?.let { cancel(it.receipt) }
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        pending?.let { cancel(it.receipt) }
    }

    override fun onDetachedFromWindow() {
        closed = true
        val unresolved = pending?.receipt
        val previous = authority.accepted?.receipt
        finishProbe()
        authority.close()
        acceptedSurface = null
        worker.shutdown()
        unresolved?.let { notifyBridge { bridge.discard(it) } }
        previous?.let { notifyBridge { bridge.retire(it) } }
        super.onDetachedFromWindow()
    }

    override fun dispatchTouchEvent(event: MotionEvent): Boolean {
        val selected = pending?.surface
        // A replacement surface can cover different targets in the accepted surface.
        if (selected != null && selected !== acceptedSurface) return true
        return super.dispatchTouchEvent(event)
    }

    private fun viewport(surface: Surface): Rect? {
        val view = surface.view
        val content = view.getChildAt(0) ?: return null
        if (!content.isAttachedToWindow || !content.isShown || content.windowToken != windowToken || !isAttachedToWindow || !isShown || !hasWindowFocus() ||
            !view.isAttachedToWindow || !view.isShown || view.windowToken != windowToken ||
            view.width < BufferMarker.SIDE || view.height < BufferMarker.SIDE
        ) return null
        val visible = Rect()
        if (!view.getLocalVisibleRect(visible) || !visible.contains(0, 0, view.width, view.height)) return null
        val location = IntArray(2)
        view.getLocationInWindow(location)
        return Rect(location[0], location[1], location[0] + view.width, location[1] + view.height)
    }

    private fun scheduleProbe() {
        if (pending != null && !copying) main.postDelayed(probe, 32)
    }

    private fun checkBuffer() {
        val candidate = pending ?: return
        val bounds = candidate.drawnViewport
        if (bounds == null || viewport(candidate.surface) != bounds) {
            scheduleProbe()
            return
        }
        val markerBounds = Rect(bounds.left, bounds.top, bounds.left + BufferMarker.SIDE, bounds.top + BufferMarker.SIDE)
        val bitmap = Bitmap.createBitmap(BufferMarker.SIDE, BufferMarker.SIDE, Bitmap.Config.ARGB_8888)
        copying = true
        worker.execute {
            try {
                PixelCopy.request(window, markerBounds, bitmap, { result ->
                    val matches = result == PixelCopy.SUCCESS && candidate.marker.matches(bitmap)
                    bitmap.recycle()
                    bufferCopied(candidate, bounds, matches)
                }, main)
            } catch (_: IllegalArgumentException) {
                bitmap.recycle()
                main.post { bufferCopied(candidate, bounds, false) }
            }
        }
    }

    private fun bufferCopied(candidate: Candidate, bounds: Rect, matches: Boolean) {
        copying = false
        if (pending === candidate && matches && candidate.drawnViewport == bounds && viewport(candidate.surface) == bounds) {
            val proof = checkNotNull(authority.queued(candidate.receipt))
            if (!authority.accept(proof) { receipt, replacing -> notifyBridge { bridge.didDraw(receipt, replacing) } }) {
                cancel(candidate.receipt)
                return
            }
            val previous = acceptedSurface
            acceptedSurface = candidate.surface
            finishProbe()
            if (previous != null && previous !== candidate.surface) removeView(previous.view)
            candidate.surface.view.importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_AUTO
        }
        scheduleProbe()
    }

    private fun inputAvailable(surface: Surface): Boolean =
        !inBridge && surface === acceptedSurface && viewport(surface) != null

    private fun offer(surface: Surface, binding: ControlBinding, event: Event, value: Any?,
                      mountedEditorFrame: RenderFrame?): Boolean {
        if (!inputAvailable(surface)) return false
        val target = authority.route(binding, event, value, mountedEditorFrame) ?: return false
        val receipt = target.receipt
        val node = target.node
        val encoded = when (value) {
            is String -> JSONObject.quote(value)
            else -> value.toString()
        }
        val revision = java.lang.Long.toUnsignedString(receipt.documentRevisionBits)
        val generation = java.lang.Long.toUnsignedString(node.generationBits)
        val envelope = """{"revision":$revision,"identity":{"id":${JSONObject.quote(node.id)},"generation":$generation},"event":"${event.name}","value":$encoded}"""
        val admitted = notifyBridge { bridge.offer(receipt, envelope.toByteArray(Charsets.UTF_8)) }
        if (admitted) {
            val superseded = authority.supersedeAfterOffer(receipt)
            if (superseded != null) {
                val trial = checkNotNull(pending)
                check(trial.receipt === superseded)
                restoreAccepted(trial)
            }
        }
        return admitted
    }

    private inline fun <T> notifyBridge(callback: () -> T): T {
        check(!inBridge)
        inBridge = true
        return try { callback() } finally { inBridge = false }
    }

    private fun requireMain() = check(Looper.myLooper() === Looper.getMainLooper())

    private fun canReuse(previous: Node, next: Node, drafts: Map<Long, EditorValue>): Boolean {
        if (previous.id != next.id || previous.generationBits != next.generationBits ||
            previous.kind != next.kind || previous.children.size != next.children.size
        ) return false
        if (next.kind == Kind.textField && (previous.disabled != next.disabled ||
            previous.string("axis") != next.string("axis") ||
            (previous.string("value") != next.string("value") &&
                drafts[next.generationBits]?.value?.text != next.string("value")))
        ) return false
        return previous.children.indices.all { canReuse(previous.children[it], next.children[it], drafts) }
    }
}
