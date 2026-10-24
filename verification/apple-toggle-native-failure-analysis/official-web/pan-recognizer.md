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
  "identifier" : "/documentation/UIKit/UIPanGestureRecognizer",
  "metadataVersion" : "0.1.0",
  "role" : "Class",
  "symbol" : {
    "kind" : "Class",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(cs)UIPanGestureRecognizer"
  },
  "title" : "UIPanGestureRecognizer"
}
-->

# UIPanGestureRecognizer

A continuous gesture recognizer that interprets panning gestures.

```
@MainActor class UIPanGestureRecognizer
```

## Overview

[`UIPanGestureRecognizer`](/documentation/UIKit/UIPanGestureRecognizer) is a concrete subclass of [`UIGestureRecognizer`](/documentation/UIKit/UIGestureRecognizer).

Clients of this class can, in their action methods, query the [`UIPanGestureRecognizer`](/documentation/UIKit/UIPanGestureRecognizer) object for the current translation of the gesture ([`translation(in:)`](/documentation/UIKit/UIPanGestureRecognizer/translation(in:))) and the velocity of the translation ([`velocity(in:)`](/documentation/UIKit/UIPanGestureRecognizer/velocity(in:))). They can specify a view’s coordinate system to use for the translation and velocity values. Clients can also reset the translation to a desired value.

A panning gesture is continuous. The user must press one or more fingers on a view while panning it. The gesture begins ([`UIGestureRecognizer.State.began`](/documentation/UIKit/UIGestureRecognizer/State-swift.enum/began)) when the user moves the minimum number of fingers allowed ([`minimumNumberOfTouches`](/documentation/UIKit/UIPanGestureRecognizer/minimumNumberOfTouches)) enough distance for recognition as a pan. It changes ([`UIGestureRecognizer.State.changed`](/documentation/UIKit/UIGestureRecognizer/State-swift.enum/changed)) when the user moves a finger while pressing with the minimum number of fingers. It ends ([`UIGestureRecognizer.State.ended`](/documentation/UIKit/UIGestureRecognizer/State-swift.enum/ended)) when the user lifts all fingers.

## Topics

### Configuring the gesture recognizer

[`var maximumNumberOfTouches: Int`](/documentation/UIKit/UIPanGestureRecognizer/maximumNumberOfTouches)

The maximum number of fingers that can touch the view for gesture recognition.

[`var minimumNumberOfTouches: Int`](/documentation/UIKit/UIPanGestureRecognizer/minimumNumberOfTouches)

The minimum number of fingers that can touch the view for gesture recognition.

### Tracking the location and velocity of the gesture

[`func translation(in: UIView?) -> CGPoint`](/documentation/UIKit/UIPanGestureRecognizer/translation(in:))

Interprets the pan gesture in the coordinate system of the specified view.

[`func setTranslation(CGPoint, in: UIView?)`](/documentation/UIKit/UIPanGestureRecognizer/setTranslation(_:in:))

Sets the translation value in the coordinate system of the specified view.

[`func velocity(in: UIView?) -> CGPoint`](/documentation/UIKit/UIPanGestureRecognizer/velocity(in:))

Interprets the velocity of the pan gesture in the coordinate system of the specified view.

### Tracking scroll events

[`var allowedScrollTypesMask: UIScrollTypeMask`](/documentation/UIKit/UIPanGestureRecognizer/allowedScrollTypesMask)

A scroll type mask that enables recognition of scroll events.

[`struct UIScrollTypeMask`](/documentation/UIKit/UIScrollTypeMask)

A bit mask identifying the scroll type of a pan gesture.

[`enum UIScrollType`](/documentation/UIKit/UIScrollType)

Constants that define the type of the scroll.

## Relationships

### Conforms To

[`Equatable`](/documentation/Swift/Equatable)

[`Sendable`](/documentation/Swift/Sendable)

[`CustomDebugStringConvertible`](/documentation/Swift/CustomDebugStringConvertible)

[`CustomStringConvertible`](/documentation/Swift/CustomStringConvertible)

[`CVarArg`](/documentation/Swift/CVarArg)

[`SendableMetatype`](/documentation/Swift/SendableMetatype)

[`NSObjectProtocol`](/documentation/ObjectiveC/NSObjectProtocol)

[`Hashable`](/documentation/Swift/Hashable)

### Inherited By

[`UIScreenEdgePanGestureRecognizer`](/documentation/UIKit/UIScreenEdgePanGestureRecognizer)

### Inherits From

[`UIGestureRecognizer`](/documentation/UIKit/UIGestureRecognizer)

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)