package dev.mixer.compose

import java.util.UUID

private const val draft = "a界 / e\u0301 👷f"

private class Host(val bridge: JoinBridge) {
    val authority = FrameAuthority()
    private val owners = mutableMapOf<UUID, StageOwner>()

    fun stage(step: Step): PrepareReceipt {
        val proposal = bridge.frame(step)
        val echo = proposal.echo
        val owner = owners.getOrPut(echo.owner) { authority.newStage(echo.owner) }
        val document = checkNotNull(DocumentReader.decode(proposal.document, proposal.generations))
        val receipt = checkNotNull(authority.prepare(owner, echo.sequence, echo.revision, echo.opaque, document))
        check(Echo(receipt) == echo)
        val previous = authority.accepted?.takeIf { it.receipt.stageOwner === owner }
        check(authority.stage(RenderFrame(receipt, previous)))
        return receipt
    }

    fun proof(receipt: PrepareReceipt) = checkNotNull(authority.queued(receipt))

    fun accept(receipt: PrepareReceipt) = authority.accept(proof(receipt), bridge::didDraw)

    fun offer(frame: RenderFrame, id: String, event: Event, value: Any? = null): Boolean {
        val binding = frame.binding(frame.receipt.node(id))
        val target = authority.route(binding, event, value) ?: return false
        if (!bridge.offer(target.receipt, target.receipt.sdkEvent(target.node, event, value))) return false
        authority.supersedeAfterOffer(target.receipt)
        return true
    }
}

private fun Echo.alterFields(): List<Echo> = listOf(
    copy(owner = UUID(owner.mostSignificantBits xor 1, owner.leastSignificantBits)),
    copy(sequence = sequence xor Long.MIN_VALUE),
    copy(revision = revision xor Long.MIN_VALUE),
    wrongOpaque(),
)

fun main(args: Array<String>) {
    SwiftSession(args.single()).use(::replay)
}

