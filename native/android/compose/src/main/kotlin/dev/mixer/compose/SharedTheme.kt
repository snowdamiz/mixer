package dev.mixer.compose

import android.content.res.Configuration
import android.content.res.Resources
import android.util.TypedValue
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import kotlin.math.abs

/** System-sans subset of MixerUI's measuredShared2 default appearance. */
internal data class SharedTheme(val dark: Boolean, val typography: TextProfile) {
    val canvasArgb: Int get() = if (dark) 0xff000000.toInt() else 0xfff2f2f7.toInt()
    val canvas: Color get() = Color(canvasArgb)
    val surface: Color get() = if (dark) Color(0xff1c1c1e) else Color.White
    val foreground: Color get() = if (dark) Color.White else Color.Black
    val placeholder: Color get() = if (dark) Color(0xff5a5a5e) else Color(0xffb3b3b5)
    val disabled: Color get() = if (dark) Color(0xff555556) else Color(0xffbfbfbf)
    val header: Color get() = if (dark) Color(0xff8d8d93) else Color(0xff85858b)
    val accent: Color get() = if (dark) Color(0xff0091ff) else Color(0xff0088ff)
    val destructive: Color get() = if (dark) Color(0xffff4245) else Color(0xffff383c)
    val trackOff: Color get() = if (dark) Color(0xff5a5a5e) else Color(0xffc5c5c7)
    val trackOffDisabled: Color get() = if (dark) Color(0xff38383b) else Color(0xffe5e5e7)
    val trackOn: Color get() = if (dark) Color(0xff30d158) else Color(0xff34c759)
    val trackOnDisabled: Color get() = if (dark) Color(0xff26773b) else Color(0xff99e3ac)
    val thumbDisabled: Color get() = if (dark) Color(0xff8e8e8f) else Color.White
    val separator: Color get() = if (dark) Color(0xff38383b) else Color(0xffe8e8e8)

    fun text(role: String = "body", color: Color = foreground): TextStyle {
        val size = when (role) {
            "title" -> typography.title
            "caption" -> typography.caption
            "navigationExpanded" -> typography.expanded
            else -> typography.body
        }
        val weight = when (role) {
            "sectionHeader", "headline" -> FontWeight.SemiBold
            "navigationExpanded" -> FontWeight.Bold
            else -> FontWeight.Normal
        }
        return TextStyle(color = color, fontSize = size.sp, fontWeight = weight, fontFamily = FontFamily.SansSerif)
    }

    companion object {
        fun capture(resources: Resources): SharedTheme? {
            val metrics = resources.displayMetrics
            val body = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 17f, metrics) / metrics.density
            val profile = TextProfile.nearest(body) ?: return null
            val dark = resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES
            return SharedTheme(dark, profile)
        }
    }
}

internal enum class TextProfile(val body: Int, val title: Int, val caption: Int, val expanded: Int, val row: Int) {
    xs(14, 25, 11, 31, 49), s(15, 26, 11, 32, 50), m(16, 27, 11, 33, 51), l(17, 28, 12, 34, 52),
    xl(19, 30, 14, 36, 54), xxl(21, 32, 16, 38, 56), xxxl(23, 34, 18, 40, 59),
    a1(28, 38, 22, 44, 59), a2(33, 43, 26, 48, 59), a3(40, 48, 32, 52, 59),
    a4(47, 53, 37, 56, 59), a5(53, 58, 43, 60, 59);

    companion object {
        fun nearest(body: Float): TextProfile? {
            if (body !in xs.body.toFloat()..a5.body.toFloat()) return null
            return entries.reversed().minBy { abs(it.body - body) }
        }
    }
}
