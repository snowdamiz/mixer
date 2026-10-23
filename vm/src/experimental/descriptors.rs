//! Private views into one sealed source/metadata owner, never independent proof.
use super::ValidatedSpans;
use crate::Type;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct SignatureView<'a> {
    pub params: &'a [Type],
    pub result: Option<Type>,
}

#[derive(Clone, Copy)]
pub(super) struct ImportView<'a> {
    pub module: &'a [u8],
    pub name: &'a [u8],
}

#[derive(Clone, Copy)]
pub(super) struct GlobalView<'a> {
    pub ty: Type,
    pub mutable: bool,
    pub initializer: &'a [u8],
}

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
