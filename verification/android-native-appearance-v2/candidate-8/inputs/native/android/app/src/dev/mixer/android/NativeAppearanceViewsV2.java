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
        void event(Record record, String event, Object value);
        void interaction();
    }
    record Binding(AppearanceResolverV2.Plan plan, AppearanceResolverV2.Node node,
                   UiPacket.Node source, AppearanceDescriptorV2.Theme theme) {
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
        Binding binding;
        Geometry geometry;
        boolean changing;int preparedScrollY;
        Record(Context context, UiPacket.Node source, Input input) {
            id=source.id; generation=source.generation; kind=source.kind; this.input=input;
            Group container=null; TextView title=null, small=null;
            switch(kind) {
                case "text" -> view=new TextView(context);
                case "button" -> view=new NativeButton(context,this);
                case "textField" -> view=new NativeField(context,this);
                case "toggle" -> view=new NativeSwitch(context,this);
                case "list" -> { container=new Group(context,this); NativeScroll scroll=new NativeScroll(context,this);
                    scroll.addView(container,new ScrollView.LayoutParams(-1,-2)); view=scroll; }
                default -> { container=new Group(context,this); view=container;
                    if(kind.equals("section")||kind.equals("navigation")) { title=new TextView(context);
                        container.addView(title); if(kind.equals("navigation")){small=new TextView(context);container.addView(small);} }
                }
            }
            group=container; header=title; compact=small;
            view.setId(View.generateViewId()); view.setTag(id);
            view.setBackground(null); view.setElevation(0); view.setStateListAnimator(null);
            view.setDefaultFocusHighlightEnabled(false); view.setPadding(0,0,0,0);
            view.setMinimumWidth(0); view.setMinimumHeight(0);
            if(view instanceof TextView text) defaults(text);
            if(header!=null)defaults(header); if(compact!=null)defaults(compact);
            if(kind.equals("button")&&view instanceof Button button) button.setOnClickListener(ignored -> { if(input.open(this)) input.event(this,"activate",null); });
            if(view instanceof EditText edit) {
                edit.setSingleLine(true); edit.setHorizontallyScrolling(true);
                edit.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
                edit.setImeOptions(EditorInfo.IME_ACTION_DONE);
                edit.setFilters(new InputFilter[]{(src,start,end,dst,dstart,dend)-> {
                    if(changing)return null;
                    if(!input.open(this))return dst.subSequence(dstart,dend);
                    String proposed=dst.subSequence(0,dstart).toString()+src.subSequence(start,end)+dst.subSequence(dend,dst.length());
                    // systemSans intentionally admits native script/emoji fallback.
                    return validBuffer(proposed) ? null : dst.subSequence(dstart,dend);
                }});
                edit.addTextChangedListener(new TextWatcher(){
                    public void beforeTextChanged(CharSequence s,int start,int count,int after){}
                    public void onTextChanged(CharSequence s,int start,int before,int count){}
                    public void afterTextChanged(Editable value){if(!changing&&input.open(Record.this))input.event(Record.this,"textChange",value.toString());}
                });
                edit.setOnEditorActionListener((field,action,event)-> {
                    if(action==EditorInfo.IME_ACTION_DONE&&input.open(this)&&binding.source.actions.containsKey("submit")) {
                        input.event(this,"submit",null);return true;
                    }return false;
                });
            }
            if(view instanceof Switch toggle) toggle.setOnCheckedChangeListener((button,checked)-> {
                if(!changing&&input.open(this))input.event(this,"valueChange",checked);
                toggle.invalidate();
            });
        }
        void bind(Binding next, Geometry measured, boolean preserveEditor) {
            changing=true;
            try {
                binding=next; geometry=measured;
                if(!preserveEditor) {
                    view.setEnabled(!next.node.disabled());
                    view.setLayoutDirection(next.rtl()?View.LAYOUT_DIRECTION_RTL:View.LAYOUT_DIRECTION_LTR);
                    view.setTag(next.source.text("accessibilityIdentifier",id));
                    view.setContentDescription(next.source.text("accessibilityLabel",kind.equals("textField")?next.source.text("label",""):null));
                    view.setTooltipText(next.source.text("accessibilityHint",null));
                    if(android.os.Build.VERSION.SDK_INT>=30)view.setStateDescription(next.source.text("accessibilityValue",null));
                    if(next.node.recipe() instanceof TextRecipe r) {
                        TextView text=(TextView)view; text(text,r.text(),next);text.setTextIsSelectable(r.text().selectable());
                        text.setTextColor(color(((TextPaints)next.plan.style(id,false,false).paints()).foreground()));
                    } else if(next.node.recipe() instanceof ButtonRecipe r) {
                        NativeButton button=(NativeButton)view;text(button,r.text(),next);button.setAllCaps(false);
                        button.setBackground(new ControlDrawable(this,false));button.setTextColor(buttonColors(next,r));
                    } else if(next.node.recipe() instanceof FieldRecipe r) {
                        NativeField field=(NativeField)view;text(field,r.text(),next);field.setHint(r.label());
                        field.setGravity((next.rtl()?Gravity.RIGHT:Gravity.LEFT)|Gravity.CENTER_VERTICAL);
                        Insets in=r.metrics().insets64();field.setPadding(px(next.rtl()?in.trailing():in.leading(),next),px(in.top(),next),
                            px(next.rtl()?in.leading():in.trailing(),next),px(in.bottom(),next));
                        field.setBackground(new ControlDrawable(this,true));field.setTextColor(fieldColors(next,false));
                        field.setHintTextColor(fieldColors(next,true));
                        field.setTextCursorDrawable(new Cursor(this));
                        field.setTextSelectHandle(new Handle(this));field.setTextSelectHandleLeft(new Handle(this));field.setTextSelectHandleRight(new Handle(this));
                        field.refreshPaint();
                    } else if(next.node.recipe() instanceof ToggleRecipe r) {
                        NativeSwitch toggle=(NativeSwitch)view;text(toggle,r.text(),next);toggle.setChecked(r.checked());
                        toggle.setSwitchMinWidth(px(r.metrics().trackWidth64(),next));toggle.setSwitchPadding(px(r.metrics().labelGap64(),next));
                        toggle.setThumbDrawable(new Empty(px(r.metrics().thumbWidth64(),next),px(r.metrics().thumbHeight64(),next)));
                        toggle.setTrackDrawable(new Empty(px(r.metrics().trackWidth64(),next),px(r.metrics().trackHeight64(),next)));
                        toggle.setSplitTrack(false);toggle.setShowText(false);toggle.setThumbTextPadding(0);
                        toggle.track=AppearanceNativePathsV2.make(AppearanceGeometryV2.track(),next.density());
                        toggle.thumb=AppearanceNativePathsV2.make(AppearanceGeometryV2.thumb(),next.density());
                        toggle.refreshPaint();
                    }
                }
                if(next.node.recipe() instanceof SectionRecipe r&&header!=null) bindTitle(header,r.header(),next,
                    ((SectionPaints)next.plan.style(id,false,false).paints()).header());
                if(next.node.recipe() instanceof NavigationRecipe r&&header!=null) {
                    NavigationPaints colors=(NavigationPaints)next.plan.style(id,false,false).paints();
                    bindTitle(header,r.expandedTitle(),next,colors.expanded());bindTitle(compact,r.compactTitle(),next,colors.compact());compact.setGravity(Gravity.TOP|Gravity.CENTER_HORIZONTAL);
                    header.setVisibility(!measured.collapsed&&r.expandedTitle()!=null?View.VISIBLE:View.INVISIBLE);compact.setVisibility(measured.collapsed&&r.compactTitle()!=null?View.VISIBLE:View.INVISIBLE);
                }
                view.invalidate();
            } finally { changing=false; }
        }
    }
    private static boolean validBuffer(String value){
        for(int i=0;i<value.length();i++){char c=value.charAt(i);if(Character.isHighSurrogate(c)){if(++i>=value.length()||!Character.isLowSurrogate(value.charAt(i)))return false;}else if(Character.isLowSurrogate(c))return false;}
        return value.getBytes(java.nio.charset.StandardCharsets.UTF_8).length<=16384;
    }
    private static void defaults(TextView text) {
        text.setIncludeFontPadding(false);text.setFallbackLineSpacing(true);text.setPadding(0,0,0,0);
        text.setMinWidth(0);text.setMinHeight(0);text.setMinimumWidth(0);text.setMinimumHeight(0);
        text.setCompoundDrawablePadding(0);text.setCompoundDrawables(null,null,null,null);
        text.setLetterSpacing(0);text.setTextScaleX(1);text.setShadowLayer(0,0,0,0);
        text.setGravity(Gravity.TOP|Gravity.START);text.setBreakStrategy(Layout.BREAK_STRATEGY_HIGH_QUALITY);
        text.setHyphenationFrequency(Layout.HYPHENATION_FREQUENCY_NORMAL);
    }
    private static void text(TextView view, Text text, Binding binding) {
        if(!view.getText().toString().equals(text.value()))view.setText(text.value());
        view.setTextSize(TypedValue.COMPLEX_UNIT_PX,(float)AppearanceGeometryV2.pixelCoordinate(text.metrics().size64(),binding.density()));
        view.setTypeface(Typeface.create(Typeface.create("sans-serif",Typeface.NORMAL),text.metrics().weight().value,false));
        view.setTextLocales(new android.os.LocaleList(java.util.Locale.forLanguageTag(binding.plan.environment.localeIdentifier())));
        view.setMaxLines(text.maximumLines()==null?Integer.MAX_VALUE:text.maximumLines());
        view.setEllipsize(text.maximumLines()==null?null:TextUtils.TruncateAt.END);
    }
    private static void bindTitle(TextView view, Text text, Binding binding, Color ink) {
        view.setVisibility(text==null?View.GONE:View.VISIBLE);
        if(text!=null){text(view,text,binding);view.setTextColor(color(ink));}
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
    static TogglePaint togglePaint(Record r) {ToggleStates s=((Switch)r.view).isChecked()?r.binding.palette().toggle().on():r.binding.palette().toggle().off();
        return !r.view.isEnabled()?s.disabled():r.view.isPressed()?s.pressed():s.enabled();}
    static int color(Color c) {return android.graphics.Color.argb(c.alpha(),c.red(),c.green(),c.blue());}
    static int px(long value,Binding b){return AppearanceGeometryV2.pixelEdge(value,b.density());}
    static long logical(int pixels,Binding b){return AppearanceGeometryV2.measuredExtent64(pixels*1024.0/b.density());}
    static long sum(long... values){long result=0;for(long value:values){extent(value);result+=value;extent(result);}return result;}
    static void extent(long value){if(value<0||value>AppearanceGeometryV2.MAXIMUM_EXTENT64)throw new Failure(Error.layout);}
    static void fail(){throw new Failure(Error.layout);}

    /** Actual native measurement, followed by checked logical aggregation. Never mutates a live record. */
    static void measure(Record r,Map<String,Record> records,long availableWidth,long availableHeight) {
        extent(availableWidth);extent(availableHeight);if(availableWidth<=0)fail();
        Binding b=r.binding;r.geometry=new Geometry();Geometry g=r.geometry;
        if(r.view instanceof TextView text) {
            long reserve=0;
            if(b.node.recipe() instanceof ToggleRecipe t)reserve=sum(t.metrics().trackWidth64(),t.metrics().labelGap64());
            if(b.node.recipe() instanceof ButtonRecipe t)reserve=sum(t.metrics().labelInsets64().leading(),t.metrics().labelInsets64().trailing());
            if(b.node.recipe() instanceof FieldRecipe t)reserve=sum(t.metrics().insets64().leading(),t.metrics().insets64().trailing());
            if(availableWidth<=reserve)fail();
            // Switch's native layout reserves its actual authored drawable width and gap.
            int maximum=px(availableWidth,b);if(maximum<=0)fail();
            text.measure(View.MeasureSpec.makeMeasureSpec(maximum,View.MeasureSpec.AT_MOST),View.MeasureSpec.makeMeasureSpec(0,View.MeasureSpec.UNSPECIFIED));
            if(text.getLayout()==null)fail();
            long nativeHeight=logical(text.getLayout().getHeight(),b);
            long width=logical(text.getMeasuredWidth(),b),height=nativeHeight;
            g.firstBaseline=logical(text.getLayout().getLineBaseline(0),b);
            g.lastBaseline=logical(text.getLayout().getLineBaseline(text.getLayout().getLineCount()-1),b);
            if(b.node.recipe() instanceof ToggleRecipe t) {g.semanticHeight=nativeHeight;
                width=Math.max(width,t.metrics().minimumHitWidth64());height=Math.max(Math.max(height,t.metrics().trackHeight64()),t.metrics().minimumHitHeight64());}
            else if(b.node.recipe() instanceof ButtonRecipe t) {Insets in=t.metrics().labelInsets64();g.semanticHeight=sum(height,in.top(),in.bottom());
                width=Math.max(width,t.metrics().minimumHitWidth64());height=Math.max(g.semanticHeight,t.metrics().minimumHitHeight64());
                text.setGravity(Gravity.CENTER);text.setPadding(px(b.rtl()?in.trailing():in.leading(),b),px(in.top(),b),px(b.rtl()?in.leading():in.trailing(),b),px(in.bottom(),b));}
            else if(b.node.recipe() instanceof FieldRecipe t) {g.semanticHeight=Math.max(t.metrics().minimumContentHeight64(),sum(height,t.metrics().insets64().top(),t.metrics().insets64().bottom()));
                width=availableWidth;height=Math.max(g.semanticHeight,t.metrics().minimumHitHeight64());}
            else g.semanticHeight=height;
            if(width>availableWidth)fail();g.box=new Box(0,0,width,height);
            text.measure(View.MeasureSpec.makeMeasureSpec(px(width,b),View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(px(height,b),View.MeasureSpec.EXACTLY));
            int first=text.getBaseline();if(first<0)fail();g.firstBaseline=logical(first,b);
            g.lastBaseline=sum(g.firstBaseline,logical(text.getLayout().getLineBaseline(text.getLayout().getLineCount()-1)-text.getLayout().getLineBaseline(0),b));return;
        }
        if(b.node.recipe() instanceof ListRecipe list) {measureList(r,records,list,availableWidth,availableHeight);return;}
        if(b.node.recipe() instanceof SectionRecipe section&&section.context() instanceof ListGroup) {
            // Its List assigns row policy and group clip using its own exact recipe.
            return;
        }
        List<String> ids=b.node.childIDs();long width=0,height=0;
        if(b.node.recipe() instanceof NavigationRecipe nav) {
            long compact=title(r.compact,nav.compactTitle(),availableWidth,nav.metrics().compactInsets64(),b);
            long expanded=title(r.header,nav.expandedTitle(),availableWidth,nav.metrics().expandedInsets64(),b);
            g.compactBar=Math.max(nav.metrics().minimumCompactBar64(),compact);
            g.expandedBar=nav.expandedTitle()==null?g.compactBar:Math.max(nav.metrics().minimumExpandedBar64(),sum(g.compactBar,expanded));
            g.overflow=g.expandedBar-g.compactBar;
            boolean collapsed=g.overflow==0||scrollOffset(records,ids,b)>=g.overflow;g.collapsed=collapsed;
            long bar=collapsed?g.compactBar:g.expandedBar;
            long eh=nav.expandedTitle()==null?0:expanded-nav.metrics().expandedInsets64().top()-nav.metrics().expandedInsets64().bottom();
            long ch=nav.compactTitle()==null?0:compact-nav.metrics().compactInsets64().top()-nav.metrics().compactInsets64().bottom();
            g.header=new Box(b.rtl()?nav.metrics().expandedInsets64().trailing():nav.metrics().expandedInsets64().leading(),sum(g.compactBar,nav.metrics().expandedInsets64().top()),
                availableWidth-nav.metrics().expandedInsets64().leading()-nav.metrics().expandedInsets64().trailing(),eh);
            g.compact=new Box(b.rtl()?nav.metrics().compactInsets64().trailing():nav.metrics().compactInsets64().leading(),(g.compactBar-ch)/2,
                availableWidth-nav.metrics().compactInsets64().leading()-nav.metrics().compactInsets64().trailing(),ch);
            r.header.setVisibility(!collapsed&&nav.expandedTitle()!=null?View.VISIBLE:View.INVISIBLE);
            r.compact.setVisibility(collapsed&&nav.compactTitle()!=null?View.VISIBLE:View.INVISIBLE);
            if(availableHeight<bar)fail();Record child=records.get(ids.get(0));measure(child,records,availableWidth,availableHeight-bar);
            g.children.put(child.id,new Box(0,bar,availableWidth,Math.min(child.geometry.box.height,availableHeight-bar)));
            g.box=new Box(0,0,availableWidth,availableHeight);g.semanticHeight=availableHeight;return;
        }
        long titleHeight=0,gap=0;
        if(b.node.recipe() instanceof SectionRecipe s) {
            titleHeight=title(r.header,s.header(),availableWidth,new Insets(0,0,0,0),b);
            gap=s.headerToContentGap64();if(s.header()!=null)g.header=new Box(0,0,availableWidth,titleHeight);
        }
        boolean horizontal=b.node.recipe() instanceof HStackRecipe;
        boolean overlay=b.node.recipe() instanceof ZStackRecipe;
        List<Integer> gaps=b.node.recipe() instanceof HStackRecipe h?h.gaps64():b.node.recipe() instanceof VStackRecipe v?v.gaps64():
            b.node.recipe() instanceof SectionRecipe s?s.contentGaps64():List.of();
        long gapsTotal=0;for(int item:gaps)gapsTotal=sum(gapsTotal,item);
        for(String id:ids) {
            Record child=records.get(id);measure(child,records,availableWidth,availableHeight);
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
                measure(child,records,quotient+(index<remainder?1:0),availableHeight);
                width=sum(width,child.geometry.box.width);height=Math.max(height,child.geometry.box.height);
            }
        }
        if(horizontal)width=sum(width,gapsTotal);else if(!overlay)height=sum(height,gapsTotal,titleHeight,gap);
        if(b.node.recipe() instanceof SectionRecipe)width=availableWidth;
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
    }
    private static long scrollOffset(Map<String,Record> records,List<String> ids,Binding binding) {
        for(String id:ids){Record r=records.get(id);if(r.view instanceof ScrollView)return logical(r.preparedScrollY,binding);
            long value=scrollOffset(records,r.binding.node.childIDs(),binding);if(value>0)return value;}return 0;
    }
    private static long title(TextView view,Text text,long available,Insets in,Binding b) {
        if(text==null)return 0;long reserve=sum(in.leading(),in.trailing());if(available<=reserve)fail();
        view.measure(View.MeasureSpec.makeMeasureSpec(px(available-reserve,b),View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(0,View.MeasureSpec.UNSPECIFIED));
        if(view.getLayout()==null)fail();return sum(logical(view.getMeasuredHeight(),b),in.top(),in.bottom());
    }
    private static long align(HorizontalAlignment alignment,long parent,long child,boolean rtl) {
        return alignment==HorizontalAlignment.center?(parent-child)/2:(alignment==HorizontalAlignment.trailing)!=rtl?parent-child:0;
    }
    private static void measureList(Record r,Map<String,Record> records,ListRecipe list,long width,long availableHeight) {
        Binding b=r.binding;Geometry g=r.geometry;GroupedList m=list.metrics();long groupWidth=width-2L*m.outerHorizontal64();
        if(groupWidth<sum(m.contentInsets64().leading(),m.contentInsets64().trailing()))fail();long y=0;
        for(AppearanceResolverV2.Group item:list.groups()) {
            if(!item.visible()) {if(item.source() instanceof SectionSource s) {Record section=records.get(s.identity().id());
                section.geometry.box=new Box(0,0,0,0);g.children.put(section.id,new Box(0,0,0,0));}continue;}
            y=sum(y,item.leadingGap64());
            Record section=item.source() instanceof SectionSource s?records.get(s.identity().id()):null;
            if(section!=null)section.geometry=new Geometry();Geometry owner=section==null?g:section.geometry;long localY=section==null?y:0;
            if(section!=null) {
                long headerHeight=title(section.header,item.header(),groupWidth,new Insets(0,0,0,0),b);
                if(item.header()!=null)owner.header=new Box(0,0,groupWidth,headerHeight);
                localY=sum(localY,headerHeight,item.headerToRowsGap64());
            }
            long groupTop=localY;List<Long> separators=new ArrayList<>();
            for(int index=0;index<item.rowIdentities().size();index++) {
                Record row=records.get(item.rowIdentities().get(index).id());
                long contentWidth=groupWidth-m.contentInsets64().leading()-m.contentInsets64().trailing();
                measure(row,records,contentWidth,availableHeight);
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

    static void installChildren(Record r,Map<String,Record> records) {
        if(r.group==null)return;
        List<View> desired=new ArrayList<>();if(r.header!=null)desired.add(r.header);if(r.compact!=null)desired.add(r.compact);
        for(String id:r.binding.node.childIDs())desired.add(records.get(id).view);
        for(int index=r.group.getChildCount()-1;index>=0;index--)if(!desired.contains(r.group.getChildAt(index)))r.group.removeViewAt(index);
        for(int index=0;index<desired.size();index++) {
            View child=desired.get(index);if(index<r.group.getChildCount()&&r.group.getChildAt(index)==child)continue;
            if(child.getParent() instanceof ViewGroup previous)previous.removeView(child);
            r.group.addView(child,index,new ViewGroup.LayoutParams(-2,-2));
        }
        r.group.records=records;
    }
    static void layoutRoot(Record root,int width,int height,SafeArea safe) {
        Binding b=root.binding;long left=b.rtl()?safe.trailing():safe.leading();
        long logicalWidth=b.plan.environment.viewport().width64()-safe.leading()-safe.trailing();
        long logicalHeight=b.plan.environment.viewport().height64()-safe.top()-safe.bottom();
        root.geometry.box=new Box(left,safe.top(),logicalWidth,logicalHeight);
        layout(root,left,safe.top(),0,0);
    }
    private static void layout(Record r,long absoluteX,long absoluteY,long parentX,long parentY) {
        Binding b=r.binding;Box frame=r.geometry.box;
        if(r.group!=null){r.group.absoluteX=absoluteX;r.group.absoluteY=absoluteY;}
        int left=px(absoluteX,b)-px(parentX,b),top=px(absoluteY,b)-px(parentY,b);
        int width=px(sum(absoluteX,frame.width),b)-px(absoluteX,b),height=px(sum(absoluteY,frame.height),b)-px(absoluteY,b);
        r.view.measure(View.MeasureSpec.makeMeasureSpec(width,View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(height,View.MeasureSpec.EXACTLY));
        r.view.layout(left,top,left+width,top+height);
        if(r.view instanceof NativeScroll)r.group.layout(0,0,width,px(r.geometry.contentHeight,b));
    }
    static final class Group extends ViewGroup {
        final Record record;Map<String,Record> records=Map.of();long absoluteX,absoluteY;
        Group(Context context,Record record){super(context);this.record=record;setWillNotDraw(false);setClipChildren(false);setClipToPadding(false);}
        @Override protected void onMeasure(int width,int height){setMeasuredDimension(View.MeasureSpec.getSize(width),record.geometry==null?0:
            record.kind.equals("list")?px(record.geometry.contentHeight,record.binding):View.MeasureSpec.getSize(height));}
        @Override protected void onLayout(boolean changed,int l,int t,int right,int bottom) {
            if(record.geometry==null)return;Geometry g=record.geometry;Binding b=record.binding;
            titleLayout(record.header,g.header,b);titleLayout(record.compact,g.compact,b);
            for(String id:b.node.childIDs()) {Record child=records.get(id);Box box=g.children.get(id);if(child==null||box==null)continue;
                child.geometry.box=box;NativeAppearanceViewsV2.layout(child,sum(absoluteX,box.x),sum(absoluteY,box.y),absoluteX,absoluteY);}
        }
        private void titleLayout(TextView view,Box box,Binding b){if(view==null||box==null)return;
            int l=px(sum(absoluteX,box.x),b)-px(absoluteX,b),t=px(sum(absoluteY,box.y),b)-px(absoluteY,b);
            int w=px(sum(absoluteX,box.x,box.width),b)-px(sum(absoluteX,box.x),b),h=px(sum(absoluteY,box.y,box.height),b)-px(sum(absoluteY,box.y),b);
            view.measure(View.MeasureSpec.makeMeasureSpec(w,View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(h,View.MeasureSpec.EXACTLY));view.layout(l,t,l+w,t+h);}
        @Override protected void onDraw(Canvas canvas) {
            if(record.binding==null)return;Binding b=record.binding;
            if(record.kind.equals("navigation")||record.kind.equals("list"))canvas.drawColor(color(b.palette().canvas()));
            Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);paint.setColor(color(b.palette().surface()));
            for(GroupDrawing group:record.geometry.groups){int save=canvas.save();translate(canvas,group.box,b);canvas.drawPath(group.path,paint);canvas.restoreToCount(save);}
        }
        private void translate(Canvas canvas,Box box,Binding b){canvas.translate(px(sum(absoluteX,box.x),b)-px(absoluteX,b),px(sum(absoluteY,box.y),b)-px(absoluteY,b));}
        @Override protected boolean drawChild(Canvas canvas,View child,long time) {
            Integer clip=record.geometry==null?null:record.geometry.clips.get(childRecordID(child));
            if(clip==null)return super.drawChild(canvas,child,time);
            GroupDrawing group=record.geometry.groups.get(clip);int save=canvas.save();Binding b=record.binding;
            int dx=px(sum(absoluteX,group.box.x),b)-px(absoluteX,b),dy=px(sum(absoluteY,group.box.y),b)-px(absoluteY,b);
            canvas.translate(dx,dy);canvas.clipPath(group.path);canvas.translate(-dx,-dy);
            boolean result=super.drawChild(canvas,child,time);canvas.restoreToCount(save);return result;
        }
        private String childRecordID(View view){for(var entry:records.entrySet())if(entry.getValue().view==view)return entry.getKey();return null;}
        @Override protected void dispatchDraw(Canvas canvas) {
            super.dispatchDraw(canvas);if(record.binding==null)return;Binding b=record.binding;GroupedList m=b.theme.groupedList();
            Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);paint.setColor(color(b.palette().separator()));
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
        NativeScroll(Context context,Record record){super(context);this.record=record;setFillViewport(false);setClipToPadding(false);setOverScrollMode(OVER_SCROLL_NEVER);setVerticalScrollBarEnabled(false);}
        @Override protected void onScrollChanged(int l,int t,int oldl,int oldt){super.onScrollChanged(l,t,oldl,oldt);
            if(record.binding==null||t==oldt||!record.input.open(record))return;record.input.interaction();
            for(var parent=getParent();parent instanceof View view;parent=view.getParent())if(view instanceof Group group&&group.record.binding.node.recipe() instanceof NavigationRecipe nav){
                Record owner=group.record;Geometry g=owner.geometry;Binding b=owner.binding;
                boolean collapsed=g.overflow==0||logical(t,b)>=g.overflow;
                boolean previously=g.collapsed;g.collapsed=collapsed;
                if(collapsed==previously)return;
                owner.header.setVisibility(!collapsed&&nav.expandedTitle()!=null?View.VISIBLE:View.INVISIBLE);
                owner.compact.setVisibility(collapsed&&nav.compactTitle()!=null?View.VISIBLE:View.INVISIBLE);
                String childID=b.node.childIDs().get(0);Box child=g.children.get(childID);
                long bar=collapsed?g.compactBar:g.expandedBar;
                g.children.put(childID,new Box(child.x,bar,child.width,g.box.height-bar));
                group.onLayout(true,group.getLeft(),group.getTop(),group.getRight(),group.getBottom());group.invalidate();return;
            }
        }
    }
    static final class Gate extends FrameLayout {
        boolean open;
        Gate(Context context){super(context);setClipChildren(false);setClipToPadding(false);}
        @Override protected void dispatchDraw(Canvas canvas){if(open)super.dispatchDraw(canvas);}
        @Override public boolean dispatchTouchEvent(MotionEvent event){return !open||super.dispatchTouchEvent(event);}
        @Override public boolean dispatchKeyEvent(android.view.KeyEvent event){return !open||super.dispatchKeyEvent(event);}
        @Override protected void onLayout(boolean changed,int l,int t,int r,int b){/* prepared frames only */}
    }
    private static final class NativeButton extends Button {
        NativeButton(Context context,Record record){super(context);setAllCaps(false);setGravity(Gravity.CENTER);}
    }
    private static final class NativeField extends EditText {
        final Record record;
        NativeField(Context context,Record record){super(context);this.record=record;}
        void refreshPaint(){if(record!=null&&record.binding!=null)setHighlightColor(color(fieldPaint(record).selection()));}
        @Override protected void drawableStateChanged(){super.drawableStateChanged();refreshPaint();}
        private boolean proposal(CharSequence value,boolean composing){
            if(!record.input.open(record))return false;Editable buffer=getText();
            int start=getSelectionStart(),end=getSelectionEnd();
            int cs=android.view.inputmethod.BaseInputConnection.getComposingSpanStart(buffer),ce=android.view.inputmethod.BaseInputConnection.getComposingSpanEnd(buffer);
            if(cs>=0&&ce>=0){start=cs;end=ce;}if(start<0||end<0)return false;
            int left=Math.min(start,end),right=Math.max(start,end);
            String proposed=buffer.subSequence(0,left).toString()+value+buffer.subSequence(right,buffer.length());
            return validBuffer(proposed);
        }
        @Override public android.view.inputmethod.InputConnection onCreateInputConnection(EditorInfo info){
            android.view.inputmethod.InputConnection nativeConnection=super.onCreateInputConnection(info);if(nativeConnection==null)return null;
            return new android.view.inputmethod.InputConnectionWrapper(nativeConnection,false){
                private boolean open(){return record.input.open(record);}
                @Override public boolean commitText(CharSequence text,int position){return proposal(text,false)&&super.commitText(text,position);}
                @Override public boolean setComposingText(CharSequence text,int position){return proposal(text,true)&&super.setComposingText(text,position);}
                @Override public boolean commitText(CharSequence text,int position,android.view.inputmethod.TextAttribute attributes){return proposal(text,false)&&super.commitText(text,position,attributes);}
                @Override public boolean setComposingText(CharSequence text,int position,android.view.inputmethod.TextAttribute attributes){return proposal(text,true)&&super.setComposingText(text,position,attributes);}
                @Override public boolean setComposingRegion(int start,int end){return open()&&super.setComposingRegion(start,end);}
                @Override public boolean setComposingRegion(int start,int end,android.view.inputmethod.TextAttribute attributes){return open()&&super.setComposingRegion(start,end,attributes);}
                @Override public boolean finishComposingText(){return open()&&super.finishComposingText();}
                @Override public boolean deleteSurroundingText(int before,int after){return open()&&super.deleteSurroundingText(before,after);}
                @Override public boolean deleteSurroundingTextInCodePoints(int before,int after){return open()&&super.deleteSurroundingTextInCodePoints(before,after);}
                @Override public boolean setSelection(int start,int end){return open()&&super.setSelection(start,end);}
                @Override public boolean performEditorAction(int action){return open()&&super.performEditorAction(action);}
                @Override public boolean sendKeyEvent(android.view.KeyEvent event){int value=event.getUnicodeChar();
                    return open()&&(event.getAction()!=android.view.KeyEvent.ACTION_DOWN||value==0||proposal(new String(Character.toChars(value)),false))&&super.sendKeyEvent(event);}
                @Override public boolean replaceText(int start,int end,CharSequence text,int position,android.view.inputmethod.TextAttribute attributes){return false;}
                @Override public boolean performPrivateCommand(String action,android.os.Bundle data){return false;}
                @Override public boolean setImeConsumesInput(boolean consumes){return open()&&super.setImeConsumesInput(consumes);}
                @Override public void performHandwritingGesture(android.view.inputmethod.HandwritingGesture gesture,java.util.concurrent.Executor executor,java.util.function.IntConsumer result){if(executor!=null&&result!=null)executor.execute(()->result.accept(android.view.inputmethod.InputConnection.HANDWRITING_GESTURE_RESULT_UNSUPPORTED));}
                @Override public boolean previewHandwritingGesture(android.view.inputmethod.PreviewableHandwritingGesture gesture,android.os.CancellationSignal cancellation){return false;}
                @Override public boolean commitCompletion(android.view.inputmethod.CompletionInfo value){return value!=null&&proposal(value.getText(),false)&&super.commitCompletion(value);}
                @Override public boolean commitCorrection(android.view.inputmethod.CorrectionInfo value){return false;}
                @Override public boolean commitContent(android.view.inputmethod.InputContentInfo content,int flags,android.os.Bundle options){return false;}
            };
        }
        @Override public boolean onKeyDown(int code,android.view.KeyEvent event){
            if(!record.input.open(record))return true;int value=event.getUnicodeChar();
            if(value!=0&&!proposal(new String(Character.toChars(value)),false))return true;return super.onKeyDown(code,event);
        }
        @Override public boolean onTextContextMenuItem(int id){
            if(!record.input.open(record))return false;
            if(id==android.R.id.paste||id==android.R.id.pasteAsPlainText){
                android.content.ClipboardManager clipboard=getContext().getSystemService(android.content.ClipboardManager.class);
                android.content.ClipData clip=clipboard==null?null:clipboard.getPrimaryClip();if(clip==null)return false;
                StringBuilder proposed=new StringBuilder();for(int i=0;i<clip.getItemCount();i++){if(i>0)proposed.append('\n');proposed.append(clip.getItemAt(i).coerceToText(getContext()));}
                if(!proposal(proposed,false))return false;
            }
            return super.onTextContextMenuItem(id);
        }
    }
    private static final class NativeSwitch extends Switch {
        final Record record;Path track,thumb;
        NativeSwitch(Context context,Record record){super(context);this.record=record;}
        void refreshPaint(){if(record!=null&&record.binding!=null)setTextColor(color(togglePaint(record).label()));}
        @Override protected void drawableStateChanged(){super.drawableStateChanged();refreshPaint();}
        @Override protected void onDraw(Canvas canvas) {
            if(record.binding==null||track==null)return;Binding b=record.binding;ToggleRecipe recipe=(ToggleRecipe)b.node.recipe();ToggleMetrics m=recipe.metrics();TogglePaint colors=togglePaint(record);
            Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);Layout text=getLayout();
            if(text!=null){int save=canvas.save();int x=b.rtl()?px(sum(m.trackWidth64(),m.labelGap64()),b):0;
                canvas.translate(x,(getHeight()-text.getHeight())/2f);text.draw(canvas);canvas.restoreToCount(save);}
            float x=b.rtl()?0:getWidth()-px(m.trackWidth64(),b),y=(getHeight()-px(m.trackHeight64(),b))/2f;
            int save=canvas.save();canvas.translate(x,y);paint.setColor(color(colors.track()));canvas.drawPath(track,paint);
            int clip=canvas.save();canvas.clipPath(track);paint.setColor(color(colors.overlay()));canvas.drawPath(track,paint);canvas.restoreToCount(clip);
            AppearanceGeometryV2.Point origin=AppearanceGeometryV2.thumbOrigin(isChecked(),b.rtl()?AppearanceGeometryV2.Direction.rightToLeft:AppearanceGeometryV2.Direction.leftToRight);
            canvas.translate((float)AppearanceGeometryV2.pixelCoordinate(origin.x64(),b.density()),(float)AppearanceGeometryV2.pixelCoordinate(origin.y64(),b.density()));
            paint.setColor(color(colors.thumb()));canvas.drawPath(thumb,paint);canvas.restoreToCount(save);
            if(isEnabled()&&isFocused()){ToggleStates states=isChecked()?b.palette().toggle().on():b.palette().toggle().off();outline(canvas,new RectF(x,y,x+px(m.trackWidth64(),b),y+px(m.trackHeight64(),b)),states.focus(),b,paint);}
        }
    }
    private abstract static class OwnedDrawable extends Drawable {
        final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        @Override public void setAlpha(int alpha){if(alpha!=255)throw new IllegalArgumentException("authored alpha only");}
        @Override public void setColorFilter(ColorFilter filter){if(filter!=null)throw new IllegalArgumentException("authored colors only");}
        @Override public int getOpacity(){return PixelFormat.TRANSLUCENT;}
    }
    private static final class ControlDrawable extends OwnedDrawable {
        final Record record;final boolean field;
        ControlDrawable(Record record,boolean field){this.record=record;this.field=field;}
        @Override public boolean isStateful(){return true;}
        @Override protected boolean onStateChange(int[] state){invalidateSelf();return true;}
        @Override public void draw(Canvas canvas){Binding b=record.binding;if(b==null)return;
            if(field){FieldPaint colors=fieldPaint(record);RectF box=new RectF(getBounds());paint.setColor(color(colors.background()));canvas.drawRect(box,paint);outline(canvas,box,colors.outline(),b,paint);}
            else {ButtonRecipe r=(ButtonRecipe)b.node.recipe();ButtonStates states=buttonStates(b,r.role());
                ButtonPaint colors=!record.view.isEnabled()?states.disabled():record.view.isPressed()?states.pressed():states.enabled();
                TextView text=(TextView)record.view;Layout layout=text.getLayout();float textWidth=0;
                if(layout!=null)for(int i=0;i<layout.getLineCount();i++)textWidth=Math.max(textWidth,layout.getLineWidth(i));
                float w=textWidth+px(sum(r.metrics().labelInsets64().leading(),r.metrics().labelInsets64().trailing()),b);
                float h=(layout==null?0:layout.getHeight())+px(sum(r.metrics().labelInsets64().top(),r.metrics().labelInsets64().bottom()),b);
                RectF box=new RectF((text.getWidth()-w)/2,(text.getHeight()-h)/2,(text.getWidth()+w)/2,(text.getHeight()+h)/2);
                paint.setColor(color(colors.background()));float radius=px(r.metrics().overlayRadius64(),b);canvas.drawRoundRect(box,radius,radius,paint);
                if(record.view.isEnabled()&&record.view.isFocused())outline(canvas,box,states.focus(),b,paint);
            }}
    }
    private static void outline(Canvas canvas,RectF box,Outline outline,Binding b,Paint paint){if(outline==null||outline.width64()==0)return;
        float width=(float)AppearanceGeometryV2.pixelCoordinate(outline.width64(),b.density());RectF inner=new RectF(box);inner.inset(width/2,width/2);
        paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(width);paint.setColor(color(outline.color()));float radius=(float)AppearanceGeometryV2.pixelCoordinate(outline.radius64(),b.density());
        canvas.drawRoundRect(inner,radius,radius,paint);paint.setStyle(Paint.Style.FILL);}
    private static final class Cursor extends OwnedDrawable {
        final Record record;Cursor(Record record){this.record=record;}
        @Override public int getIntrinsicWidth(){return 2;}
        @Override public void draw(Canvas canvas){paint.setColor(color(fieldPaint(record).caret()));canvas.drawRect(getBounds(),paint);}
    }
    private static final class Handle extends OwnedDrawable {
        final Record record;Handle(Record record){this.record=record;}
        @Override public int getIntrinsicWidth(){return 12;}@Override public int getIntrinsicHeight(){return 12;}
        @Override public void draw(Canvas canvas){paint.setColor(color(fieldPaint(record).selection()));canvas.drawOval(new RectF(getBounds()),paint);}
    }
    private static final class Empty extends OwnedDrawable {
        final int width,height;Empty(int width,int height){this.width=width;this.height=height;}
        @Override public int getIntrinsicWidth(){return width;}@Override public int getIntrinsicHeight(){return height;}
        @Override public void draw(Canvas canvas){}
    }
}
