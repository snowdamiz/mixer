//! Closed borrowed policies. Frozen validation never materializes widened Limits.
use crate::{Limits, Profile};

pub(super) enum Policy<'a> {
    Frozen(&'a Limits),
    #[cfg(feature = "experimental-swift-reactor")]
    SwiftReactorExperimentV1,
}
impl<'a> Policy<'a> {
    pub fn frozen(limits: &'a Limits) -> Self {
        Self::Frozen(limits)
    }
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
            Self::SwiftReactorExperimentV1 => 80_000,
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
            Self::SwiftReactorExperimentV1 => 8_000_000,
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
