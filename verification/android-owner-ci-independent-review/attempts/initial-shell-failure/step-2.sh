: "${JAVA_HOME_17_X64:?The runner's official JDK 17 is required}"
python3 -B native/android/tests/run-private-owner-host.py \
  --jdk "$JAVA_HOME_17_X64" --closure B \
  --evidence "$RUNNER_TEMP/android-owner-renderer"
