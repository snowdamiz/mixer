
/// The currently focused item in this focus system.
@property (nonatomic, weak, readonly, nullable) id<UIFocusItem> focusedItem API_AVAILABLE(tvos(12.0), ios(12.0)) API_UNAVAILABLE(watchos);

+ (instancetype)new NS_UNAVAILABLE;
- (instancetype)init NS_UNAVAILABLE;

/// Return the focus system that the provided environment is contained in. Returns nil if focus
/// interaction is not supported, or if the environment is not associated with any focus system.
#if __swift__
+ (nullable UIFocusSystem *)focusSystemForEnvironment:(id<UIFocusEnvironment>)environment API_DEPRECATED("Use UIFocusSystem.focusSystem(for:) instead.", tvos(12.0, 15.0), ios(12.0, 15.0), visionos(1.0, 1.0));
#else
+ (nullable UIFocusSystem *)focusSystemForEnvironment:(id<UIFocusEnvironment>)environment API_AVAILABLE(tvos(12.0), ios(12.0)) API_UNAVAILABLE(watchos);
#endif

/// Requests a focus update to the specified environment. If accepted, the focus update will happen
/// in the next run loop cycle.
