<!--
{
  "availability" : [
    "iOS: 13.0.0 -",
    "iPadOS: 13.0.0 -",
    "macCatalyst: 13.1.0 -",
    "tvOS: 13.0.0 -",
    "visionOS: 1.0.0 -"
  ],
  "documentType" : "symbol",
  "framework" : "UIKit",
  "identifier" : "/documentation/UIKit/UIScene/didActivateNotification",
  "metadataVersion" : "0.1.0",
  "role" : "Type Property",
  "symbol" : {
    "kind" : "Type Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:@UISceneDidActivateNotification"
  },
  "title" : "didActivateNotification"
}
-->

# didActivateNotification

A notification that indicates that the scene is now onscreen and responding to user events.

```
nonisolated class let didActivateNotification: NSNotification.Name
```

## Discussion

Use this notification to prepare your scene to be onscreen. UIKit posts this notification after loading the interface for your scene, but before that interface appears onscreen. Use it to refresh the contents of views, start timers, or increase frame rates for your UI. UIKit places the scene object in the <doc://com.apple.documentation/documentation/Foundation/NSNotification/object> property of the notification.

UIKit also calls the [`sceneDidBecomeActive(_:)`](/documentation/UIKit/UISceneDelegate/sceneDidBecomeActive(_:)) method of your scene delegate object.

For more information on what to do when your app becomes active, see [Preparing your UI to run in the foreground](/documentation/UIKit/preparing-your-ui-to-run-in-the-foreground).

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)