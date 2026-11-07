package dev.mixer.android;
final class AppearanceResolverV2 {
    enum Scheme { light,dark } enum Direction { leftToRight,rightToLeft }
    record Viewport(int width, int height) {} record SafeArea(int top,int leading,int bottom,int trailing) {}
    record Accessibility(boolean highContrast, boolean bold, boolean reducedMotion) {}
    record Environment(Scheme scheme, Direction direction, AppearanceDescriptorV2.Profile profile, int density,
        Viewport viewport, SafeArea safeArea, String locale, Accessibility accessibility, String epoch) {}
}
