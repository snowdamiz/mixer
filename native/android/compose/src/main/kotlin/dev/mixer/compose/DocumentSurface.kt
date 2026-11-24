package dev.mixer.compose

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicText
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.LocalTextSelectionColors
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.text.selection.TextSelectionColors
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.layout.FirstBaseline
import androidx.compose.ui.layout.LastBaseline
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.disabled
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.text.TextRange
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp

internal class EditorValue(initial: String) {
    var value by mutableStateOf(TextFieldValue(initial, TextRange(initial.length)))
}

internal class ControlInput(
    val emit: (Event, Any?) -> Boolean,
    val canEditLocally: () -> Boolean,
)

private typealias BindControl = @Composable (Node) -> ControlInput

@Composable
internal fun DocumentSurface(
    root: Node,
    theme: SharedTheme,
    editorValues: MutableMap<Long, EditorValue>,
    bindControl: BindControl,
    drawMarker: (DrawScope) -> Unit,
) {
    val density = LocalDensity.current
    // The platform preference has already selected one shared metric profile.
    CompositionLocalProvider(LocalDensity provides Density(density.density, 1f)) {
        Box(Modifier.fillMaxSize().clipToBounds().background(theme.canvas).semantics {
            testTagsAsResourceId = true
        }.drawWithContent {
            drawContent()
            if (drawContext.canvas.nativeCanvas.isHardwareAccelerated) drawMarker(this)
        }.padding(16.dp)) {
            Render(root, theme, editorValues, bindControl)
        }
    }
}

@Composable
private fun Render(node: Node, theme: SharedTheme, editors: MutableMap<Long, EditorValue>,
                   bindControl: BindControl, placement: Modifier = Modifier) {
    val modifier = placement.testTag(node.string("accessibilityIdentifier") ?: node.id).semantics {
        val label = node.string("accessibilityLabel")
        val hint = node.string("accessibilityHint")
        if (label != null || hint != null) contentDescription = listOfNotNull(label, hint).joinToString(". ")
        node.string("accessibilityValue")?.let { stateDescription = it }
        if (node.disabled) disabled()
    }
    when (node.kind) {
        Kind.text -> {
            val style = theme.text(node.string("style") ?: "body")
            val lines = node.number("maxLines")?.toInt() ?: Int.MAX_VALUE
            if (node.flag("selectable")) {
                SelectionContainer(modifier) {
                    BasicText(node.string("text")!!, style = style, maxLines = lines, overflow = TextOverflow.Ellipsis)
                }
            } else {
                BasicText(node.string("text")!!, modifier, style, maxLines = lines, overflow = TextOverflow.Ellipsis)
            }
        }
        Kind.vStack -> Column(modifier, horizontalAlignment = node.horizontal()) {
            node.children.forEachIndexed { index, child ->
                if (index > 0) {
                    val previous = node.children[index - 1]
                    val bodyCaption = previous.kind == Kind.text && (previous.string("style") ?: "body") == "body" &&
                        child.kind == Kind.text && child.string("style") == "caption"
                    Box(Modifier.height((node.number("spacing") ?: if (bodyCaption) 2.0 else 8.0).dp))
                }
                key(child.generationBits) { Render(child, theme, editors, bindControl) }
            }
        }
        Kind.hStack -> Row(modifier, horizontalArrangement = Arrangement.spacedBy((node.number("spacing") ?: 8.0).dp),
            verticalAlignment = when (node.string("alignment")) {
                "top" -> Alignment.Top
                "bottom" -> Alignment.Bottom
                else -> Alignment.CenterVertically
            }) {
            Children(node) { child ->
                val alignment = when (node.string("alignment")) {
                    "firstTextBaseline" -> Modifier.alignBy(FirstBaseline)
                    "lastTextBaseline" -> Modifier.alignBy(LastBaseline)
                    else -> Modifier
                }
                Render(child, theme, editors, bindControl, alignment)
            }
        }
        Kind.zStack -> Box(modifier, contentAlignment = node.overlay()) {
            Children(node) { Render(it, theme, editors, bindControl) }
        }
        Kind.list -> ListSurface(node, theme, editors, bindControl, modifier)
        Kind.section -> Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            node.string("title")?.let { BasicText(it, style = theme.text("sectionHeader", theme.header)) }
            Children(node) { Render(it, theme, editors, bindControl) }
        }
        Kind.navigation -> Column(modifier.fillMaxSize()) {
            node.string("title")?.takeIf { it.isNotEmpty() }?.let {
                Box(Modifier.fillMaxWidth().defaultMinSize(minHeight = 106.dp).padding(bottom = 8.dp),
                    contentAlignment = Alignment.BottomStart) {
                    BasicText(it, style = theme.text("navigationExpanded"))
                }
            }
            Children(node) { Render(it, theme, editors, bindControl) }
        }
        Kind.button -> Button(node, theme, bindControl(node), modifier)
        Kind.toggle -> Toggle(node, theme, bindControl(node), modifier)
        Kind.textField -> Field(node, theme, editors, bindControl(node), modifier)
    }
}

