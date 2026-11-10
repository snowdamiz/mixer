package dev.mixer.android;

/** Explicit adapter source profile. This declaration is not runtime qualification,
 * attachment authority, an OTA capability proof, or a stable JNI ABI. */
public enum AndroidUIProfile {
    LEGACY_HORIZONTAL,
    MEASURED_MULTILINE_V2,
    MEASURED_MULTILINE_RETIREMENT_V3,
    MEASURED_MULTILINE_LONG_NOTES_V4;

    boolean retirement() { return this == MEASURED_MULTILINE_RETIREMENT_V3 || this == MEASURED_MULTILINE_LONG_NOTES_V4; }
}
