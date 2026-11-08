ObjC.import('ApplicationServices');
ObjC.import('Foundation');
function run() {
    return JSON.stringify({
        api: 'AXIsProcessTrustedWithOptions(NULL)',
        trusted: Boolean($.AXIsProcessTrustedWithOptions(null)),
        requestingExecutable: '/usr/bin/osascript',
        pid: Number($.NSProcessInfo.processInfo.processIdentifier),
        promptRequested: false,
        UIReadOrMutationAttempted: false
    });
}
