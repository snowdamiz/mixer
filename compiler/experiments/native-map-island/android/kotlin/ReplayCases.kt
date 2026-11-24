package dev.mixer.gc3

import java.io.InputStream
import java.util.Base64

class SignedMapCase internal constructor(
    val name: String,
    internal val signedManifest: ByteArray,
    internal val payload: ByteArray,
)

fun readSignedMapCases(input: InputStream): List<SignedMapCase> = input.bufferedReader().useLines { lines ->
    val decoder = Base64.getDecoder()
    lines.map { line ->
        val fields = line.split('\t')
        check(fields.size == 3)
        SignedMapCase(fields[0], decoder.decode(fields[1]), decoder.decode(fields[2]))
    }.toList()
}

fun <Surface : Any> MapPlacementHost<Surface>.apply(case: SignedMapCase): Admission =
    apply(case.signedManifest, case.payload)
