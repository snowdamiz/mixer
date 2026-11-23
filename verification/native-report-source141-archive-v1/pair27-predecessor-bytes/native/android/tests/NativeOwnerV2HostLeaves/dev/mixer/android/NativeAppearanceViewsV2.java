package dev.mixer.android;

import android.view.View;

/** Type boundary for the orchestration closure. The concrete closure owns editor behavior. */
final class NativeAppearanceViewsV2 {
    static final class Binding {}
    static final class Gate {}

    interface Input {
        Gate committedInputGate(Record record);
    }

    static final class Record {
        boolean verticalInput;
        Binding binding;
        Input input;
    }

    abstract static class NativeField extends View {
        enum Close { RETURNED }

        static final class Attempt {
            Close close;
        }

        Record record;
        Attempt attempt;

        NativeField(android.content.Context context) { super(context); }

        abstract boolean hasLiveTarget();
        abstract boolean resumeInputReady(Attempt predecessor);
        abstract boolean resumeInputIdle(Attempt predecessor);
        abstract boolean resumeInputLive(Attempt predecessor);
    }
}
