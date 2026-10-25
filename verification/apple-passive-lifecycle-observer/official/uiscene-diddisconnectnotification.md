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
  "identifier" : "/documentation/UIKit/UIScene/didDisconnectNotification",
  "metadataVersion" : "0.1.0",
  "role" : "Type Property",
  "symbol" : {
    "kind" : "Type Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:@UISceneDidDisconnectNotification"
  },
  "title" : "didDisconnectNotification"
}
-->

# didDisconnectNotification

A notification that indicates that UIKit removed a scene from your app.

```
nonisolated class let didDisconnectNotification: NSNotification.Name
```

## Discussion

Use this notification to perform any final cleanup before your scene is purged from memory. For example, use it to release references to files or shared resources and to save user data. UIKit places the affected scene in the <doc://com.apple.documentation/documentation/Foundation/NSNotification/object> property of the notification.

The removal of a scene is a precursor to the destruction of that scene. UIKit disconnects a scene when the user explicitly closes it in the app switcher. UIKit may also disconnect a scene in order to reclaim memory for other processes. UIKit does not automatically disconnect a scene when the user switches to another app.

UIKit also calls the [`sceneDidDisconnect(_:)`](/documentation/UIKit/UISceneDelegate/sceneDidDisconnect(_:)) method of your scene delegate object.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)