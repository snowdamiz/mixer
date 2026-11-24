package dev.mixer.compose

import java.util.UUID

/** One Swift stage/activation lifetime, scoped to the issuing host instance. */
public class StageOwner private constructor(private val hostIdentity: Any, public val id: UUID) {
    private var retired = false
    private var lastSequence: Long? = null

    internal fun belongsTo(identity: Any): Boolean = hostIdentity === identity

    internal fun stage(identity: Any, sequenceBits: Long): Boolean {
        val previous = lastSequence
        if (!belongsTo(identity) || retired ||
            (previous != null && java.lang.Long.compareUnsigned(sequenceBits, previous) <= 0)
        ) return false
        lastSequence = sequenceBits
        return true
    }

    internal fun retire(identity: Any) {
        check(belongsTo(identity))
        retired = true
    }

    internal companion object {
        fun issue(identity: Any, id: UUID) = StageOwner(identity, id)
    }
}

/** Pass this exact reference across JNI. Sequence and revision use UInt64 bit patterns. */
public class PrepareReceipt private constructor(
    private val hostIdentity: Any,
    internal val stageOwner: StageOwner,
    public val sequenceBits: Long,
    public val documentRevisionBits: Long,
    public val opaqueId: UUID,
    internal val document: Document,
) {
    public val owner: UUID get() = stageOwner.id

    internal fun belongsTo(identity: Any): Boolean = hostIdentity === identity

    internal companion object {
        fun issue(identity: Any, owner: StageOwner, sequenceBits: Long, revisionBits: Long, opaqueId: UUID,
                  document: Document) = PrepareReceipt(identity, owner, sequenceBits, revisionBits, opaqueId, document)
    }
}

internal class InputTarget(val receipt: PrepareReceipt, val node: Node)

internal class ControlBinding(val shown: InputTarget, val carried: InputTarget?)

/** Capture both exact targets before composition. A transition retains only one preceding frame's targets. */
internal class RenderFrame(
    val receipt: PrepareReceipt,
    previous: RenderFrame? = null,
    drafts: Map<Long, String> = emptyMap(),
) {
    val previousReceipt = previous?.receipt
    val inputIdentity = Any()
    private val controls: Map<String, ControlBinding> = buildMap {
        for (node in receipt.document.nodes.values) {
            if (node.actions.isEmpty()) continue
            val carried = previous?.controls?.get(node.id)?.shown?.takeIf {
                it.node.canCarry(node, drafts[node.generationBits])
            }
            put(node.id, ControlBinding(InputTarget(receipt, node), carried))
        }
    }

    fun binding(node: Node): ControlBinding = controls.getValue(node.id).also { check(it.shown.node === node) }

    fun owns(binding: ControlBinding): Boolean = controls[binding.shown.node.id] === binding

    fun carries(target: InputTarget): Boolean = controls[target.node.id]?.carried === target

    private fun Node.canCarry(next: Node, draft: String?): Boolean {
        if (kind != next.kind || generationBits != next.generationBits || disabled != next.disabled ||
            actions != next.actions
        ) return false
        if (kind != Kind.textField) return properties == next.properties
        // A candidate can echo the retained draft while the field keeps the same TextFieldValue.
        return properties - "value" == next.properties - "value" &&
            (string("value") == next.string("value") || draft == next.string("value"))
    }
}

/** Main-thread selection state. A queued-buffer proof is valid for one selected offer. */
internal class FrameAuthority {
    private val identity = Any()
    private var closed = false
    private var pending: Pending? = null
    private var supersededInputIdentity: Any? = null
    var accepted: RenderFrame? = null
        private set

    private class Pending(val frame: RenderFrame, var proof: DrawProof? = null)

    internal class DrawProof internal constructor(internal val receipt: PrepareReceipt)

    fun newStage(owner: UUID) = StageOwner.issue(identity, owner)

