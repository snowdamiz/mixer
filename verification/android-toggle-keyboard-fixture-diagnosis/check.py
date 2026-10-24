#!/usr/bin/env python3
"""Read-only sealed fixture/oracle check; never executes subprocess/native/Git tools."""
import json
import support,test_host
def main():
    packet=support.check_packet();candidate=support.frozen();controls=test_host.test()
    host=support.read(support.HERE/'host-2/receipt.json')
    if not host['exactDexReplay'] or not host['cleanup']['absent']:raise ValueError('host replay/cleanup evidence absent')
    print(json.dumps({'schema':1,'status':'passed-read-only-frozen-keyboard-fixture-host-check-native-NOT-RUN','packetFiles':len(packet['files']),'checks':controls['checks'],'apkSHA256':candidate['apkSHA256'],'sourceClosureSHA256':candidate['sourceClosureSHA256'],'privatePackage':support.PACKAGE,'original45CasesAccepted':False,'nativeCommandsExecuted':0,'physicalPhones':'deferred disconnected'},sort_keys=True))
if __name__=='__main__':main()
