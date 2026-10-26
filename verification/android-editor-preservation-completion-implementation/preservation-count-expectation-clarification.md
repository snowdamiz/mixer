# Retained cohort counts in historical controls

The selected preservation-completion lifetime in root selection
`7bc0948928801e5d04ea73267bd2dec01b2d71ae93b7169dfeaaf7893d543a91`
holds every captured preservation count through the transaction outcome.
Its already explicit three-field expectation is count3 at commit, scalar finish
to B's count1, and B's existing unwind to0.

The same rule necessarily supersedes the historical producer
multiple-preservations expectation for two inactive fields with no active B:
expect count2 at commit and scalar finish to0. Preserve the old source and raw
failure, adjust only this obsolete lifetime assertion in the derivative, and
retain unchanged post-finish replay and exact owner/counter assertions.
This clarifies the selected lifetime for the already existing control; it adds
no product interface, native authority, counter reset or acceptance.
