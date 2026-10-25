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
  "identifier" : "/documentation/UIKit/UIWindow/didBecomeKeyNotification",
  "metadataVersion" : "0.1.0",
  "role" : "Type Property",
  "symbol" : {
    "kind" : "Type Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:@UIWindowDidBecomeKeyNotification"
  },
  "title" : "didBecomeKeyNotification"
}
-->

# didBecomeKeyNotification

A notification that posts whenever a window becomes the key window.

```
nonisolated class let didBecomeKeyNotification: NSNotification.Name
```

## Discussion

The notification object is the window that became key. This notification doesn’t contain a `userInfo` dictionary.

The system posts this notification on the main actor. In iOS 15 and later, the system posts this notification when the window becomes the key window of its scene. In iOS 14 and earlier, the system posts this notification when the window becomes the key window of the app.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)