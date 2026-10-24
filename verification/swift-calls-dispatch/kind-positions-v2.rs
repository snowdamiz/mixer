// Exact private Kind declarations remain inside a child of its original defining module.
#[allow(dead_code)]
pub(crate) mod calls_kind_accounting {
#[allow(dead_code)]
pub(super) struct CallsKindPositions {
    m_swift_release_production_11_43_source: super::super::Kind,
    m_swift_release_production_11_43_argument: super::super::Kind,
    m_swift_release_production_11_43_returned: super::super::Kind,
    m_swift_release_production_11_43_caller: super::super::Kind,
    #[cfg(test)]
    m_swift_release_unit_11_43_source: super::super::Kind,
    #[cfg(test)]
    m_swift_release_unit_11_43_argument: super::super::Kind,
    #[cfg(test)]
    m_swift_release_unit_11_43_returned: super::super::Kind,
    #[cfg(test)]
    m_swift_release_unit_11_43_caller: super::super::Kind,
    m_all_release_production_11_43_source: super::super::Kind,
    m_all_release_production_11_43_argument: super::super::Kind,
    m_all_release_production_11_43_returned: super::super::Kind,
    m_all_release_production_11_43_caller: super::super::Kind,
    #[cfg(test)]
    m_all_release_unit_11_43_source: super::super::Kind,
    #[cfg(test)]
    m_all_release_unit_11_43_argument: super::super::Kind,
    #[cfg(test)]
    m_all_release_unit_11_43_returned: super::super::Kind,
    #[cfg(test)]
    m_all_release_unit_11_43_caller: super::super::Kind,
}
pub(crate) const BYTES: usize = size_of::<CallsKindPositions>();
}
