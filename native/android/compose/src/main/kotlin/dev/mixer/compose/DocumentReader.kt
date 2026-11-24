package dev.mixer.compose

import java.nio.ByteBuffer
import java.text.Normalizer

/** Decode the SDK UIDocument with the V4 text policy. No native action IDs cross input. */
internal object DocumentReader {
    fun decode(bytes: ByteArray, generations: LongArray): Document? {
        if (bytes.size !in 1..1_048_576 || generations.size !in 1..4096) return null
        return try {
            val input = Charsets.UTF_8.newDecoder().decode(ByteBuffer.wrap(bytes)).toString()
            val wire = Json(input).read().fields("schemaVersion", "revision", "root")
            require(wire["schemaVersion"] == NumberToken("1"))
            val revision = (wire["revision"] as? NumberToken)?.text?.takeIf { it.all(Char::isDigit) }
                ?.toULongOrNull() ?: error("Invalid revision")
            val validator = Nodes(generations)
            val root = validator.read(wire["root"], 1, ancestorDisabled = false, insideList = false)
            require(validator.nodes.size == generations.size)
            Document(revision.toLong(), root, validator.nodes.toMap())
        } catch (_: java.nio.charset.CharacterCodingException) {
            null
        } catch (_: IllegalArgumentException) {
            null
        } catch (_: IllegalStateException) {
            null
        }
    }

    private class Nodes(private val generations: LongArray) {
        val nodes = mutableMapOf<String, Node>()
        private val ids = mutableSetOf<String>()
        private val issued = mutableSetOf<Long>()

        fun read(value: Any?, depth: Int, ancestorDisabled: Boolean, insideList: Boolean): Node {
            require(depth <= 64 && ids.size < generations.size)
            val fields = value.fields("id", "kind", "properties", "children", "actions")
            val id = identifier(fields["id"])
            val generation = generations[ids.size]
            require(generation != 0L && issued.add(generation) && ids.add(Normalizer.normalize(id, Normalizer.Form.NFC)))
            val kind = Kind.valueOf(fields["kind"].string(128))
            require(kind != Kind.list || !insideList)
            val properties = properties(kind, fields["properties"])
            val actions = actions(kind, fields["actions"])
            val children = fields["children"].array(1000)
            when (kind) {
                Kind.text, Kind.button, Kind.textField, Kind.toggle -> require(children.isEmpty())
                Kind.navigation -> require(children.size == 1)
                else -> Unit
            }
            val disabled = ancestorDisabled || properties["disabled"] == true
            val descendantsInsideList = insideList || kind == Kind.list
            val descendants = children.map { read(it, depth + 1, disabled, descendantsInsideList) }
            return Node(id, generation, kind, properties, actions, descendants, disabled).also { nodes[id] = it }
        }
    }

    private fun properties(kind: Kind, value: Any?): Map<String, Any> {
        val fields = value.obj()
        require(fields.size <= 16)
        val result = mutableMapOf<String, Any>()
        fun copyString(key: String, required: Boolean = false, max: Int = 16_384, choices: Set<String>? = null) {
            if (required || key in fields) {
                val string = fields[key].string(max)
                require(choices == null || string in choices)
                result[key] = string
            }
        }
        fun copyBool(key: String, required: Boolean = false) {
            if (required || key in fields) result[key] = fields[key] as? Boolean ?: error("Invalid boolean")
        }
        fun copyNumber(key: String, allowed: ClosedFloatingPointRange<Double>, integral: Boolean = false) {
            if (key !in fields) return
            val number = (fields[key] as? NumberToken)?.text?.toDoubleOrNull() ?: error("Invalid number")
            require(number in allowed && (!integral || number == number.toInt().toDouble()))
            result[key] = number
        }

        listOf("accessibilityLabel", "accessibilityHint", "accessibilityValue", "accessibilityIdentifier")
            .forEach { copyString(it) }
        copyBool("disabled")
        when (kind) {
            Kind.text -> {
                copyString("text", required = true)
                copyString("style", choices = setOf("body", "headline", "title", "caption"))
                copyBool("selectable")
                copyNumber("maxLines", 1.0..100.0, integral = true)
            }
            Kind.button -> {
                copyString("label", required = true)
                copyString("role", choices = setOf("normal", "destructive", "cancel"))
            }
            Kind.textField -> {
                copyString("label", required = true)
                copyString("axis", choices = setOf("vertical", "horizontal"))
                copyString("value", required = true, max = if (result["axis"] == "vertical") 100_000 else 16_384)
            }
            Kind.toggle -> {
                copyString("label", required = true)
                copyBool("value", required = true)
            }
            Kind.vStack, Kind.hStack, Kind.zStack -> {
                val alignments = when (kind) {
                    Kind.vStack -> setOf("leading", "center", "trailing")
                    Kind.hStack -> setOf("top", "center", "bottom", "firstTextBaseline", "lastTextBaseline")
                    else -> setOf("center", "leading", "trailing", "top", "bottom", "topLeading", "topTrailing",
                        "bottomLeading", "bottomTrailing")
                }
                copyString("alignment", choices = alignments)
                if (kind != Kind.zStack) copyNumber("spacing", 0.0..256.0)
            }
            Kind.section, Kind.navigation -> copyString("title")
            Kind.list -> Unit
        }
        require(result.keys == fields.keys)
        return result.toMap()
    }

