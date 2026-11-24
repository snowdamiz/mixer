package dev.mixer.compose

internal enum class Kind {
    text, button, textField, toggle, vStack, hStack, zStack, list, section, navigation
}

internal enum class Event {
    activate, textChange, valueChange, submit
}

internal data class Node(
    val id: String,
    val generationBits: Long,
    val kind: Kind,
    val properties: Map<String, Any>,
    val actions: Map<Event, String>,
    val children: List<Node>,
    val disabled: Boolean,
) {
    fun string(key: String): String? = properties[key] as? String
    fun flag(key: String): Boolean = properties[key] == true
    fun number(key: String): Double? = properties[key] as? Double
    val textLimit: Int get() = if (string("axis") == "vertical") 100_000 else 16_384
}

internal class Document(val revisionBits: Long, val root: Node, val nodes: Map<String, Node>)
