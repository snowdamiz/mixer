//! Private views into one sealed source/metadata owner, never independent proof.
#[cfg(feature = "experimental-span-execution")]
use super::ValidatedSpans;
use crate::Type;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct SignatureView<'a> {
    pub(crate) params: &'a [Type],
    pub(crate) result: Option<Type>,
}

#[derive(Clone, Copy)]
#[cfg(feature = "experimental-span-execution")]
pub(super) struct ImportView<'a> {
    pub module: &'a [u8],
    pub name: &'a [u8],
}

#[derive(Clone, Copy)]
pub(crate) struct GlobalView<'a> {
    pub(crate) ty: Type,
    pub(crate) mutable: bool,
    pub(crate) initializer: &'a [u8],
}

/// Borrowed code span; the function index includes the sealed imports.
#[cfg(feature = "experimental-swift-reactor")]
#[allow(dead_code)] // Consumed by the later private execution/cache stage.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct FunctionSpanView<'a> {
    pub(crate) absolute_index: u32,
    pub(crate) type_index: u32,
    pub(crate) body_offset: usize,
    pub(crate) body: &'a [u8],
}

/// Encoded initializer bytes, retaining source order and the absolute cursor.
#[cfg(feature = "experimental-swift-reactor")]
#[allow(dead_code)] // Consumed by the later private execution stage.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct SegmentExecutionView<'a> {
    pub(crate) destination: u32,
    pub(crate) count: u32,
    pub(crate) payload_offset: usize,
    pub(crate) encoded_payload: &'a [u8],
}

#[cfg(feature = "experimental-swift-reactor")]
#[allow(dead_code)] // Consumed by the later private execution stage.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct MemoryExecutionView {
    pub(crate) minimum: u32,
    pub(crate) declared_maximum: Option<u32>,
    pub(crate) host_maximum: u32,
}

#[cfg(feature = "experimental-swift-reactor")]
#[allow(dead_code)] // Consumed by the later private execution stage.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct TableExecutionView {
    pub(crate) minimum: u32,
    pub(crate) declared_maximum: Option<u32>,
    pub(crate) host_maximum: u32,
}

#[cfg(feature = "experimental-span-execution")]
impl ValidatedSpans {
    pub(super) fn execution_signature(&self, function: u32) -> Option<SignatureView<'_>> {
        let signature = self.metadata.signature(function)?;
        Some(SignatureView {
            params: self.metadata.params(signature),
            result: signature.result,
        })
    }

    pub(super) fn execution_type(&self, index: u32) -> Option<SignatureView<'_>> {
        let signature = *self.metadata.signatures.get(index as usize)?;
        Some(SignatureView {
            params: self.metadata.params(signature),
            result: signature.result,
        })
    }

    pub(super) fn execution_import(&self, function: u32) -> Option<ImportView<'_>> {
        let import = self.metadata.imports.get(function as usize)?;
        Some(ImportView {
            module: import.module.slice(&self.source),
            name: import.name.slice(&self.source),
        })
    }

    /// The execution owner charges bounded scan work before calling this lookup.
    pub(super) fn execution_export(&self, name: &str) -> Option<(u8, u32)> {
        self.metadata
            .exports
            .as_slice()
            .iter()
            .find(|export| export.name.slice(&self.source) == name.as_bytes())
            .map(|export| (export.kind, export.index))
    }

    pub(super) fn execution_export_count(&self) -> usize {
        self.metadata.exports.len()
    }

    pub(super) fn execution_memory(&self) -> Option<(u32, u32)> {
        self.metadata.memory
    }

    pub(super) fn execution_table(&self) -> Option<(u32, u32)> {
        self.metadata.table
    }

    pub(super) fn execution_global_count(&self) -> usize {
        self.metadata.globals.len()
    }

    pub(super) fn execution_global(&self, index: usize) -> Option<GlobalView<'_>> {
        let global = self.metadata.globals.get(index)?;
        Some(GlobalView {
            ty: global.ty,
            mutable: global.mutable,
            initializer: global.initializer.slice(&self.source),
        })
    }

    pub(super) fn execution_data_count(&self) -> usize {
        self.metadata.data.len()
    }

    pub(super) fn execution_element_count(&self) -> usize {
        self.metadata.elements.len()
    }
}