    fun prepare(owner: StageOwner, sequenceBits: Long, revisionBits: Long, opaqueId: UUID, document: Document): PrepareReceipt? =
        if (owner.belongsTo(identity) && revisionBits == document.revisionBits) {
            PrepareReceipt.issue(identity, owner, sequenceBits, revisionBits, opaqueId, document)
        } else null

    fun stage(frame: RenderFrame): Boolean {
        val receipt = frame.receipt
        val previous = accepted?.receipt
        if (closed || pending != null || !receipt.belongsTo(identity) ||
            (frame.previousReceipt != null &&
                (frame.previousReceipt !== previous || previous.stageOwner !== receipt.stageOwner)) ||
            (previous?.stageOwner === receipt.stageOwner &&
                java.lang.Long.compareUnsigned(receipt.documentRevisionBits, previous.documentRevisionBits) <= 0)
        ) return false
        if (!receipt.stageOwner.stage(identity, receipt.sequenceBits)) return false
        pending = Pending(frame)
        supersededInputIdentity = null
        return true
    }

    fun queued(receipt: PrepareReceipt): DrawProof? {
        val next = pending ?: return null
        if (next.frame.receipt !== receipt || next.proof != null) return null
        return DrawProof(receipt).also { next.proof = it }
    }

    fun isPending(frame: RenderFrame): Boolean = pending?.frame === frame

    fun accept(proof: DrawProof, admit: (PrepareReceipt, replacing: PrepareReceipt?) -> Boolean): Boolean {
        val next = pending ?: return false
        val receipt = next.frame.receipt
        val replacing = accepted?.receipt?.takeIf { it.stageOwner !== receipt.stageOwner }
        if (next.proof !== proof || !admit(receipt, replacing) || pending !== next) return false
        replacing?.stageOwner?.retire(identity)
        accepted = next.frame
        pending = null
        return true
    }

    fun cancel(receipt: PrepareReceipt): Boolean {
        if (pending?.frame?.receipt !== receipt) return false
        pending = null
        return true
    }

    fun target(binding: ControlBinding, event: Event, mountedEditorFrame: RenderFrame? = null): InputTarget? {
        val active = accepted ?: return null
        val trial = pending?.frame
        if (trial != null && trial.receipt.stageOwner !== active.receipt.stageOwner) return null
        val shown = binding.shown
        // The admitted offer restores the accepted frame before Compose replaces the mounted editor callbacks.
        val restoringEditor = mountedEditorFrame != null && shown.node.kind == Kind.textField &&
            mountedEditorFrame.inputIdentity === supersededInputIdentity && mountedEditorFrame.owns(binding)
        val target = when {
            active.owns(binding) &&
                (trial == null || trial.previousReceipt !== shown.receipt || trial.carries(shown)) -> shown
            trial?.owns(binding) == true || restoringEditor -> binding.carried?.takeIf { it.receipt === active.receipt }
            else -> null
        }
        return target?.takeIf { !it.node.disabled && event in it.node.actions }
    }

    fun route(binding: ControlBinding, event: Event, value: Any?, mountedEditorFrame: RenderFrame? = null): InputTarget? {
        val target = target(binding, event, mountedEditorFrame) ?: return null
        val valid = when (event) {
            Event.activate, Event.submit -> value == null
            Event.textChange -> value is String &&
                value.length <= target.node.textLimit && Charsets.UTF_8.newEncoder().canEncode(value) &&
                value.toByteArray(Charsets.UTF_8).size <= target.node.textLimit
            Event.valueChange -> value is Boolean
        }
        return target.takeIf { valid }
    }

    fun supersedeAfterOffer(receipt: PrepareReceipt): PrepareReceipt? {
        if (accepted?.receipt !== receipt) return null
        val superseded = pending?.frame ?: return null
        supersededInputIdentity = superseded.takeIf { it.previousReceipt === receipt }?.inputIdentity
        pending = null
        return superseded.receipt
    }

    fun close() {
        closed = true
        pending = null
        supersededInputIdentity = null
        accepted?.receipt?.stageOwner?.retire(identity)
        accepted = null
    }
}
