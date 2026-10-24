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
  "identifier" : "/documentation/UIKit/UITextInput/textInputView",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Property",
  "symbol" : {
    "kind" : "Instance Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(pl)UITextInput(py)textInputView"
  },
  "title" : "textInputView"
}
-->

# textInputView

An affiliated view that provides a coordinate system for all geometric values in the protocol.

```
optional var textInputView: UIView { get }
```

## Discussion

The view that both draws the text and provides a coordinate system for all geometric values in this protocol. (This is typically an instance of the [`UITextInput`](/documentation/UIKit/UITextInput)-adopting class.) If this property is unimplemented, the first view in the responder chain is selected.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)