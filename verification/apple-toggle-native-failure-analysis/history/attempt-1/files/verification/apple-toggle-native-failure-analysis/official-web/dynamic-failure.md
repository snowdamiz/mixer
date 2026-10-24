<!--
{
  "availability" : [
    "iOS: 7.0.0 -",
    "iPadOS: 7.0.0 -",
    "macCatalyst: 13.1.0 -",
    "tvOS: -",
    "visionOS: 1.0.0 -"
  ],
  "documentType" : "symbol",
  "framework" : "UIKit",
  "identifier" : "/documentation/UIKit/UIGestureRecognizerDelegate/gestureRecognizer(_:shouldBeRequiredToFailBy:)",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Method",
  "symbol" : {
    "kind" : "Instance Method",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(pl)UIGestureRecognizerDelegate(im)gestureRecognizer:shouldBeRequiredToFailByGestureRecognizer:"
  },
  "title" : "gestureRecognizer(_:shouldBeRequiredToFailBy:)"
}
-->

# gestureRecognizer(_:shouldBeRequiredToFailBy:)

Asks the delegate if a gesture recognizer should be required to fail by another gesture recognizer.

```
optional func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldBeRequiredToFailBy otherGestureRecognizer: UIGestureRecognizer) -> Bool
```

## Parameters

`gestureRecognizer`

An instance of a subclass of the abstract base class [`UIGestureRecognizer`](/documentation/UIKit/UIGestureRecognizer). This is the object sending the message to the delegate.

`otherGestureRecognizer`

An instance of a subclass of the abstract base class [`UIGestureRecognizer`](/documentation/UIKit/UIGestureRecognizer).

## Return Value

<doc://com.apple.documentation/documentation/Swift/true> to set up a dynamic failure requirement between `gestureRecognizer` and `otherGestureRecognizer`. The default implementation returns <doc://com.apple.documentation/documentation/Swift/false>—`gestureRecognizer` isn’t required to fail by `otherGestureRecognizer`.

## Discussion

This method is called once per attempt to recognize, so failure requirements can be determined lazily and may be set up between recognizers across view hierarchies. Note that returning <doc://com.apple.documentation/documentation/Swift/true> is guaranteed to set up the failure requirement; returning <doc://com.apple.documentation/documentation/Swift/false>, on the other hand, isn’t guaranteed to prevent or remove a failure requirement because `otherGestureRecognizer` might make itself a failure requirement by using its own subclass or delegate methods.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)