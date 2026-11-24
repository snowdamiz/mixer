package dev.mixer.compose

import java.io.File
import java.util.UUID

private fun wireNode(kind: String, properties: String, actions: String = "[]", children: String = "[]",
                     id: String = "one") =
    """{"id":"$id","kind":"$kind","properties":$properties,"children":$children,"actions":$actions}"""

private fun document(root: String, revision: String = "1") =
    """{"schemaVersion":1,"revision":$revision,"root":$root}""".toByteArray()

private fun rejectNestedLists() {
    val inner = wireNode("list", "{}", id = "inner")
    for (wrappers in listOf(emptyList(), listOf("section"), listOf("vStack", "hStack", "zStack"),
                            listOf("section", "vStack", "navigation"))) {
        val branch = wrappers.fold(inner) { child, kind ->
            wireNode(kind, "{}", children = "[$child]", id = kind)
        }
        val outer = wireNode("list", "{}", children = "[$branch]", id = "outer")
        check(DocumentReader.decode(document(outer), LongArray(wrappers.size + 2) { it + 1L }) == null) {
            "Admitted a nested list through wrappers $wrappers"
        }
    }
    val peer = wireNode("list", "{}", id = "peer")
    val root = wireNode("vStack", "{}", children = "[$inner,$peer]", id = "root")
    check(DocumentReader.decode(document(root), longArrayOf(1, 2, 3)) != null)
}

private fun validateWire() {
    val action = """[{"id":"swift.save","event":"activate"}]"""
    val button = wireNode("button", """{"label":"Save ✍🏽"}""", action)
    val root = wireNode("vStack", """{"disabled":true}""", children = "[$button]", id = "root")
    val valid = document(root, "18446744073709551615")
    val generations = longArrayOf(1, -1)
    val decoded = checkNotNull(DocumentReader.decode(valid, generations))
    check(decoded.revisionBits == -1L)
    check(decoded.nodes.getValue("one").generationBits == -1L && decoded.nodes.getValue("one").disabled)
    check(decoded.nodes.getValue("one").string("label") == "Save ✍🏽")

    val invalid = listOf(
        valid.decodeToString().replace("\"schemaVersion\":1", "\"schemaVersion\":4"),
        valid.decodeToString().replace("\"schemaVersion\":1", "\"schemaVersion\":1,\"schemaVersion\":1"),
        valid.decodeToString().replace("\"schemaVersion\":1", "\"schemaVersion\":1,\"schemaVersio\\u006e\":1"),
        valid.decodeToString().replace("\"kind\":\"button\"", "\"kind\":\"arbitrary\""),
        valid.decodeToString().replace("\"label\":", "\"redirect\":"),
        valid.decodeToString().replace("\"swift.save\"", "null"),
        valid.decodeToString().replace("\"activate\"", "\"submit\""),
        valid.decodeToString().replace("✍🏽", "\\ud800"),
        valid.decodeToString().replace("✍🏽", "\\x"),
        valid.decodeToString().replace("\"disabled\":true", "\"disabled\":\"true\""),
        valid.decodeToString().replace("18446744073709551615", "18446744073709551616"),
        valid.decodeToString().replace("\"one\"", "\"root\""),
        valid.decodeToString() + " {}",
    )
    for (wire in invalid) check(DocumentReader.decode(wire.toByteArray(), generations) == null) { wire }
    check(DocumentReader.decode(valid + byteArrayOf(0xC0.toByte(), 0x80.toByte()), generations) == null)
    check(DocumentReader.decode(valid, longArrayOf(1, 1)) == null)
    check(DocumentReader.decode(valid, longArrayOf(1)) == null)
    check(DocumentReader.decode(valid, longArrayOf(1, 0)) == null)
    check(DocumentReader.decode(valid, longArrayOf(1, 2, 3)) == null)
    check(DocumentReader.decode(
        document(wireNode("vStack", "{}", children = """[
            ${wireNode("text", """{"text":"A"}""", id = "é")},
            ${wireNode("text", """{"text":"B"}""", id = "e\u0301")} ]""", id = "root")),
        longArrayOf(1, 2, 3),
    ) == null)

    val textChange = """[{"id":"swift.edit","event":"textChange"}]"""
    val note = "界".repeat(33_333)
    val longNote = wireNode("textField", """{"label":"Note","axis":"vertical","value":"$note"}""", textChange)
    check(DocumentReader.decode(document(longNote), longArrayOf(1)) != null)
    check(DocumentReader.decode(document(longNote.replace("vertical", "horizontal")), longArrayOf(1)) == null)
    check(DocumentReader.decode(document(longNote.replace(note, "${note}界")), longArrayOf(1)) == null)

    var nested = wireNode("text", """{"text":"leaf"}""", id = "leaf")
    repeat(64) { nested = wireNode("vStack", "{}", children = "[$nested]", id = "stack$it") }
    check(DocumentReader.decode(document(nested), LongArray(65) { it + 1L }) == null)
}

