package dev.mixer.gc3

import androidx.compose.foundation.layout.Column
import androidx.compose.runtime.Composable
import androidx.compose.runtime.movableContentOf
import androidx.compose.runtime.remember

/** Installed code owns the map renderer and reads the admitted coordinate and style. */
interface ComposeMapSurface {
    @Composable fun Content(coordinate: SiteCoordinate, style: MapStyle)
}

@Composable
fun ProjectSiteMapLayout(
    mounted: MountedMap<ComposeMapSurface>?,
    details: @Composable () -> Unit,
) {
    val map = if (mounted != null) {
        val surface = mounted.surface
        remember(surface, mounted.placement.node) {
            movableContentOf { placement: MapPlacement -> surface.Content(placement.coordinate, placement.style) }
        }
    } else {
        null
    }
    Column {
        if (mounted?.placement?.slot == MapSlot.ABOVE_DETAILS) map?.invoke(mounted.placement)
        details()
        if (mounted?.placement?.slot == MapSlot.BELOW_DETAILS) map?.invoke(mounted.placement)
    }
}
