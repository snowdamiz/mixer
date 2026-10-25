#if TARGET_OS_OSX || TARGET_OS_MACCATALYST || TARGET_OS_IOS

/*!
 * Hold modifier keys while the given block runs. This method pushes and pops the modifiers as global state
 * without need for reference to a particular element. Inside the block, elements can be clicked on, dragged
 * from, typed into, etc.
 */
+ (void)performWithKeyModifiers:(XCUIKeyModifierFlags)flags block:(XCUI_NOESCAPE void (^)(void))block API_AVAILABLE(ios(15.0), macCatalyst(13.0));

/*!
 * Types a single key with the specified modifier flags. Although `key` is a string, it must represent
 * a single key on a physical keyboard; strings that resolve to multiple keys will raise an error at runtime.
 * In addition to literal string key representations like "a", "6", and "[", keys such as the arrow keys,
 * command, control, option, and function keys can be typed using constants defined for them in XCUIKeyboardKeys.h
 */
- (void)typeKey:(NSString *)key modifierFlags:(XCUIKeyModifierFlags)flags;

#endif // TARGET_OS_OSX || TARGET_OS_MACCATALYST || TARGET_OS_IOS
