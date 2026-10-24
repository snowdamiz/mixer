<!--
{
  "availability" : [
    "iOS: 2.0.0 -",
    "iPadOS: 2.0.0 -",
    "macCatalyst: 13.1.0 -",
    "tvOS: -",
    "visionOS: 1.0.0 -"
  ],
  "documentType" : "symbol",
  "framework" : "UIKit",
  "identifier" : "/documentation/UIKit/UITouch/location(in:)-8rd36",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Method",
  "symbol" : {
    "kind" : "Instance Method",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(cs)UITouch(im)locationInView:"
  },
  "title" : "location(in:)"
}
-->

# location(in:)

Returns the current location of the touch in the coordinate system of the given view.

```
func location(in view: UIView?) -> CGPoint
```

## Parameters

`view`

The view object in whose coordinate system you want the touch located. A custom view that is handling the touch may specify `self` to get the touch location in its own coordinate system. Pass `nil` to get the touch location in the window’s coordinates.

## Return Value

A point specifying the location of the receiver in `view`.

## Discussion

This method returns the current location of a [`UITouch`](/documentation/UIKit/UITouch) object in the coordinate system of the specified view. Because the touch object might have been forwarded to a view from another view, this method performs any necessary conversion of the touch location to the coordinate system of the specified view.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)