package dev.mixer.compose

import android.os.Bundle
import androidx.activity.ComponentActivity
import org.json.JSONObject

class SmokeActivity : ComponentActivity() {
    internal lateinit var host: ComposeDocumentHost
    internal val bridge = SmokeBridge()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        host = ComposeDocumentHost(window, bridge)
        setContentView(host)
    }
}

internal class SmokeBridge : ComposeSwiftBridge {
    var selected: PrepareReceipt? = null
    var expected: PrepareReceipt? = null
    var refuse = false
    val draws = mutableListOf<PrepareReceipt>()
    val discards = mutableListOf<PrepareReceipt>()
    val events = mutableListOf<Pair<PrepareReceipt, JSONObject>>()

    override fun didDraw(receipt: PrepareReceipt, replacing: PrepareReceipt?): Boolean {
        check(expected === receipt) { "Bridge got the wrong selected receipt" }
        check(replacing === selected?.takeIf { it.stageOwner !== receipt.stageOwner })
        draws += receipt
        if (refuse) return false
        selected = receipt
        return true
    }

    override fun discard(receipt: PrepareReceipt) {
        check(expected === receipt)
        discards += receipt
    }

    override fun offer(receipt: PrepareReceipt, envelopeUtf8: ByteArray): Boolean {
        check(selected === receipt)
        events += receipt to JSONObject(envelopeUtf8.decodeToString(throwOnInvalidSequence = true))
        return true
    }

    override fun retire(receipt: PrepareReceipt) {
        check(selected === receipt)
        selected = null
    }
}
