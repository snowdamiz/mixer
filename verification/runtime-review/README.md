# Independent native wrapper review

The receipt records read-only review of runtime3915397 linked to owned VM64123c5.
The original extra assertions are preserved unchanged in this package; only the
package dependency path changes from the local review workspace to `../../runtime`.
The receipt records historical commands and ignored raw-log hashes, not reruns at
this new path. Run the preserved suite against a staged static library with:

```sh
swift test --package-path verification/runtime-review -Xlinker -L"$PWD/runtime/.build/native-host-reclamation/lib"
```

The review found a header-identity assertion bypass under Python optimization;
3a8a791 replaces it with an explicit check and tests normal Python, `-O`, and
`PYTHONOPTIMIZE=1`. No further ownership, type-transport or buffer-copy defect was
confirmed. Host Swift ThreadSanitizer did not instrument the native Rust archive;
this is not native race freedom, physical-device or complete security qualification.
