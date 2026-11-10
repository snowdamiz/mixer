//! Closed borrowed policies. Frozen validation never materializes widened Limits.
use crate::{Limits, Profile};

// Command ceilings are selected at compile time without another runtime tag.
pub(crate) enum Policy<'a, const COMMAND: bool = false> {
    Frozen(&'a Limits),
    #[cfg(feature = "experimental-swift-reactor")]
    SwiftReactorExperimentV1,
}
impl<'a> Policy<'a> {
    pub fn frozen(limits: &'a Limits) -> Self {
        Self::Frozen(limits)
    }
}
impl<const COMMAND: bool> Policy<'_, COMMAND> {
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
            Self::SwiftReactorExperimentV1 => 128,
        }
    }
    pub fn parameters_plus_locals(&self) -> usize {
        match self {
            Self::Frozen(l) => l.locals,
            #[cfg(feature = "experimental-swift-reactor")]
            Self::SwiftReactorExperimentV1 => 256,
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
            Self::SwiftReactorExperimentV1 => 128,
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
}

// Sealed ABI selection belongs to the Swift owner, not the frozen policy enum.
// Command's entry index shares this eight-byte selection with the reactor case.
#[cfg(feature = "experimental-swift-reactor")]
pub(crate) enum SwiftSelection {
    Reactor,
    Command { entry: u32 },
}
#[cfg(feature = "experimental-swift-reactor")]
impl SwiftSelection {
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
    pub fn parameters_per_signature(&self) -> usize { Policy::swift().parameters_per_signature() }
    pub fn parameters_plus_locals(&self) -> usize { Policy::swift().parameters_plus_locals() }
    pub fn local_groups(&self) -> usize { Policy::swift().local_groups() }
    pub fn operand_stack(&self) -> usize { Policy::swift().operand_stack() }
    pub fn control_depth(&self) -> usize { Policy::swift().control_depth() }
    pub fn instructions(&self) -> usize {
        match self {
            Self::Reactor => Policy::swift().instructions(),
            Self::Command { .. } => Policy::command().instructions(),
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
