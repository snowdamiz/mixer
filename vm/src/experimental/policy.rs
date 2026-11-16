//! Closed borrowed policies. Frozen validation never materializes widened Limits.
use crate::{Limits, Profile};

// Closed development tuple selected after the complete pinned UI module audit.
// Aggregate runtime arenas, cache, work and deadlines remain independently bounded.
struct UIEnvelope { parameters: usize, locals: usize, operands: usize }
const UI_ENVELOPE: UIEnvelope = UIEnvelope { parameters: 783, locals: 1575, operands: 783 };

// Command ceilings are selected at compile time without another runtime tag.
pub(crate) enum Policy<'a, const COMMAND: bool = false, const UI: bool = false> {
    Frozen(&'a Limits),
    #[cfg(feature = "experimental-swift-reactor")]
    SwiftReactorExperimentV1,
}
impl<'a> Policy<'a> {
    pub fn frozen(limits: &'a Limits) -> Self {
        Self::Frozen(limits)
    }
}
impl<const COMMAND: bool, const UI: bool> Policy<'_, COMMAND, UI> {
    pub fn legacy_imports(&self) -> bool {
        matches!(self, Self::Frozen(_))
    }
    pub fn floats(&self) -> bool {
        match self {
            Self::Frozen(l) => l.profile.floats(),
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => true,
        }
    }
    pub fn tables(&self) -> bool {
        match self {
            Self::Frozen(l) => l.profile == Profile::TableMemoryV3,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => true,
        }
    }
    pub fn module_bytes(&self) -> usize {
        match self {
            Self::Frozen(l) => l.module_bytes,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => 64 * 1024 * 1024,
        }
    }
    pub fn functions(&self) -> usize {
        match self {
            Self::Frozen(l) => l.functions,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => if COMMAND { 131_072 } else { 80_000 },
        }
    }
    pub fn types(&self) -> usize {
        match self {
            Self::Frozen(l) => l.types,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => 512,
        }
    }
    pub fn type_parameters_total(&self) -> usize {
        match self {
            Self::Frozen(_) => usize::MAX,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => 8192,
        }
    }
    pub fn parameters_per_signature(&self) -> usize {
        match self {
            Self::Frozen(l) => l.locals,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => if UI { UI_ENVELOPE.parameters } else { 128 },
        }
    }
    pub fn parameters_plus_locals(&self) -> usize {
        match self {
            Self::Frozen(l) => l.locals,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => if UI { UI_ENVELOPE.locals } else { 256 },
        }
    }
    pub fn local_groups(&self) -> usize {
        match self {
            Self::Frozen(l) => l.locals,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => 256,
        }
    }
    pub fn instructions(&self) -> usize {
        match self {
            Self::Frozen(l) => l.instructions,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => if COMMAND { 16_000_000 } else { 8_000_000 },
        }
    }
    pub fn operand_stack(&self) -> usize {
        match self {
            Self::Frozen(l) => l.operand_stack,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => if UI { UI_ENVELOPE.operands } else { 128 },
        }
    }
    pub fn control_depth(&self) -> usize {
        match self {
            Self::Frozen(l) => l.control_depth,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => 512,
        }
    }
    pub fn globals(&self) -> usize {
        match self {
            Self::Frozen(_) => 1024,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => 8192,
        }
    }
    pub fn exports(&self) -> usize {
        4096
    }
    pub fn data_segments(&self) -> usize {
        4096
    }
    pub fn element_segments(&self) -> usize {
        4096
    }
    pub fn name_bytes(&self) -> usize {
        4096
    }
    pub fn table_elements(&self) -> usize {
        match self {
            Self::Frozen(l) => l.table_elements,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => 65_536,
        }
    }
    pub fn memory_pages(&self) -> u32 {
        match self {
            Self::Frozen(l) => l.memory_pages,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => 768,
        }
    }
}
#[cfg(feature = "experimental-swift-reactor")]
impl Policy<'static> {
    pub fn swift() -> Self {
        Self::SwiftReactorExperimentV1
    }
}

