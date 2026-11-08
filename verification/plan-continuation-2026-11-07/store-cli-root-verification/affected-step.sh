swift --version
python3 scripts/ci/check-sdk-package.py
swift test
swift test --package-path updates
swift build --package-path cli --product mixer -j 2
MIXER_STORE_CLI_BIN_DIR="$(swift build --package-path cli --product mixer -j 2 --show-bin-path)"
test -x "$MIXER_STORE_CLI_BIN_DIR/mixer"
MIXER_STORE_TEST_CLI="$MIXER_STORE_CLI_BIN_DIR/mixer" swift test --package-path cli
python3 -B -m unittest discover -s cli/build-tests -v
swift test --package-path native/android/engine
python3 runtime-identity/tools/vectors.py --check
python3 runtime-identity/tools/vectors_v2.py --check
swift test --package-path runtime-identity
python3 -B -m unittest discover -s runtime-identity/build-tools/tests -v
