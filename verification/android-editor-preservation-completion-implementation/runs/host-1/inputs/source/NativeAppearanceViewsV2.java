package dev.mixer.android;

import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.text.Editable;
import android.text.InputFilter;
import android.text.InputType;
import android.text.Layout;
import android.text.TextUtils;
import android.text.TextWatcher;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import static dev.mixer.android.AppearanceDescriptorV2.*;
import dev.mixer.android.AppearanceDescriptorV2.Error;
import static dev.mixer.android.AppearanceResolverV2.*;

/** Concrete Android Views for the closed private measuredShared2 consumer. */
@SuppressWarnings("deprecation")
final class NativeAppearanceViewsV2 {
    private NativeAppearanceViewsV2() {}
    interface Input {
        boolean open(Record record);
        boolean draw();
        void event(Record record, String event, Object value);
        void interaction();
        Mutation mutation();
        boolean editorRetained(Record record);
        boolean editorDispatchAvailable(Record record);
        void editorEnter(Record record, EditorLease lease);
        void editorLeave(Record record, EditorLease lease);
        boolean editorCloseAllowed(Record record,NativeField.Attempt attempt);
        void replacementBegin(Record record,Replacement replacement);
        void replacementEnd(Record record,Replacement replacement);
        long editorLossObservation();
        void editorLossObserved(Record record);
        void fieldPreservationBegin(Record record,FieldPreservation preservation);
        void fieldPreservationEnd(Record record,FieldPreservation preservation);
        void replacementEvent(Record record,Replacement replacement);
        Mutation editorCleanupMutation(Record record, EditorLease lease);
        void editorFinishBegin(Record record, EditorLease lease);
        void editorFinishEnd(Record record, EditorLease lease);
        void editorDrainBegin(Record record, EditorLease lease);
        void editorDrainEnd(Record record, EditorLease lease);
        void editorFailure(Throwable primary, java.lang.Error firstFatal);
    }
    /** Captured direct authority; never asks the allocating lifecycle core from native code. */
    static final class Mutation {
        enum Mode { TRANSACTION, LIVE_PRESENTATION, CLEANUP }
        final Mode mode;
        final NativeOwnerV2.Fence fence;
        final OwnerLifecycleV2.Token token;
        final EditorLease editorLease;
        final Replacement replacementLease;
        final FieldPreservation fieldLease;
        private Mutation(Mode mode, NativeOwnerV2.Fence fence, OwnerLifecycleV2.Token token) {
            this(mode,fence,token,null);
        }
        private Mutation(Mode mode, NativeOwnerV2.Fence fence, OwnerLifecycleV2.Token token,EditorLease editorLease) {
            this(mode,fence,token,editorLease,null);
        }
        private Mutation(Mode mode,NativeOwnerV2.Fence fence,OwnerLifecycleV2.Token token,EditorLease editorLease,Replacement replacementLease){
            this(mode,fence,token,editorLease,replacementLease,null);
        }
        private Mutation(Mode mode,NativeOwnerV2.Fence fence,OwnerLifecycleV2.Token token,EditorLease editorLease,Replacement replacementLease,FieldPreservation fieldLease){
            this.mode=mode;this.fence=fence;this.token=token;this.editorLease=editorLease;this.replacementLease=replacementLease;this.fieldLease=fieldLease;
        }
        static Mutation fieldContinuation(Mutation original,FieldPreservation lease){return new Mutation(original.mode,original.fence,original.token,null,null,lease);}
        static Mutation replacement(Mutation original,Replacement lease,boolean cleanup){return new Mutation(cleanup?Mode.CLEANUP:original.mode,original.fence,cleanup?null:original.token,null,lease);}
        static Mutation editorContinuation(Mutation original,EditorLease lease){return new Mutation(original.mode,original.fence,original.token,lease);}
        static Mutation editorCleanup(NativeOwnerV2.Fence fence,EditorLease lease){return new Mutation(Mode.CLEANUP,fence,null,lease);}
        static Mutation transaction(NativeOwnerV2.Fence fence, OwnerLifecycleV2.Token token) {
            Mutation result=new Mutation(Mode.TRANSACTION,fence,token); result.require(); return result;
        }
        static Mutation live(NativeOwnerV2.Fence fence) {
            Mutation result=new Mutation(Mode.LIVE_PRESENTATION,fence,fence.presentation); result.require(); return result;
        }
        static Mutation cleanup(NativeOwnerV2.Fence fence) { return new Mutation(Mode.CLEANUP,fence,null); }
        boolean current() {
            if(editorLease!=null)editorLease.exact();
            if(replacementLease!=null)replacementLease.exact();
            if(fieldLease!=null)fieldLease.exact();
            return mode==Mode.CLEANUP ? !fence.drawAllowed&&!fence.inputAllowed :
                !fence.terminal&&token!=null&&(mode==Mode.TRANSACTION ? token==fence.operation : token==fence.presentation&&fence.drawAllowed);
        }
        void require() {
            if(editorLease!=null)editorLease.exact();
            if(replacementLease!=null)replacementLease.exact();
            if(fieldLease!=null)fieldLease.exact();
            if(mode==Mode.CLEANUP) {
                if(fence.drawAllowed||fence.inputAllowed)throw new IllegalStateException("cleanup requires sealed authority");
            } else if(fence.terminal||token==null||(mode==Mode.TRANSACTION ? token!=fence.operation :
                token!=fence.presentation||!fence.drawAllowed))throw new IllegalStateException("V2 mutation authority lost");
        }
        void requireMutation() {
            if(fieldLease!=null)throw new IllegalStateException("field callback cannot authorize bind/layout");
            if(replacementLease!=null)throw new IllegalStateException("replacement cannot authorize bind/layout");
            if(mode==Mode.CLEANUP)throw new IllegalStateException("cleanup cannot authorize V2 bind/layout");
            require();
        }
        boolean result(boolean result) {
            if(editorLease!=null)editorLease.exact();
            if(replacementLease!=null)replacementLease.exact();
            if(fieldLease!=null)fieldLease.exact();
            // Observe the original captured scope after the delegate. A completed result is not a new mutation.
            if(mode!=Mode.LIVE_PRESENTATION){require();return result;}
            boolean same=!fence.terminal&&token!=null&&token==fence.presentation&&fence.drawAllowed;
            if(same)return result;
            // A synchronous accepted feature event can publish a successor before the delegate returns.
            // No native call, event, mutation, or replacement scope is acquired on this return path.
            return token!=null&&!fence.terminal&&fence.drawAllowed&&fence.presentation!=null&&token!=fence.presentation&&result;
        }
        <T> T result(T result) { require(); return result; }
    }
    record Binding(AppearanceResolverV2.Plan plan, AppearanceResolverV2.Node node,
                   UiPacket.Node source, AppearanceDescriptorV2.Theme theme,
                   String nativeFieldValue, Boolean nativeToggleValue) {
        Binding(AppearanceResolverV2.Plan plan,AppearanceResolverV2.Node node,UiPacket.Node source,AppearanceDescriptorV2.Theme theme){
            this(plan,node,source,theme,node.recipe() instanceof FieldRecipe field?field.text().value():null,
                node.recipe() instanceof ToggleRecipe toggle?toggle.checked():null);
        }
        AppearanceDescriptorV2.Paints palette() { return plan.environment.scheme() == Scheme.light ? theme.light() : theme.dark(); }
        int density() { return plan.environment.density1024(); }
        boolean rtl() { return plan.environment.direction() == AppearanceResolverV2.Direction.rightToLeft; }
    }
    /** Logical edges are rounded once in the containing coordinate system. */
    record Box(long x, long y, long width, long height) {
        Box { extent(x); extent(y); extent(width); extent(height); extent(x+width); extent(y+height); }
    }
    static final class Geometry {
        Box box = new Box(0,0,0,0);
        long semanticHeight;
        long firstBaseline = -1, lastBaseline = -1;
        final Map<String,Box> children = new HashMap<>();
        final List<GroupDrawing> groups = new ArrayList<>();
        final Map<String,Integer> clips = new HashMap<>();
        Box header, compact;
        long contentHeight, expandedBar, compactBar, overflow;boolean collapsed;
    }
    static final class GroupDrawing {
        final Box box;
        final Path path;
        final List<Long> separators;
        GroupDrawing(Box box, int radius, int density, List<Long> separators) {
            this.box=box; this.separators=List.copyOf(separators);
            path=AppearanceNativePathsV2.make(AppearanceGeometryV2.group(box.width,box.height,radius),density);
        }
    }
    static final class Record {
        final String id, generation, kind;
        final View view;
        final Group group;
        final TextView header, compact;
        final Input input;
        final NativeOwnerV2.Fence editorFence;
        Binding binding;
        Geometry geometry;
        boolean changing;int preparedScrollY;
        long cancelClaim;
        Throwable cancellationOrdinary;java.lang.Error cancellationFatal;
        private void cancellationFailure(Throwable failure){
            if(failure instanceof RuntimeException&&cancellationOrdinary==null)cancellationOrdinary=failure;
            if(failure instanceof java.lang.Error fatal&&cancellationFatal==null)cancellationFatal=fatal;
        }
        private Mutation scoped;
        private boolean constructed;
        EditorLease editorCallbackLease;
        Replacement replacementCallback;
        FieldPreservation fieldPreservation;
        InputFilter editorFilter;
        boolean editorEventsAllowed() {
            NativeEnvironmentV2.requireMain();
            return !(view instanceof NativeField field)||field.eventsAllowed();
        }
        boolean editorConstruction() { return scoped!=null&&!constructed; }
        Mutation mutation() {
            NativeEnvironmentV2.requireMain();
            if(replacementCallback!=null)return replacementCallback.continuation();
            if(fieldPreservation!=null)return fieldPreservation.continuation();
            if(editorCallbackLease!=null)return editorCallbackLease.continuation();
            return scoped!=null?scoped:input.mutation();
        }
        void editorAvailable(boolean preserve) {
            NativeEnvironmentV2.requireMain();
            if(view instanceof NativeField field)field.available(preserve);
        }
        void retireEditor() {
            if(view instanceof NativeField field)field.retirePermanent();
        }
        Record(Context context, UiPacket.Node source, Input input, Mutation mutation) {
            mutation.requireMutation();scoped=mutation;
            id=source.id; generation=source.generation; kind=source.kind; this.input=input;editorFence=mutation.fence;
            try {
            Group container=null; TextView title=null, small=null;
            switch(kind) {
                case "text" -> { view=new TextView(context);mutation.require(); }
                case "button" -> { view=new NativeButton(context,this);mutation.require(); }
                case "textField" -> { view=new NativeField(context,this);mutation.require(); }
                case "toggle" -> { view=new NativeSwitch(context,this);mutation.require(); }
                case "list" -> { container=new Group(context,this);mutation.require();
 NativeScroll scroll=new NativeScroll(context,this);mutation.require();

                    scroll.addView(container,new ScrollView.LayoutParams(-1,-2));mutation.require();
 view=scroll; }
                default -> { container=new Group(context,this);mutation.require();
 view=container;
                    if(kind.equals("section")||kind.equals("navigation")) { title=new TextView(context);mutation.require();

                        container.addView(title);mutation.require();
 if(kind.equals("navigation")){small=new TextView(context);mutation.require();
container.addView(small);mutation.require();
} }
                }
            }
            group=container; header=title; compact=small;
            view.setId(View.generateViewId());mutation.require();
 view.setTag(id);mutation.require();

            view.setBackground(null);mutation.require();
view.setBackgroundTintList(null);mutation.require();
view.setBackgroundTintMode(null);mutation.require();
 view.setElevation(0);mutation.require();
 view.setStateListAnimator(null);mutation.require();

            view.setDefaultFocusHighlightEnabled(false);mutation.require();
 view.setPadding(0,0,0,0);mutation.require();

            view.setMinimumWidth(0);mutation.require();
 view.setMinimumHeight(0);mutation.require();

            view.setOnFocusChangeListener((changed,focused)->{if(editorEventsAllowed()&&input.open(this))input.interaction();});mutation.require();

            if(view instanceof TextView text) defaults(text,mutation);
            if(header!=null)defaults(header,mutation); if(compact!=null)defaults(compact,mutation);
            if(kind.equals("button")&&view instanceof Button button) button.setOnClickListener(ignored -> { if(input.open(this)) input.event(this,"activate",null); });mutation.require();

            if(view instanceof EditText edit) {
                edit.setSingleLine(true);mutation.require();
 edit.setHorizontallyScrolling(true);mutation.require();

                edit.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);mutation.require();

                edit.setImeOptions(EditorInfo.IME_ACTION_DONE);mutation.require();

                editorFilter=(src,start,end,dst,dstart,dend)-> {
                    if(replacementCallback!=null)return replacementCallback.filter(src,start,end,dst,dstart,dend);
                    if(changing)return null;
                    if(!editorEventsAllowed())return dst.subSequence(dstart,dend);
                    if(!input.open(this))return dst.subSequence(dstart,dend);
                    String proposed=dst.subSequence(0,dstart).toString()+src.subSequence(start,end)+dst.subSequence(dend,dst.length());
                    // systemSans intentionally admits native script/emoji fallback.
                    return validBuffer(proposed) ? null : dst.subSequence(dstart,dend);
                };edit.setFilters(new InputFilter[]{editorFilter});mutation.require();

                edit.addTextChangedListener(new TextWatcher(){
                    public void beforeTextChanged(CharSequence s,int start,int count,int after){}
                    public void onTextChanged(CharSequence s,int start,int before,int count){}
                    public void afterTextChanged(Editable value){if(view instanceof NativeField field&&field.replacement!=null&&replacementCallback==null&&editorCallbackLease==null){field.uncertain(new IllegalStateException("unknown replacement pre-native text callback"));field.surface();return;}if(replacementCallback!=null){replacementCallback.watch(value);return;}if(!changing&&editorEventsAllowed()&&input.open(Record.this))input.event(Record.this,"textChange",value.toString());}
                });mutation.require();

                edit.setOnEditorActionListener((field,action,event)-> {
                    if(action==EditorInfo.IME_ACTION_DONE&&editorEventsAllowed()&&input.open(this)&&binding!=null&&binding.source.actions.containsKey("submit")) {
                        input.event(this,"submit",null);return true;
                    }return false;
                });mutation.require();

            }
            if(view instanceof Switch toggle) toggle.setOnCheckedChangeListener((button,checked)-> {
                if(!changing&&input.open(this))input.event(this,"valueChange",checked);
                if(input.open(this)){Mutation callbackScope=mutation();callbackScope.require();toggle.invalidate();callbackScope.require();}
            });mutation.require();
            constructed=true;
            } finally { scoped=null; }
        }
        void cancelToggleInput() { if(view instanceof NativeSwitch toggle)toggle.cancelTouch(); }
        void bind(Binding next, Geometry measured, boolean preserveEditor, Mutation mutation) {
            mutation.requireMutation();editorAvailable(preserveEditor);Mutation previousScope=scoped;scoped=mutation;
            boolean previousChanging=changing;
            try {
                cancelToggleInput();mutation.require();changing=true;
                binding=next; geometry=measured;
                if(!preserveEditor) {
                    view.setEnabled(!next.node.disabled());mutation.require();

                    view.setLayoutDirection(next.rtl()?View.LAYOUT_DIRECTION_RTL:View.LAYOUT_DIRECTION_LTR);mutation.require();

                    view.setTag(next.source.text("accessibilityIdentifier",id));mutation.require();

                    view.setContentDescription(next.source.text("accessibilityLabel",kind.equals("textField")?next.source.text("label",""):null));mutation.require();

                    view.setTooltipText(next.source.text("accessibilityHint",null));mutation.require();

                    if(android.os.Build.VERSION.SDK_INT>=30)view.setStateDescription(next.source.text("accessibilityValue",null));mutation.require();

                    if(next.node.recipe() instanceof TextRecipe r) {
                        TextView text=(TextView)view; text(text,r.text(),next,mutation);text.setTextIsSelectable(r.text().selectable());mutation.require();

                        text.setTextColor(color(((TextPaints)next.plan.style(id,false,false).paints()).foreground()));mutation.require();

                    } else if(next.node.recipe() instanceof ButtonRecipe r) {
                        NativeButton button=(NativeButton)view;text(button,r.text(),next,mutation);button.setAllCaps(false);mutation.require();

                        button.setBackground(new ControlDrawable(this,false));mutation.require();
button.setTextColor(buttonColors(next,r));mutation.require();

                    } else if(next.node.recipe() instanceof FieldRecipe r) {
                        NativeField field=(NativeField)view;Text value=r.text();text(field,new Text(next.nativeFieldValue(),value.role(),value.metrics(),value.selectable(),value.maximumLines()),next,mutation);field.setHint(r.label());mutation.require();

                        field.setGravity((next.rtl()?Gravity.RIGHT:Gravity.LEFT)|Gravity.CENTER_VERTICAL);mutation.require();

                        Insets in=r.metrics().insets64();field.setPadding(px(next.rtl()?in.trailing():in.leading(),next),px(in.top(),next),
                            px(next.rtl()?in.leading():in.trailing(),next),px(in.bottom(),next));mutation.require();

                        field.setBackground(new ControlDrawable(this,true));mutation.require();
field.setTextColor(fieldColors(next,false));mutation.require();

                        field.setHintTextColor(fieldColors(next,true));mutation.require();

                        field.setTextCursorDrawable(new Cursor(this));mutation.require();

                        field.setTextSelectHandle(new Handle(this));mutation.require();
field.setTextSelectHandleLeft(new Handle(this));mutation.require();
field.setTextSelectHandleRight(new Handle(this));mutation.require();

                        field.refreshPaint();
                    } else if(next.node.recipe() instanceof ToggleRecipe r) {
                        NativeSwitch toggle=(NativeSwitch)view;text(toggle,r.text(),next,mutation);toggle.setChecked(next.nativeToggleValue());mutation.require();

                        toggle.setSwitchMinWidth(px(r.metrics().trackWidth64(),next));mutation.require();
toggle.setSwitchPadding(px(r.metrics().labelGap64(),next));mutation.require();

                        toggle.setThumbDrawable(new Empty(px(r.metrics().thumbWidth64(),next),px(r.metrics().thumbHeight64(),next)));mutation.require();

                        toggle.setTrackDrawable(new Empty(px(r.metrics().trackWidth64(),next),px(r.metrics().trackHeight64(),next)));mutation.require();

                        toggle.setSplitTrack(false);mutation.require();
toggle.setShowText(false);mutation.require();
toggle.setThumbTextPadding(0);mutation.require();

                        toggle.track=AppearanceNativePathsV2.make(AppearanceGeometryV2.track(),next.density());
                        toggle.thumb=AppearanceNativePathsV2.make(AppearanceGeometryV2.thumb(),next.density());
                        toggle.refreshPaint();
                    }
                }
                if(next.node.recipe() instanceof SectionRecipe r&&header!=null) bindTitle(header,r.header(),next,
                    ((SectionPaints)next.plan.style(id,false,false).paints()).header(),mutation);
                if(next.node.recipe() instanceof NavigationRecipe r&&header!=null) {
                    NavigationPaints colors=(NavigationPaints)next.plan.style(id,false,false).paints();
                    bindTitle(header,r.expandedTitle(),next,colors.expanded(),mutation);bindTitle(compact,r.compactTitle(),next,colors.compact(),mutation);compact.setGravity(Gravity.TOP|Gravity.CENTER_HORIZONTAL);mutation.require();

                    header.setVisibility(!measured.collapsed&&r.expandedTitle()!=null?View.VISIBLE:View.INVISIBLE);mutation.require();
compact.setVisibility(measured.collapsed&&r.compactTitle()!=null?View.VISIBLE:View.INVISIBLE);mutation.require();

                }
                view.invalidate();mutation.require();

            } finally { changing=previousChanging; scoped=previousScope; }
        }
    }
    private static boolean plainProposal(CharSequence value,boolean composing){
        if(value==null)return false;
        if(value instanceof android.text.Spanned spans)for(Object span:spans.getSpans(0,spans.length(),Object.class))
            if(!(span instanceof android.text.Annotation)&&!(composing&&span.getClass()==android.text.style.UnderlineSpan.class))return false;
        return true;
    }
    private static boolean validBuffer(String value){
        for(int i=0;i<value.length();i++){char c=value.charAt(i);if(Character.isHighSurrogate(c)){if(++i>=value.length()||!Character.isLowSurrogate(value.charAt(i)))return false;}else if(Character.isLowSurrogate(c))return false;}
        return value.getBytes(java.nio.charset.StandardCharsets.UTF_8).length<=16384;
    }
    private static void defaults(TextView text,Mutation mutation) {mutation.requireMutation();
        text.setIncludeFontPadding(false);mutation.require();
text.setFallbackLineSpacing(true);mutation.require();
text.setPadding(0,0,0,0);mutation.require();

        text.setAllCaps(false);mutation.require();
text.setAutoSizeTextTypeWithDefaults(TextView.AUTO_SIZE_TEXT_TYPE_NONE);mutation.require();
text.setTextAlignment(View.TEXT_ALIGNMENT_GRAVITY);mutation.require();
text.setTextDirection(View.TEXT_DIRECTION_FIRST_STRONG);mutation.require();

        text.setMinWidth(0);mutation.require();
text.setMinHeight(0);mutation.require();
text.setMinimumWidth(0);mutation.require();
text.setMinimumHeight(0);mutation.require();

        text.setCompoundDrawablePadding(0);mutation.require();
text.setCompoundDrawables(null,null,null,null);mutation.require();

        text.setLetterSpacing(0);mutation.require();
text.setTextScaleX(1);mutation.require();
text.setShadowLayer(0,0,0,0);mutation.require();

        text.setGravity(Gravity.TOP|Gravity.START);mutation.require();
text.setBreakStrategy(Layout.BREAK_STRATEGY_HIGH_QUALITY);mutation.require();

        text.setHyphenationFrequency(Layout.HYPHENATION_FREQUENCY_NORMAL);mutation.require();

    }
    private static void text(TextView view, Text text, Binding binding,Mutation mutation) {mutation.requireMutation();
        if(!view.getText().toString().equals(text.value()))view.setText(text.value());mutation.require();

        view.setTextSize(TypedValue.COMPLEX_UNIT_PX,(float)AppearanceGeometryV2.pixelCoordinate(text.metrics().size64(),binding.density()));mutation.require();

        view.setTypeface(Typeface.create(Typeface.create("sans-serif",Typeface.NORMAL),text.metrics().weight().value,false));mutation.require();

        view.setTextLocales(new android.os.LocaleList(java.util.Locale.forLanguageTag(binding.plan.environment.localeIdentifier())));mutation.require();

        view.setMaxLines(text.maximumLines()==null?Integer.MAX_VALUE:text.maximumLines());mutation.require();

        view.setEllipsize(text.maximumLines()==null?null:TextUtils.TruncateAt.END);mutation.require();

    }
    private static void bindTitle(TextView view, Text text, Binding binding, Color ink,Mutation mutation) {mutation.requireMutation();
        view.setVisibility(text==null?View.GONE:View.VISIBLE);mutation.require();

        if(text!=null){text(view,text,binding,mutation);view.setTextColor(color(ink));mutation.require();
}
    }
    private static ColorStateList buttonColors(Binding b,ButtonRecipe recipe) {
        ButtonStates s=buttonStates(b,recipe.role());
        return colors(s.disabled().label(),s.pressed().label(),s.enabled().label(),s.enabled().label());
    }
    private static ColorStateList fieldColors(Binding b,boolean placeholder) {
        FieldStates s=b.palette().field();
        return new ColorStateList(new int[][]{{-android.R.attr.state_enabled},{android.R.attr.state_focused},{}},
            new int[]{color(placeholder?s.disabled().placeholder():s.disabled().text()),
                color(placeholder?s.focused().placeholder():s.focused().text()),color(placeholder?s.enabled().placeholder():s.enabled().text())});
    }
    private static ColorStateList colors(Color disabled,Color pressed,Color focused,Color enabled) {
        return new ColorStateList(new int[][]{{-android.R.attr.state_enabled},{android.R.attr.state_pressed},
            {android.R.attr.state_focused},{}},new int[]{color(disabled),color(pressed),color(focused),color(enabled)});
    }
    static ButtonStates buttonStates(Binding b,ButtonRole role) {return switch(role){
        case normal -> b.palette().button().normal();case destructive -> b.palette().button().destructive();case cancel -> b.palette().button().cancel();};}
    static FieldPaint fieldPaint(Record r) {FieldStates s=r.binding.palette().field();return !r.view.isEnabled()?s.disabled():r.view.isFocused()?s.focused():s.enabled();}
    static TogglePaint togglePaint(Record r) {ToggleStates s=((NativeSwitch)r.view).visualChecked()?r.binding.palette().toggle().on():r.binding.palette().toggle().off();
        return !r.view.isEnabled()?s.disabled():r.view.isPressed()?s.pressed():s.enabled();}
    static int color(Color c) {return android.graphics.Color.argb(c.alpha(),c.red(),c.green(),c.blue());}
    static int px(long value,Binding b){return AppearanceGeometryV2.pixelEdge(value,b.density());}
    static long logical(int pixels,Binding b){return AppearanceGeometryV2.measuredExtent64(pixels*1024.0/b.density());}
    static long sum(long... values){long result=0;for(long value:values){extent(value);result+=value;extent(result);}return result;}
    static void extent(long value){if(value<0||value>AppearanceGeometryV2.MAXIMUM_EXTENT64)throw new Failure(Error.layout);}
    static void fail(){throw new Failure(Error.layout);}

    /** Actual native measurement, followed by checked logical aggregation. Never mutates a live record. */
    static void measure(Record r,Map<String,Record> records,long availableWidth,long availableHeight,Mutation mutation) {
        mutation.requireMutation();Mutation previous=r.scoped;r.scoped=mutation;
        try {
        extent(availableWidth);extent(availableHeight);if(availableWidth<=0)fail();
        Binding b=r.binding;r.geometry=new Geometry();Geometry g=r.geometry;
        if(r.view instanceof TextView text) {
            long reserve=0;
            if(b.node.recipe() instanceof ToggleRecipe t)reserve=sum(t.metrics().trackWidth64(),t.metrics().labelGap64());
            if(b.node.recipe() instanceof ButtonRecipe t){Insets in=t.metrics().labelInsets64();reserve=sum(in.leading(),in.trailing());
                text.setGravity(Gravity.CENTER);mutation.require();
text.setPadding(px(b.rtl()?in.trailing():in.leading(),b),px(in.top(),b),px(b.rtl()?in.leading():in.trailing(),b),px(in.bottom(),b));mutation.require();
}
            if(b.node.recipe() instanceof FieldRecipe t)reserve=sum(t.metrics().insets64().leading(),t.metrics().insets64().trailing());
            if(availableWidth<=reserve)fail();
            // Switch's native layout reserves its actual authored drawable width and gap.
            int maximum=px(availableWidth,b);if(maximum<=0)fail();
            text.measure(View.MeasureSpec.makeMeasureSpec(maximum,View.MeasureSpec.AT_MOST),View.MeasureSpec.makeMeasureSpec(0,View.MeasureSpec.UNSPECIFIED));mutation.require();

            if(text.getLayout()==null)fail();
            long nativeHeight=logical(text.getLayout().getHeight(),b);
            long width=logical(text.getMeasuredWidth(),b),height=nativeHeight;
            if(b.node.recipe() instanceof ToggleRecipe t) {g.semanticHeight=nativeHeight;
                width=Math.max(width,t.metrics().minimumHitWidth64());height=Math.max(Math.max(height,t.metrics().trackHeight64()),t.metrics().minimumHitHeight64());}
            else if(b.node.recipe() instanceof ButtonRecipe t) {Insets in=t.metrics().labelInsets64();g.semanticHeight=sum(height,in.top(),in.bottom());
                width=Math.max(width,t.metrics().minimumHitWidth64());height=Math.max(g.semanticHeight,t.metrics().minimumHitHeight64());}
            else if(b.node.recipe() instanceof FieldRecipe t) {g.semanticHeight=Math.max(t.metrics().minimumContentHeight64(),sum(height,t.metrics().insets64().top(),t.metrics().insets64().bottom()));
                width=availableWidth;height=Math.max(g.semanticHeight,t.metrics().minimumHitHeight64());}
            else g.semanticHeight=height;
            if(width>availableWidth)fail();g.box=new Box(0,0,width,height);
            text.measure(View.MeasureSpec.makeMeasureSpec(px(width,b),View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(px(height,b),View.MeasureSpec.EXACTLY));mutation.require();

            // The shared first-consumer subset exposes baseline scalars only for ordinary text.
            // Native control carriers/custom label drawing do not establish matching shaped baselines.
            if(b.node.recipe() instanceof TextRecipe){int first=text.getBaseline();if(first<0)fail();g.firstBaseline=logical(first,b);
                g.lastBaseline=sum(g.firstBaseline,logical(text.getLayout().getLineBaseline(text.getLayout().getLineCount()-1)-text.getLayout().getLineBaseline(0),b));}return;
        }
        if(b.node.recipe() instanceof ListRecipe list) {measureList(r,records,list,availableWidth,availableHeight,mutation);return;}
        if(b.node.recipe() instanceof SectionRecipe section&&section.context() instanceof ListGroup) {
            // Its List assigns row policy and group clip using its own exact recipe.
            return;
        }
        List<String> ids=b.node.childIDs();long width=0,height=0;
        if(b.node.recipe() instanceof NavigationRecipe nav) {
            long compact=title(r.compact,nav.compactTitle(),availableWidth,nav.metrics().compactInsets64(),b,mutation);
            long expanded=title(r.header,nav.expandedTitle(),availableWidth,nav.metrics().expandedInsets64(),b,mutation);
            g.compactBar=Math.max(nav.metrics().minimumCompactBar64(),compact);
            g.expandedBar=nav.expandedTitle()==null?g.compactBar:Math.max(nav.metrics().minimumExpandedBar64(),sum(g.compactBar,expanded));
            g.overflow=g.expandedBar-g.compactBar;
            boolean collapsed=g.overflow==0||scrollOffset(records,ids,b)>=g.overflow;g.collapsed=collapsed;
            long bar=collapsed?g.compactBar:g.expandedBar;
            long eh=nav.expandedTitle()==null?0:expanded-nav.metrics().expandedInsets64().top()-nav.metrics().expandedInsets64().bottom();
            long ch=nav.compactTitle()==null?0:compact-nav.metrics().compactInsets64().top()-nav.metrics().compactInsets64().bottom();
            g.header=new Box(b.rtl()?nav.metrics().expandedInsets64().trailing():nav.metrics().expandedInsets64().leading(),sum(g.compactBar,nav.metrics().expandedInsets64().top()),
                availableWidth-nav.metrics().expandedInsets64().leading()-nav.metrics().expandedInsets64().trailing(),eh);
            g.compact=new Box(b.rtl()?nav.metrics().compactInsets64().trailing():nav.metrics().compactInsets64().leading(),nav.metrics().compactInsets64().top()+(g.compactBar-nav.metrics().compactInsets64().top()-nav.metrics().compactInsets64().bottom()-ch)/2,
                availableWidth-nav.metrics().compactInsets64().leading()-nav.metrics().compactInsets64().trailing(),ch);
            r.header.setVisibility(!collapsed&&nav.expandedTitle()!=null?View.VISIBLE:View.INVISIBLE);mutation.require();

            r.compact.setVisibility(collapsed&&nav.compactTitle()!=null?View.VISIBLE:View.INVISIBLE);mutation.require();

            if(availableHeight<bar)fail();Record child=records.get(ids.get(0));measure(child,records,availableWidth,availableHeight-bar,mutation);
            g.children.put(child.id,new Box(0,bar,availableWidth,Math.min(child.geometry.box.height,availableHeight-bar)));
            g.box=new Box(0,0,availableWidth,availableHeight);g.semanticHeight=availableHeight;return;
        }
        long titleWidth=0,titleHeight=0,titleFirst=-1,titleLast=-1,gap=0;
        if(b.node.recipe() instanceof SectionRecipe s) {
            if(s.header()!=null){
                r.header.measure(View.MeasureSpec.makeMeasureSpec(px(availableWidth,b),View.MeasureSpec.AT_MOST),View.MeasureSpec.makeMeasureSpec(0,View.MeasureSpec.UNSPECIFIED));mutation.require();

                if(r.header.getLayout()==null)fail();titleWidth=logical(r.header.getMeasuredWidth(),b);titleHeight=logical(r.header.getLayout().getHeight(),b);
                if(titleWidth>availableWidth)fail();
                int first=r.header.getBaseline();if(first>=0){titleFirst=logical(first,b);
                    titleLast=sum(titleFirst,logical(r.header.getLayout().getLineBaseline(r.header.getLayout().getLineCount()-1)-r.header.getLayout().getLineBaseline(0),b));}
            }
            gap=s.headerToContentGap64();
        }
        boolean horizontal=b.node.recipe() instanceof HStackRecipe;
        boolean overlay=b.node.recipe() instanceof ZStackRecipe;
        List<Integer> gaps=b.node.recipe() instanceof HStackRecipe h?h.gaps64():b.node.recipe() instanceof VStackRecipe v?v.gaps64():
            b.node.recipe() instanceof SectionRecipe s?s.contentGaps64():List.of();
        long gapsTotal=0;for(int item:gaps)gapsTotal=sum(gapsTotal,item);
        for(String id:ids) {
            Record child=records.get(id);measure(child,records,availableWidth,availableHeight,mutation);
            width=horizontal?sum(width,child.geometry.box.width):Math.max(width,child.geometry.box.width);
            height=overlay?Math.max(height,child.geometry.box.height):horizontal?Math.max(height,child.geometry.box.height):sum(height,child.geometry.box.height);
        }
        // Private shared consumer proposal: intrinsic probes first, equal proposals only on overflow.
        if(horizontal&&sum(width,gapsTotal)>availableWidth) {
            if(gapsTotal>availableWidth||ids.isEmpty())fail();
            long remaining=availableWidth-gapsTotal,quotient=remaining/ids.size(),remainder=remaining%ids.size();
            width=0;height=0;
            for(int index=0;index<ids.size();index++) {
                Record child=records.get(ids.get(index));child.geometry=new Geometry();
                measure(child,records,quotient+(index<remainder?1:0),availableHeight,mutation);
                width=sum(width,child.geometry.box.width);height=Math.max(height,child.geometry.box.height);
            }
        }
        if(horizontal)width=sum(width,gapsTotal);else if(!overlay)height=sum(height,gapsTotal,titleHeight,gap);
        if(b.node.recipe() instanceof SectionRecipe s){width=Math.max(width,titleWidth);
            if(s.header()!=null)g.header=new Box(align(HorizontalAlignment.leading,width,titleWidth,b.rtl()),0,titleWidth,titleHeight);}
        long baseline=0,descent=0;
        if(b.node.recipe() instanceof HStackRecipe h&&(h.alignment()==VerticalAlignment.firstTextBaseline||h.alignment()==VerticalAlignment.lastTextBaseline)) {
            for(String id:ids){Record c=records.get(id);long cb=h.alignment()==VerticalAlignment.firstTextBaseline?c.geometry.firstBaseline:c.geometry.lastBaseline;
                if(cb<0)throw new Failure(Error.unsupportedNativeOperation);baseline=Math.max(baseline,cb);descent=Math.max(descent,c.geometry.box.height-cb);}
            height=sum(baseline,descent);
        }
        long cursor=horizontal?0:sum(titleHeight,gap);
        for(int index=0;index<ids.size();index++) {
            Record child=records.get(ids.get(index));Box cb=child.geometry.box;long x=0,y=0;
            if(horizontal) {x=b.rtl()?width-cursor-cb.width:cursor;
                VerticalAlignment a=((HStackRecipe)b.node.recipe()).alignment();
                y=switch(a){case top->0;case center->(height-cb.height)/2;case bottom->height-cb.height;
                    case firstTextBaseline->baseline-child.geometry.firstBaseline;case lastTextBaseline->baseline-child.geometry.lastBaseline;};
            } else if(overlay) {
                OverlayAlignment a=((ZStackRecipe)b.node.recipe()).alignment();String value=a.name();
                HorizontalAlignment ha=value.contains("Leading")||a==OverlayAlignment.leading?HorizontalAlignment.leading:
                    value.contains("Trailing")||a==OverlayAlignment.trailing?HorizontalAlignment.trailing:HorizontalAlignment.center;
                x=align(ha,width,cb.width,b.rtl());y=value.startsWith("top")?0:value.startsWith("bottom")?height-cb.height:(height-cb.height)/2;
            } else {HorizontalAlignment a=b.node.recipe() instanceof VStackRecipe v?v.alignment():HorizontalAlignment.leading;
                x=align(a,width,cb.width,b.rtl());y=cursor;}
            g.children.put(child.id,new Box(x,y,cb.width,cb.height));
            if(!overlay)cursor=sum(cursor,horizontal?cb.width:cb.height,index<gaps.size()?gaps.get(index):0);
        }
        g.box=new Box(0,0,width,height);g.semanticHeight=height;
        if(!ids.isEmpty()){Record first=records.get(ids.get(0)),last=records.get(ids.get(ids.size()-1));
            if(first.geometry.firstBaseline>=0)g.firstBaseline=sum(g.children.get(first.id).y,first.geometry.firstBaseline);
            if(last.geometry.lastBaseline>=0)g.lastBaseline=sum(g.children.get(last.id).y,last.geometry.lastBaseline);}
        if(b.node.recipe() instanceof SectionRecipe s&&s.header()!=null){
            g.firstBaseline=titleFirst>=0?sum(g.header.y,titleFirst):-1;
            if(ids.isEmpty())g.lastBaseline=titleLast>=0?sum(g.header.y,titleLast):-1;
        }
        } finally { r.scoped=previous; }
    }
    private static long scrollOffset(Map<String,Record> records,List<String> ids,Binding binding) {
        for(String id:ids){Record r=records.get(id);if(r.view instanceof ScrollView)return logical(r.preparedScrollY,binding);
            long value=scrollOffset(records,r.binding.node.childIDs(),binding);if(value>0)return value;}return 0;
    }
    private static long title(TextView view,Text text,long available,Insets in,Binding b,Mutation mutation) {mutation.requireMutation();
        if(text==null)return 0;long reserve=sum(in.leading(),in.trailing());if(available<=reserve)fail();
        view.measure(View.MeasureSpec.makeMeasureSpec(px(available-reserve,b),View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(0,View.MeasureSpec.UNSPECIFIED));mutation.require();

        if(view.getLayout()==null)fail();return sum(logical(view.getMeasuredHeight(),b),in.top(),in.bottom());
    }
    private static long align(HorizontalAlignment alignment,long parent,long child,boolean rtl) {
        return alignment==HorizontalAlignment.center?(parent-child)/2:(alignment==HorizontalAlignment.trailing)!=rtl?parent-child:0;
    }
    private static void measureList(Record r,Map<String,Record> records,ListRecipe list,long width,long availableHeight,Mutation mutation) {
        mutation.requireMutation();
        Binding b=r.binding;Geometry g=r.geometry;GroupedList m=list.metrics();long groupWidth=width-2L*m.outerHorizontal64();
        if(groupWidth<sum(m.contentInsets64().leading(),m.contentInsets64().trailing()))fail();long y=0;
        for(AppearanceResolverV2.Group item:list.groups()) {
            if(!item.visible()) {if(item.source() instanceof SectionSource s) {Record section=records.get(s.identity().id());
                section.geometry.box=new Box(0,0,0,0);g.children.put(section.id,new Box(0,0,0,0));}continue;}
            y=sum(y,item.leadingGap64());
            Record section=item.source() instanceof SectionSource s?records.get(s.identity().id()):null;
            if(section!=null)section.geometry=new Geometry();Geometry owner=section==null?g:section.geometry;long localY=section==null?y:0;
            if(section!=null) {
                long headerHeight=title(section.header,item.header(),groupWidth,new Insets(0,0,0,0),b,mutation);
                if(item.header()!=null)owner.header=new Box(0,0,groupWidth,headerHeight);
                localY=sum(localY,headerHeight,item.headerToRowsGap64());
            }
            long groupTop=localY;List<Long> separators=new ArrayList<>();
            for(int index=0;index<item.rowIdentities().size();index++) {
                Record row=records.get(item.rowIdentities().get(index).id());
                long contentWidth=groupWidth-m.contentInsets64().leading()-m.contentInsets64().trailing();
                measure(row,records,contentWidth,availableHeight,mutation);
                long semantic=row.geometry.semanticHeight;
                long rowHeight=Math.max(list.rowHeightFloor64(),sum(semantic,m.contentInsets64().top(),m.contentInsets64().bottom()));
                long childHeight=Math.max(row.geometry.box.height,semantic);
                // Minimum hit envelopes do not enter semantic row-height arithmetic.
                if(childHeight>rowHeight)fail();
                long leading=m.contentInsets64().leading();long x=section==null?m.outerHorizontal64()+leading:leading;
                long childWidth=row.geometry.box.width;
                if(row.binding.node.recipe() instanceof ToggleRecipe||row.binding.node.recipe() instanceof FieldRecipe)childWidth=contentWidth;
                if(b.rtl())x=(section==null?width:groupWidth)-x-childWidth;
                long vertical=m.contentInsets64().top()+(rowHeight-m.contentInsets64().top()-m.contentInsets64().bottom()-childHeight)/2;
                if(vertical<0||vertical+childHeight>rowHeight)fail();
                owner.children.put(row.id,new Box(x,sum(localY,vertical),childWidth,childHeight));
                localY=sum(localY,rowHeight);if(index+1<item.rowIdentities().size())separators.add(localY);
            }
            if(!item.rowIdentities().isEmpty()) {
                Box box=new Box(section==null?m.outerHorizontal64():0,groupTop,groupWidth,localY-groupTop);
                int clip=owner.groups.size();owner.groups.add(new GroupDrawing(box,m.radius64(),b.density(),separators));
                for(Identity id:item.rowIdentities())owner.clips.put(id.id(),clip);
            }
            if(section!=null){owner.box=new Box(0,0,groupWidth,localY);owner.semanticHeight=localY;
                g.children.put(section.id,new Box(m.outerHorizontal64(),y,groupWidth,localY));y=sum(y,localY);}
            else y=localY;
        }
        g.contentHeight=sum(y,list.trailingPadding64());g.box=new Box(0,0,width,Math.min(g.contentHeight,availableHeight));g.semanticHeight=g.box.height;
    }

    static void installChildren(Record r,Map<String,Record> records,Mutation mutation) {
        mutation.requireMutation();
        if(r.group==null)return;
        List<View> desired=new ArrayList<>();if(r.header!=null)desired.add(r.header);if(r.compact!=null)desired.add(r.compact);
        for(String id:r.binding.node.childIDs())desired.add(records.get(id).view);
        for(int index=r.group.getChildCount()-1;index>=0;index--)if(!desired.contains(r.group.getChildAt(index))){r.group.removeViewAt(index);mutation.require();}

        for(int index=0;index<desired.size();index++) {
            View child=desired.get(index);if(index<r.group.getChildCount()&&r.group.getChildAt(index)==child)continue;
            if(child.getParent() instanceof ViewGroup previous)previous.removeView(child);mutation.require();

            r.group.addView(child,index,new ViewGroup.LayoutParams(-2,-2));mutation.require();

        }
        r.group.records=records;
    }
    static void layoutRoot(Record root,int width,int height,SafeArea safe,Mutation mutation) {
        mutation.requireMutation();
        Binding b=root.binding;long left=b.rtl()?safe.trailing():safe.leading();
        long logicalWidth=b.plan.environment.viewport().width64()-safe.leading()-safe.trailing();
        long logicalHeight=b.plan.environment.viewport().height64()-safe.top()-safe.bottom();
        root.geometry.box=new Box(left,safe.top(),logicalWidth,logicalHeight);
        layout(root,left,safe.top(),0,0,mutation);
    }
    private static void layout(Record r,long absoluteX,long absoluteY,long parentX,long parentY,Mutation mutation) {
        mutation.requireMutation();Mutation previous=r.scoped;r.scoped=mutation;
        try {
        Binding b=r.binding;Box frame=r.geometry.box;
        if(r.group!=null){r.group.absoluteX=absoluteX;r.group.absoluteY=absoluteY;}
        int left=px(absoluteX,b)-px(parentX,b),top=px(absoluteY,b)-px(parentY,b);
        int width=px(sum(absoluteX,frame.width),b)-px(absoluteX,b),height=px(sum(absoluteY,frame.height),b)-px(absoluteY,b);
        r.view.measure(View.MeasureSpec.makeMeasureSpec(width,View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(height,View.MeasureSpec.EXACTLY));mutation.require();

        r.view.layout(left,top,left+width,top+height);mutation.require();

        if(r.view instanceof NativeScroll)r.group.layout(0,0,width,px(r.geometry.contentHeight,b));mutation.require();
        } finally { r.scoped=previous; }
    }
    static final class Group extends ViewGroup {
        final Record record;Map<String,Record> records=Map.of();long absoluteX,absoluteY;
        Group(Context context,Record record){super(context);this.record=record;Mutation mutation=record.mutation();mutation.require();setWillNotDraw(false);mutation.require();setClipChildren(false);mutation.require();setClipToPadding(false);mutation.require();}
        @Override protected void onMeasure(int width,int height){NativeEnvironmentV2.requireMain();if(record==null)return;Mutation mutation=record.mutation();mutation.require();setMeasuredDimension(View.MeasureSpec.getSize(width),record.geometry==null?0:
            record.kind.equals("list")?px(record.geometry.contentHeight,record.binding):View.MeasureSpec.getSize(height));mutation.require();}
        @Override protected void onLayout(boolean changed,int l,int t,int right,int bottom) {NativeEnvironmentV2.requireMain();
            if(record==null||record.geometry==null)return;Mutation mutation=record.mutation();onLayout(changed,l,t,right,bottom,mutation);
        }
        void onLayout(boolean changed,int l,int t,int right,int bottom,Mutation mutation) {
            mutation.requireMutation();Geometry g=record.geometry;Binding b=record.binding;
            titleLayout(record.header,g.header,b,mutation);titleLayout(record.compact,g.compact,b,mutation);
            for(String id:b.node.childIDs()) {Record child=records.get(id);Box box=g.children.get(id);if(child==null||box==null)continue;
                child.geometry.box=box;NativeAppearanceViewsV2.layout(child,sum(absoluteX,box.x),sum(absoluteY,box.y),absoluteX,absoluteY,mutation);mutation.require();
}
        }
        private void titleLayout(TextView view,Box box,Binding b,Mutation mutation){if(record==null||view==null||box==null)return;mutation.requireMutation();
            int l=px(sum(absoluteX,box.x),b)-px(absoluteX,b),t=px(sum(absoluteY,box.y),b)-px(absoluteY,b);
            int w=px(sum(absoluteX,box.x,box.width),b)-px(sum(absoluteX,box.x),b),h=px(sum(absoluteY,box.y,box.height),b)-px(sum(absoluteY,box.y),b);
            view.measure(View.MeasureSpec.makeMeasureSpec(w,View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(h,View.MeasureSpec.EXACTLY));mutation.require();
view.layout(l,t,l+w,t+h);mutation.require();
}
        @Override protected void onDraw(Canvas canvas) {NativeEnvironmentV2.requireMain();
            if(record==null||record.binding==null||!record.input.draw())return;Mutation mutation=record.mutation();mutation.require();Binding b=record.binding;
            if(record.kind.equals("navigation")||record.kind.equals("list"))canvas.drawColor(color(b.palette().canvas()));
            Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);paint.setColor(color(b.palette().surface()));mutation.require();

            for(GroupDrawing group:record.geometry.groups){int save=canvas.save();translate(canvas,group.box,b);canvas.drawPath(group.path,paint);canvas.restoreToCount(save);}
        }
        private void translate(Canvas canvas,Box box,Binding b){canvas.translate(px(sum(absoluteX,box.x),b)-px(absoluteX,b),px(sum(absoluteY,box.y),b)-px(absoluteY,b));}
        @Override protected boolean drawChild(Canvas canvas,View child,long time) {NativeEnvironmentV2.requireMain();
            if(record==null||!record.input.draw())return false;Mutation mutation=record.mutation();mutation.require();
            Integer clip=record.geometry==null?null:record.geometry.clips.get(childRecordID(child));
            if(clip==null)return mutation.result(super.drawChild(canvas,child,time));
            GroupDrawing group=record.geometry.groups.get(clip);int save=canvas.save();Binding b=record.binding;
            int dx=px(sum(absoluteX,group.box.x),b)-px(absoluteX,b),dy=px(sum(absoluteY,group.box.y),b)-px(absoluteY,b);
            canvas.translate(dx,dy);canvas.clipPath(group.path);canvas.translate(-dx,-dy);
            boolean result=super.drawChild(canvas,child,time);mutation.require();canvas.restoreToCount(save);mutation.require();return result;
        }
        private String childRecordID(View view){for(var entry:records.entrySet())if(entry.getValue().view==view)return entry.getKey();return null;}
        @Override protected void dispatchDraw(Canvas canvas) {NativeEnvironmentV2.requireMain();
            if(record==null||!record.input.draw())return;Mutation mutation=record.mutation();mutation.require();
            super.dispatchDraw(canvas);mutation.require();if(record.binding==null)return;Binding b=record.binding;GroupedList m=b.theme.groupedList();
            Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);paint.setColor(color(b.palette().separator()));mutation.require();

            for(GroupDrawing group:record.geometry.groups) {
                int save=canvas.save();translate(canvas,group.box,b);canvas.clipPath(group.path);
                float leading=(float)AppearanceGeometryV2.pixelCoordinate(m.separatorInset64(),b.density());
                float end=(float)AppearanceGeometryV2.pixelCoordinate(group.box.width-m.separatorInset64(),b.density());
                float half=(float)AppearanceGeometryV2.pixelCoordinate(m.separatorThickness64(),b.density())/2;
                for(long boundary:group.separators){float y=(float)AppearanceGeometryV2.pixelCoordinate(boundary-group.box.y,b.density());canvas.drawRect(leading,y-half,end,y+half,paint);}
                canvas.restoreToCount(save);
            }
        }
    }
    static final class NativeScroll extends ScrollView {
        final Record record;
        NativeScroll(Context context,Record record){super(context);this.record=record;Mutation mutation=record.mutation();mutation.require();setFillViewport(false);mutation.require();setClipToPadding(false);mutation.require();setOverScrollMode(OVER_SCROLL_NEVER);mutation.require();setVerticalScrollBarEnabled(false);mutation.require();}
        @Override protected void onScrollChanged(int l,int t,int oldl,int oldt){NativeEnvironmentV2.requireMain();if(record==null)return;Mutation mutation=record.mutation();mutation.require();super.onScrollChanged(l,t,oldl,oldt);mutation.require();
            if(record.binding==null||t==oldt||!record.input.open(record))return;record.input.interaction();
            for(var parent=getParent();parent instanceof View view;parent=view.getParent())if(view instanceof Group group&&group.record.binding.node.recipe() instanceof NavigationRecipe nav){
                Record owner=group.record;Geometry g=owner.geometry;Binding b=owner.binding;
                boolean collapsed=g.overflow==0||logical(t,b)>=g.overflow;
                boolean previously=g.collapsed;g.collapsed=collapsed;
                if(collapsed==previously)return;
                owner.header.setVisibility(!collapsed&&nav.expandedTitle()!=null?View.VISIBLE:View.INVISIBLE);mutation.require();

                owner.compact.setVisibility(collapsed&&nav.compactTitle()!=null?View.VISIBLE:View.INVISIBLE);mutation.require();

                String childID=b.node.childIDs().get(0);Box child=g.children.get(childID);
                long bar=collapsed?g.compactBar:g.expandedBar;
                g.children.put(childID,new Box(child.x,bar,child.width,g.box.height-bar));
                group.onLayout(true,group.getLeft(),group.getTop(),group.getRight(),group.getBottom(),mutation);mutation.require();
                group.invalidate();mutation.require();
return;
            }
        }
    }
    static final class Gate extends FrameLayout {
        boolean open;int canvasColor;final NativeRenderer owner;
        Gate(Context context,NativeRenderer owner){super(context);this.owner=owner;Mutation mutation=owner.mutationV2();mutation.require();setClipChildren(false);mutation.require();setClipToPadding(false);mutation.require();setWillNotDraw(false);mutation.require();}
        private boolean current(){NativeEnvironmentV2.requireMain();return owner!=null&&owner.drawAllowedV2()&&open&&owner.presentationCurrentV2();}
        @Override protected void onDraw(Canvas canvas){NativeEnvironmentV2.requireMain();if(current())canvas.drawColor(canvasColor);}
        @Override protected void dispatchDraw(Canvas canvas){NativeEnvironmentV2.requireMain();if(!current())return;Mutation mutation=owner.mutationV2();mutation.require();super.dispatchDraw(canvas);mutation.require();}
        @Override public boolean dispatchTouchEvent(MotionEvent event){NativeEnvironmentV2.requireMain();if(!current())return true;Mutation mutation=owner.mutationV2();mutation.require();return mutation.result(super.dispatchTouchEvent(event));}
        @Override public boolean dispatchKeyEvent(android.view.KeyEvent event){NativeEnvironmentV2.requireMain();if(!current())return true;Mutation mutation=owner.mutationV2();mutation.require();return mutation.result(super.dispatchKeyEvent(event));}
        @Override protected void onLayout(boolean changed,int l,int t,int r,int b){NativeEnvironmentV2.requireMain();/* prepared frames only */}
    }
    private static final class NativeButton extends Button {
        NativeButton(Context context,Record record){super(context);Mutation mutation=record.mutation();mutation.require();setAllCaps(false);mutation.require();setGravity(Gravity.CENTER);mutation.require();}
    }
    /** One captured native continuation. It cannot authorize another record or a new input call. */
    static final class EditorLease {
        final NativeField field;
        final Record record;
        final NativeField.Attempt attempt;
        final Editable editable;
        final Mutation original;
        final EditorLease parent;
        final String hook;
        android.view.inputmethod.InputConnection target;
        boolean entered,ended;
        EditorSnapshot before;
        EditorLease(NativeField field,NativeField.Attempt attempt,Editable editable,Mutation original,EditorLease parent,String hook) {
            this.field=field;record=field.record;this.attempt=attempt;this.editable=editable;
            this.original=original;this.parent=parent;this.hook=hook;target=attempt==null?null:attempt.target;
        }
        private boolean onStack(){int bound=0;for(EditorLease cursor=record.editorCallbackLease;cursor!=null&&bound++<16;cursor=cursor.parent)if(cursor==this)return true;return false;}
        void exact() {
            if(!onStack()||!entered||ended||record.view!=field||field.attempt!=attempt||editable==null)
                throw new IllegalStateException("lost exact editor continuation");
            Editable actual=field.nativeEditable();
            if(!entered||ended||record.view!=field||field.attempt!=attempt||!record.input.editorRetained(record)||actual!=editable||
                attempt!=null&&attempt.target!=target||!onStack())
                throw new IllegalStateException("lost exact editor continuation after getter");
        }
        Mutation continuation() {
            exact();
            if(original.current())return Mutation.editorContinuation(original,this);
            // Only this captured exact continuation may request sealed authority.
            return record.input.editorCleanupMutation(record,this);
        }
        void check() {
            exact();
            if(original.current()){original.require();return;}
            if(!original.fence.drawAllowed&&!original.fence.inputAllowed){record.input.editorCleanupMutation(record,this).require();return;}
            // A captured exact suffix can observe accepted synchronous Binding continuity.
            // This postcheck supplies no new Mutation or native entry authority.
            if(original.mode==Mutation.Mode.LIVE_PRESENTATION&&original.result(true))return;
            original.require();
        }
    }
    static final class EditorSnapshot {
        final String text;final int start,end;final Object[] spans;final int[] bounds;
        EditorSnapshot(NativeField field,Editable editable){
            text=editable.toString();start=field.getSelectionStart();end=field.getSelectionEnd();
            java.util.ArrayList<Object> composing=new java.util.ArrayList<>();
            for(Object span:editable.getSpans(0,editable.length(),Object.class))if((editable.getSpanFlags(span)&android.text.Spanned.SPAN_COMPOSING)!=0)composing.add(span);
            spans=composing.toArray();bounds=new int[spans.length*3];
            for(int i=0;i<spans.length;i++){bounds[i*3]=editable.getSpanStart(spans[i]);bounds[i*3+1]=editable.getSpanEnd(spans[i]);bounds[i*3+2]=editable.getSpanFlags(spans[i]);}
        }
        private boolean sameSpans(Object[] next){if(spans.length!=next.length)return false;for(int i=0;i<spans.length;i++)if(spans[i]!=next[i])return false;return true;}
        boolean same(NativeField field,Editable editable){
            EditorSnapshot next=new EditorSnapshot(field,editable);
            return text.equals(next.text)&&start==next.start&&end==next.end&&sameSpans(next.spans)&&java.util.Arrays.equals(bounds,next.bounds);
        }
    }
    /** Exact compatible transaction callbacks for a settled field; never an old target lease. */
    static final class FieldPreservation {
        final NativeField field;final Record record;final Mutation original;final Editable editable;
        final Binding before,selected;final NativeField.Attempt predecessor;final NativeField.Close disposition;
        final long lossObservation;
        final NativeRenderer renderer;final NativeRenderer.Candidate candidate;final NativeRenderer.AttachmentJournal journal;
        EditorSnapshot snapshot;
        static final int CAPTURED=0,ATTACHING=1,ATTACHED=2,PRECOMMIT_READY=3,RESTORING=4,RESTORED_HELD=5,FAILED_HELD=6,COMMITTED=7,RELEASED=8;
        boolean entered,ended,checking,counted,released,releaseReady;int callbacks,phase=CAPTURED;
        final java.util.ArrayDeque<String> hooks=new java.util.ArrayDeque<>();
        FieldPreservation(NativeField field,Mutation original,Binding selected,Editable editable,NativeRenderer renderer,NativeRenderer.Candidate candidate,NativeRenderer.AttachmentJournal journal){
            this.field=field;record=field.record;this.original=original;this.selected=selected;this.editable=editable;
            this.renderer=renderer;this.candidate=candidate;this.journal=journal;
            before=record.binding;predecessor=field.attempt;disposition=predecessor==null?null:predecessor.close;
            lossObservation=record.input.editorLossObservation();
        }
        boolean tuple(){return entered&&counted&&!ended&&record.fieldPreservation==this&&record.view==field&&renderer.fieldPreservationCurrent(candidate,journal,record,this)&&
            original.mode==Mutation.Mode.TRANSACTION&&original.editorLease==null&&original.replacementLease==null&&original.fieldLease==null&&
            original.current()&&record.input.editorRetained(record)&&field.settledField()&&field.depth==0&&record.editorCallbackLease==null&&
            field.attempt==predecessor&&(predecessor==null||predecessor.close==disposition)&&
            (record.binding==before||record.binding==selected)&&record.input.editorLossObservation()==lossObservation;}
        void capture(){if(!tuple())throw new IllegalStateException("invalid preserved field entry");snapshot=new EditorSnapshot(field,editable);exact();}
        void exact(){
            if(checking||snapshot==null||!tuple())throw new IllegalStateException("lost exact field preservation");
            checking=true;
            try{Editable actual=field.nativeEditable();boolean same=actual==editable&&snapshot.same(field,editable);
                if(!same||!tuple())throw new IllegalStateException("preserved field changed after getter");}
            finally{checking=false;}
        }
        Mutation continuation(){exact();return Mutation.fieldContinuation(original,this);}
        private void enter(String hook){exact();if(callbacks>=16||hooks.contains(hook))throw new IllegalStateException("field callback recursion exhausted");hooks.push(hook);callbacks++;}
        private void leave(){callbacks--;hooks.pop();}
        void callback(String hook,Runnable nativeCall){enter(hook);try{nativeCall.run();exact();}finally{leave();}}
        void lifecycle(String hook,boolean loss,Runnable denial,Runnable gain,Runnable nativeCall){
            enter(hook);
            try{if(loss)field.actualLoss(denial);else gain.run();nativeCall.run();exact();}finally{leave();}
        }
        boolean endReady(){return entered&&ended&&record.fieldPreservation==null&&callbacks==0&&hooks.isEmpty()&&!checking;}
    }
    /** One field-only accessibility replacement, with no native InputConnection permission. */
    static final class Replacement {
        enum Stage { SNAPSHOTTING, CLOSING, NATIVE, DONE }
        final NativeField field;final Record record;final Mutation original;final Editable oldEditable;
        final NativeField.Attempt predecessor;
        final long lossObservation;
        Stage stage=Stage.SNAPSHOTTING;
        Editable nextEditable;
        CharSequence proposal;String eventValue;
        boolean registered,nativeExecuting,setterActive,started,setterReturned,watcherSeen,lost,completed,eventClaimed,eventEvaluating;
        int setterCalls,callbacks;final java.util.ArrayDeque<String> hooks=new java.util.ArrayDeque<>();
        Replacement(NativeField field,Mutation original,Editable oldEditable,long lossObservation){this.field=field;record=field.record;this.original=original;this.oldEditable=oldEditable;predecessor=field.attempt;this.lossObservation=lossObservation;}
        boolean unchangedLoss(){return !lost&&record.input.editorLossObservation()==lossObservation;}
        void successAuthority(){if(!unchangedLoss()||!original.current()||field.fieldDenied())throw new IllegalStateException("replacement loss or original authority changed");}
        boolean tuple(){return registered&&field.replacement==this&&record.view==field&&record.input.editorRetained(record);}
        boolean endReady(){return stage==Stage.DONE&&!registered&&!nativeExecuting&&!setterActive&&callbacks==0&&hooks.isEmpty()&&field.replacement==null&&record.replacementCallback==null&&record.editorCallbackLease==null&&field.depth==0;}
        boolean permitsPredecessor(Record selected,NativeField.Attempt attempt){
            return tuple()&&stage==Stage.CLOSING&&selected==record&&predecessor!=null&&attempt==predecessor&&
                field.attempt==predecessor&&attempt.editable==oldEditable&&attempt.target!=null&&record.editorCallbackLease==null;
        }
        void exact(){
            if(!tuple()||stage!=Stage.NATIVE||!nativeExecuting)throw new IllegalStateException("lost replacement continuation");
            Editable actual=field.nativeEditable();
            // Callable getter effects precede the final tuple check.
            if(!tuple()||stage!=Stage.NATIVE||!nativeExecuting||actual==null)throw new IllegalStateException("lost replacement tuple after getter");
            if(nextEditable==null){
                if(actual!=oldEditable){
                    if(!setterActive||setterCalls!=1)throw new IllegalStateException("replacement identity outside selected setter");
                    if(actual.getClass()!=android.text.SpannableStringBuilder.class)throw new IllegalStateException("unsupported replacement factory output");
                    nextEditable=actual;
                }
            }else if(actual!=nextEditable)throw new IllegalStateException("second or reverted replacement Editable");
        }
        Mutation continuation(){
            exact();
            if(original.current())return Mutation.replacement(original,this,false);
            if(started&&!original.fence.drawAllowed&&!original.fence.inputAllowed)return Mutation.replacement(original,this,true);
            original.require();throw new IllegalStateException("replacement authority unavailable");
        }
        void check(){continuation().require();}
        void callback(String hook,Runnable nativeCall){
            if(!nativeExecuting||stage!=Stage.NATIVE)throw new IllegalStateException("replacement callback outside native frame");
            if(callbacks>=16||hooks.contains(hook))throw new IllegalStateException("replacement callback recursion exhausted");
            exact();hooks.push(hook);callbacks++;
            try{nativeCall.run();check();}finally{callbacks--;hooks.pop();}
        }
        void watch(Editable value){exact();if(value!=field.nativeEditable())throw new IllegalStateException("foreign replacement watcher");exact();watcherSeen=true;}
        CharSequence filter(CharSequence src,int start,int end,android.text.Spanned dst,int dstart,int dend){
            exact();
            if(!setterActive||setterCalls!=1||src!=proposal||start!=0||end!=proposal.length()||dstart!=0||
                !((dend==0&&dst.length()==0)||(dend==oldEditable.length()&&dst==oldEditable)))
                throw new IllegalStateException("foreign replacement filter proposal");
            // This is the already validated immutable proposal, not permission from a revoked adapter.
            return null;
        }
        void setter(CharSequence value,TextView.BufferType type,Runnable nativeCall){
            if(stage!=Stage.NATIVE||!nativeExecuting||setterActive||setterCalls!=0||value!=proposal||type!=TextView.BufferType.EDITABLE)
                throw new IllegalStateException("unexpected replacement setter");
            check();setterCalls=1;setterActive=true;
            try{nativeCall.run();exact();setterReturned=true;}
            finally{setterActive=false;}
        }
        void premises(){
            if(field.getAccessibilityDelegate()!=null||field.getAutoLinkMask()!=0||
                field.getMovementMethod()!=android.text.method.ArrowKeyMovementMethod.getInstance()||
                field.getTransformationMethod()!=null&&field.getTransformationMethod()!=android.text.method.SingleLineTransformationMethod.getInstance()||
                oldEditable.getClass()!=android.text.SpannableStringBuilder.class)
                throw new IllegalStateException("unsupported native replacement configuration");
            InputFilter[] filters=field.getFilters();
            if(filters.length!=1||filters[0]!=record.editorFilter)throw new IllegalStateException("unsupported replacement filter configuration");
        }
    }
    static final class NativeField extends EditText {
        enum Phase { IDLE, CREATING, ACTIVE, DRAINING, CLOSING, QUARANTINED }
        enum Close { NOT_REQUESTED, DEFERRED, ATTEMPTED, RETURNED, FAILED_UNCERTAIN, NO_TARGET }
        static final class Attempt {
            final Editable editable;
            final EditorInfo output;
            android.view.inputmethod.InputConnection target;
            NativeEditorConnectionV2.Base adapter;
            boolean revoked;
            Close close=Close.NOT_REQUESTED;
            Attempt(Editable editable,EditorInfo output){this.editable=editable;this.output=output;}
        }
        final Record record;
        private Phase phase=Phase.IDLE;
        private Attempt attempt;
        private Replacement replacement;
        private int depth;
        private boolean permanent,focusLost,windowFocusLost,windowHidden,aggregateHidden,viewHidden,detached;
        private Throwable primary;
        private java.lang.Error firstFatal;
        private boolean reporting,finishing;
        private static final int MAX_DEPTH=16;
        NativeField(Context context,Record record){super(context);this.record=record;}
        Editable nativeEditable(){return super.getEditableText();}
        private boolean construction(){return record!=null&&(!record.constructed||record.binding==null||record.changing)&&record.scoped!=null;}
        private void observe(Throwable failure) {
            if(failure==null)return;
            if(primary==null)primary=failure;
            if(failure instanceof java.lang.Error fatal&&firstFatal==null)firstFatal=fatal;
        }
        private void revoke(boolean terminal) {
            if(terminal)permanent=true;
            if(attempt!=null) {
                attempt.revoked=true;
                if(attempt.close==Close.NOT_REQUESTED)attempt.close=Close.DEFERRED;
            }
            if(phase!=Phase.CLOSING&&phase!=Phase.QUARANTINED)phase=Phase.DRAINING;
        }
        private void uncertain(Throwable failure) {
            observe(failure);revoke(true);phase=Phase.QUARANTINED;
            if(record==null||reporting)return;
            reporting=true;
            try{record.input.editorFailure(primary,firstFatal);}
            catch(RuntimeException|java.lang.Error report){observe(report);}
            finally{reporting=false;}
        }
        private void surface() {
            if(firstFatal!=null)throw firstFatal;
            if(primary instanceof RuntimeException ordinary)throw ordinary;
        }
        void preservationFailure(Throwable failure){uncertain(failure);}
        void preservationSurface(){surface();}
        private boolean denied(){return permanent||focusLost||windowFocusLost||windowHidden||aggregateHidden||viewHidden||detached;}
        private boolean fieldDenied(){return permanent||windowFocusLost||windowHidden||aggregateHidden||viewHidden||detached;}
        private boolean consumedPredecessor(){return attempt==null||attempt.revoked&&(attempt.close==Close.RETURNED||attempt.close==Close.NO_TARGET);}
        private boolean settledField(){return record!=null&&record.view==this&&record.constructed&&record.binding!=null&&!finishing&&!fieldDenied()&&
            replacement==null&&phase==Phase.IDLE&&consumedPredecessor();}
        boolean needsFieldPreservation(){return focusLost&&settledField();}
        boolean completedReplacementEligible(Replacement operation){return operation!=null&&operation.field==this&&operation.record==record&&
            operation.completed&&operation.stage==Replacement.Stage.DONE&&operation.endReady()&&operation.eventValue!=null&&!operation.eventClaimed&&
            replacement==null&&record.fieldPreservation==null&&depth==0&&settledField()&&!record.changing&&
            record.input.editorRetained(record)&&operation.unchangedLoss()&&operation.original.current();}
        boolean eventsAllowed() {
            NativeEnvironmentV2.requireMain();
            return record!=null&&replacement==null&&!finishing&&!denied()&&phase!=Phase.CREATING&&phase!=Phase.DRAINING&&phase!=Phase.CLOSING&&phase!=Phase.QUARANTINED&&
                (attempt==null||!attempt.revoked);
        }
        private boolean live() {
            return record!=null&&record.view==this&&record.constructed&&record.binding!=null&&!record.changing&&replacement==null&&!finishing&&!denied()&&
                phase!=Phase.CREATING&&phase!=Phase.DRAINING&&phase!=Phase.CLOSING&&phase!=Phase.QUARANTINED&&
                record.input.editorDispatchAvailable(record)&&record.input.editorRetained(record)&&record.input.open(record)&&hasFocus();
        }
        private boolean replacementLive(){
            return record!=null&&record.view==this&&record.constructed&&record.binding!=null&&!record.changing&&replacement==null&&!finishing&&!fieldDenied()&&
                phase!=Phase.CREATING&&phase!=Phase.DRAINING&&phase!=Phase.CLOSING&&phase!=Phase.QUARANTINED&&
                (!focusLost||consumedPredecessor())&&record.fieldPreservation==null&&
                record.input.editorDispatchAvailable(record)&&record.input.editorRetained(record)&&record.input.open(record);
        }
        boolean hasLiveTarget(){return attempt!=null&&attempt.target!=null&&!attempt.revoked&&attempt.close==Close.NOT_REQUESTED;}
        void available(boolean preserve) {
            NativeEnvironmentV2.requireMain();
            if(construction())return;
            if(replacement!=null||finishing||(preserve?fieldDenied()||focusLost&&!settledField():denied())||phase==Phase.CREATING||phase==Phase.DRAINING||phase==Phase.CLOSING||phase==Phase.QUARANTINED)
                throw new IllegalStateException("editor replacement unavailable");
            if(preserve&&focusLost&&!record.input.editorRetained(record))throw new IllegalStateException("foreign preserved field");
            if(depth!=0&&!preserve)throw new IllegalStateException("editor native frame active");
            if(!preserve&&attempt!=null&&attempt.close!=Close.RETURNED&&attempt.close!=Close.NO_TARGET) {
                revoke(false);drain();
                if(phase!=Phase.IDLE)throw new IllegalStateException("editor predecessor not closed");
            }
        }
        void retirePermanent() {NativeEnvironmentV2.requireMain();revoke(true);if(depth==0)drain();surface();}
        private EditorLease begin(Attempt expected,Mutation mutation,String hook,boolean nested) {
            if(depth>=MAX_DEPTH) {uncertain(new IllegalStateException("editor continuation depth exhausted"));return null;}
            EditorLease parent=record.editorCallbackLease;
            if(depth!=0&&!nested)return null;
            if(parent!=null) {
                if(parent.attempt!=expected||parent.field!=this)return null;
                for(EditorLease cursor=parent;cursor!=null;cursor=cursor.parent)if(cursor.hook.equals(hook)) {
                    uncertain(new IllegalStateException("recursive editor hook"));return null;
                }
                parent.check();mutation=parent.original;
            }
            Editable editable=expected==null?nativeEditable():expected.editable;
            if(editable==null){uncertain(new IllegalStateException("editor Editable unavailable"));return null;}
            EditorLease lease=new EditorLease(this,expected,editable,mutation,parent,hook);
            record.input.editorEnter(record,lease);lease.entered=true;depth++;record.editorCallbackLease=lease;
            try{lease.check();return lease;}catch(RuntimeException|java.lang.Error failure){uncertain(failure);end(lease);return null;}
        }
        private void end(EditorLease lease) {
            if(lease==null)return;
            if(lease.ended||record.editorCallbackLease!=lease||depth<=0) {
                uncertain(new IllegalStateException("unbalanced editor continuation"));return;
            }
            record.editorCallbackLease=lease.parent;lease.ended=true;depth--;
            // Balance once. This scalar exit never resumes the owner or coordinator.
            try{record.input.editorLeave(record,lease);}catch(RuntimeException|java.lang.Error failure){uncertain(failure);}
            if(depth==0)drain();
        }
        private void drain() {
            Attempt old=attempt;
            if(old==null){if(phase==Phase.DRAINING)phase=permanent?Phase.QUARANTINED:Phase.IDLE;return;}
            if(!old.revoked||depth!=0||phase==Phase.CLOSING||old.close==Close.ATTEMPTED||old.close==Close.RETURNED||old.close==Close.FAILED_UNCERTAIN||old.close==Close.NO_TARGET)return;
            if(old.target==null) {
                // A still-running creator owns the unknown target. A thrown creator marks uncertainty itself.
                return;
            }
            if(!record.input.editorCloseAllowed(record,old)) {
                old.close=Close.DEFERRED;uncertain(new IllegalStateException("editor close deferred by transaction"));return;
            }
            EditorLease lease=new EditorLease(this,old,old.editable,(!record.editorFence.drawAllowed&&!record.editorFence.inputAllowed)?Mutation.cleanup(record.editorFence):entryMutation(),null,"close");
            boolean drain=false,entered=false;
            try {
                record.input.editorDrainBegin(record,lease);drain=true;
                // Exact checks are inside executing-drain busy, before consuming the sole close.
                record.input.editorEnter(record,lease);entered=true;lease.entered=true;depth++;record.editorCallbackLease=lease;
                lease.exact();
                phase=Phase.CLOSING;old.close=Close.ATTEMPTED;
                lease.target.closeConnection();lease.check();old.close=Close.RETURNED;
                phase=permanent?Phase.QUARANTINED:Phase.IDLE;
            } catch(RuntimeException|java.lang.Error failure) {
                observe(failure);old.close=Close.FAILED_UNCERTAIN;uncertain(failure);
            } finally {
                if(entered){record.editorCallbackLease=null;depth--;lease.ended=true;
                    try{record.input.editorLeave(record,lease);}catch(RuntimeException|java.lang.Error failure){uncertain(failure);}}
                // Restore and report before final busy clear. Never synchronously resume after this line.
                if(primary!=null)uncertain(primary);
                if(drain)record.input.editorDrainEnd(record,lease);
            }
        }
        private Mutation entryMutation(){return record.scoped!=null?record.scoped:record.input.mutation();}
        @SuppressWarnings("unchecked")
        <T> T dispatch(Attempt expected,String hook,T refused,java.util.function.Supplier<T> action) {
            NativeEnvironmentV2.requireMain();
            if(expected==null||attempt!=expected||expected.revoked||phase!=Phase.ACTIVE||depth!=0||!live())return refused;
            Mutation mutation=entryMutation();mutation.require();EditorLease lease=begin(expected,mutation,hook,false);if(lease==null){surface();return refused;}
            T result=refused;
            try{
                lease.before=new EditorSnapshot(this,expected.editable);lease.check();
                result=action.get();lease.check();
                if(!expected.revoked&&(!validBuffer(expected.editable.toString())||getSelectionStart()<0||getSelectionEnd()<0||
                    getSelectionStart()>expected.editable.length()||getSelectionEnd()>expected.editable.length()))
                    throw new IllegalStateException("invalid native editor result");
                if(!expected.revoked&&result instanceof Boolean completed)result=(T)Boolean.valueOf(lease.original.result(completed.booleanValue()));
                else if(!expected.revoked){
                    // Queries require strict original authority and an unchanged editor snapshot.
                    if(!lease.original.current()||!lease.before.same(this,expected.editable))result=refused;
                }
            }
            catch(RuntimeException|java.lang.Error failure){uncertain(failure);}
            finally{end(lease);}
            surface();return expected.revoked?refused:result;
        }
        <T> T nativeValue(Attempt expected,T refused,java.util.function.Supplier<T> nativeCall) {
            EditorLease lease=record.editorCallbackLease;
            if(lease==null||lease.attempt!=expected||expected.revoked)return refused;
            lease.check();
            if(lease.before==null||!lease.before.same(this,expected.editable)||!lease.original.current()||!live())return refused;
            lease.exact();return nativeCall.get();
        }
        void close(Attempt expected) {
            NativeEnvironmentV2.requireMain();
            if(expected!=attempt||expected==null||expected.close==Close.RETURNED||expected.close==Close.NO_TARGET)return;
            revoke(false);if(depth==0)drain();surface();
        }
        boolean proposal(CharSequence value,boolean composing) {
            if(!eventsAllowed()||!plainProposal(value,composing))return false;
            Editable buffer=nativeEditable();int start=getSelectionStart(),end=getSelectionEnd();
            int cs=android.view.inputmethod.BaseInputConnection.getComposingSpanStart(buffer),ce=android.view.inputmethod.BaseInputConnection.getComposingSpanEnd(buffer);
            if(cs>=0&&ce>=0){start=cs;end=ce;}if(start<0||end<0||start>buffer.length()||end>buffer.length())return false;
            int left=Math.min(start,end),right=Math.max(start,end);
            return validBuffer(buffer.subSequence(0,left).toString()+value+buffer.subSequence(right,buffer.length()));
        }
        @Override public android.view.inputmethod.InputConnection onCreateInputConnection(EditorInfo info) {
            NativeEnvironmentV2.requireMain();
            if(info==null||info.getClass()!=EditorInfo.class||replacement!=null||finishing||depth!=0||phase==Phase.CREATING||phase==Phase.CLOSING||phase==Phase.DRAINING||phase==Phase.QUARANTINED||!live())return null;
            if(attempt!=null&&attempt.close!=Close.RETURNED&&attempt.close!=Close.NO_TARGET){revoke(false);drain();surface();if(phase!=Phase.IDLE)return null;}
            Mutation mutation=entryMutation();mutation.require();Editable editable=nativeEditable();
            if(editable==null)return null;
            Attempt fresh=new Attempt(editable,info);attempt=fresh;phase=Phase.CREATING;
            EditorLease lease=begin(fresh,mutation,"create",false);if(lease==null){fresh.revoked=true;fresh.close=Close.NO_TARGET;phase=Phase.QUARANTINED;surface();return null;}
            android.view.inputmethod.InputConnection result=null;boolean populated=false;
            try {
                populated=true;fresh.target=super.onCreateInputConnection(info);lease.target=fresh.target;
                if(fresh.target==null){fresh.close=Close.NO_TARGET;fresh.revoked=true;}
                else {
                    lease.check();mutation.require();
                    if(fresh.revoked||denied()||!record.input.open(record)||!hasFocus()||!validBuffer(editable.toString())||
                        info.initialSelStart!=getSelectionStart()||info.initialSelEnd!=getSelectionEnd()||
                        info.initialSelStart<0||info.initialSelEnd<0||info.initialSelStart>editable.length()||info.initialSelEnd>editable.length()||
                        info.inputType!=(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_CAP_SENTENCES)||
                        (info.imeOptions&EditorInfo.IME_MASK_ACTION)!=EditorInfo.IME_ACTION_DONE)
                        revoke(false);
                    else {
                        EditorSnapshot outputSnapshot=new EditorSnapshot(this,editable);
                        info.imeOptions=(info.imeOptions&~(EditorInfo.IME_FLAG_NAVIGATE_NEXT|EditorInfo.IME_FLAG_NAVIGATE_PREVIOUS))|
                            EditorInfo.IME_FLAG_NO_EXTRACT_UI|EditorInfo.IME_FLAG_NO_FULLSCREEN;
                        info.setSupportedHandwritingGestures(java.util.Collections.emptyList());lease.check();mutation.require();
                        if(!outputSnapshot.same(this,editable))revoke(false);
                        info.setSupportedHandwritingGesturePreviews(java.util.Collections.emptySet());lease.check();mutation.require();
                        if(fresh.revoked||denied()||!record.input.open(record)||!hasFocus()||!outputSnapshot.same(this,editable)||
                            info.initialSelStart!=getSelectionStart()||info.initialSelEnd!=getSelectionEnd()||
                            info.inputType!=(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_CAP_SENTENCES)||
                            (info.imeOptions&EditorInfo.IME_MASK_ACTION)!=EditorInfo.IME_ACTION_DONE||
                            (info.imeOptions&(EditorInfo.IME_FLAG_NAVIGATE_NEXT|EditorInfo.IME_FLAG_NAVIGATE_PREVIOUS))!=0||
                            (info.imeOptions&(EditorInfo.IME_FLAG_NO_EXTRACT_UI|EditorInfo.IME_FLAG_NO_FULLSCREEN))!=(EditorInfo.IME_FLAG_NO_EXTRACT_UI|EditorInfo.IME_FLAG_NO_FULLSCREEN)||
                            !info.getSupportedHandwritingGestures().isEmpty()||!info.getSupportedHandwritingGesturePreviews().isEmpty())revoke(false);
                        else {lease.check();mutation.require();fresh.adapter=NativeEditorConnectionV2.create(this,fresh);result=fresh.adapter;}
                    }
                }
            } catch(RuntimeException|java.lang.Error failure) {
                observe(failure);
                if(fresh.target==null)fresh.close=Close.FAILED_UNCERTAIN;
                uncertain(failure);
            } finally {
                boolean held=false;
                try{record.input.editorFinishBegin(record,lease);held=true;finishing=true;}
                catch(RuntimeException|java.lang.Error failure){uncertain(failure);}
                if(result==null&&populated) {
                    fresh.revoked=true;
                    try{scrub(info);}catch(RuntimeException|java.lang.Error failure){uncertain(failure);}
                }
                try{end(lease);}catch(RuntimeException|java.lang.Error failure){uncertain(failure);}
                // Final lease/drain/reporting may revoke an otherwise assigned adapter.
                if(populated&&(result==null||fresh.revoked||primary!=null)) {
                    fresh.revoked=true;
                    try{scrub(info);}catch(RuntimeException|java.lang.Error failure){uncertain(failure);}
                }
                if(result!=null&&!fresh.revoked&&primary==null)phase=Phase.ACTIVE;
                else if(phase==Phase.CREATING)phase=denied()?Phase.QUARANTINED:Phase.IDLE;
                finishing=false;
                if(held)record.input.editorFinishEnd(record,lease);
                // No native effect, callback or owner/coordinator resumption after final busy clear.
            }
            surface();return fresh.revoked?null:result;
        }
        private void resetOutput(EditorInfo info){
            info.inputType=0;info.imeOptions=0;info.actionId=0;info.actionLabel=null;info.label=null;info.hintText=null;
            info.privateImeOptions=null;info.extras=null;info.contentMimeTypes=null;info.hintLocales=null;
            info.initialSelStart=-1;info.initialSelEnd=-1;info.initialCapsMode=0;
        }
        private void scrub(EditorInfo info) {
            resetOutput(info);
            try{
                info.setSupportedHandwritingGestures(java.util.Collections.emptyList());
                info.setSupportedHandwritingGesturePreviews(java.util.Collections.emptySet());
                info.initialSelStart=-1;info.initialSelEnd=-1;
                info.setInitialSurroundingText("");
            }finally{resetOutput(info);}
            // Exact EditorInfo class is admitted before any effects. These are official public getters;
            // a detected failure remains uncertainty, never fabricated private-payload cleanup success.
            if(!info.getSupportedHandwritingGestures().isEmpty()||!info.getSupportedHandwritingGesturePreviews().isEmpty()||
                info.getInitialSurroundingText(0,0,0)!=null||info.inputType!=0||info.imeOptions!=0||info.hintText!=null||
                info.initialSelStart!=-1||info.initialSelEnd!=-1)throw new IllegalStateException("EditorInfo scrub uncertain");
        }
        private void callback(String hook,Runnable nativeCall,boolean interaction) {
            NativeEnvironmentV2.requireMain();
            if(record==null){nativeCall.run();return;}
            if(replacement!=null&&replacement.nativeExecuting){try{replacement.callback(hook,nativeCall);}catch(RuntimeException|java.lang.Error failure){uncertain(failure);surface();}return;}
            if(record.fieldPreservation!=null){try{record.fieldPreservation.callback(hook,nativeCall);}catch(RuntimeException|java.lang.Error failure){uncertain(failure);surface();}return;}
            if(construction()){Mutation mutation=record.scoped;mutation.requireMutation();nativeCall.run();mutation.require();return;}
            if(replacement!=null&&!replacement.nativeExecuting&&record.editorCallbackLease==null){uncertain(new IllegalStateException("unknown replacement pre-native callback"));surface();return;}
            EditorLease parent=record.editorCallbackLease;
            if(parent==null&&(denied()||attempt!=null&&attempt.revoked||phase==Phase.QUARANTINED||phase==Phase.DRAINING||phase==Phase.CLOSING)) {
                uncertain(new IllegalStateException("unknown retired editor callback"));surface();return;
            }
            if(parent==null&&!live())return;
            EditorLease lease=begin(attempt,parent==null?entryMutation():parent.original,hook,true);if(lease==null){surface();return;}
            try{nativeCall.run();lease.check();if(interaction&&eventsAllowed()&&!record.changing&&record.input.open(record))record.input.interaction();}
            catch(RuntimeException|java.lang.Error failure){uncertain(failure);}
            finally{end(lease);}
            surface();
        }
        void refreshPaint(){if(record!=null&&record.binding!=null){Mutation mutation=record.mutation();mutation.require();setHighlightColor(color(fieldPaint(record).selection()));mutation.require();}}
        @Override protected void drawableStateChanged(){callback("drawable",()->{super.drawableStateChanged();if(record!=null&&(record.fieldPreservation!=null||eventsAllowed())&&(record.editorCallbackLease==null||record.editorCallbackLease.original.current()))refreshPaint();},false);}
        @Override protected void onSelectionChanged(int start,int end){callback("selection",()->super.onSelectionChanged(start,end),true);}
        private void actualLoss(Runnable denial){
            try{record.input.editorLossObserved(record);}catch(RuntimeException|java.lang.Error failure){uncertain(failure);}
            // Observation exhaustion cannot discard the exact already-entered native suffix.
            denial.run();revoke(false);
        }
        private void lifecycle(String hook,boolean loss,Runnable denial,Runnable gain,Runnable nativeCall) {
            NativeEnvironmentV2.requireMain();
            if(record==null){nativeCall.run();return;}
            if(replacement!=null&&replacement.nativeExecuting){
                try{if(loss){replacement.lost=true;actualLoss(denial);}else gain.run();replacement.callback(hook,nativeCall);}
                catch(RuntimeException|java.lang.Error failure){uncertain(failure);surface();}return;
            }
            if(record.fieldPreservation!=null){try{record.fieldPreservation.lifecycle(hook,loss,denial,gain,nativeCall);}catch(RuntimeException|java.lang.Error failure){uncertain(failure);surface();}return;}
            if(!record.constructed&&construction()){Mutation mutation=record.scoped;mutation.requireMutation();if(loss)try{record.input.editorLossObserved(record);}catch(RuntimeException|java.lang.Error failure){uncertain(failure);}nativeCall.run();mutation.require();surface();return;}
            EditorLease parent=record.editorCallbackLease;
            // A public lifecycle entry owns its native super, even with no admitted target.
            Mutation mutation=parent==null?((!record.editorFence.drawAllowed&&!record.editorFence.inputAllowed)?Mutation.cleanup(record.editorFence):entryMutation()):parent.original;
            EditorLease lease=begin(attempt,mutation,hook,true);if(lease==null){surface();return;}
            try {
                if(loss)actualLoss(denial);else gain.run();
                nativeCall.run();lease.check();
            }catch(RuntimeException|java.lang.Error failure){uncertain(failure);}
            finally{end(lease);}
            surface();
        }
        @Override protected void onFocusChanged(boolean focused,int direction,android.graphics.Rect old) {
            lifecycle("focus",!focused,()->focusLost=true,()->focusLost=false,()->super.onFocusChanged(focused,direction,old));
        }
        @Override public void onWindowFocusChanged(boolean focused) {
            lifecycle("windowFocus",!focused,()->windowFocusLost=true,()->windowFocusLost=false,()->super.onWindowFocusChanged(focused));
        }
        @Override protected void onWindowVisibilityChanged(int visibility) {
            lifecycle("windowVisibility",visibility!=View.VISIBLE,()->windowHidden=true,()->windowHidden=false,()->super.onWindowVisibilityChanged(visibility));
        }
        @Override public void onVisibilityAggregated(boolean visible) {
            lifecycle("aggregate",!visible,()->aggregateHidden=true,()->aggregateHidden=false,()->super.onVisibilityAggregated(visible));
        }
        @Override protected void onVisibilityChanged(View changed,int visibility) {
            lifecycle("visibility",visibility!=View.VISIBLE,()->viewHidden=true,()->viewHidden=false,()->super.onVisibilityChanged(changed,visibility));
        }
        @Override protected void onDetachedFromWindow() {
            lifecycle("detach",true,()->detached=true,()->{},()->super.onDetachedFromWindow());
        }
        @Override protected void onAttachedToWindow() {
            lifecycle("attach",false,()->{},()->detached=false,()->super.onAttachedToWindow());
        }
        @Override public void setText(CharSequence value,TextView.BufferType type) {
            NativeEnvironmentV2.requireMain();
            if(record==null){super.setText(value,type);return;}
            if(replacement!=null){replacement.setter(value,type,()->super.setText(value,type));return;}
            if(construction()){Mutation mutation=record.scoped;mutation.requireMutation();super.setText(value,type);mutation.require();return;}
            if(attempt!=null&&attempt.close!=Close.RETURNED&&attempt.close!=Close.NO_TARGET) {
                revoke(false);
                if(depth!=0)throw new IllegalStateException("Editable replacement inside native editor call refused");
                drain();surface();if(phase!=Phase.IDLE)throw new IllegalStateException("Editable predecessor unresolved");
            }
            available(false);Mutation mutation=entryMutation();mutation.requireMutation();
            super.setText(value,type);mutation.require();
        }
        private boolean widget(String hook,java.util.function.Supplier<Boolean> validation,java.util.function.Supplier<Boolean> nativeCall) {
            NativeEnvironmentV2.requireMain();
            if(record==null||!live())return false;
            EditorLease parent=record.editorCallbackLease;
            if(parent!=null&&!parent.hook.equals("context"))return false;
            EditorLease lease=begin(attempt,parent==null?entryMutation():parent.original,hook,parent!=null);if(lease==null){surface();return false;}
            boolean result=false;
            try{
                lease.before=new EditorSnapshot(this,lease.editable);lease.check();
                if(validation.get()&&lease.before.same(this,lease.editable)&&lease.original.current()&&live()){
                    lease.exact();result=nativeCall.get();lease.check();
                    result=lease.original.result(result);
                }
            }
            catch(RuntimeException|java.lang.Error failure){uncertain(failure);}
            finally{end(lease);}
            surface();return eventsAllowed()&&result;
        }
        private boolean replaceAccessibility(android.os.Bundle arguments){
            NativeEnvironmentV2.requireMain();
            if(record==null||replacement!=null||record.fieldPreservation!=null||depth!=0||finishing)return false;
            long observation=record.input.editorLossObservation();
            Mutation original=entryMutation();original.require();
            if(!replacementLive()||record.input.editorLossObservation()!=observation||!original.current())return false;
            Editable old=nativeEditable();
            if(old==null||record.input.editorLossObservation()!=observation||!original.current()||!replacementLive()||
                record.input.editorLossObservation()!=observation||!original.current())return false;
            Replacement operation=new Replacement(this,original,old,observation);replacement=operation;
            boolean event=false,result=false;String completed=null;
            try{
                try{record.input.replacementBegin(record,operation);}catch(IllegalArgumentException|IllegalStateException refused){return false;}
                operation.registered=true;
                EditorSnapshot snapshot=new EditorSnapshot(this,old);
                CharSequence source=arguments==null?null:arguments.getCharSequence(android.view.accessibility.AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE);
                if(!plainProposal(source,false))return false;
                operation.proposal=source instanceof android.text.Spanned?new android.text.SpannedString(source):source.toString();
                if(!plainProposal(operation.proposal,false)||!validBuffer(operation.proposal.toString())||!snapshot.same(this,old)||
                    nativeEditable()!=old||!operation.tuple()||!operation.unchangedLoss()||!original.current()||fieldDenied()||!record.input.open(record)||
                    !operation.tuple()||!operation.unchangedLoss()||!original.current()||fieldDenied())return false;
                operation.premises();
                if(!operation.tuple()||!operation.unchangedLoss()||!original.current()||fieldDenied()||nativeEditable()!=old||
                    !operation.tuple()||!operation.unchangedLoss()||!original.current())return false;
                android.os.Bundle owned=new android.os.Bundle();owned.putCharSequence(android.view.accessibility.AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,operation.proposal);
                operation.stage=Replacement.Stage.CLOSING;
                if(operation.predecessor!=null&&operation.predecessor.close!=Close.RETURNED&&operation.predecessor.close!=Close.NO_TARGET){
                    revoke(false);drain();surface();
                    if(operation.predecessor.close!=Close.RETURNED)return false;
                }
                if(!operation.tuple()||depth!=0||record.editorCallbackLease!=null||nativeEditable()!=old||!operation.tuple()||
                    !original.current()||fieldDenied()||!operation.unchangedLoss()||!record.input.open(record)||
                    !operation.tuple()||!operation.unchangedLoss()||!original.current()||fieldDenied())throw new IllegalStateException("replacement close authority lost");
                // Consumed predecessor is retained by the operation only as history, never dispatch authority.
                attempt=null;phase=Phase.IDLE;
                EditorSnapshot postClose=new EditorSnapshot(this,old);
                operation.successAuthority();
                operation.stage=Replacement.Stage.NATIVE;operation.nativeExecuting=true;operation.started=true;record.replacementCallback=operation;
                try{result=super.performAccessibilityAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,owned);operation.check();}
                finally{operation.nativeExecuting=false;record.replacementCallback=null;}
                operation.successAuthority();
                if(!record.input.open(record))throw new IllegalStateException("replacement final field unavailable");
                operation.successAuthority();
                Editable actual=nativeEditable();
                operation.successAuthority();
                if(!operation.tuple()||actual==null)throw new IllegalStateException("replacement final tuple or authority lost");
                if(!result&&operation.setterCalls==0&&actual==old&&postClose.same(this,old))return false;
                if(!result||operation.setterCalls!=1||!operation.setterReturned||!operation.watcherSeen||operation.nextEditable==null||actual!=operation.nextEditable||
                    !validBuffer(actual.toString())||!actual.toString().equals(operation.proposal.toString())||
                    getSelectionStart()!=actual.length()||getSelectionEnd()!=actual.length())throw new IllegalStateException("incomplete native replacement result");
                // Empty selection0 is supplied by native default ArrowKeyMovementMethod.initialize;
                // nonempty end selection is supplied by TextView's accessibility suffix.
                completed=actual.toString();original.require();
                if(nativeEditable()!=actual||!operation.tuple())throw new IllegalStateException("replacement changed at final check");
                operation.successAuthority();
                operation.eventValue=completed;operation.completed=true;event=true;
            }catch(RuntimeException|java.lang.Error failure){
                if(operation.started||operation.stage==Replacement.Stage.CLOSING)uncertain(failure);
                else throw failure;
            }finally{
                operation.nativeExecuting=false;record.replacementCallback=null;
                operation.stage=Replacement.Stage.DONE;
                boolean held=operation.registered;operation.registered=false;replacement=null;
                if(held)try{record.input.replacementEnd(record,operation);}
                catch(RuntimeException|java.lang.Error failure){uncertain(failure);surface();}
                // Busy/continuation clear last; never synchronously resume owner disposal.
            }
            surface();
            if(!event)return false;
            try{record.input.replacementEvent(record,operation);}catch(RuntimeException|java.lang.Error failure){uncertain(failure);surface();return false;}
            // The native suffix is finished. This observes scalars only, never successor native authority.
            return original.result(true);
        }
        @Override public boolean performAccessibilityAction(int action,android.os.Bundle arguments) {
            NativeEnvironmentV2.requireMain();
            if(action==android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT)return replaceAccessibility(arguments);
            return widget("accessibility",()->{
                if(action!=android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT)return true;
                CharSequence text=arguments==null?null:arguments.getCharSequence(android.view.accessibility.AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE);
                return plainProposal(text,false)&&validBuffer(text.toString());
            },()->super.performAccessibilityAction(action,arguments));
        }
        @Override public boolean onKeyDown(int code,android.view.KeyEvent event) {
            NativeEnvironmentV2.requireMain();if(event==null)return true;
            return widget("key",()->{
                int value=event.getUnicodeChar();
                return value==0||Character.isValidCodePoint(value)&&proposal(new String(Character.toChars(value)),false);
            },()->super.onKeyDown(code,event));
        }
        @Override public boolean onTextContextMenuItem(int id) {
            NativeEnvironmentV2.requireMain();
            return widget("menu",()->{
                if(id==android.R.id.paste||id==android.R.id.pasteAsPlainText) {
                    android.content.ClipboardManager clipboard=getContext().getSystemService(android.content.ClipboardManager.class);
                    android.content.ClipData clip=clipboard==null?null:clipboard.getPrimaryClip();if(clip==null)return false;
                    StringBuilder proposed=new StringBuilder();for(int i=0;i<clip.getItemCount();i++){if(i>0)proposed.append('\n');CharSequence item=clip.getItemAt(i).coerceToText(getContext());if(!plainProposal(item,false))return false;proposed.append(item);}
                    if(!proposal(proposed,false))return false;
                }
                return true;
            },()->super.onTextContextMenuItem(id));
        }
    }
    private static final class NativeSwitch extends Switch implements AuthoredToggleInputV2.CheckedBinding {
        final Record record;Path track,thumb;
        private final AuthoredToggleInputV2 touch = new AuthoredToggleInputV2();
        private android.view.ViewParent downParent, disallowedParent;
        private boolean cancelling;
        private int downLeft,downTop;
        NativeSwitch(Context context,Record record){super(context);this.record=record;}
        private boolean open(){NativeEnvironmentV2.requireMain();return record!=null&&record.view==this&&!record.changing&&record.binding!=null&&
            record.binding.node.recipe() instanceof ToggleRecipe&&record.binding.nativeToggleValue()!=null&&
            isChecked()==record.binding.nativeToggleValue()&&record.input.open(record);}
        private AuthoredToggleInputV2.Geometry authoredGeometry(){
            if(record==null||record.binding==null||!(record.binding.node.recipe() instanceof ToggleRecipe recipe))return null;
            Binding b=record.binding;ToggleMetrics m=recipe.metrics();
            return AuthoredToggleInputV2.geometry(getWidth(),getHeight(),b.density(),b.rtl(),m.trackWidth64(),m.trackHeight64(),m.thumbWidth64(),m.thumbHeight64());
        }
        private boolean fence(){
            if(touch==null||!touch.active()||!open())return false;
            var geometry=touch.geometry();return touch.matches(record.binding,isChecked())&&getParent()==downParent&&
                getLeft()==downLeft&&getTop()==downTop&&geometry.width()==getWidth()&&geometry.height()==getHeight();
        }
        // Clear ownership before invoking a parent: a callback may synchronously rebind or retire this view.
        void cancelTouch(){clearTouch(false);}
        private void clearTouch(boolean terminal){
            if(touch==null||record==null||cancelling)return;
            boolean nativeOwned=touch.active()||downParent!=null||disallowedParent!=null||isPressed();
            if(terminal)touch.end();else touch.cancel();downParent=null;
            var parent=disallowedParent;disallowedParent=null;
            if(!nativeOwned)return;
            cancelling=true;
            Throwable ordinary=null;java.lang.Error fatal=null;
            try{
                try{setPressed(false);}catch(RuntimeException failure){record.cancellationFailure(failure);ordinary=failure;}catch(java.lang.Error failure){record.cancellationFailure(failure);fatal=failure;}
                try{invalidate();}catch(RuntimeException failure){record.cancellationFailure(failure);if(ordinary==null)ordinary=failure;}catch(java.lang.Error failure){record.cancellationFailure(failure);if(fatal==null)fatal=failure;}
                try{if(parent!=null)parent.requestDisallowInterceptTouchEvent(false);}
                catch(RuntimeException failure){record.cancellationFailure(failure);if(ordinary==null)ordinary=failure;}catch(java.lang.Error failure){record.cancellationFailure(failure);if(fatal==null)fatal=failure;}
            }finally{cancelling=false;}
            if(fatal!=null){if(ordinary!=null)try{fatal.addSuppressed(ordinary);}catch(Throwable unavailable){}throw fatal;}
            if(ordinary instanceof RuntimeException failure)throw failure;
        }
        private void endTouch(){clearTouch(true);}
        private void syncPaint(){Mutation mutation=record.mutation();mutation.require();setPressed(touch.pressed());mutation.require();refreshPaint();mutation.require();invalidate();mutation.require();}
        private boolean sample(int id,int count,double x,double y,long time){
            if(!fence()){cancelTouch();return false;}
            record.input.interaction(); // Local epoch only, never a feature envelope or JNI call.
            if(!fence()){cancelTouch();return false;}
            var before=touch.phase();boolean valid=touch.sample(id,count,x,y,time);
            if(!valid){cancelTouch();return false;}
            syncPaint();
            if(before!=AuthoredToggleInputV2.Phase.drag&&touch.phase()==AuthoredToggleInputV2.Phase.drag){
                var parent=getParent();disallowedParent=parent;
                Mutation mutation=record.mutation();mutation.require();
                if(parent!=null)parent.requestDisallowInterceptTouchEvent(true);mutation.require();
                if(!fence()){cancelTouch();return false;}
            }
            return true;
        }
        private boolean samples(MotionEvent event){
            if(event.getPointerCount()!=1||event.getActionIndex()!=0||event.getPointerId(0)<0||
                event.getToolType(0)!=MotionEvent.TOOL_TYPE_FINGER||event.getDownTime()!=touch.downTime()){
                cancelTouch();return false;
            }
            int id=event.getPointerId(0);
            for(int h=0;h<event.getHistorySize();h++)
                if(!sample(id,1,event.getHistoricalX(0,h),event.getHistoricalY(0,h),event.getHistoricalEventTime(h)))return false;
            return sample(id,1,event.getX(0),event.getY(0),event.getEventTime());
        }
        @Override public boolean onTouchEvent(MotionEvent event){NativeEnvironmentV2.requireMain();
            if(touch==null||record==null||event==null)return false;
            int action=event.getActionMasked(),index=event.getActionIndex();
            boolean owned=touch.ownsRemainder();
            if(event.getAction()!=(action|(index<<MotionEvent.ACTION_POINTER_INDEX_SHIFT))){cancelTouch();return owned;}
            if(action==MotionEvent.ACTION_DOWN){
                endTouch();if(!open()||event.getPointerCount()!=1||index!=0||event.getHistorySize()!=0||event.getToolType(0)!=MotionEvent.TOOL_TYPE_FINGER)return false;
                var binding=record.binding;
                record.input.interaction();if(!open()||record.binding!=binding)return false;var geometry=authoredGeometry();
                if(!touch.begin(binding,geometry,event.getPointerId(0),1,event.getX(0),event.getY(0),isChecked(),
                    android.view.ViewConfiguration.get(getContext()).getScaledTouchSlop(),event.getDownTime(),event.getEventTime()))return false;
                downParent=getParent();downLeft=getLeft();downTop=getTop();syncPaint();return true;
            }
            if(action==MotionEvent.ACTION_CANCEL||action==MotionEvent.ACTION_OUTSIDE){endTouch();return owned;}
            if(!touch.active()){
                if(action==MotionEvent.ACTION_UP)endTouch();return owned;
            }
            if(action!=MotionEvent.ACTION_MOVE&&action!=MotionEvent.ACTION_UP){cancelTouch();return owned;}
            if(!samples(event)){
                boolean consume=touch.ownsRemainder();if(action==MotionEvent.ACTION_UP)endTouch();return consume;
            }
            if(action==MotionEvent.ACTION_MOVE)return true;
            var binding=touch.binding();int desired=touch.result(event.getX(0),event.getY(0));
            endTouch();
            if(desired!=AuthoredToggleInputV2.NO_CHANGE&&record.binding==binding&&open()&&isChecked()!=(desired==1))performClick();
            return true;
        }
        @Override public boolean performClick(){NativeEnvironmentV2.requireMain();
            if(record==null||!open())return false;Mutation mutation=record.mutation();mutation.require();cancelTouch();mutation.require();
            try{return mutation.result(super.performClick());}finally{
                if(mutation.current()&&open()){mutation.require();AuthoredToggleInputV2.reconcile(this);mutation.require();refreshPaint();mutation.require();invalidate();mutation.require();}
            }
        }
        @Override public boolean dispatchKeyEvent(android.view.KeyEvent event){NativeEnvironmentV2.requireMain();
            if(record==null)return false;Mutation mutation=record.mutation();mutation.require();
            if(touch!=null&&touch.active())cancelTouch();mutation.require();
            if(!open()){cancelTouch();return false;}return mutation.result(super.dispatchKeyEvent(event));
        }
        @Override public boolean performAccessibilityAction(int action,android.os.Bundle arguments){NativeEnvironmentV2.requireMain();
            if(record==null||!open())return false;Mutation mutation=record.mutation();mutation.require();
            cancelTouch();mutation.require();return open()&&mutation.result(super.performAccessibilityAction(action,arguments));
        }
        @Override public Boolean latestBoundChecked(){NativeEnvironmentV2.requireMain();return record==null||record.binding==null?null:record.binding.nativeToggleValue();}
        @Override public boolean nativeChecked(){NativeEnvironmentV2.requireMain();return isChecked();}
        @Override public boolean changingGuard(){NativeEnvironmentV2.requireMain();return record!=null&&record.changing;}
        @Override public void changingGuard(boolean value){NativeEnvironmentV2.requireMain();if(record!=null)record.changing=value;}
        @Override public void restoreChecked(boolean value){NativeEnvironmentV2.requireMain();if(record==null)return;Mutation mutation=record.mutation();mutation.require();setChecked(value);mutation.require();}
        boolean visualChecked(){return touch!=null&&record!=null&&touch.matches(record.binding,isChecked())?touch.visualChecked():isChecked();}
        void refreshPaint(){if(record==null||record.binding==null||cancelling)return;Mutation mutation=record.mutation();mutation.require();setTextColor(color(togglePaint(record).label()));mutation.require();}
        @Override protected void drawableStateChanged(){NativeEnvironmentV2.requireMain();if(record==null||cancelling)return;Mutation mutation=record.mutation();mutation.require();super.drawableStateChanged();mutation.require();refreshPaint();}
        @Override public void setEnabled(boolean enabled){NativeEnvironmentV2.requireMain();if(record==null||touch==null||cancelling)return;Mutation mutation=record.mutation();mutation.require();cancelTouch();mutation.require();super.setEnabled(enabled);mutation.require();}
        @Override protected boolean setFrame(int left,int top,int right,int bottom){NativeEnvironmentV2.requireMain();
            if(record==null||touch==null||cancelling)return false;Mutation mutation=record.mutation();mutation.require();
            if(left!=getLeft()||top!=getTop()||right!=getRight()||bottom!=getBottom())cancelTouch();mutation.require();
            return mutation.result(super.setFrame(left,top,right,bottom));
        }
        @Override protected void onDetachedFromWindow(){NativeEnvironmentV2.requireMain();if(record==null||cancelling)return;cancelTouch();if(!record.input.draw())return;Mutation mutation=record.mutation();mutation.require();super.onDetachedFromWindow();mutation.require();}
        @Override protected void onAttachedToWindow(){NativeEnvironmentV2.requireMain();if(record==null||cancelling)return;Mutation mutation=record.mutation();mutation.require();cancelTouch();mutation.require();super.onAttachedToWindow();mutation.require();}
        @Override protected void onVisibilityChanged(View changed,int visibility){NativeEnvironmentV2.requireMain();if(record==null||cancelling)return;cancelTouch();if(!record.input.draw())return;Mutation mutation=record.mutation();mutation.require();super.onVisibilityChanged(changed,visibility);mutation.require();}
        @Override protected void onWindowVisibilityChanged(int visibility){NativeEnvironmentV2.requireMain();if(record==null||cancelling)return;cancelTouch();if(!record.input.draw())return;Mutation mutation=record.mutation();mutation.require();super.onWindowVisibilityChanged(visibility);mutation.require();}
        @Override public void onWindowFocusChanged(boolean focused){NativeEnvironmentV2.requireMain();if(record==null||cancelling)return;cancelTouch();if(!record.input.draw())return;Mutation mutation=record.mutation();mutation.require();super.onWindowFocusChanged(focused);mutation.require();}
        @Override protected void onFocusChanged(boolean focused,int direction,android.graphics.Rect old){NativeEnvironmentV2.requireMain();if(record==null||cancelling)return;Mutation mutation=record.mutation();mutation.require();if(!focused)cancelTouch();mutation.require();super.onFocusChanged(focused,direction,old);mutation.require();}
        @Override public void onRtlPropertiesChanged(int direction){NativeEnvironmentV2.requireMain();if(record==null||cancelling)return;Mutation mutation=record.mutation();mutation.require();cancelTouch();mutation.require();super.onRtlPropertiesChanged(direction);mutation.require();}
        @Override protected void onDraw(Canvas canvas) {NativeEnvironmentV2.requireMain();
            if(record==null||record.binding==null||track==null||!record.input.draw())return;Mutation mutation=record.mutation();mutation.require();Binding b=record.binding;ToggleRecipe recipe=(ToggleRecipe)b.node.recipe();ToggleMetrics m=recipe.metrics();TogglePaint colors=togglePaint(record);
            var geometry=authoredGeometry();if(geometry==null)return;
            Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);Layout text=getLayout();
            if(text!=null){int save=canvas.save();int x=b.rtl()?px(sum(m.trackWidth64(),m.labelGap64()),b):0;
                canvas.translate(x,(getHeight()-text.getHeight())/2f);text.draw(canvas);canvas.restoreToCount(save);}
            float x=geometry.trackX(),y=geometry.trackY();
            int save=canvas.save();canvas.translate(x,y);paint.setColor(color(colors.track()));mutation.require();
canvas.drawPath(track,paint);
            int clip=canvas.save();canvas.clipPath(track);paint.setColor(color(colors.overlay()));mutation.require();
canvas.drawPath(track,paint);canvas.restoreToCount(clip);
            double fraction=touch!=null&&touch.matches(b,isChecked())?touch.fraction():(isChecked()?1:0);
            canvas.translate((float)geometry.origin(fraction),(float)geometry.thumbY());
            paint.setColor(color(colors.thumb()));mutation.require();
canvas.drawPath(thumb,paint);canvas.restoreToCount(save);
            if(isEnabled()&&isFocused()){ToggleStates states=visualChecked()?b.palette().toggle().on():b.palette().toggle().off();outline(canvas,new RectF(x,y,x+geometry.trackWidth(),y+geometry.trackHeight()),states.focus(),b,paint,mutation);}
        }
    }
    private abstract static class OwnedDrawable extends Drawable {
        final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        @Override public void setAlpha(int alpha){NativeEnvironmentV2.requireMain();if(alpha!=255)throw new IllegalArgumentException("authored alpha only");}
        @Override public void setColorFilter(ColorFilter filter){NativeEnvironmentV2.requireMain();if(filter!=null)throw new IllegalArgumentException("authored colors only");}
        @Override public int getOpacity(){NativeEnvironmentV2.requireMain();return PixelFormat.TRANSLUCENT;}
    }
    private static final class ControlDrawable extends OwnedDrawable {
        final Record record;final boolean field;
        ControlDrawable(Record record,boolean field){this.record=record;this.field=field;}
        @Override public boolean isStateful(){NativeEnvironmentV2.requireMain();return true;}
        @Override protected boolean onStateChange(int[] state){NativeEnvironmentV2.requireMain();invalidateSelf();return true;}
        @Override public void draw(Canvas canvas){NativeEnvironmentV2.requireMain();Binding b=record.binding;if(b==null||!record.input.draw())return;Mutation mutation=record.mutation();mutation.require();
            if(field){FieldPaint colors=fieldPaint(record);RectF box=new RectF(getBounds());paint.setColor(color(colors.background()));mutation.require();
canvas.drawRect(box,paint);outline(canvas,box,colors.outline(),b,paint,mutation);}
            else {ButtonRecipe r=(ButtonRecipe)b.node.recipe();ButtonStates states=buttonStates(b,r.role());
                ButtonPaint colors=!record.view.isEnabled()?states.disabled():record.view.isPressed()?states.pressed():states.enabled();
                TextView text=(TextView)record.view;Layout layout=text.getLayout();float textWidth=0;
                if(layout!=null)for(int i=0;i<layout.getLineCount();i++)textWidth=Math.max(textWidth,layout.getLineWidth(i));
                float w=textWidth+px(sum(r.metrics().labelInsets64().leading(),r.metrics().labelInsets64().trailing()),b);
                float h=(layout==null?0:layout.getHeight())+px(sum(r.metrics().labelInsets64().top(),r.metrics().labelInsets64().bottom()),b);
                RectF box=new RectF((text.getWidth()-w)/2,(text.getHeight()-h)/2,(text.getWidth()+w)/2,(text.getHeight()+h)/2);
                paint.setColor(color(colors.background()));mutation.require();
float radius=px(r.metrics().overlayRadius64(),b);canvas.drawRoundRect(box,radius,radius,paint);
                if(record.view.isEnabled()&&record.view.isFocused())outline(canvas,box,states.focus(),b,paint,mutation);
            }}
    }
    private static void outline(Canvas canvas,RectF box,Outline outline,Binding b,Paint paint,Mutation mutation){mutation.require();if(outline==null||outline.width64()==0)return;
        float width=(float)AppearanceGeometryV2.pixelCoordinate(outline.width64(),b.density());RectF inner=new RectF(box);inner.inset(width/2,width/2);
        paint.setStyle(Paint.Style.STROKE);mutation.require();
paint.setStrokeWidth(width);mutation.require();
paint.setColor(color(outline.color()));mutation.require();
float radius=(float)AppearanceGeometryV2.pixelCoordinate(outline.radius64(),b.density());
        canvas.drawRoundRect(inner,radius,radius,paint);paint.setStyle(Paint.Style.FILL);mutation.require();
}
    private static final class Cursor extends OwnedDrawable {
        final Record record;Cursor(Record record){this.record=record;}
        @Override public int getIntrinsicWidth(){NativeEnvironmentV2.requireMain();return 2;}
        @Override public void draw(Canvas canvas){NativeEnvironmentV2.requireMain();if(!record.input.draw())return;Mutation mutation=record.mutation();mutation.require();paint.setColor(color(fieldPaint(record).caret()));mutation.require();
canvas.drawRect(getBounds(),paint);}
    }
    private static final class Handle extends OwnedDrawable {
        final Record record;Handle(Record record){this.record=record;}
        @Override public int getIntrinsicWidth(){NativeEnvironmentV2.requireMain();return 12;}@Override public int getIntrinsicHeight(){NativeEnvironmentV2.requireMain();return 12;}
        @Override public void draw(Canvas canvas){NativeEnvironmentV2.requireMain();if(!record.input.draw())return;Mutation mutation=record.mutation();mutation.require();paint.setColor(color(fieldPaint(record).selection()));mutation.require();
canvas.drawOval(new RectF(getBounds()),paint);}
    }
    private static final class Empty extends OwnedDrawable {
        final int width,height;Empty(int width,int height){this.width=width;this.height=height;}
        @Override public int getIntrinsicWidth(){NativeEnvironmentV2.requireMain();return width;}@Override public int getIntrinsicHeight(){NativeEnvironmentV2.requireMain();return height;}
        @Override public void draw(Canvas canvas){NativeEnvironmentV2.requireMain();}
    }
}
