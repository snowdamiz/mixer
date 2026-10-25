<!--
{
  "availability" : [
    "iOS: 4.0.0 -",
    "iPadOS: 4.0.0 -",
    "macCatalyst: 13.1.0 -",
    "tvOS: -",
    "visionOS: 1.0.0 -"
  ],
  "documentType" : "symbol",
  "framework" : "UIKit",
  "identifier" : "/documentation/UIKit/UIApplication/willEnterForegroundNotification",
  "metadataVersion" : "0.1.0",
  "role" : "Type Property",
  "symbol" : {
    "kind" : "Type Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:@UIApplicationWillEnterForegroundNotification"
  },
  "title" : "willEnterForegroundNotification"
}
-->

# willEnterForegroundNotification

A notification that posts shortly before your app’s UI transitions to the foreground.

```
nonisolated class let willEnterForegroundNotification: NSNotification.Name
```

## Discussion

The `object` of the notification is the [`UIApplication`](/documentation/UIKit/UIApplication) object. There is no `userInfo` dictionary.

If your app adopts the scene-based life cycle, this notification isn’t an app-level mirror of [`willEnterForegroundNotification`](/documentation/UIKit/UIScene/willEnterForegroundNotification). That scene notification comes from an individual scene’s own life-cycle transition. This notification instead reflects your app’s aggregate state across all of its scenes. UIKit posts this notification when that aggregate state moves from background to foreground. If a person performs an action that brings an additional scene to the foreground while your app’s aggregate state is already in the foreground, that action doesn’t change the aggregate state, so this notification doesn’t fire again.

If your app launches directly into the foreground, UIKit posts this notification around launch time, as the launching scene transitions to the foreground and becomes visible. If your app launches into the background instead, for example to handle a silent push notification or a location update, this notification doesn’t fire at launch. It arrives later, only if your app actually enters the foreground.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)