<!--
{
  "availability" : [
    "iOS: 15.0.0 -",
    "iPadOS: 15.0.0 -",
    "macCatalyst: 15.0.0 -",
    "tvOS: 17.0.0 -",
    "visionOS: 1.0.0 -"
  ],
  "documentType" : "symbol",
  "framework" : "UIKit",
  "identifier" : "/documentation/UIKit/UIButton/changesSelectionAsPrimaryAction",
  "metadataVersion" : "0.1.0",
  "role" : "Instance Property",
  "symbol" : {
    "kind" : "Instance Property",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(cs)UIButton(py)changesSelectionAsPrimaryAction"
  },
  "title" : "changesSelectionAsPrimaryAction"
}
-->

# changesSelectionAsPrimaryAction

A Boolean value that indicates whether the button tracks a selection, either through a menu or a toggle.

```
var changesSelectionAsPrimaryAction: Bool { get set }
```

## Discussion

This behavior of this property composes with [`showsMenuAsPrimaryAction`](/documentation/UIKit/UIControl/showsMenuAsPrimaryAction) and the [`menu`](/documentation/UIKit/UIButton/menu) property.

If [`menu`](/documentation/UIKit/UIButton/menu) is `nil`, setting this property to <doc://com.apple.documentation/documentation/Swift/true> makes the button toggle its [`selected`](/documentation/UIKit/UIControl/State-swift.struct/selected) state.

If you set a menu and [`showsMenuAsPrimaryAction`](/documentation/UIKit/UIControl/showsMenuAsPrimaryAction) is <doc://com.apple.documentation/documentation/Swift/false>, setting this property to <doc://com.apple.documentation/documentation/Swift/true> makes the button a toggle button. The menu functions as a contextual menu, which appears after a long press.

If you set a menu and [`showsMenuAsPrimaryAction`](/documentation/UIKit/UIControl/showsMenuAsPrimaryAction) is <doc://com.apple.documentation/documentation/Swift/true>, setting this property to <doc://com.apple.documentation/documentation/Swift/true> makes the button function as a pop-up. The button presents the menu on touch, the menu tracks the selection in its [`selectedElements`](/documentation/UIKit/UIMenu/selectedElements) property, and the button title updates to reflect the selection.

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)