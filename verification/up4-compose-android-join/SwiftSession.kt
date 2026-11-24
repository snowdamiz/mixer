package dev.mixer.compose

import java.nio.ByteBuffer
import java.util.UUID

/** The unchanged S5 JNI entry points. All calls and close belong to the caller thread. */
internal class SwiftSession(library: String? = null) : AutoCloseable {
    private val caller = Thread.currentThread()
    private var handle: Long

    init {
        if (library == null) System.loadLibrary("mixer_compose_editor_jni") else System.load(library)
        handle = openNative()
        check(handle != 0L)
    }

    fun call(operation: Operation, bytes: ByteArray): ByteArray? {
        check(Thread.currentThread() === caller && handle != 0L)
        return callNative(handle, operation.ordinal, bytes)
    }

    override fun close() {
        check(Thread.currentThread() === caller)
        if (handle == 0L) return
        val closing = handle
        handle = 0
        closeNative(closing)
    }

    private external fun openNative(): Long
    private external fun callNative(handle: Long, operation: Int, bytes: ByteArray): ByteArray?
    private external fun closeNative(handle: Long)
}

internal enum class Operation { PREPARE, DRAW, DISCARD, OFFER, RETIRE }
internal enum class Step { INITIAL, CANCEL, PROMOTE, SUPERSEDE, REPLACEMENT, REPLACEMENT_RETRY, REPLACEMENT_READBACK }

/** Test framing only. Long serialization preserves the original Swift UInt64 bits. */
internal data class Echo(val owner: UUID, val sequence: Long, val revision: Long, val opaque: UUID) {
    constructor(receipt: PrepareReceipt) :
        this(receipt.owner, receipt.sequenceBits, receipt.documentRevisionBits, receipt.opaqueId)

    fun bytes(): ByteArray = ByteBuffer.allocate(48)
        .putLong(owner.mostSignificantBits).putLong(owner.leastSignificantBits)
        .putLong(sequence).putLong(revision)
        .putLong(opaque.mostSignificantBits).putLong(opaque.leastSignificantBits)
        .array()

    fun wrongOpaque(): Echo =
        copy(opaque = UUID(opaque.mostSignificantBits xor 1, opaque.leastSignificantBits))

    companion object {
        fun read(bytes: ByteBuffer): Echo =
            Echo(UUID(bytes.long, bytes.long), bytes.long, bytes.long, UUID(bytes.long, bytes.long))
    }
}

internal class Proposal(val echo: Echo, val document: ByteArray, val generations: LongArray)

internal data class OfferResult(val admitted: Boolean, val detail: String) {
    companion object {
        fun decode(bytes: ByteArray): OfferResult {
            val response = bytes.decodeToString(throwOnInvalidSequence = true)
            return when {
                response.startsWith("admitted ") -> OfferResult(true, response)
                response.startsWith("rejected ") -> OfferResult(false, response)
                else -> error("Unexpected Swift dispatch response: $response")
            }
        }
    }
}

internal class JoinBridge(private val session: SwiftSession) : ComposeSwiftBridge {
    data class Draw(val receipt: PrepareReceipt, val replacing: PrepareReceipt?, val admitted: Boolean)
    data class Discard(val receipt: PrepareReceipt, val canceled: Boolean)
    data class Input(val receipt: PrepareReceipt, val envelope: ByteArray, val result: OfferResult)

    val draws = mutableListOf<Draw>()
    val discards = mutableListOf<Discard>()
    val inputs = mutableListOf<Input>()
    val retirements = mutableListOf<PrepareReceipt>()

    fun frame(step: Step): Proposal {
        val buffer = ByteBuffer.wrap(checkNotNull(session.call(Operation.PREPARE, byteArrayOf(step.ordinal.toByte()))))
        val echo = Echo.read(buffer)
        val count = buffer.int
        check(count > 0 && count <= (buffer.remaining() - 1) / Long.SIZE_BYTES)
        val generations = LongArray(count) { buffer.long }
        val document = ByteArray(buffer.remaining()).also { buffer.get(it) }
        return Proposal(echo, document, generations)
    }

    override fun didDraw(receipt: PrepareReceipt, replacing: PrepareReceipt?): Boolean {
        val accepted = acknowledge(Echo(receipt), replacing?.let(::Echo))
        draws += Draw(receipt, replacing, accepted)
        return accepted
    }

    fun acknowledge(echo: Echo, replacing: Echo? = null): Boolean =
        session.call(Operation.DRAW, replacing?.let { echo.bytes() + it.bytes() } ?: echo.bytes()) != null

    override fun discard(receipt: PrepareReceipt) {
        discards += Discard(receipt, cancel(Echo(receipt)))
    }

    fun cancel(echo: Echo): Boolean = session.call(Operation.DISCARD, echo.bytes()) != null

    override fun offer(receipt: PrepareReceipt, envelopeUtf8: ByteArray): Boolean {
        val result = send(Echo(receipt), envelopeUtf8)
        inputs += Input(receipt, envelopeUtf8, result)
        return result.admitted
    }

    fun send(echo: Echo, envelope: ByteArray): OfferResult =
        OfferResult.decode(checkNotNull(session.call(Operation.OFFER, echo.bytes() + envelope)))

    override fun retire(receipt: PrepareReceipt) {
        check(retireEcho(Echo(receipt)))
        retirements += receipt
    }

    fun retireEcho(echo: Echo): Boolean = session.call(Operation.RETIRE, echo.bytes()) != null
}
