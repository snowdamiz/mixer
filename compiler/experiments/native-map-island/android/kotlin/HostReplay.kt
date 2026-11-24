package dev.mixer.gc3

import java.nio.file.Path
import java.security.MessageDigest
import java.util.HexFormat
import kotlin.io.path.inputStream
import kotlin.io.path.readLines

private data class Frame(val slot: MapSlot, val style: MapStyle, val coordinate: SiteCoordinate)

private val frames = mapOf(
    "mount" to Frame(MapSlot.ABOVE_DETAILS, MapStyle.STANDARD, SiteCoordinate(37.7749, -122.4194)),
    "move" to Frame(MapSlot.BELOW_DETAILS, MapStyle.SATELLITE, SiteCoordinate(40.6892, -74.0445)),
)

private fun sha256(bytes: ByteArray): String =
    HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))

fun main(args: Array<String>) {
    val cases = readSignedMapCases(Path.of(args[0]).inputStream())
    val lines = Path.of(args[1]).readLines()
    val installation = lines.first().split('\t')
    check(installation.size == 6)
    val (island, schema, runtime, rootSha, node) = installation
    val generation = installation[5]
    val expectedInstallation = InstalledMapGrant(island, schema, runtime)
    val expectedIdentity = NodeIdentity(node, generation.toLong())
    var factories = 0
    var applies = 0
    var acceptedStep = ""
    var surface: Any? = null
    val host = MapPlacementHost {
        ++factories
        Any()
    }
    check(cases.size == 32 && lines.size == cases.size + 1)
    for ((case, expectation) in cases.zip(lines.drop(1))) {
        val fields = expectation.split('\t')
        check(fields.size == 6)
        val (name, refusal, retained, count, releaseId) = fields
        val artifactSha = fields[5]
        check(case.name == name)
        val previous = host.mounted
        val outcome = when (val result = host.apply(case)) {
            is Admission.Accepted -> {
                check(refusal.isEmpty()) { "$name should refuse with $refusal" }
                val observed = result.placement
                val frame = frames.getValue(name)
                check(observed.slot == frame.slot && observed.style == frame.style && observed.coordinate == frame.coordinate)
                check(observed.node == expectedIdentity && observed.installed == expectedInstallation)
                check(observed.release == CheckedReleaseGrant(
                    schema, releaseId, artifactSha, sha256(case.signedManifest), sha256(case.payload), rootSha,
                ))
                val accepted = checkNotNull(host.mounted)
                check(accepted.placement === observed)
                surface = surface ?: accepted.surface
                check(accepted.surface === surface)
                check(accepted !== previous)
                ++applies
                acceptedStep = name
                "accepted"
            }
            is Admission.Refused -> {
                check(result.code == refusal) { "$name expected $refusal, got ${result.code}" }
                check(host.mounted === previous) { "$name replaced the mounted placement on refusal" }
                result.code
            }
        }
        check(retained == acceptedStep && count.toInt() == applies)
        check(factories == if (acceptedStep.isEmpty()) 0 else 1)
        val frame = host.mounted
        check(frame?.surface === surface)
        println(listOf(name, outcome, acceptedStep, applies, factories,
            frame?.placement?.release?.artifactSha256.orEmpty()).joinToString("\t"))
    }
    check(applies == 2 && factories == 1 && acceptedStep == "move")

    // Bound JNI input before any snapshot and keep the same warm frame.
    val accepted = host.mounted
    val mount = cases.single { it.name == "mount" }
    check(host.apply(ByteArray(65_537), mount.payload) == Admission.Refused("v3.document.size"))
    check(host.apply(mount.signedManifest, ByteArray(4_097)) == Admission.Refused("placement.malformed"))
    check(host.mounted === accepted && factories == 1)
    println("PASS: 32 signed cases, one surface, 2 size-bound controls")
}
