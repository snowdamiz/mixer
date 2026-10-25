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
  "identifier" : "/documentation/UIKit/UIScene/didEnterBackgroundNotification",
  "metadataVersion" : "0.1.0",
  "role" : "Type Property",
  "symbol" : {
    "kind" : "Type Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:@UISceneDidEnterBackgroundNotification"
  },
  "title" : "didEnterBackgroundNotification"
}
-->

# didEnterBackgroundNotification

A notification that indicates that the scene is running in the background and is no longer onscreen.

```
nonisolated class let didEnterBackgroundNotification: NSNotification.Name
```

## Discussion

Use this notification to reduce your scene’s memory usage, free up any shared resources, and clean up your scene’s user interface. Shortly after your notification handler returns, UIKit takes a snapshot of your scene’s interface for display in the app switcher. Make sure your interface doesn’t contain sensitive user information.

UIKit also calls the [`sceneDidEnterBackground(_:)`](/documentation/UIKit/UISceneDelegate/sceneDidEnterBackground(_:)) method of your scene delegate object.

For more information about what to do when your app enters the background, see [Preparing your UI to run in the background](/documentation/UIKit/preparing-your-ui-to-run-in-the-background).

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)