private fun FrameAuthority.prepare(owner: StageOwner, sequenceBits: Long, document: Document,
                                   opaqueId: UUID = UUID.randomUUID()) =
    prepare(owner, sequenceBits, document.revisionBits, opaqueId, document)

private fun exerciseAuthority() {
    val state = FrameAuthority()
    val owner = state.newStage(UUID.randomUUID())
    val replacementOwner = state.newStage(UUID.randomUUID())
    val foreign = FrameAuthority()
    val foreignOwner = foreign.newStage(UUID.randomUUID())

    fun snapshot(revision: Long, disabled: Boolean = false): Document {
        val props = """{"label":"Save","disabled":$disabled}"""
        val button = wireNode("button", props, """[{"id":"save","event":"activate"}]""")
        return checkNotNull(DocumentReader.decode(document(button, revision.toString()), longArrayOf(4)))
    }

    val a = checkNotNull(state.prepare(owner, 1, snapshot(1)))
    val same = checkNotNull(state.prepare(owner, 1, a.document, a.opaqueId))
    val b = checkNotNull(state.prepare(owner, 2, snapshot(2, disabled = true)))
    val next = checkNotNull(state.prepare(replacementOwner, 1, snapshot(1)))
    val frameA = RenderFrame(a)
    val frameB = RenderFrame(b)
    val frameNext = RenderFrame(next)
    val save = frameA.binding(a.document.root)
    val saveB = frameB.binding(b.document.root)
    val saveNext = frameNext.binding(next.document.root)
    check(a.owner == owner.id && a.sequenceBits == 1L && a.documentRevisionBits == 1L)
    check(same.owner == a.owner && same.opaqueId == a.opaqueId && same !== a)
    check(state.prepare(owner, 5, 7, UUID.randomUUID(), a.document) == null)
    check(runCatching { frameA.binding(a.document.root.copy()) }.isFailure)

    check(state.prepare(foreignOwner, 1, a.document) == null)
    check(!state.stage(RenderFrame(checkNotNull(foreign.prepare(foreignOwner, 1, a.document)))))
    check(state.stage(frameA))
    check(state.route(save, Event.activate, null) == null)
    check(state.queued(same) == null && !state.cancel(same) && !state.stage(frameB))
    val firstProof = checkNotNull(state.queued(a))
    check(!state.accept(FrameAuthority.DrawProof(a)) { _, _ -> error("forged proof") })
    check(state.accept(firstProof) { receipt, replacing -> receipt === a && replacing == null })
    check(state.accepted === frameA)
    check(!state.accept(firstProof) { _, _ -> error("replayed proof") })
    check(state.route(save, Event.activate, null) === save.shown)
    check(state.route(save, Event.submit, null) == null)
    check(state.route(save, Event.activate, true) == null)
    check(state.route(ControlBinding(save.shown, null), Event.activate, null) == null)

    check(state.stage(frameB))
    check(state.route(save, Event.activate, null) === save.shown)
    check(state.route(saveB, Event.activate, null) == null)
    check(state.supersedeAfterOffer(b) == null)
    val canceled = checkNotNull(state.queued(b))
    check(!state.accept(canceled) { _, _ -> false })
    check(state.supersedeAfterOffer(a) === b && state.accepted === frameA)
    check(!state.cancel(b) && !state.accept(canceled) { _, _ -> error("superseded proof") })
    check(state.route(save, Event.activate, null) === save.shown)
    check(!state.stage(frameB))

    val disabled = checkNotNull(state.prepare(owner, 3, b.document))
    val frameDisabled = RenderFrame(disabled)
    check(state.stage(frameDisabled))
    val disabledProof = checkNotNull(state.queued(disabled))
    check(!state.accept(canceled) { _, _ -> error("canceled proof selected a new frame") })
    check(state.accept(disabledProof) { receipt, replacing -> receipt === disabled && replacing == null })
    check(state.route(frameDisabled.binding(disabled.document.root), Event.activate, null) == null)
    check(state.route(save, Event.activate, null) == null)
    check(!state.stage(frameDisabled))
    check(state.stage(frameNext))
    check(state.route(saveNext, Event.activate, null) == null)
    check(state.accept(checkNotNull(state.queued(next))) { issued, replacing ->
        check(issued === next && replacing === disabled)
        check(state.route(saveNext, Event.activate, null) == null)
        true
    })
    check(state.route(saveNext, Event.activate, null) === saveNext.shown)
    check(!state.stage(RenderFrame(checkNotNull(state.prepare(owner, 5, snapshot(3))))))
    check(!state.stage(RenderFrame(checkNotNull(state.prepare(replacementOwner, 5, next.document)))))
    state.close()
    check(state.route(saveNext, Event.activate, null) == null)
    check(!state.stage(RenderFrame(checkNotNull(state.prepare(state.newStage(UUID.randomUUID()), 6, snapshot(1))))))

    val unsigned = FrameAuthority()
    val unsignedOwner = unsigned.newStage(UUID.randomUUID())
    val zero = checkNotNull(unsigned.prepare(unsignedOwner, 0L, snapshot(0)))
    val maximum = checkNotNull(unsigned.prepare(unsignedOwner, -1L, snapshot(1)))
    check(unsigned.stage(RenderFrame(zero)) && unsigned.cancel(zero))
    check(unsigned.stage(RenderFrame(maximum)) && unsigned.cancel(maximum))
    check(!unsigned.stage(RenderFrame(checkNotNull(unsigned.prepare(unsignedOwner, Long.MAX_VALUE, snapshot(2))))))
}

