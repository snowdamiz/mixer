<!--
{
  "availability" : [
    "iOS: 3.2.0 -",
    "iPadOS: 3.2.0 -",
    "macCatalyst: 13.1.0 -",
    "tvOS: -",
    "visionOS: 1.0.0 -"
  ],
  "documentType" : "symbol",
  "framework" : "UIKit",
  "identifier" : "/documentation/UIKit/UIGestureRecognizer/cancelsTouchesInView",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Property",
  "symbol" : {
    "kind" : "Instance Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(cs)UIGestureRecognizer(py)cancelsTouchesInView"
  },
  "title" : "cancelsTouchesInView"
}
-->

# cancelsTouchesInView

A Boolean value that determines whether touches are delivered to a view when a gesture is recognized.

```
var cancelsTouchesInView: Bool { get set }
```

## Discussion

When this property is <doc://com.apple.documentation/documentation/Swift/true> (the default) and the gesture recognizer recognizes its gesture, the touches of that gesture that are pending aren’t delivered to the view and previously delivered touches are canceled through a [`touchesCancelled(_:with:)`](/documentation/UIKit/UIResponder/touchesCancelled(_:with:)) message sent to the view. If a gesture recognizer doesn’t recognize its gesture or if the value of this property is <doc://com.apple.documentation/documentation/Swift/false>, the view receives all touches in the multi-touch sequence.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)