private fun replay(session: SwiftSession) {
    val bridge = JoinBridge(session)
    val host = Host(bridge)
    val initial = host.stage(Step.INITIAL)
    val first = Echo(initial)
    check(first.sequence == 1L && first.revision == -4L)
    check(initial.document.root.generationBits == 1L && initial.node("readback").generationBits == 2L)
    check(initial.node("title").generationBits == 3L && initial.node("save").generationBits == 4L)
    check(bridge.send(first, initial.saveEvent()).detail == "rejected staleReceipt")
    for (echo in first.alterFields()) {
        check(!bridge.acknowledge(echo) && !bridge.cancel(echo))
    }
    check(host.accept(initial))
    for ((index, echo) in first.alterFields().withIndex()) {
        val error = if (index == 0) "staleOwner" else "staleReceipt"
        check(bridge.send(echo, initial.saveEvent()) == OfferResult(false, "rejected $error"))
    }
    val initialFrame = checkNotNull(host.authority.accepted)
    println("PASS old and new receipt fields cross JNI as original signed Long bit patterns")

    val held = host.stage(Step.CANCEL)
    val late = host.proof(held)
    check(bridge.send(first, "not json".encodeToByteArray()).detail == "rejected malformedJSON")
    check(bridge.send(first, initial.sdkEvent(initial.node("save"), Event.activate, true)).detail ==
        "rejected invalidValue")
    check(bridge.send(first, initial.sdkEvent(initial.node("save"), Event.submit)).detail ==
        "rejected unboundEvent")
    check(host.offer(initialFrame, "title", Event.textChange, draft))
    check(bridge.inputs.single().receipt === initial && bridge.inputs.single().result.detail == "admitted success edited")
    check(!host.authority.accept(late, bridge::didDraw) && !bridge.acknowledge(Echo(held)))
    check(host.offer(initialFrame, "save", Event.activate))
    check(bridge.inputs.last().result.detail == "admitted success save-initial/$draft")
    println("PASS held edit supersedes its pending draw and the accepted Swift Save reads back its exact Unicode draft")

    val promoted = host.stage(Step.PROMOTE)
    val promotedEcho = Echo(promoted)
    check(promoted.node("readback").string("text") == "promote | Draft: $draft | Saved: $draft")
    check(!bridge.acknowledge(promotedEcho, first))
    check(host.accept(promoted) && bridge.draws.last().replacing == null)
    val promotedFrame = checkNotNull(host.authority.accepted)
    val superseded = host.stage(Step.SUPERSEDE)
    check(superseded.documentRevisionBits == -1L)
    val stale = host.proof(superseded)
    check(bridge.send(promotedEcho, promoted.sdkEvent(promoted.node("save"), Event.submit)) ==
        OfferResult(false, "rejected unboundEvent"))
    check(host.offer(promotedFrame, "save", Event.activate))
    check(bridge.inputs.last().result == OfferResult(true, "admitted failure unboundEvent"))
    check(!host.authority.accept(stale, bridge::didDraw) && !bridge.acknowledge(Echo(superseded)))
    println("PASS admitted handler error supersedes pending and the same routing error refuses dispatch")

    val refused = host.stage(Step.REPLACEMENT)
    check(Echo(refused).copy(owner = first.owner, opaque = first.opaque) == first)
    check(bridge.cancel(Echo(refused)))
    check(!host.accept(refused))
    check(bridge.draws.last() == JoinBridge.Draw(refused, promoted, false))
    check(host.authority.accepted === promotedFrame)
    check(host.authority.cancel(refused))
    bridge.discard(refused)
    check(bridge.discards.single() == JoinBridge.Discard(refused, false))
    check(host.offer(promotedFrame, "save", Event.activate))
    check(bridge.inputs.last().result == OfferResult(true, "admitted failure unboundEvent"))
    println("PASS exact old echo with refused new draw preserves old Kotlin and Swift input")

    val replacement = host.stage(Step.REPLACEMENT_RETRY)
    val newEcho = Echo(replacement)
    check(replacement.owner != first.owner && replacement.opaqueId != refused.opaqueId)
    check(!bridge.acknowledge(newEcho) && !bridge.acknowledge(newEcho, first))
    for (echo in promotedEcho.alterFields()) check(!bridge.acknowledge(newEcho, echo))
    for (echo in newEcho.alterFields()) check(!bridge.acknowledge(echo, promotedEcho))
    check(bridge.send(newEcho, replacement.saveEvent()).detail == "rejected staleReceipt")
    check(bridge.send(promotedEcho, promoted.saveEvent()).detail == "admitted failure unboundEvent")
    check(host.authority.accept(host.proof(replacement)) { receipt, replacing ->
        check(receipt === replacement && replacing === promoted)
        check(bridge.didDraw(receipt, replacing))
        check(host.authority.accepted === promotedFrame)
        check(bridge.send(promotedEcho, promoted.saveEvent()).detail == "rejected staleOwner")
        true
    })
    check(!host.offer(promotedFrame, "save", Event.activate))
    val replacementFrame = checkNotNull(host.authority.accepted)
    check(host.offer(replacementFrame, "save", Event.activate))
    check(bridge.inputs.last().result.detail == "admitted success save-replacementRetry/replacement title")
    check(!bridge.retireEcho(promotedEcho) && !bridge.retireEcho(newEcho.wrongOpaque()))
    val final = host.stage(Step.REPLACEMENT_READBACK)
    check(final.node("readback").string("text") ==
        "replacementReadback | Draft: replacement title | Saved: replacement title")
    check(host.accept(final) && bridge.draws.last() == JoinBridge.Draw(final, null, true))
    host.authority.close()
    bridge.retire(final)
    check(bridge.send(Echo(final), final.saveEvent()).detail == "rejected staleOwner")
    println("PASS Swift retires the exact old owner inside didDraw before Kotlin opens replacement input, then detaches")
}