@Composable
private fun Children(node: Node, render: @Composable (Node) -> Unit) {
    for (child in node.children) key(child.generationBits) { render(child) }
}

@Composable
private fun ListSurface(node: Node, theme: SharedTheme, editors: MutableMap<Long, EditorValue>,
                        bindControl: BindControl, modifier: Modifier) {
    val row: @Composable (Node) -> Unit = { child ->
        Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(26.dp)).background(theme.surface)
            .defaultMinSize(minHeight = theme.typography.row.dp).padding(horizontal = 16.dp, vertical = 15.dp),
            contentAlignment = Alignment.CenterStart) {
            Render(child, theme, editors, bindControl)
        }
    }
    LazyColumn(modifier.fillMaxWidth(), contentPadding = PaddingValues(bottom = 10.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp)) {
        items(items = node.children, key = { it.generationBits }) { row(it) }
    }
}

@Composable
private fun Button(node: Node, theme: SharedTheme, input: ControlInput, modifier: Modifier) {
    val interactions = remember { MutableInteractionSource() }
    val focused by interactions.collectIsFocusedAsState()
    val pressed by interactions.collectIsPressedAsState()
    val tint = if (node.string("role") == "destructive") theme.destructive else theme.accent
    val shape = RoundedCornerShape(8.dp)
    Box(modifier.defaultMinSize(minWidth = 44.dp, minHeight = 44.dp).clip(shape)
        .background(if (pressed) tint.copy(alpha = .12f) else Color.Transparent)
        .then(if (focused) Modifier.border(2.dp, tint, shape) else Modifier)
        .clickable(enabled = !node.disabled, role = Role.Button, interactionSource = interactions, indication = null) {
            input.emit(Event.activate, null)
        }, contentAlignment = Alignment.Center) {
        BasicText(node.string("label")!!, style = theme.text(color = if (node.disabled) theme.disabled else tint))
    }
}

