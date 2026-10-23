import MixerUI

// Expected compiler failure: public resolved node output is immutable.
func cannotRewriteResolvedDisabled(_ node: inout UIResolvedAppearanceNodeV1) {
    node.disabled = false
}
