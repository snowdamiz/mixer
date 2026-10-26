: "${JAVA_HOME_17_X64:?Official JDK 17 is required}"
python3 -B native/android/tests/run-environment-observer-host.py \
  --jdk "$JAVA_HOME_17_X64" \
  --evidence "$RUNNER_TEMP/android-owner-observer"
