# Focused missing-support correction and failed-run review

No blocking findings. Recommend one exact root-released bounded run of plan
8e9df8c3eb6f4653629f1fa4694e0df662ad0473f03a31c95f3bbf718afc1852,
under freeze
c79e8af319b32376d1d6dc4b074436eb10b20bae8415062f6313b1615989a910.

Candidate 2 remains failed. Its six exact execution files are unchanged and
source-bound. Product nineteen-module compilation and three support modules had
zero warnings; full KeyOwnerTest compilation then reported SocketProbe.info/1
undefined from unselected method bodies. The bootstrap rejected those warnings
and exited 2 before ExUnit or TLS fixture setup. Only the OpenSSL version probe
ran; its exact child was reaped. There is no exunit-result, selected-case pass,
certificate-generation or TLS-success claim. Final membership validation also
correctly recorded the six missing artifacts instead of accepting partial output.
The retained outer PID 51011 was reaped, group absent, scratch removed and source/
tool posthashes stable; no cleanup fault was hidden.

The minimal correction adds the existing SocketProbe source, SHA-256
8135af832ad0f1877e7370ff491c882597c1510d82f15c011a35897e936f9416,
to the compile-only support roster. Direct source review finds only GenServer
and existing Elixir/OTP references, with no top-level process/timer/socket start.
Its sampling effects require an explicit start from probe-using methods, which
remain excluded. Bootstrap now requires four warning-free support modules;
warning checks and all full test bodies stay intact. Runner changes are only
prepared-3/candidate-3 path literals. Existing R01 directory guard, strict schemas,
temporary helper/K07g patch, 29/7/22 selection, eighteen accepted product sources,
OpenSSL wrapper, tool/dependency closure and cleanup remain unchanged.

Independent custody passes 229 new members, 228 prepared pins, 26 canonical pins
and 980 tool pins, preserving the old 221/225-member source packets and six-file
failed run. No producer, compiler, formatter, OpenSSL, TLS or test replay occurred.
Fresh targeted evidence is still required; a later seven-case pass cannot
qualify the full Phoenix suite. Native/UI/capture/devices and production/GA
remain outside this slice.
