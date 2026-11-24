package dev.mixer.gc3

enum class MapSlot { ABOVE_DETAILS, BELOW_DETAILS }
enum class MapStyle { STANDARD, SATELLITE }

data class NodeIdentity(val id: String, val generation: Long)
data class SiteCoordinate(val latitude: Double, val longitude: Double)
data class InstalledMapGrant(val islandId: String, val schemaSha256: String, val runtimeSha256: String)
data class CheckedReleaseGrant(
    val schemaSha256: String,
    val releaseId: String,
    val artifactSha256: String,
    val signedManifestSha256: String,
    val payloadSha256: String,
    val rootSha256: String,
)

class MapPlacement internal constructor(
    val node: NodeIdentity,
    val slot: MapSlot,
    val style: MapStyle,
    val coordinate: SiteCoordinate,
    val installed: InstalledMapGrant,
    val release: CheckedReleaseGrant,
)

sealed interface Admission {
    data class Accepted(val placement: MapPlacement) : Admission
    data class Refused(val code: String) : Admission
}

private object NativeMap {
    init {
        System.loadLibrary("GC3MapAdmission")
        System.loadLibrary("gc3_map_jni")
    }

    fun check(manifest: ByteArray, payload: ByteArray): Admission {
        val sink = ResultSink()
        val refusal = admit(manifest, payload, sink)
        if (refusal != null) {
            check(sink.placement == null)
            return Admission.Refused(refusal)
        }
        return Admission.Accepted(checkNotNull(sink.placement))
    }

    @JvmStatic private external fun admit(manifest: ByteArray, payload: ByteArray, sink: ResultSink): String?

    private class ResultSink {
        var placement: MapPlacement? = null
            private set

        // JNI borrows the input bytes for the duration of admit and invokes this
        // once with values copied out of Swift's checked placement.
        fun record(
            slot: Int, style: Int, latitude: Double, longitude: Double, generation: Long,
            nodeId: String, islandId: String, runtime: String, installedSchema: String,
            grantSchema: String, releaseId: String, artifact: String, manifest: String, payload: String, root: String,
        ) {
            check(placement == null)
            val typedSlot = when (slot) {
                1 -> MapSlot.ABOVE_DETAILS
                2 -> MapSlot.BELOW_DETAILS
                else -> error("Unknown admitted map slot $slot")
            }
            val typedStyle = when (style) {
                1 -> MapStyle.STANDARD
                2 -> MapStyle.SATELLITE
                else -> error("Unknown admitted map style $style")
            }
            placement = MapPlacement(
                NodeIdentity(nodeId, generation), typedSlot, typedStyle, SiteCoordinate(latitude, longitude),
                InstalledMapGrant(islandId, installedSchema, runtime),
                CheckedReleaseGrant(grantSchema, releaseId, artifact, manifest, payload, root),
            )
        }
    }
}

/** Own this host on the UI thread. The installed app supplies the surface factory. */
class MapPlacementHost<Surface : Any>(private val makeSurface: () -> Surface) {
    var mounted: MountedMap<Surface>? = null
        private set

    fun apply(manifest: ByteArray, payload: ByteArray): Admission {
        val admission = NativeMap.check(manifest, payload)
        if (admission is Admission.Accepted) {
            val previous = mounted
            check(previous == null || previous.placement.node == admission.placement.node)
            mounted = MountedMap(previous?.surface ?: makeSurface(), admission.placement)
        }
        return admission
    }
}

data class MountedMap<Surface : Any>(val surface: Surface, val placement: MapPlacement)
