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
  "identifier" : "/documentation/UIKit/UIGestureRecognizerDelegate/gestureRecognizer(_:shouldReceive:)-16fuh",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Method",
  "symbol" : {
    "kind" : "Instance Method",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(pl)UIGestureRecognizerDelegate(im)gestureRecognizer:shouldReceiveTouch:"
  },
  "title" : "gestureRecognizer(_:shouldReceive:)"
}
-->

# gestureRecognizer(_:shouldReceive:)

Asks the delegate if a gesture recognizer should receive an object representing a touch.

```
optional func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool
```

## Parameters

`gestureRecognizer`

An instance of a subclass of the abstract base class [`UIGestureRecognizer`](/documentation/UIKit/UIGestureRecognizer).

`touch`

A [`UITouch`](/documentation/UIKit/UITouch) object from the current multi-touch sequence.

## Return Value

<doc://com.apple.documentation/documentation/Swift/true> (the default) to allow the gesture recognizer to examine the touch object, <doc://com.apple.documentation/documentation/Swift/false> to prevent the gesture recognizer from seeing this touch object.

## Discussion

UIKit calls this method before calling the [`touchesBegan(_:with:)`](/documentation/UIKit/UIGestureRecognizer/touchesBegan(_:with:)) method of the gesture recognizer.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)