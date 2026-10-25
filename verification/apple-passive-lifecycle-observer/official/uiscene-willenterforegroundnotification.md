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
  "identifier" : "/documentation/UIKit/UIScene/willEnterForegroundNotification",
  "metadataVersion" : "0.1.0",
  "role" : "Type Property",
  "symbol" : {
    "kind" : "Type Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:@UISceneWillEnterForegroundNotification"
  },
  "title" : "willEnterForegroundNotification"
}
-->

# willEnterForegroundNotification

A notification that indicates that a scene is about to begin running in the foreground and become visible to the user.

```
nonisolated class let willEnterForegroundNotification: NSNotification.Name
```

## Discussion

UIKit posts this notification before moving a scene to the foreground. This transition occurs both for newly created and connected scenes and for scenes that were running in the background and were brought to the foreground by the system or a user action. A scene enters the foreground as a precursor to becoming visible onscreen, so this method is invariably followed by the posting of a [`didActivateNotification`](/documentation/UIKit/UIScene/didActivateNotification) notification. UIKit places the scene object in the <doc://com.apple.documentation/documentation/Foundation/NSNotification/object> property of the notification.

UIKit also calls the [`sceneWillEnterForeground(_:)`](/documentation/UIKit/UISceneDelegate/sceneWillEnterForeground(_:)) method of your scene delegate object.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)