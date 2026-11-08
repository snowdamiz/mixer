ObjC.import('ApplicationServices');
ObjC.import('Foundation');
function run() {
    const options = $.NSMutableDictionary.alloc.init;
    options.setObjectForKey($.NSNumber.numberWithBool(true), $.kAXTrustedCheckOptionPrompt);
    return JSON.stringify({
        api: 'AXIsProcessTrustedWithOptions',
        trusted: Boolean($.AXIsProcessTrustedWithOptions(options)),
        promptRequested: true,
        requestingExecutable: '/usr/bin/osascript',
        pid: Number($.NSProcessInfo.processInfo.processIdentifier),
        permissionChangedByAgent: false,
        UIReadOrMutationAttempted: false
    });
}
