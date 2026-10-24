<!--
{
  "availability" : [
    "Xcode: 16.3.0 -",
    "iOS: -",
    "iPadOS: -",
    "macCatalyst: -",
    "macOS: -",
    "visionOS: -",
    "watchOS: -"
  ],
  "documentType" : "symbol",
  "framework" : "XCUIAutomation",
  "identifier" : "/documentation/XCUIAutomation/XCUICoordinate/press(forDuration:thenDragTo:withVelocity:thenHoldForDuration:)",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Method",
  "symbol" : {
    "kind" : "Instance Method",
    "modules" : [
      "XCUIAutomation"
    ],
    "preciseIdentifier" : "c:objc(cs)XCUICoordinate(im)pressForDuration:thenDragToCoordinate:withVelocity:thenHoldForDuration:"
  },
  "title" : "press(forDuration:thenDragTo:withVelocity:thenHoldForDuration:)"
}
-->

# press(forDuration:thenDragTo:withVelocity:thenHoldForDuration:)

Initiates a press-and-hold gesture, drags to another coordinate with a velocity you specify, and holds for a duration you specify.

```
func press(forDuration duration: TimeInterval, thenDragTo otherCoordinate: XCUICoordinate, withVelocity velocity: XCUIGestureVelocity, thenHoldForDuration holdDuration: TimeInterval)
```

## Parameters

`duration`

The duration of the initial press-and-hold gesture.

`otherCoordinate`

The coordinate over which to finish the drag.

`velocity`

The speed at which to move from the initial press position to the other element, expressed in pixels per second.

`holdDuration`

The duration for which to hold over the other coordinate after dragging.

## Discussion

This method is available in iOS and for Touch Bar interactions in macOS.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)