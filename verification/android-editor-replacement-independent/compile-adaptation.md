The first test-source type-check failed because the immutable baseline host
Spanned leaf omits SPAN_INCLUSIVE_INCLUSIVE. Its source and compiler output remain
under syntax-attempt-1/. The pinned official SDK37 javap constant is exactly 18.
The second control source uses an explicit named test constant with that value;
it still requires the actual replacement Annotation range/flags to be preserved.
No product or existing host leaf was changed and no behavioral expectation was
weakened. Neither attempt invokes a product method or fixture.
