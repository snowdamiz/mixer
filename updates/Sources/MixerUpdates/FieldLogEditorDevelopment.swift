/// The marker is reserved even in builds without the macOS development owner.
@_spi(PrivateFieldLogEditor)
public enum FieldLogEditorDevelopment {
    public static let dependency = "mixer.fieldlog-compact-editor-v1"
    public static let contractSHA256 = "9f45c82756688d7c1ccd3bc4055ecf0a4e0f238bc62da63cbb7e34cc76daad71"
    public static let bundleID = "com.example.fieldlog.signed-local"
    public static let scope = UpdateScope(organization: "mixer-local", project: "fieldlog", app: "fieldlog",
                                          environment: "development", platform: "macos")
}
