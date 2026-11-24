package __PACKAGE__

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.ViewCompositionStrategy
import dev.mixer.compose.ControlInput
import dev.mixer.compose.DocumentReader
import dev.mixer.compose.DocumentSurface
import dev.mixer.compose.EditorValue
import dev.mixer.compose.SharedTheme
import java.nio.ByteBuffer

class MixerComposeActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val documentBytes = assets.open("mixer/bundled-document.json").use { it.readBytes() }
        val identityBytes = assets.open("mixer/bundled-generations.bin").use { it.readBytes() }
        require(identityBytes.size % Long.SIZE_BYTES == 0)
        val buffer = ByteBuffer.wrap(identityBytes)
        val generations = LongArray(identityBytes.size / Long.SIZE_BYTES) { buffer.long }
        val document = checkNotNull(DocumentReader.decode(documentBytes, generations))
        val theme = checkNotNull(SharedTheme.capture(resources))
        val editorValues = mutableMapOf<Long, EditorValue>()
        val disabledInput = ControlInput(emit = { _, _ -> false }, canEditLocally = { false })
        val surface = ComposeView(this).apply {
            setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)
            setContent { DocumentSurface(document.root, theme, editorValues, { disabledInput }, {}) }
        }
        surface.setOnApplyWindowInsetsListener { view, insets ->
            @Suppress("DEPRECATION")
            view.setPadding(insets.systemWindowInsetLeft, insets.systemWindowInsetTop,
                insets.systemWindowInsetRight, insets.systemWindowInsetBottom)
            insets
        }
        setContentView(surface)
    }
}