@Composable
private fun Toggle(node: Node, theme: SharedTheme, input: ControlInput, modifier: Modifier) {
    val checked = node.flag("value")
    val interactions = remember { MutableInteractionSource() }
    val focused by interactions.collectIsFocusedAsState()
    val pressed by interactions.collectIsPressedAsState()
    val track = when {
        checked && node.disabled -> theme.trackOnDisabled
        checked -> theme.trackOn
        node.disabled -> theme.trackOffDisabled
        else -> theme.trackOff
    }
    val shape = RoundedCornerShape(14.dp)
    Row(modifier.fillMaxWidth().defaultMinSize(minHeight = 44.dp)
        .then(if (focused) Modifier.border(2.dp, theme.accent, shape) else Modifier)
        .background(if (pressed) theme.accent.copy(alpha = .12f) else Color.Transparent, shape)
        .toggleable(checked, enabled = !node.disabled, role = Role.Switch, interactionSource = interactions,
            indication = null, onValueChange = { input.emit(Event.valueChange, it) }),
        horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
        BasicText(node.string("label")!!, Modifier.weight(1f),
            theme.text(color = if (node.disabled) theme.disabled else theme.foreground))
        Box(Modifier.size(63.dp, 28.dp).background(track, shape).padding(2.dp),
            contentAlignment = if (checked) Alignment.CenterEnd else Alignment.CenterStart) {
            Box(Modifier.size(37.dp, 24.dp).background(
                if (node.disabled) theme.thumbDisabled else Color.White, RoundedCornerShape(12.dp)))
        }
    }
}

@Composable
private fun Field(node: Node, theme: SharedTheme, editors: MutableMap<Long, EditorValue>,
                  input: ControlInput, modifier: Modifier) {
    val editor = remember(node.generationBits) { EditorValue(node.string("value")!!) }
    DisposableEffect(editor) {
        editors[node.generationBits] = editor
        onDispose { if (editors[node.generationBits] === editor) editors.remove(node.generationBits) }
    }
    val interactions = remember { MutableInteractionSource() }
    val focused by interactions.collectIsFocusedAsState()
    val shape = RoundedCornerShape(8.dp)
    val vertical = node.string("axis") == "vertical"
    val submit = Event.submit in node.actions
    val label = node.string("label")!!
    CompositionLocalProvider(LocalTextSelectionColors provides TextSelectionColors(theme.accent, theme.accent.copy(alpha = .24f))) {
        BasicTextField(
            editor.value,
            onValueChange = { next ->
                val admitted = if (editor.value.text == next.text) {
                    input.canEditLocally()
                } else {
                    input.emit(Event.textChange, next.text)
                }
                if (admitted) editor.value = next
            },
            modifier = modifier.fillMaxWidth().widthIn(min = 44.dp).defaultMinSize(minHeight = 44.dp)
                .then(if (focused) Modifier.border(2.dp, theme.accent, shape) else Modifier)
                .semantics {
                    if (node.string("accessibilityLabel") == null) contentDescription = label
                },
            enabled = !node.disabled,
            textStyle = theme.text(color = if (node.disabled) theme.disabled else theme.foreground),
            singleLine = !vertical,
            maxLines = if (vertical) 8 else 1,
            keyboardOptions = if (!vertical && submit) KeyboardOptions(imeAction = ImeAction.Done) else KeyboardOptions.Default,
            keyboardActions = if (submit) KeyboardActions(onDone = { input.emit(Event.submit, null) }) else KeyboardActions.Default,
            interactionSource = interactions,
            cursorBrush = SolidColor(theme.accent),
            decorationBox = { inner ->
                Box(Modifier.fillMaxWidth().defaultMinSize(minHeight = 44.dp), contentAlignment = Alignment.CenterStart) {
                    if (editor.value.text.isEmpty()) {
                        BasicText(label, style = theme.text(color = if (node.disabled) theme.disabled else theme.placeholder))
                    }
                    inner()
                }
            },
        )
    }
}

private fun Node.horizontal() = when (string("alignment")) {
    "leading" -> Alignment.Start
    "trailing" -> Alignment.End
    else -> Alignment.CenterHorizontally
}

private fun Node.overlay() = when (string("alignment")) {
    "top" -> Alignment.TopCenter
    "bottom" -> Alignment.BottomCenter
    "leading" -> Alignment.CenterStart
    "trailing" -> Alignment.CenterEnd
    "topLeading" -> Alignment.TopStart
    "topTrailing" -> Alignment.TopEnd
    "bottomLeading" -> Alignment.BottomStart
    "bottomTrailing" -> Alignment.BottomEnd
    else -> Alignment.Center
}
