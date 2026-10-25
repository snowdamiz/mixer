<!--
{
  "availability" : [
    "iOS: -",
    "iPadOS: -",
    "macCatalyst: -",
    "tvOS: -",
    "visionOS: -"
  ],
  "documentType" : "symbol",
  "framework" : "UIKit",
  "identifier" : "/documentation/UIKit/UIWindow/didResignKeyNotification",
  "metadataVersion" : "0.1.0",
  "role" : "Type Property",
  "symbol" : {
    "kind" : "Type Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:@UIWindowDidResignKeyNotification"
  },
  "title" : "didResignKeyNotification"
}
-->

# didResignKeyNotification

A notification that posts whenever a window resigns its status as main window.

```
nonisolated class let didResignKeyNotification: NSNotification.Name
```

## Discussion

The notification object is the window that resigned its main window status. This notification doesn’t contain a `userInfo` dictionary.

The system posts this notification on the main actor. In iOS 15 and later, the system posts this notification when the window is no longer the key window of its scene. In iOS 14 and earlier, the system posts this notification when the window is no longer the key window of the app.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)