#[cfg(feature = "experimental-swift-reactor")]
impl Policy<'static, true> {
    pub fn command() -> Self {
        Self::SwiftReactorExperimentV1
    }
    pub fn ui() -> Policy<'static, true, true> {
        Policy::SwiftReactorExperimentV1
    }
}

// Validation-only ABI result. UI export indexes are not retained in the
// compact decode-policy field of a stock proof.
#[cfg(feature = "experimental-swift-reactor")]
pub(crate) enum SwiftSelection {
    Reactor,
    Command { entry: u32 },
    UI { entries: [u32; 4] },
}
#[cfg(feature = "experimental-swift-reactor")]
impl SwiftSelection {
    pub(crate) fn decode_policy(&self) -> SwiftDecodePolicy {
        match *self {
            Self::Reactor => SwiftDecodePolicy::Reactor,
            Self::Command { entry } => SwiftDecodePolicy::Command { entry },
            Self::UI { .. } => SwiftDecodePolicy::UI {},
        }
    }
    #[cfg(test)]
    pub fn legacy_imports(&self) -> bool { self.decode_policy().legacy_imports() }
    #[cfg(test)]
    pub fn module_bytes(&self) -> usize { self.decode_policy().module_bytes() }
    #[cfg(test)]
    pub fn table_elements(&self) -> usize { self.decode_policy().table_elements() }
    #[cfg(test)]
    pub fn memory_pages(&self) -> u32 { self.decode_policy().memory_pages() }
    pub fn floats(&self) -> bool { self.decode_policy().floats() }
    pub fn tables(&self) -> bool { self.decode_policy().tables() }
    pub fn parameters_per_signature(&self) -> usize { self.decode_policy().parameters_per_signature() }
    pub fn parameters_plus_locals(&self) -> usize { self.decode_policy().parameters_plus_locals() }
    pub fn local_groups(&self) -> usize { self.decode_policy().local_groups() }
    pub fn operand_stack(&self) -> usize { self.decode_policy().operand_stack() }
    pub fn control_depth(&self) -> usize { self.decode_policy().control_depth() }
    pub fn instructions(&self) -> usize { self.decode_policy().instructions() }
}
// Decode authority stores the policy kind and command entry only. UI entry
// metadata already belongs to the sealed UI proof's retained export descriptors.
#[cfg(feature = "experimental-swift-reactor")]
#[derive(Clone, Copy, Debug)]
pub(crate) enum SwiftDecodePolicy {
    Reactor,
    Command { entry: u32 },
    UI {},
}
#[cfg(feature = "experimental-swift-reactor")]
impl SwiftDecodePolicy {
    #[cfg(test)]
    pub fn legacy_imports(&self) -> bool { Policy::swift().legacy_imports() }
    #[cfg(test)]
    pub fn module_bytes(&self) -> usize { Policy::swift().module_bytes() }
    #[cfg(test)]
    pub fn table_elements(&self) -> usize { Policy::swift().table_elements() }
    #[cfg(test)]
    pub fn memory_pages(&self) -> u32 { Policy::swift().memory_pages() }
    pub fn floats(&self) -> bool { Policy::swift().floats() }
    pub fn tables(&self) -> bool { Policy::swift().tables() }
    pub fn parameters_per_signature(&self) -> usize {
        match self { Self::UI { .. } => Policy::ui().parameters_per_signature(), _ => Policy::swift().parameters_per_signature() }
    }
    pub fn parameters_plus_locals(&self) -> usize { match self { Self::UI { .. } => Policy::ui().parameters_plus_locals(), _ => Policy::swift().parameters_plus_locals() } }
    pub fn local_groups(&self) -> usize { Policy::swift().local_groups() }
    pub fn operand_stack(&self) -> usize { match self { Self::UI { .. } => Policy::ui().operand_stack(), _ => Policy::swift().operand_stack() } }
    pub fn control_depth(&self) -> usize { Policy::swift().control_depth() }
    pub fn instructions(&self) -> usize {
        match self {
            Self::Reactor => Policy::swift().instructions(),
            Self::Command { .. } | Self::UI { .. } => Policy::command().instructions(),
        }
    }
}

