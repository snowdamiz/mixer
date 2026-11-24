package dev.mixer.compose

import android.graphics.Bitmap
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import java.util.UUID

/** Proof of the exact candidate in an API 28 window buffer, following S5's PixelCopy check. */
internal class BufferMarker(canvasArgb: Int) {
    private val nonce = UUID.randomUUID()
    // Reserve the top-left corner in the common canvas padding. Both sRGB colours
    // stay close to the opaque shared canvas colour and are only drawn in trial frames.
    private val zero = canvasArgb and 0xffffff00.toInt() or ((canvasArgb and 0xff) xor 0x1)
    private val one = canvasArgb and 0xffffff00.toInt() or ((canvasArgb and 0xff) xor 0x7)

    fun draw(scope: DrawScope) = with(scope) {
        for (index in 0 until BITS) {
            drawRect(Color(pixel(index)), Offset((index % SIDE).toFloat(), (index / SIDE).toFloat()), Size(1f, 1f))
        }
    }

    fun matches(bitmap: Bitmap): Boolean =
        (0 until BITS).all { bitmap.getPixel(it % SIDE, it / SIDE) == pixel(it) }

    private fun pixel(index: Int): Int {
        val word = if (index < 64) nonce.mostSignificantBits else nonce.leastSignificantBits
        return if (word.ushr(index % 64) and 1L == 0L) zero else one
    }

    companion object {
        const val SIDE = 16
        private const val BITS = 128
    }
}
