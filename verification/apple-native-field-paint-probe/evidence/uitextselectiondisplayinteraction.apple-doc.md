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
  "identifier" : "/documentation/UIKit/UITextSelectionDisplayInteraction",
  "metadataVersion" : "0.1.0",
  "role" : "Class",
  "symbol" : {
    "kind" : "Class",
    "modules" : [
      "UIKit"
    ],
    "preciseIdentifier" : "c:objc(cs)UITextSelectionDisplayInteraction"
  },
  "title" : "UITextSelectionDisplayInteraction"
}
-->

# UITextSelectionDisplayInteraction

An object that provides the system UI for displaying text selection.

```
@MainActor class UITextSelectionDisplayInteraction
```

## Overview> Related sessions from WWDC23:
> Session 10058: [What’s new with text and text interactions](https://developer.apple.com/videos/play/wwdc2023/10058/)

## Topics

### Creating a text selection display interaction

[`init(textInput: any UITextInput, delegate: any UITextSelectionDisplayInteractionDelegate)`](/documentation/UIKit/UITextSelectionDisplayInteraction/init(textInput:delegate:))

Creates a new text selection display interaction object for the specified text view.

### Managing the drawing view

[`var delegate: (any UITextSelectionDisplayInteractionDelegate)?`](/documentation/UIKit/UITextSelectionDisplayInteraction/delegate)

A delegate that provides a container view to manage the system-supplied selection views.

[`protocol UITextSelectionDisplayInteractionDelegate`](/documentation/UIKit/UITextSelectionDisplayInteractionDelegate)

An object you use to customize the presentation of text selections in your interface.

### Activating the selection UI

[`var isActivated: Bool`](/documentation/UIKit/UITextSelectionDisplayInteraction/isActivated)

A Boolean value that indicates whether to display the system selection UI.

### Reporting changes to the selection

[`func setNeedsSelectionUpdate()`](/documentation/UIKit/UITextSelectionDisplayInteraction/setNeedsSelectionUpdate())

Tells the system to update the selection UI to match the current selection state.

[`func layoutManagedSubviews()`](/documentation/UIKit/UITextSelectionDisplayInteraction/layoutManagedSubviews())

Loads the selection from the text input view and lays out the selection-related views.

### Getting the text input view

[`var textInput: (any UITextInput)?`](/documentation/UIKit/UITextSelectionDisplayInteraction/textInput)

The text input object that manages the selection.

### Getting the system selection views

[`var highlightView: any UIView & UITextSelectionHighlightView`](/documentation/UIKit/UITextSelectionDisplayInteraction/highlightView)

The view that draws the selection highlight behind the rendered text.

[`var handleViews: [any UIView & UITextSelectionHandleView]`](/documentation/UIKit/UITextSelectionDisplayInteraction/handleViews)

The view that draws the selection handles for the selected text.

[`var cursorView: any UIView & UITextCursorView`](/documentation/UIKit/UITextSelectionDisplayInteraction/cursorView)

The view that draws the caret at the text insertion point.

## Relationships

### Conforms To

[`CVarArg`](/documentation/Swift/CVarArg)

[`CustomStringConvertible`](/documentation/Swift/CustomStringConvertible)

[`Sendable`](/documentation/Swift/Sendable)

[`CustomDebugStringConvertible`](/documentation/Swift/CustomDebugStringConvertible)

[`NSObjectProtocol`](/documentation/ObjectiveC/NSObjectProtocol)

[`UIInteraction`](/documentation/UIKit/UIInteraction)

[`Equatable`](/documentation/Swift/Equatable)

[`Hashable`](/documentation/Swift/Hashable)

### Inherits From

[`NSObject-swift.class`](/documentation/ObjectiveC/NSObject-swift.class)

---

Copyright &copy; 2026 Apple Inc. All rights reserved. | [Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html) | [Privacy Policy](https://www.apple.com/privacy/privacy-policy)