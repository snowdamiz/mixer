<!--
{
  "availability" : [
    "iOS: 17.0.0 -",
    "iPadOS: 17.0.0 -",
    "macCatalyst: 17.0.0 -",
    "tvOS: 17.0.0 -",
    "visionOS: 1.0.0 -"
  ],
  "documentType" : "symbol",
  "framework" : "UIKit",
  "identifier" : "/documentation/UIKit/UITextSelectionDisplayInteraction/highlightView",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Property",
  "symbol" : {
    "kind" : "Instance Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(cs)UITextSelectionDisplayInteraction(py)highlightView"
  },
  "title" : "highlightView"
}
-->

# highlightView

The view that draws the selection highlight behind the rendered text.

```
var highlightView: any UIView & UITextSelectionHighlightView { get set }
```

## Discussion

When you install the interaction on your text input view, the system installs a view in this property that provides the standard system highlight appearance for selections. You can replace this view with a custom one you provide to change the appearance of selections.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)