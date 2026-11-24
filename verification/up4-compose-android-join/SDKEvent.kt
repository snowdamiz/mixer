package dev.mixer.compose

import org.json.JSONObject

internal fun PrepareReceipt.node(id: String): Node = document.nodes.getValue(id)

internal fun PrepareReceipt.sdkEvent(node: Node, event: Event, value: Any? = null): ByteArray {
    val encoded = if (value is String) JSONObject.quote(value) else value.toString()
    val revision = java.lang.Long.toUnsignedString(documentRevisionBits)
    val generation = java.lang.Long.toUnsignedString(node.generationBits)
    return """{"revision":$revision,"identity":{"id":${JSONObject.quote(node.id)},"generation":$generation},"event":"${event.name}","value":$encoded}"""
        .encodeToByteArray()
}

internal fun PrepareReceipt.saveEvent() = sdkEvent(node("save"), Event.activate)
