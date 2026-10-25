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
  "identifier" : "/documentation/UIKit/UIScene/willConnectNotification",
  "metadataVersion" : "0.1.0",
  "role" : "Type Property",
  "symbol" : {
    "kind" : "Type Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:@UISceneWillConnectNotification"
  },
  "title" : "willConnectNotification"
}
-->

# willConnectNotification

A notification that indicates that UIKit added a scene to your app.

```
nonisolated class let willConnectNotification: NSNotification.Name
```

## Discussion

When the user or your app requests a new instance of your user interface, UIKit creates an appropriate [`UIScene`](/documentation/UIKit/UIScene) object and places it in the <doc://com.apple.documentation/documentation/Foundation/NSNotification/object> property of the notification. Use this notification to respond to the addition of the new scene and to begin loading any data that the scene needs to display.

UIKit also calls the [`scene(_:willConnectTo:options:)`](/documentation/UIKit/UISceneDelegate/scene(_:willConnectTo:options:)) method of your scene delegate object.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)