"""One read-only AppKit/Security identity observation; no AX, UI, or subprocesses."""
import ctypes as c
import datetime
import json
import os
import platform
import plistlib
import sys
from pathlib import Path

P = c.c_void_p
I = c.c_int32
U = c.c_uint32
O = c.POINTER(P)
objc = c.CDLL('/usr/lib/libobjc.A.dylib')
c.CDLL('/System/Library/Frameworks/AppKit.framework/AppKit')
sec = c.CDLL('/System/Library/Frameworks/Security.framework/Security')
cf = c.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
objc.objc_getClass.argtypes = [c.c_char_p]
objc.objc_getClass.restype = P
objc.sel_registerName.argtypes = [c.c_char_p]
objc.sel_registerName.restype = P
address = c.cast(objc.objc_msgSend, P).value

def msg(receiver, selector, result=P, args=(), types=()):
    return c.CFUNCTYPE(result, P, P, *types)(address)(
        receiver, objc.sel_registerName(selector.encode()), *args)

def cls(name):
    return objc.objc_getClass(name.encode())

def string(text):
    return msg(cls('NSString'), 'stringWithUTF8String:', args=(text.encode(),), types=(c.c_char_p,))

def text(value):
    if not value:
        return None
    return msg(value, 'UTF8String', c.c_char_p).decode('utf-8')

def description(value):
    return text(msg(value, 'description')) if value else None

def function(name, args, result=I, lib=sec):
    fn = getattr(lib, name)
    fn.argtypes, fn.restype = args, result
    return fn

static_create = function('SecStaticCodeCreateWithPath', [P, U, O])
guest_create = function('SecCodeCopyGuestWithAttributes', [P, P, U, O])
signing_info = function('SecCodeCopySigningInformation', [P, U, O])
check = function('SecCodeCheckValidityWithErrors', [P, U, P, O])
requirement_text = function('SecRequirementCopyString', [P, U, O])
error_message = function('SecCopyErrorMessageString', [I, P], P)
get_value = function('CFDictionaryGetValue', [P, P], P, cf)
data_length = function('CFDataGetLength', [P], c.c_long, cf)
data_bytes = function('CFDataGetBytePtr', [P], P, cf)
release = function('CFRelease', [P], None, cf)

def key(name):
    return P.in_dll(sec, name).value

def status(value):
    message = error_message(value, None)
    result = {'OSStatus': value, 'message': text(message)}
    if message:
        release(message)
    return result

def info(code, flags):
    dictionary = P()
    result = status(signing_info(code, flags, c.byref(dictionary)))
    if not dictionary.value:
        return result, None
    for name in ('Identifier', 'TeamIdentifier', 'Format', 'Flags', 'Status'):
        value = get_value(dictionary, key('kSecCodeInfo' + name))
        result[name] = description(value)
    value = get_value(dictionary, key('kSecCodeInfoUnique'))
    result['Unique'] = c.string_at(data_bytes(value), data_length(value)).hex() if value else None
    value = get_value(dictionary, key('kSecCodeInfoMainExecutable'))
    result['MainExecutable'] = text(msg(value, 'path')) if value else None
    requirement = get_value(dictionary, key('kSecCodeInfoDesignatedRequirement'))
    if requirement:
        rendered = P()
        result['requirementStringStatus'] = status(requirement_text(requirement, 0, c.byref(rendered)))
        result['DesignatedRequirement'] = text(rendered)
        if rendered:
            release(rendered)
    return result, (dictionary, requirement)

pool = msg(msg(cls('NSAutoreleasePool'), 'alloc'), 'init')
app_path = '/Users/andreyyurlov/Applications/Acid.app'
bundle_id = 'com.t3tools.t3code'
report = {'observedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'python': sys.version, 'pythonExecutable': sys.executable,
          'kernel': platform.uname()._asdict(), 'probePid': os.getpid(),
          'scope': 'Only NSRunningApplication instances for com.t3tools.t3code and installed Acid bundle',
          'storedConsentRequirement': 'Not observed; public APIs used here do not expose TCC consent records',
          'operationsExcluded': ['AX trust check', 'UI automation', 'permission request', 'TCC database access',
                                 'process mutation', 'compile', 'subprocess', 'unrelated app enumeration']}
try:
    with open(app_path + '/Contents/Info.plist', 'rb') as stream:
        plist = plistlib.load(stream)
    report['installedPlist'] = {k: plist.get(k) for k in (
        'CFBundleIdentifier', 'CFBundleExecutable', 'CFBundleVersion', 'CFBundleShortVersionString')}
    url = msg(cls('NSURL'), 'fileURLWithPath:', args=(string(app_path),), types=(P,))
    static = P()
    report['staticCreate'] = status(static_create(url, 0, c.byref(static)))
    static_data = None
    if static:
        report['installedSigning'], static_data = info(static, 6)
    apps = msg(cls('NSRunningApplication'), 'runningApplicationsWithBundleIdentifier:',
               args=(string(bundle_id),), types=(P,))
    count = msg(apps, 'count', c.c_ulong)
    report['matchingApplicationCount'] = count
    report['applications'] = []
    held = {40708, 40709, 40711, 23663, 20745, 20770, 20780, 20817, 20842, 20851, 20866, 2424, 2621}
    if count > 3:
        report['limit'] = 'More than three matching Acid applications; no process identity queried'
    else:
        for index in range(count):
            app = msg(apps, 'objectAtIndex:', args=(index,), types=(c.c_ulong,))
            pid = msg(app, 'processIdentifier', I)
            item = {'pid': pid}
            report['applications'].append(item)
            if pid in held or pid <= 0:
                item['limit'] = 'PID excluded by hold/sanity guard; no Security query'
                continue
            item['bundleIdentifier'] = text(msg(app, 'bundleIdentifier'))
            for name in ('bundleURL', 'executableURL'):
                value = msg(app, name)
                item[name] = text(msg(value, 'path')) if value else None
            item['launchDate'] = description(msg(app, 'launchDate'))
            item['terminated'] = bool(msg(app, 'isTerminated', c.c_bool))
            if item['bundleURL'] != app_path or item['bundleIdentifier'] != bundle_id or item['terminated']:
                item['limit'] = 'Unexpected path, bundle identifier, or terminated application; no Security query'
                continue
            number = msg(cls('NSNumber'), 'numberWithInt:', args=(pid,), types=(I,))
            attributes = msg(cls('NSDictionary'), 'dictionaryWithObject:forKey:',
                             args=(number, key('kSecGuestAttributePid')), types=(P, P))
            code = P()
            item['guestCreate'] = status(guest_create(None, attributes, 0, c.byref(code)))
            if code:
                errors = P()
                requirement = static_data[1] if static_data else None
                if requirement:
                    item['dynamicValidityAgainstInstalledRequirement'] = status(check(code, 0, requirement, c.byref(errors)))
                    item['validityErrorDescription'] = description(errors)
                    if errors:
                        release(errors)
                else:
                    item['limit'] = 'Installed designated requirement unavailable; dynamic comparison not attempted'
                item['signingInformation'], dynamic_data = info(code, 14)
                item['signingInformationCaveat'] = 'Static fields originate from disk; dynamic validity result governs whether identity match is established'
                if dynamic_data:
                    release(dynamic_data[0])
                release(code)
    if static_data:
        release(static_data[0])
    if static:
        release(static)
except Exception as error:
    report['error'] = {'type': type(error).__name__, 'message': str(error)}
finally:
    print(json.dumps(report, indent=2), flush=True)
    msg(pool, 'drain', None)
