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
  "identifier" : "/documentation/UIKit/UIGestureRecognizerDelegate/gestureRecognizerShouldBegin(_:)",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Method",
  "symbol" : {
    "kind" : "Instance Method",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(pl)UIGestureRecognizerDelegate(im)gestureRecognizerShouldBegin:"
  },
  "title" : "gestureRecognizerShouldBegin(_:)"
}
-->

# gestureRecognizerShouldBegin(_:)

Asks the delegate if a gesture recognizer should begin interpreting touches.

```
optional func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool
```

## Parameters

`gestureRecognizer`

An instance of a subclass of the abstract base class [`UIGestureRecognizer`](/documentation/UIKit/UIGestureRecognizer). This gesture-recognizer object is about to begin processing touches to determine if its gesture is occurring.

## Return Value

<doc://com.apple.documentation/documentation/Swift/true> (the default) to tell the gesture recognizer to proceed with interpreting touches, <doc://com.apple.documentation/documentation/Swift/false> to prevent it from attempting to recognize its gesture.

## Discussion

This method is called when a gesture recognizer attempts to transition out of the [`UIGestureRecognizer.State.possible`](/documentation/UIKit/UIGestureRecognizer/State-swift.enum/possible) state. Returning <doc://com.apple.documentation/documentation/Swift/false> causes the gesture recognizer to transition to the [`UIGestureRecognizer.State.failed`](/documentation/UIKit/UIGestureRecognizer/State-swift.enum/failed) state.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)