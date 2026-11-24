package dev.mixer.gc3

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.text.BasicText
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp

/** A credential-free surface for observing slot, coordinate and style changes. */
private class OfflineSiteMap : ComposeMapSurface {
    @Composable
    override fun Content(coordinate: SiteCoordinate, style: MapStyle) {
        val color = when (style) {
            MapStyle.STANDARD -> Color(0xFFD8E8E3)
            MapStyle.SATELLITE -> Color(0xFF304748)
        }
        val latitude = coordinate.latitude
        val longitude = coordinate.longitude
        Canvas(
            Modifier.fillMaxWidth().height(144.dp).semantics {
                contentDescription = "Project site $latitude, $longitude, ${style.name}"
            },
        ) {
            drawRect(color)
            val x = ((longitude + 180.0) / 360.0).toFloat() * size.width
            val y = ((90.0 - latitude) / 180.0).toFloat() * size.height
            drawCircle(Color(0xFFE26546), radius = 5.dp.toPx(), center = Offset(x, y))
        }
    }
}

@Composable
fun SignedMapFixture(cases: List<SignedMapCase>) {
    val host = remember(cases) { MapPlacementHost<ComposeMapSurface>(::OfflineSiteMap) }
    var mounted by remember(host) { mutableStateOf(host.mounted) }
    var next by remember(host) { mutableIntStateOf(0) }
    var status by remember(host) { mutableStateOf("Ready") }
    Column {
        val advance = Modifier.clickable(enabled = next < cases.size) {
            val case = cases[next++]
            val code = when (val admission = host.apply(case)) {
                is Admission.Accepted -> {
                    mounted = host.mounted
                    "accepted"
                }
                is Admission.Refused -> admission.code
            }
            status = "${case.name} $code"
        }
        BasicText("Apply next signed case", modifier = advance)
        BasicText(status)
        ProjectSiteMapLayout(mounted) { BasicText("Site details") }
    }
}