#[cfg(all(test, feature = "experimental-swift-reactor"))]
mod tests {
    use super::*;

    #[test]
    fn command_selection_keeps_distinct_validation_and_decode_ceilings() {
        let reactor = Policy::swift();
        let command = Policy::command();
        assert_eq!(reactor.functions(), 80_000);
        assert_eq!(command.functions(), 131_072);
        assert_eq!(reactor.instructions(), 8_000_000);
        assert_eq!(command.instructions(), 16_000_000);
        assert_eq!(SwiftSelection::Reactor.instructions(), reactor.instructions());
        assert_eq!(SwiftSelection::Command { entry: 34 }.instructions(), command.instructions());
        assert_eq!(command.module_bytes(), reactor.module_bytes());
        assert_eq!(command.memory_pages(), reactor.memory_pages());
        assert_eq!(command.table_elements(), reactor.table_elements());
        assert_eq!(command.parameters_plus_locals(), reactor.parameters_plus_locals());
        assert_eq!(command.control_depth(), reactor.control_depth());
        assert!(!command.legacy_imports());
    }
}

#[cfg(all(test, feature = "experimental-swift-reactor"))]
mod ui_policy_tests {
    use super::*;
    #[test]
    fn ui_signature_envelope_is_separate_and_other_guards_stay_fixed() {
        let ui = Policy::ui(); let command = Policy::command(); let reactor = Policy::swift();
        assert_eq!(ui.parameters_per_signature(), 783);
        assert_eq!(command.parameters_per_signature(), 128);
        assert_eq!(reactor.parameters_per_signature(), 128);
        assert_eq!(SwiftSelection::UI { entries: [34,35,36,37] }.parameters_per_signature(), 783);
        assert_eq!(SwiftSelection::Command { entry: 34 }.parameters_per_signature(), 128);
        assert_eq!(ui.parameters_plus_locals(), 1575);
        assert_eq!(command.parameters_plus_locals(), 256);
        assert_eq!(ui.operand_stack(), 783);
        assert_eq!(command.operand_stack(), 128);
        assert_eq!(ui.type_parameters_total(), command.type_parameters_total());
        assert_eq!(ui.memory_pages(), command.memory_pages());
        assert_eq!(ui.instructions(), command.instructions());
    }
}

#[cfg(all(test, feature = "experimental-swift-reactor"))]
mod r3554_pure {
    use super::*;
    #[test]
    fn stock_and_ui_policy_limits_are_separate() {
        let limits = Limits::default(); let frozen = Policy::frozen(&limits);
        let reactor = Policy::swift(); let command = Policy::command(); let ui = Policy::ui();
        assert_eq!(std::mem::size_of_val(&frozen), 8);
        assert_eq!(std::mem::size_of_val(&reactor), 8);
        assert_eq!(std::mem::size_of_val(&command), 8);
        assert_eq!(std::mem::size_of_val(&ui), 8);
        assert!(frozen.legacy_imports()); assert!(!ui.legacy_imports());
        assert_eq!(frozen.parameters_per_signature(), limits.locals);
        assert_eq!(frozen.operand_stack(), limits.operand_stack);
        assert_eq!(command.parameters_per_signature(), 128);
        assert_eq!(command.parameters_plus_locals(), 256);
        assert_eq!(command.operand_stack(), 128);
        assert_eq!(reactor.functions(), 80_000);
        assert_eq!(command.functions(), 131_072);
        assert_eq!(ui.parameters_per_signature(), 783);
        assert_eq!(ui.parameters_plus_locals(), 1575);
        assert_eq!(ui.operand_stack(), 783);
        assert_eq!(ui.instructions(), command.instructions());
        assert_eq!(ui.memory_pages(), command.memory_pages());
        assert_eq!(ui.table_elements(), command.table_elements());
        assert_eq!(ui.control_depth(), command.control_depth());
    }
}