private fun exerciseTransitionBindings() {
    val state = FrameAuthority()
    val owner = state.newStage(UUID.randomUUID())
    var sequence = 0L
    val draft = "draft 界"
    fun frame(previous: RenderFrame? = null, wireEdit: (String) -> String = { it }): RenderFrame {
        val wire = """
            {"id":"root","kind":"vStack","properties":{},"actions":[],"children":[
              {"id":"save","kind":"button","properties":{"label":"Save","role":"normal"},"children":[],
                "actions":[{"id":"save.old","event":"activate"}]},
              {"id":"editor","kind":"textField","properties":{"label":"Title","value":"","axis":"horizontal"},
                "children":[],"actions":[{"id":"edit","event":"textChange"},{"id":"submit.old","event":"submit"}]},
              {"id":"flag","kind":"toggle","properties":{"label":"Flag","value":false},
                "children":[],"actions":[{"id":"toggle","event":"valueChange"}]}
            ]}
        """.trimIndent()
        val revision = (++sequence).toString()
        val decoded = checkNotNull(DocumentReader.decode(document(wireEdit(wire), revision), longArrayOf(1, 2, 3, 4)))
        return RenderFrame(checkNotNull(state.prepare(owner, sequence, decoded)), previous, mapOf(3L to draft))
    }
    fun RenderFrame.control(id: String) = binding(receipt.document.nodes.getValue(id))
    val prior = frame()
    val originalSave = prior.control("save")
    val originalEditor = prior.control("editor")
    val originalFlag = prior.control("flag")
    check(state.stage(prior))
    check(state.accept(checkNotNull(state.queued(prior.receipt))) { _, _ -> true })

    for ((id, event, payload) in listOf(
        Triple("save", Event.activate, null),
        Triple("editor", Event.textChange, "typed after veto"),
        Triple("editor", Event.submit, null),
    )) {
        val held = frame(prior) { it.replace("\"value\":\"\"", "\"value\":\"$draft\"") }
        val heldControl = held.control(id)
        check(state.stage(held))
        check(state.queued(held.receipt) != null)
        val target = checkNotNull(state.route(heldControl, event, payload))
        check(target === prior.control(id).shown && target.node === prior.receipt.document.nodes[id])
        check(state.target(held.control("editor"), Event.textChange) === originalEditor.shown)
        check(state.supersedeAfterOffer(target.receipt) === held.receipt)
        check(state.route(heldControl, event, payload) == null)
        check(state.queued(held.receipt) == null && !state.stage(held))
    }

    val burst = frame(prior)
    val burstEditor = burst.control("editor")
    check(state.stage(burst))
    check(state.route(burstEditor, Event.textChange, "first edit", burst) === originalEditor.shown)
    check(state.supersedeAfterOffer(prior.receipt) === burst.receipt)
    check(state.target(burstEditor, Event.textChange, burst) === originalEditor.shown)
    check(state.route(burstEditor, Event.textChange, "second edit", burst) === originalEditor.shown)
    check(state.route(burstEditor, Event.submit, null, burst) === originalEditor.shown)
    check(state.route(burstEditor, Event.submit, null) == null)
    check(state.route(burstEditor, Event.submit, null, prior) == null)
    check(state.route(burstEditor, Event.submit, true, burst) == null)
    check(state.route(burst.control("save"), Event.activate, null, burst) == null)

    val changed = listOf(
        Triple("save", Event.activate, "\"role\":\"normal\"" to "\"role\":\"destructive\""),
        Triple("save", Event.activate, "\"role\":\"normal\"" to "\"disabled\":true"),
        Triple("save", Event.activate, "save.old" to "save.new"),
        Triple("editor", Event.submit, "submit.old" to "submit.new"),
        Triple("editor", Event.textChange, "\"value\":\"\"" to "\"value\":\"server reset\""),
        Triple("flag", Event.valueChange, "\"value\":false" to "\"value\":true"),
    )
    for ((id, event, change) in changed) {
        val held = frame(prior) { it.replace(change.first, change.second) }
        check(state.stage(held))
        check(state.route(burstEditor, Event.submit, null, burst) == null)
        check(state.target(held.control(id), event) == null)
        check(state.target(prior.control(id), event) == null)
        if (id == "editor") check(state.target(held.control(id), Event.textChange) == null)
        check(state.cancel(held.receipt))
        check(state.target(held.control(id), event) == null)
        check(state.target(held.control(id), event, held) == null)
        check(state.target(prior.control(id), event) === prior.control(id).shown)
    }

    val replacement = frame(prior) { it.replace("save.old", "save.new") }
    val changedSave = replacement.control("save")
    check(state.stage(replacement))
    val proof = checkNotNull(state.queued(replacement.receipt))
    check(state.route(changedSave, Event.activate, null) == null)
    check(state.accept(proof) { receipt, replacing -> receipt === replacement.receipt && replacing == null })
    check(state.route(changedSave, Event.activate, null) === changedSave.shown)
    check(state.route(originalSave, Event.activate, null) == null)
    check(state.target(originalEditor, Event.textChange) == null)
    check(state.route(originalFlag, Event.valueChange, true) == null)

    val noSubmit = frame(replacement) { it.replace(""",{"id":"submit.old","event":"submit"}""", "") }
    check(state.stage(noSubmit))
    check(state.accept(checkNotNull(state.queued(noSubmit.receipt))) { _, _ -> true })
    val addsSubmit = frame(noSubmit)
    val newEditor = addsSubmit.control("editor")
    check(state.stage(addsSubmit))
    check(state.route(newEditor, Event.submit, null) == null)
    check(state.target(newEditor, Event.textChange) == null)
    check(state.accept(checkNotNull(state.queued(addsSubmit.receipt))) { _, _ -> true })
    check(state.route(newEditor, Event.submit, null) === newEditor.shown)
}

fun main(args: Array<String>) {
    if (args.isNotEmpty()) {
        val swift = checkNotNull(DocumentReader.decode(File(args.single()).readBytes(), longArrayOf(1, 2, 3)))
        check(swift.revisionBits == 10L)
        check(swift.nodes.getValue("title").string("value") == "日本語 👩🏽‍💻")
        check(swift.nodes.getValue("save").generationBits == 3L)
        println("PASS Kotlin read Swift's canonical SDK fixture bytes")
    }
    validateWire()
    rejectNestedLists()
    exerciseAuthority()
    exerciseTransitionBindings()
    println("PASS UIDocument wire, V4 input limits, nested-list refusal, exact proof, held control bindings, stale and disabled input")
}
