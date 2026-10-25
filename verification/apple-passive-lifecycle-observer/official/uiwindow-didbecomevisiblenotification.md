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
  "identifier" : "/documentation/UIKit/UIWindow/didBecomeVisibleNotification",
  "metadataVersion" : "0.1.0",
  "role" : "Type Property",
  "symbol" : {
    "kind" : "Type Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:@UIWindowDidBecomeVisibleNotification"
  },
  "title" : "didBecomeVisibleNotification"
}
-->

# didBecomeVisibleNotification

A notification that posts when a window becomes visible.

```
nonisolated class let didBecomeVisibleNotification: NSNotification.Name
```

## Discussion

The notification object is the visible window. This notification doesn’t contain a `userInfo` dictionary.

Switching between apps doesn’t generate visibility-related notifications for windows. Window visibility changes reflect changes to the window’s [`isHidden`](/documentation/UIKit/UIView/isHidden) property and reflect only the window’s visibility within the app.

The system posts this notification on the main actor.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)