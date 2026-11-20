# Verify a native attestation after a lost acknowledgment

Use macOS arm64, Go 1.26.4, and Apple Clang. Run from the Mixer root. The
test uses the existing loopback fixture for a build whose worker has closed.
It generates temporary development keys and a synthetic session.

```sh
mkdir -p verification/local
scratch="$(mktemp -d "$PWD/verification/local/l07-attestation.XXXXXXXX")"
git archive aae21e0880ea8991992f83322fa1ec47cb4e2908 \
  services/go.mod services/go.sum services/cmd/mixer-native-attest \
  > "$scratch/source.tar"
tar -xf "$scratch/source.tar" -C "$scratch"
cp tests/integration/l07-native-attestation/lost_ack_darwin_test.go \
  "$scratch/services/cmd/mixer-native-attest/"
mkdir "$scratch/cache" "$scratch/modules" "$scratch/tmp"

export CGO_ENABLED=1 CC=/usr/bin/clang GOTOOLCHAIN=local GOENV=off GOWORK=off
export GOPROXY=off GOSUMDB=off GOTELEMETRY=off GORACE=atexit_sleep_ms=0
export GOCACHE="$scratch/cache" GOMODCACHE="$scratch/modules" GOTMPDIR="$scratch/tmp"
export MIXER_ATTEST_PROOF_BIN="$scratch/mixer-native-attest"
go -C "$scratch/services" build -race -buildvcs=false -mod=readonly \
  -o "$MIXER_ATTEST_PROOF_BIN" ./cmd/mixer-native-attest
go -C "$scratch/services" test -race -buildvcs=false -mod=readonly \
  ./cmd/mixer-native-attest -run '^TestWorkerClosedSignerLostPublicationAck$' \
  -count=3 -timeout=45s -v
```

The signer writes one envelope and loses its stdout acknowledgment. The test
checks that a repeated `sign` is refused without loading the private key or
making an HTTP request. The original public key verifies the committed envelope.
The test also checks that the fixture port can be reused.

Remove the exact `scratch` directory after the commands exit and the test
confirms closure. See the [recorded run](../../../verification/receipts/l07-signer-post-publication-aae21e08.json).
