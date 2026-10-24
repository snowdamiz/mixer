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
  "identifier" : "/documentation/UIKit/UIGestureRecognizer/location(in:)",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Method",
  "symbol" : {
    "kind" : "Instance Method",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(cs)UIGestureRecognizer(im)locationInView:"
  },
  "title" : "location(in:)"
}
-->

# location(in:)

Returns the point computed as the location in a given view of the gesture represented by the gesture recognizer.

```
func location(in view: UIView?) -> CGPoint
```

## Parameters

`view`

A [`UIView`](/documentation/UIKit/UIView) object on which the gesture took place. Specify `nil` to indicate the window.

## Return Value

A point in the local coordinate system of `view` that identifies the location of the gesture. If `nil` is specified for `view`, the method returns the gesture location in the window’s base coordinate system.

## Discussion

The returned value is a generic single-point location for the gesture computed by the UIKit framework. It is usually the centroid of the touches involved in the gesture. For objects of the [`UISwipeGestureRecognizer`](/documentation/UIKit/UISwipeGestureRecognizer) and [`UITapGestureRecognizer`](/documentation/UIKit/UITapGestureRecognizer) classes, the location returned by this method has a significance special to the gesture. This significance is documented in the reference for those classes.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)