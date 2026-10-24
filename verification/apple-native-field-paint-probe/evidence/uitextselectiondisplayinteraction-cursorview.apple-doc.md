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
  "identifier" : "/documentation/UIKit/UITextSelectionDisplayInteraction/cursorView",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Property",
  "symbol" : {
    "kind" : "Instance Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(cs)UITextSelectionDisplayInteraction(py)cursorView"
  },
  "title" : "cursorView"
}
-->

# cursorView

The view that draws the caret at the text insertion point.

```
var cursorView: any UIView & UITextCursorView { get set }
```

## Discussion

When you install the interaction on your text input view, the system installs a view in this property that provides the standard system appearance for the caret at the insertion point. You can replace this view with a custom one you provide to change the appearance of the caret.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)