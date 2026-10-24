# Private Linux compiler checkpoint

The selected C6 V4 attempt passes compiler and exported-artifact qualification
on the pinned Linux arm64 runtime image. The unchanged resource helper and NIF
each compile twice; native byte comparisons and independently inspected exports
match. The helper is 73,288 bytes and the NIF is 71,144 bytes. Four retained
products total 288,864 bytes. Their AArch64 headers, dynamic dependencies and
required GNU symbol versions match the captured runtime providers.

V4 changes only product export transport to fixed `docker exec` tar arguments.
The compiler/sysroot, exact archive decoder, resource limits and ownership
checks remain unchanged. All 46 host controls pass, including the 43 inherited
controls. Root verifies all 118 execution bindings and 27 command outputs,
the actual container isolation, successful removal and input-snapshot cleanup.
Earlier image-inspection, archive-name and product-export failures remain
preserved. The prior export failure's underlying Docker cause is not established.

This accepts the reviewed compiler invocation under `/opt/mixer-compiler`.
It does not qualify the resource controller's `/usr/bin/cc` invocation, execute
the helper, load the NIF, start BEAM or run any of the 30 resource-test rows.
Those steps and all production/GA gates remain pending.

The [root acceptance receipt](../verification/stripe-webhook-resource-ingress-root-review/linux-compiler-qualification-v4-review/runtime-acceptance.json)
records exact hashes, tools, commands and scope. Its execution seal is
`d385a0485403b9f4df5c6e3920e71ae14595b620f8bae367ba39bf3a8c7a8913`.
The [execution outcome](../verification/stripe-resource-linux-compiler-qualification-v4/execution-outcome.json)
links the selected source, native output, binary exports and cleanup records.
