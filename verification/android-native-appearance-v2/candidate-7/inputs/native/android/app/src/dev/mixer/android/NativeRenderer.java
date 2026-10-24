package dev.mixer.android;
import android.content.Context;
import android.os.Build;
import android.text.*;
import android.view.*;
import android.view.inputmethod.EditorInfo;
import android.widget.*;
import java.util.*;

/** Native Android widget toolkit adapter. All state/actions remain in Swift. */
final class NativeRenderer {
    interface Events { void send(byte[] envelope); }
    static final class Record {
        final View view;final ViewGroup children;final TextView title;final String kind,generation;boolean binding;TextWatcher watcher;
        Record(View v,ViewGroup c,TextView t,UiPacket.Node n){view=v;children=c;title=t;kind=n.kind;generation=n.generation;}
    }
    private final Context context;private final Events events;private Map<String,Record>records=new HashMap<>();UiPacket packet;
    NativeRenderer(Context c,Events e){context=c;events=e;}
    private int dp(double value){return(int)Math.round(value*context.getResources().getDisplayMetrics().density);}
    View view(String id){if(v2Records.containsKey(id))return v2Records.get(id).view;Record r=records.get(id);if(r==null)throw Json.bad("missing native ID "+id);return r.view;}
    View apply(UiPacket next){
        if(android.os.Looper.myLooper()!=android.os.Looper.getMainLooper())throw new IllegalStateException("renderer requires UI thread");if(v2Pending!=null||v2Plan!=null)throw Json.bad("V2 owner cannot use legacy apply");next.requireSuccessor(packet);
        if(Build.VERSION.SDK_INT<30)for(UiPacket.Node n:next.nodes.values())if(n.properties.containsKey("accessibilityValue"))throw Json.bad("accessibilityValue requires API30");
        Map<String,Record>candidate=new HashMap<>();for(UiPacket.Node n:next.nodes.values()){Record old=records.get(n.id);candidate.put(n.id,old!=null&&old.kind.equals(n.kind)&&old.generation.equals(n.generation)?old:create(n));}
        for(UiPacket.Node n:next.nodes.values())bind(candidate.get(n.id),n,next);
        for(UiPacket.Node n:next.nodes.values()){Record r=candidate.get(n.id);if(r.children!=null)children(r,n,candidate);}
        packet=next;records=candidate;return records.get(next.root.id).view;
    }
    private Record create(UiPacket.Node n){
        View v;ViewGroup children=null;TextView title=null;
        switch(n.kind){
            case "text":v=new TextView(context);break;
            case "textField":EditText e=new EditText(context);e.setSingleLine(true);e.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);e.setImeOptions(EditorInfo.IME_ACTION_DONE);v=e;break;
            case "button":Button b=new Button(context);b.setAllCaps(false);v=b;break;
            case "toggle":v=new Switch(context);break;
            case "zStack":FrameLayout z=new FrameLayout(context);v=z;children=z;break;
            case "list":ScrollView scroll=new ScrollView(context);scroll.setFillViewport(true);LinearLayout content=new LinearLayout(context);content.setOrientation(LinearLayout.VERTICAL);content.setPadding(dp(16),dp(8),dp(16),dp(24));scroll.addView(content,new ScrollView.LayoutParams(-1,-2));v=scroll;children=content;break;
            case "section":case "navigation":LinearLayout outer=new LinearLayout(context);outer.setOrientation(LinearLayout.VERTICAL);title=new TextView(context);title.setTextSize(n.kind.equals("navigation")?22:15);title.setTypeface(null,android.graphics.Typeface.BOLD);title.setPadding(dp(8),dp(16),dp(8),dp(12));outer.addView(title,new LinearLayout.LayoutParams(-1,-2));LinearLayout inner=new LinearLayout(context);inner.setOrientation(LinearLayout.VERTICAL);outer.addView(inner,new LinearLayout.LayoutParams(-1,n.kind.equals("navigation")?-1:-2));v=outer;children=inner;break;
            default:LinearLayout layout=new LinearLayout(context);layout.setOrientation(n.kind.equals("hStack")?LinearLayout.HORIZONTAL:LinearLayout.VERTICAL);v=layout;children=layout;break;
        }
        v.setId(View.generateViewId());v.setTag(n.id);return new Record(v,children,title,n);
    }
    private void send(UiPacket source,UiPacket.Node n,String event,Object value){events.send(source.event(n.id,n.generation,event,value));}
    private void bind(Record r,UiPacket.Node n,UiPacket source){
        r.binding=true;View v=r.view;v.setTag(n.text("accessibilityIdentifier",n.id));v.setEnabled(!n.disabled);String label=n.text("accessibilityLabel",n.kind.equals("textField")?n.text("label",""):null);v.setContentDescription(label);
        v.setTooltipText(n.text("accessibilityHint",null));if(Build.VERSION.SDK_INT>=30)v.setStateDescription(n.text("accessibilityValue",null));
        if(r.title!=null){String title=n.text("title","");r.title.setText(title);r.title.setVisibility(title.isEmpty()?View.GONE:View.VISIBLE);}
        switch(n.kind){
            case "text":TextView text=(TextView)v;text.setText(n.text("text",""));String style=n.text("style","body");text.setTextSize(style.equals("title")?26:style.equals("headline")?19:style.equals("caption")?14:16);text.setTypeface(null,style.equals("headline")||style.equals("title")?android.graphics.Typeface.BOLD:android.graphics.Typeface.NORMAL);text.setTextIsSelectable(n.flag("selectable",false));text.setMaxLines((int)n.number("maxLines",Integer.MAX_VALUE));text.setPadding(dp(4),dp(6),dp(4),dp(6));break;
            case "button":Button button=(Button)v;button.setText(n.text("label",""));String role=n.text("role","normal");button.setTextColor(n.disabled?0xff777777:role.equals("destructive")?0xffa52020:0xff304ffe);button.setOnClickListener(ignored->send(source,n,"activate",null));break;
            case "textField":EditText edit=(EditText)v;edit.setHint(n.text("label",""));String value=n.text("value","");if(!edit.getText().toString().equals(value)){int cursor=edit.getSelectionStart();edit.setText(value);edit.setSelection(Math.max(0,Math.min(cursor,value.length())));}edit.setFilters(new InputFilter[]{(src,start,end,dst,dstart,dend)->{String candidate=dst.subSequence(0,dstart).toString()+src.subSequence(start,end)+dst.subSequence(dend,dst.length());return candidate.getBytes(java.nio.charset.StandardCharsets.UTF_8).length<=16384?null:"";}});edit.setOnEditorActionListener((field,action,event)->{if(action==EditorInfo.IME_ACTION_DONE&&n.actions.containsKey("submit")){send(source,n,"submit",null);return true;}return false;});
                if(r.watcher!=null)edit.removeTextChangedListener(r.watcher);TextWatcher next=new TextWatcher(){public void beforeTextChanged(CharSequence s,int st,int count,int after){}public void onTextChanged(CharSequence s,int st,int before,int count){}public void afterTextChanged(Editable s){if(!r.binding)send(source,n,"textChange",s.toString());}};edit.addTextChangedListener(next);r.watcher=next;break;
            case "toggle":Switch toggle=(Switch)v;toggle.setOnCheckedChangeListener(null);toggle.setText(n.text("label",""));toggle.setChecked(n.flag("value",false));toggle.setPadding(dp(4),dp(12),dp(4),dp(12));toggle.setOnCheckedChangeListener((buttonView,checked)->{if(!r.binding)send(source,n,"valueChange",checked);});break;
            case "vStack":case "hStack":LinearLayout stack=(LinearLayout)v;String alignment=n.text("alignment","center");stack.setGravity(alignment.equals("center")?(n.kind.equals("hStack")?Gravity.CENTER_VERTICAL:Gravity.CENTER_HORIZONTAL):gravity(alignment));break;
            default:break;
        }r.binding=false;
    }
    private int gravity(String a){switch(a){case "leading":return Gravity.START;case "trailing":return Gravity.END;case "top":return Gravity.TOP;case "bottom":return Gravity.BOTTOM;case "topLeading":return Gravity.TOP|Gravity.START;case "topTrailing":return Gravity.TOP|Gravity.END;case "bottomLeading":return Gravity.BOTTOM|Gravity.START;case "bottomTrailing":return Gravity.BOTTOM|Gravity.END;default:return Gravity.CENTER;}}
    private void children(Record r,UiPacket.Node n,Map<String,Record>candidate){
        ViewGroup parent=r.children;Set<View>desired=new HashSet<>();for(UiPacket.Node child:n.children)desired.add(candidate.get(child.id).view);for(int i=parent.getChildCount()-1;i>=0;i--)if(!desired.contains(parent.getChildAt(i)))parent.removeViewAt(i);
        for(int i=0;i<n.children.size();i++){View view=candidate.get(n.children.get(i).id).view;if(i>=parent.getChildCount()||parent.getChildAt(i)!=view){if(view.getParent()instanceof ViewGroup)((ViewGroup)view.getParent()).removeView(view);parent.addView(view,i);}
            if(parent instanceof FrameLayout){FrameLayout.LayoutParams lp=new FrameLayout.LayoutParams(-2,-2,gravity(n.text("alignment","center")));view.setLayoutParams(lp);}else{boolean horizontal=n.kind.equals("hStack");int height=n.kind.equals("navigation")?-1:-2;LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(horizontal?-2:-1,height);int spacing=dp(n.number("spacing",n.kind.equals("list")?8:0));if(i+1<n.children.size()){if(horizontal)lp.setMarginEnd(spacing);else lp.bottomMargin=spacing;}view.setLayoutParams(lp);}}
    }

    // Ordinary private V2 lane. Existing apply()/signed/V1 behavior is unchanged.
    private Map<String,NativeAppearanceViewsV2.Record> v2Records=Map.of();
    private AppearanceResolverV2.Plan v2Plan;
    private InstalledAppearanceV2 v2Installed;
    private NativeEnvironmentV2.Observer v2Environment;
    private NativeAppearanceViewsV2.Gate v2Gate;
    private Candidate v2Pending;
    private boolean v2Open=true,v2Retired;
    private long v2Interaction;
    private int v2Fault=-1,v2Steps;
    private boolean v2RollbackFault;
    private final NativeAppearanceViewsV2.Input v2Input=new NativeAppearanceViewsV2.Input(){
        public boolean open(NativeAppearanceViewsV2.Record record){return v2Open&&!v2Retired&&v2Records.get(record.id)==record&&record.view.isEnabled();}
        public void event(NativeAppearanceViewsV2.Record record,String name,Object value){
            if(!open(record))return;interaction();events.send(packet.event(record.id,record.generation,name,value));
        }
        public void interaction(){if(!v2Open)return;if(v2Interaction==Long.MAX_VALUE){retireV2();return;}v2Interaction++;}
    };
    InstalledAppearanceV2 captureInstalledV2(){
        NativeEnvironmentV2.requireMain();requireV2Live();
        InstalledAppearanceV2 capture=InstalledAppearanceV2.capture(context,this);
        v2Installed=capture;return capture;
    }
    NativeEnvironmentV2 captureEnvironmentV2(android.app.Activity activity,FrameLayout root){
        NativeEnvironmentV2.requireMain();requireV2Live();
        if(v2Environment==null)v2Environment=new NativeEnvironmentV2.Observer(this,activity,root);
        else if(v2Environment.activity!=activity||v2Environment.root!=root)throw Json.bad("foreign V2 window");
        return v2Environment.capture();
    }
    static final class Candidate {
        private final NativeRenderer owner;
        private final UiPacket base,next;
        private final Map<String,NativeAppearanceViewsV2.Record> baseRecords,targets,detached;
        private final AppearanceResolverV2.Plan plan;
        private final InstalledAppearanceV2 installed;
        private final NativeEnvironmentV2 environment;
        private final long interaction;
        private final NativeAppearanceViewsV2.Gate gate;
        private final AttachmentJournal journal;
        private boolean used,attached;
        private Candidate(NativeRenderer owner,UiPacket next,Map<String,NativeAppearanceViewsV2.Record> targets,
                          Map<String,NativeAppearanceViewsV2.Record> detached,AppearanceResolverV2.Plan plan,
                          InstalledAppearanceV2 installed,NativeEnvironmentV2 environment,NativeAppearanceViewsV2.Gate gate){
            this.owner=owner;this.base=owner.packet;this.next=next;this.baseRecords=owner.v2Records;
            this.targets=targets;this.detached=detached;this.plan=plan;this.installed=installed;
            this.environment=environment;this.interaction=owner.v2Interaction;this.gate=gate;
            journal=new AttachmentJournal(this);
        }
    }
    static final class AttachmentJournal {
        private final Candidate candidate;
        private final List<NativeState> previous;
        private final List<ParentState> parents;
        private final View[] rootChildren;
        private final NativeAppearanceViewsV2.Gate oldGate;
        private final int rootWidth,rootHeight;
        private boolean complete;
        private AttachmentJournal(Candidate candidate){
            this.candidate=candidate;previous=new ArrayList<>();parents=new ArrayList<>();
            for(var record:candidate.baseRecords.values()){
                previous.add(new NativeState(record));
                if(record.group!=null)parents.add(new ParentState(record.group));
            }
            FrameLayout root=candidate.environment.root();rootChildren=childrenV2(root);
            rootWidth=root.getWidth();rootHeight=root.getHeight();oldGate=candidate.owner.v2Gate;if(oldGate!=null)parents.add(new ParentState(oldGate));
        }
    }
    private static final class NativeState {
        final NativeAppearanceViewsV2.Record record;
        final NativeAppearanceViewsV2.Binding binding;
        final NativeAppearanceViewsV2.Geometry geometry;
        final CharSequence text;
        final int selectionStart,selectionEnd,scrollX,scrollY;final boolean active,checked,focused,pressed;
        NativeState(NativeAppearanceViewsV2.Record record){
            this.record=record;binding=record.binding;geometry=record.geometry;active=record.view instanceof EditText e&&(e.hasFocus()||android.view.inputmethod.BaseInputConnection.getComposingSpanStart(e.getText())>=0)||record.view instanceof TextView t&&t.getSelectionStart()>=0&&t.getSelectionStart()!=t.getSelectionEnd();
            text=record.view instanceof TextView t?new android.text.SpannableString(t.getText()):null;
            selectionStart=record.view instanceof TextView t?t.getSelectionStart():-1;
            selectionEnd=record.view instanceof TextView t?t.getSelectionEnd():-1;
            scrollX=record.view.getScrollX();scrollY=record.view.getScrollY();checked=record.view instanceof Switch value&&value.isChecked();focused=record.view.hasFocus();pressed=record.view.isPressed();
        }
    }
    private record ParentState(ViewGroup parent,View[] children) {
        ParentState(ViewGroup parent){this(parent,childrenV2(parent));}
    }
    private static View[] childrenV2(ViewGroup parent){View[] result=new View[parent.getChildCount()];for(int i=0;i<result.length;i++)result[i]=parent.getChildAt(i);return result;}
    Candidate prepareV2(byte[] bytes,InstalledAppearanceV2 installed,NativeEnvironmentV2 environment){
        NativeEnvironmentV2.requireMain();requireV2Live();
        if(v2Pending!=null)throw Json.bad("V2 candidate already pending");
        if(installed==null||installed!=v2Installed||!installed.belongsTo(this)||environment==null||!environment.current(this))throw Json.bad("stale/foreign V2 capture");
        if(bytes==null||bytes.length>1048576)throw Json.bad("V2 packet byte limit");byte[] owned=bytes.clone();UiPacket next=UiPacket.decode(owned);next.requireSuccessor(packet);
        AppearanceResolverV2.Plan plan=AppearanceResolverV2.prepare(owned,installed.descriptorCopy(),environment.value,AppearanceResolverV2.Platform.android);
        for(var node:plan.nodes)if(node.recipe() instanceof AppearanceResolverV2.ButtonRecipe||node.recipe() instanceof AppearanceResolverV2.FieldRecipe||node.recipe() instanceof AppearanceResolverV2.ToggleRecipe){
            String ancestor=parentV2(next,node.identity().id());while(ancestor!=null){if(plan.node(ancestor).rowPlacement()!=null)throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);ancestor=parentV2(next,ancestor);}}
        Map<String,NativeAppearanceViewsV2.Record> detached=new LinkedHashMap<>(),targets=new LinkedHashMap<>();
        for(var node:plan.nodes){UiPacket.Node source=next.nodes.get(node.identity().id());
            NativeAppearanceViewsV2.Record shadow=new NativeAppearanceViewsV2.Record(context,source,v2Input);
            NativeAppearanceViewsV2.Geometry geometry=new NativeAppearanceViewsV2.Geometry();
            shadow.bind(new NativeAppearanceViewsV2.Binding(plan,node,source,installed.configuration.android),geometry,false);
            detached.put(source.id,shadow);
            var old=v2Records.get(source.id);if(old!=null)shadow.preparedScrollY=old.view.getScrollY();targets.put(source.id,old!=null&&old.kind.equals(source.kind)&&old.generation.equals(source.generation)?old:shadow);
        }
        for(var record:detached.values())NativeAppearanceViewsV2.installChildren(record,detached);
        var safe=environment.value.safeArea64();long width=environment.value.viewport().width64()-safe.leading()-safe.trailing();
        long height=environment.value.viewport().height64()-safe.top()-safe.bottom();
        NativeAppearanceViewsV2.measure(detached.get(next.root.id),detached,width,height);
        NativeAppearanceViewsV2.layoutRoot(detached.get(next.root.id),environment.width,environment.height,safe);
        NativeAppearanceViewsV2.Gate gate=v2Gate==null?new NativeAppearanceViewsV2.Gate(context):v2Gate;
        Candidate candidate=new Candidate(this,next,Collections.unmodifiableMap(targets),Collections.unmodifiableMap(detached),plan,installed,environment,gate);
        preflightEditorsV2(candidate);
        v2Pending=candidate;return candidate;
    }
    private void preflightEditorsV2(Candidate c){
        for(var previous:v2Records.values()){
            boolean active=previous.view instanceof EditText edit&&(edit.hasFocus()||android.view.inputmethod.BaseInputConnection.getComposingSpanStart(edit.getText())>=0);
            boolean selecting=previous.view instanceof TextView text&&text.getSelectionStart()>=0&&text.getSelectionStart()!=text.getSelectionEnd();
            if(!active&&!selecting)continue;
            var shadow=c.detached.get(previous.id);
            if(c.targets.get(previous.id)!=previous||shadow==null||!sameEditorBindingV2(previous,shadow)||!sameAncestorsV2(c,previous.id)||
                !sameFrameV2(previous.view,shadow.view))throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);
        }
    }
    private static boolean sameEditorBindingV2(NativeAppearanceViewsV2.Record old,NativeAppearanceViewsV2.Record next){
        // Engine echo can acknowledge the current native buffer without calling setText or replacing Editable.
        if(!(old.view instanceof TextView text)||!text.getText().toString().equals(((TextView)next.view).getText().toString()))return false;
        var a=old.binding;var b=next.binding;
        boolean recipe=a.node().recipe().equals(b.node().recipe());
        Map<String,Object> ap=new HashMap<>(a.source().properties),bp=new HashMap<>(b.source().properties);
        if(a.node().recipe() instanceof AppearanceResolverV2.FieldRecipe x&&b.node().recipe() instanceof AppearanceResolverV2.FieldRecipe y){
            recipe=x.label().equals(y.label())&&x.metrics().equals(y.metrics())&&x.text().role()==y.text().role()&&x.text().metrics().equals(y.text().metrics());ap.remove("value");bp.remove("value");}
        return recipe&&a.node().disabled()==b.node().disabled()&&ap.equals(bp)&&
            a.plan().environment.scheme()==b.plan().environment.scheme()&&a.plan().environment.profile()==b.plan().environment.profile()&&
            a.plan().environment.direction()==b.plan().environment.direction()&&a.plan().environment.density1024()==b.plan().environment.density1024()&&
            a.plan().environment.localeIdentifier().equals(b.plan().environment.localeIdentifier())&&a.theme().equals(b.theme());
    }
    private static boolean sameFrameV2(View a,View b){
        int[] ap=positionV2(a),bp=positionV2(b);return Arrays.equals(ap,bp)&&a.getWidth()==b.getWidth()&&a.getHeight()==b.getHeight();
    }
    private static int[] positionV2(View view){int x=view.getLeft(),y=view.getTop();for(var parent=view.getParent();parent instanceof View v;parent=v.getParent()){
        if(v instanceof NativeAppearanceViewsV2.Gate||v instanceof FrameLayout)break;x+=v.getLeft();y+=v.getTop();}return new int[]{x,y};}
    private static String parentV2(UiPacket packet,String id){if(packet==null)return null;for(var n:packet.nodes.values())for(var c:n.children)if(c.id.equals(id))return n.id;return null;}
    private static boolean sameAncestorsV2(Candidate c,String id){String current=id;
        while(current!=null){String before=parentV2(c.base,current),after=parentV2(c.next,current);if(!Objects.equals(before,after))return false;
            if(before!=null){UiPacket.Node a=c.base.nodes.get(before),b=c.next.nodes.get(after);if(b==null||!a.kind.equals(b.kind)||!a.generation.equals(b.generation))return false;
                List<String> ac=new ArrayList<>(),bc=new ArrayList<>();for(var n:a.children)ac.add(n.id);for(var n:b.children)bc.add(n.id);if(!ac.equals(bc))return false;}
            current=before;}return true;}
    private void validateV2(Candidate c,boolean attached){
        NativeEnvironmentV2.requireMain();requireV2Live();
        if(c==null||c.owner!=this||v2Pending!=c||c.used||c.attached!=attached||packet!=c.base||v2Records!=c.baseRecords||
            v2Installed!=c.installed||v2Interaction!=c.interaction||!c.environment.current(this))throw Json.bad("stale/foreign/consumed V2 candidate");
    }
    AttachmentJournal attachV2(Candidate c,FrameLayout root){
        validateV2(c,false);if(root!=c.environment.root())throw Json.bad("foreign V2 root");preflightEditorsV2(c);
        v2Open=false;c.gate.open=false;if(v2Gate!=null)v2Gate.open=false;v2Steps=0;
        try {
            for(var entry:c.targets.entrySet()){
                var target=entry.getValue();var shadow=c.detached.get(entry.getKey());
                if(target!=shadow){boolean preserve=target.view instanceof TextView&&sameEditorBindingV2(target,shadow);
                    target.bind(shadow.binding,shadow.geometry,preserve);}
                faultV2();
            }
            for(var target:c.targets.values()){NativeAppearanceViewsV2.installChildren(target,c.targets);faultV2();}
            View desired=c.targets.get(c.next.root.id).view;
            if(desired.getParent()!=c.gate){if(desired.getParent() instanceof ViewGroup previous)previous.removeView(desired);c.gate.addView(desired);}
            for(int i=c.gate.getChildCount()-1;i>=0;i--)if(c.gate.getChildAt(i)!=desired)c.gate.removeViewAt(i);
            faultV2();
            if(c.gate.getParent()!=root){if(c.gate.getParent() instanceof ViewGroup previous)previous.removeView(c.gate);root.addView(c.gate,new FrameLayout.LayoutParams(-1,-1));}
            for(int i=root.getChildCount()-1;i>=0;i--)if(root.getChildAt(i)!=c.gate)root.removeViewAt(i);
            c.gate.measure(View.MeasureSpec.makeMeasureSpec(root.getWidth(),View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(root.getHeight(),View.MeasureSpec.EXACTLY));
            c.gate.layout(0,0,root.getWidth(),root.getHeight());
            NativeAppearanceViewsV2.layoutRoot(c.targets.get(c.next.root.id),root.getWidth(),root.getHeight(),c.environment.value.safeArea64());
            faultV2();c.attached=true;return c.journal;
        }catch(RuntimeException|java.lang.Error failure){try{restoreV2(c);}catch(RuntimeException|java.lang.Error rollback){retireV2();failure.addSuppressed(rollback);}c.used=true;v2Pending=null;throw failure;}
    }
    /** Scalar/reference checks and prepared swaps only. Coordinator commits engine immediately before this call. */
    void finishV2(Candidate c,AttachmentJournal journal){
        NativeEnvironmentV2.requireMain();
        // The coordinator must call validateAttachedV2 immediately before its scalar engine commit.
        // Never read resources or invoke native layout/setters/JNI after that commit boundary.
        if(c==null||c.owner!=this||v2Pending!=c||c.used||!c.attached||journal!=c.journal||journal.complete||v2Retired)
            throw Json.bad("invalid V2 finish");
        packet=c.next;v2Records=c.targets;v2Plan=c.plan;v2Gate=c.gate;
        c.used=true;journal.complete=true;v2Pending=null;v2Open=true;c.gate.open=true;
    }
    void validateAttachedV2(Candidate c,AttachmentJournal journal){validateV2(c,true);if(journal!=c.journal||journal.complete)throw Json.bad("foreign V2 journal");}
    void rollbackV2(Candidate c,AttachmentJournal journal){
        NativeEnvironmentV2.requireMain();if(c==null||c.owner!=this||v2Pending!=c||c.used||journal!=c.journal||journal.complete)throw Json.bad("invalid V2 rollback");
        v2Open=false;c.gate.open=false;
        try{restoreV2(c);c.used=true;journal.complete=true;v2Pending=null;}
        catch(RuntimeException|java.lang.Error failure){retireV2();c.used=true;v2Pending=null;throw failure;}
    }
    void discardV2(Candidate c){NativeEnvironmentV2.requireMain();if(c==null||c.owner!=this||v2Pending!=c||c.used||c.attached)throw Json.bad("invalid V2 discard");c.used=true;v2Pending=null;}
    private void restoreV2(Candidate c){
        if(v2RollbackFault)throw new IllegalStateException("test-only rollback fault");
        for(NativeState state:c.journal.previous){var r=state.record;boolean preserve=state.active;r.bind(state.binding,state.geometry,preserve);
            if(!preserve&&r.view instanceof TextView text&&state.text!=null){r.changing=true;try{text.setText(state.text);
                if(text instanceof EditText edit&&state.selectionStart>=0)edit.setSelection(state.selectionStart,state.selectionEnd);}finally{r.changing=false;}}
        }
        for(NativeState state:c.journal.previous){var r=state.record;
            r.changing=true;try{if(r.view instanceof Switch value)value.setChecked(state.checked);r.view.setPressed(state.pressed);}finally{r.changing=false;}}
        for(ParentState parent:c.journal.parents)restoreParentV2(parent.parent,parent.children);
        for(var old:c.baseRecords.values())if(old.group!=null)old.group.records=c.baseRecords;
        restoreParentV2(c.environment.root(),c.journal.rootChildren);
        if(c.journal.oldGate!=null&&c.base!=null){var old=v2Records.get(c.base.root.id);
            NativeAppearanceViewsV2.layoutRoot(old,c.journal.rootWidth,c.journal.rootHeight,old.binding.plan().environment.safeArea64());}
        for(NativeState state:c.journal.previous)if(state.focused&&!state.record.view.hasFocus())state.record.view.requestFocus();
        for(NativeState state:c.journal.previous)if(state.record.view.getScrollX()!=state.scrollX||state.record.view.getScrollY()!=state.scrollY)
            state.record.view.scrollTo(state.scrollX,state.scrollY);
        v2Open=true;if(c.journal.oldGate!=null)c.journal.oldGate.open=true;
    }
    private static void restoreParentV2(ViewGroup parent,View[] children){
        for(int i=parent.getChildCount()-1;i>=0;i--)if(!Arrays.asList(children).contains(parent.getChildAt(i)))parent.removeViewAt(i);
        for(int i=0;i<children.length;i++){View view=children[i];if(i<parent.getChildCount()&&parent.getChildAt(i)==view)continue;
            if(view.getParent() instanceof ViewGroup previous)previous.removeView(view);parent.addView(view,i);}
    }
    void disposeV2(){NativeEnvironmentV2.requireMain();retireV2();if(v2Environment!=null)v2Environment.close();}
    void retireV2(){v2Retired=true;v2Open=false;if(v2Gate!=null)v2Gate.open=false;if(v2Pending!=null)v2Pending.gate.open=false;}
    private void requireV2Live(){if(v2Retired)throw Json.bad("V2 owner retired");}
    private void faultV2(){if(v2Fault>=0&&v2Steps++==v2Fault)throw new IllegalStateException("test-only V2 attachment fault");}
    // Package-private fault injection is confined to this concrete owner; it grants no native support authority.
    void testFaultV2(int attachmentStep,boolean rollback){v2Fault=attachmentStep;v2RollbackFault=rollback;}
    boolean testRetiredV2(){return v2Retired;}
    Map<String,NativeAppearanceViewsV2.Record> inspectV2(){NativeEnvironmentV2.requireMain();return v2Records;}

}