    private fun actions(kind: Kind, value: Any?): Map<Event, String> {
        val actions = mutableMapOf<Event, String>()
        for (entry in value.array(4)) {
            val binding = entry.fields("id", "event")
            val id = identifier(binding["id"])
            val event = Event.valueOf(binding["event"].string(128))
            require(actions.put(event, id) == null)
        }
        val events = actions.keys
        require(when (kind) {
            Kind.button -> events == setOf(Event.activate)
            Kind.toggle -> events == setOf(Event.valueChange)
            Kind.textField -> Event.textChange in events && events.all { it == Event.textChange || it == Event.submit }
            else -> events.isEmpty()
        })
        return actions.toMap()
    }

    private fun identifier(value: Any?): String = value.string(128).also {
        require(it.isNotEmpty() && it.none { char -> char < ' ' || char == '\u007f' })
    }

    private fun Any?.string(max: Int): String {
        val string = this as? String ?: error("Invalid string")
        require(string.length <= max && string.toByteArray(Charsets.UTF_8).size <= max)
        return string
    }

    @Suppress("UNCHECKED_CAST")
    private fun Any?.obj(): Map<String, Any?> = this as? Map<String, Any?> ?: error("Expected object")

    private fun Any?.fields(vararg expected: String) = obj().also { require(it.keys == expected.toSet()) }

    private fun Any?.array(max: Int) = (this as? List<*> ?: error("Expected array")).also { require(it.size <= max) }
}

private data class NumberToken(val text: String)

/** Strict JSON grammar, with bounds applied before mapping objects to the SDK schema. */
private class Json(private val input: String) {
    private var offset = 0
    private var values = 0

    fun read(): Any? = value(0).also {
        whitespace()
        require(offset == input.length)
    }

    private fun value(depth: Int): Any? {
        require(depth <= 130 && ++values <= 163_856)
        whitespace()
        return when (peek()) {
            '{' -> {
                val result = mutableMapOf<String, Any?>()
                entries('{', '}') {
                    val key = string(128)
                    require(key.toByteArray(Charsets.UTF_8).size <= 128 && !result.containsKey(key))
                    whitespace()
                    take(':')
                    result[key] = value(depth + 1)
                }
                result
            }
            '[' -> buildList { entries('[', ']') { add(value(depth + 1)) } }
            '"' -> string(100_000)
            't' -> literal("true", true)
            'f' -> literal("false", false)
            'n' -> literal("null", null)
            else -> number()
        }
    }

    private inline fun entries(open: Char, close: Char, item: () -> Unit) {
        take(open)
        whitespace()
        if (peek() != close) {
            while (true) {
                item()
                whitespace()
                if (peek() != ',') break
                offset++
                whitespace()
            }
        }
        take(close)
    }

    private fun string(max: Int): String {
        take('"')
        val result = buildString {
            while (peek() != '"') {
                val next = peek()
                require(next >= ' ' && length < max)
                offset++
                append(if (next == '\\') escape() else next)
            }
        }
        take('"')
        require(Charsets.UTF_8.newEncoder().canEncode(result))
        return result
    }

    private fun escape(): Char {
        val escaped = peek()
        offset++
        return when (escaped) {
            '"', '\\', '/' -> escaped
            'b' -> '\b'
            'f' -> '\u000c'
            'n' -> '\n'
            'r' -> '\r'
            't' -> '\t'
            'u' -> {
                require(offset + 4 <= input.length)
                val digits = input.substring(offset, offset + 4)
                require(digits.all { it in '0'..'9' || it in 'a'..'f' || it in 'A'..'F' })
                offset += 4
                digits.toInt(16).toChar()
            }
            else -> error("Invalid escape")
        }
    }

    private fun number(): NumberToken {
        val start = offset
        if (peek() == '-') offset++
        if (peek() == '0') offset++ else digits()
        if (peek() == '.') {
            offset++
            digits()
        }
        if (peek() == 'e' || peek() == 'E') {
            offset++
            if (peek() == '+' || peek() == '-') offset++
            digits()
        }
        return NumberToken(input.substring(start, offset))
    }

    private fun digits() {
        val start = offset
        while (peek() in '0'..'9') offset++
        require(offset > start && offset - start <= 128)
    }

    private fun literal(text: String, value: Any?): Any? {
        require(input.startsWith(text, offset))
        offset += text.length
        return value
    }

    private fun whitespace() {
        while (peek() == ' ' || peek() == '\t' || peek() == '\r' || peek() == '\n') offset++
    }

    private fun take(expected: Char) {
        require(peek() == expected)
        offset++
    }

    private fun peek() = input.getOrElse(offset) { '\u0000' }
}
