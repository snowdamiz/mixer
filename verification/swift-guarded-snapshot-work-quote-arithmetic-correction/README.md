# Separate work-quote multiplication correction

The frozen complete-work proposal's `checked_mul` validates its two operands by
calling `checked_sum(a,b)`. That rejects a valid multiplication such as
`MAX64*1`: its product is MAX64, but the unrelated validation sum overflows.
Root's immutable finding is
`verification/swift-semantic-adapter-root-review/guarded-snapshot-complete-work-proposal-custody.json`
SHA256 `4486fa022350dec1884713a21c0aa528acb2c8810c72d7b6427690126cb9ec48`.

`quote.py` validates each operand independently as an integer in `[0,MAX64]`,
multiplies, then checks the product. Invalid operands refuse even when the other
operand is zero. It preserves the existing `isinstance(value,int)` contract,
including bool's existing integer compatibility. Noninteger operands reject
with the unchanged invalid-input OverflowError. No ledger or product contract
change is introduced. The original checked-sum, emission and quote function ASTs
are identical; fixed prefix451703621, every coefficient and required incoming
price/dispatch argument remain unchanged.

`check.py` reproduces the original MAX64*1 defect, verifies corrected MAX64*0,
*1,*2, symmetric operands, adjacent boundaries, checked-product overflow,
negative/out-of-range/noninteger operands, unchanged sums and a small set of
unchanged quote values. It extracts and executes only the four named pure
arithmetic function ASTs from the old and corrected utilities. It never imports
or runs the old harness, `make()` or any product module. All five original frozen
members are checked before and after and remain immutable. The command receipt
records the Python tool/version, exact argv, output, correction/frozen source
hashes and source-only scope.

Run `python3 verification/swift-guarded-snapshot-work-quote-arithmetic-correction/check.py --verify`.
This is an independently reviewable utility correction. It grants no writer
dispatch, complete work/storage acceptance, numeric ingress/WASI ledger
acceptance, healthy cleanup, native or GA qualification. No product/frozen source,
active ingress/funding packet, Git, process, native test or UI/capture state was
changed or inspected.
