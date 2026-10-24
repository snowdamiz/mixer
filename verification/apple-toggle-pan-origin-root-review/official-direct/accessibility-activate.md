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
  "framework" : "ObjectiveC",
  "identifier" : "/documentation/ObjectiveC/NSObject-swift.class/accessibilityActivate()",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Method",
  "symbol" : {
    "kind" : "Instance Method",
    "modules" : [
      "Objective-C Runtime",
      "ObjectiveC"
    ],
    "preciseIdentifier" : "c:objc(cs)NSObject(im)accessibilityActivate"
  },
  "title" : "accessibilityActivate()"
}
-->

# accessibilityActivate()

Tells the element to activate itself and report the success or failure of the operation.

```
@MainActor func accessibilityActivate() -> Bool
```

## Return Value

[`YES`](/documentation/ObjectiveC/YES) if the element was activated or [`NO`](/documentation/ObjectiveC/NO) if it was not.

## Discussion

You can use this method to make complex controls more readily accessible to users. The accessibility system calls this method when a VoiceOver user double taps the selected element. Your implementation of this method should activate the element and perform whatever other tasks it deems appropriate. For example, you might use the method to activate a control that requires a complex gesture and would be difficult for VoiceOver users to perform, possibly because the gesture has a different meaning when VoiceOver is running.

After performing any tasks, return an appropriate Boolean value to indicate success or failure.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)