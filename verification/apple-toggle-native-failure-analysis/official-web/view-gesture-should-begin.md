<!--
{
  "availability" : [
    "iOS: 6.0.0 -",
    "iPadOS: 6.0.0 -",
    "macCatalyst: 13.1.0 -",
    "tvOS: -",
    "visionOS: 1.0.0 -"
  ],
  "documentType" : "symbol",
  "framework" : "UIKit",
  "identifier" : "/documentation/UIKit/UIView/gestureRecognizerShouldBegin(_:)",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Method",
  "symbol" : {
    "kind" : "Instance Method",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(cs)UIView(im)gestureRecognizerShouldBegin:"
  },
  "title" : "gestureRecognizerShouldBegin(_:)"
}
-->

# gestureRecognizerShouldBegin(_:)

Asks the view if the gesture recognizer should continue tracking touch events.

```
func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool
```

## Parameters

`gestureRecognizer`

The gesture recognizer that’s attempting to transition out of the [`UIGestureRecognizer.State.possible`](/documentation/UIKit/UIGestureRecognizer/State-swift.enum/possible) state.

## Return Value

<doc://com.apple.documentation/documentation/Swift/true> if the gesture recognizer should continue tracking touch events and use them to trigger a gesture or <doc://com.apple.documentation/documentation/Swift/false> if it should transition to the [`UIGestureRecognizer.State.failed`](/documentation/UIKit/UIGestureRecognizer/State-swift.enum/failed) state.

## Discussion

Subclasses may override this method and use it to prevent the recognition of particular gestures. For example, the [`UISlider`](/documentation/UIKit/UISlider) class uses this method to prevent swipes parallel to the slider’s travel direction and that start in the thumb.

At the time this method is called, the gesture recognizer is in the [`UIGestureRecognizer.State.possible`](/documentation/UIKit/UIGestureRecognizer/State-swift.enum/possible) state and thinks it has the events needed to move to the [`UIGestureRecognizer.State.began`](/documentation/UIKit/UIGestureRecognizer/State-swift.enum/began) state.

The default implementation of this method returns <doc://com.apple.documentation/documentation/Swift/true>.

> Note:
> In iOS 17, Messages allows you to interactively resize iMessage apps with a vertical pan gesture. Messages handles any conflicts between resize gestures and your custom gestures. If your app uses manual touch handling, override those methods in your app’s ``doc://com.apple.uikit/documentation/UIKit/UIView``. You can either change your manual touch handling code to use a gesture recognizer instead, or your ``doc://com.apple.uikit/documentation/UIKit/UIView`` can override ``doc://com.apple.uikit/documentation/UIKit/UIGestureRecognizerDelegate/gestureRecognizerShouldBegin(_:)`` and return NO when your iMessage app doesn’t own the gesture.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)