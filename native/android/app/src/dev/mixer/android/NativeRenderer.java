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
    private final AndroidUIProfile v2Profile;private final Context context;private final Events events;private Map<String,Record>records=new HashMap<>();UiPacket packet;
    NativeRenderer(Context c,Events e){context=c;events=e;v2Fence=null;v2Profile=AndroidUIProfile.LEGACY_HORIZONTAL;}
    NativeRenderer(Context c,Events e,NativeEnvironmentV2.Observer observer,NativeOwnerV2.Fence fence){
        this(c,e,observer,fence,AndroidUIProfile.LEGACY_HORIZONTAL);
    }
    NativeRenderer(Context c,Events e,NativeEnvironmentV2.Observer observer,NativeOwnerV2.Fence fence,AndroidUIProfile profile){
        NativeEnvironmentV2.requireMain();v2Profile=Objects.requireNonNull(profile);context=Objects.requireNonNull(c);events=Objects.requireNonNull(e);
        v2Environment=Objects.requireNonNull(observer);v2Fence=Objects.requireNonNull(fence);
        if(observer.activity!=c)throw Json.bad("foreign V2 renderer context");
    }
    boolean belongsToV2(Context c,NativeEnvironmentV2.Observer observer){NativeEnvironmentV2.requireMain();return context==c&&v2Environment==observer&&v2Fence!=null;}

    private int dp(double value){return(int)Math.round(value*context.getResources().getDisplayMetrics().density);}
    View view(String id){if(v2Records.containsKey(id))return v2Records.get(id).view;Record r=records.get(id);if(r==null)throw Json.bad("missing native ID "+id);return r.view;}
    View apply(UiPacket next){
        if(android.os.Looper.myLooper()!=android.os.Looper.getMainLooper())throw new IllegalStateException("renderer requires UI thread");if(v2Pending!=null||v2Plan!=null||v2Installed!=null||v2Environment!=null)throw Json.bad("V2 owner cannot use legacy apply");next.requireSuccessor(packet);
        for(UiPacket.Node n:next.nodes.values())if(n.properties.containsKey("axis"))throw Json.bad("legacy renderer axis unsupported");
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
        v.setTooltipText(n.text("accessibilityHint",null));if(Build.VERSION.SDK_INT>=30)Api30.stateDescription(v,n.text("accessibilityValue",null));
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
    private static final class Api30 {
        static void stateDescription(View view,CharSequence value){view.setStateDescription(value);}
    }
    private int gravity(String a){switch(a){case "leading":return Gravity.START;case "trailing":return Gravity.END;case "top":return Gravity.TOP;case "bottom":return Gravity.BOTTOM;case "topLeading":return Gravity.TOP|Gravity.START;case "topTrailing":return Gravity.TOP|Gravity.END;case "bottomLeading":return Gravity.BOTTOM|Gravity.START;case "bottomTrailing":return Gravity.BOTTOM|Gravity.END;default:return Gravity.CENTER;}}
    private void children(Record r,UiPacket.Node n,Map<String,Record>candidate){
        ViewGroup parent=r.children;Set<View>desired=new HashSet<>();for(UiPacket.Node child:n.children)desired.add(candidate.get(child.id).view);for(int i=parent.getChildCount()-1;i>=0;i--)if(!desired.contains(parent.getChildAt(i)))parent.removeViewAt(i);
        for(int i=0;i<n.children.size();i++){View view=candidate.get(n.children.get(i).id).view;if(i>=parent.getChildCount()||parent.getChildAt(i)!=view){if(view.getParent()instanceof ViewGroup)((ViewGroup)view.getParent()).removeView(view);parent.addView(view,i);}
            if(parent instanceof FrameLayout){FrameLayout.LayoutParams lp=new FrameLayout.LayoutParams(-2,-2,gravity(n.text("alignment","center")));view.setLayoutParams(lp);}else{boolean horizontal=n.kind.equals("hStack");int height=n.kind.equals("navigation")?-1:-2;LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(horizontal?-2:-1,height);int spacing=dp(n.number("spacing",n.kind.equals("list")?8:0));if(i+1<n.children.size()){if(horizontal)lp.setMarginEnd(spacing);else lp.bottomMargin=spacing;}view.setLayoutParams(lp);}}
    }

    // Ordinary private V2 lane. Existing apply()/signed/V1 behavior is unchanged.
    private Map<String,NativeAppearanceViewsV2.Record> v2Records=Collections.emptyMap();
    private AppearanceResolverV2.Plan v2Plan;
    private byte[] v2PacketBytes;
    private InstalledAppearanceV2 v2Installed;
    private NativeEnvironmentV2.Observer v2Environment;
    private NativeEnvironmentV2 v2CommittedEnvironment;
    private NativeAppearanceViewsV2.Gate v2Gate;
    private Candidate v2Pending;
    private final NativeOwnerV2.Fence v2Fence;
    private boolean v2Open,v2Retired,v2ReportClaimed,v2Disposed;
    private long v2Interaction;
    private int v2Fault=-1,v2Steps;
    private boolean v2RollbackFault;
    private NativeAppearanceViewsV2.Input v2Input;
    private NativeAppearanceViewsV2.Mutation v2Mutation;
    private NativeAppearanceViewsV2.Record[] v2Roster=new NativeAppearanceViewsV2.Record[4096];
    private int v2RosterCount;
    private int outstandingEditorNativeCalls,outstandingFieldPreservations;
    private int outstandingFieldTransitions;
    private boolean nativeInstallFailure;
    private NativeAppearanceViewsV2.EditorLease editorDrain,editorFinishing;
    private NativeAppearanceViewsV2.Replacement editorReplacement;
    private long editorLossSerial;
    private NativeAppearanceViewsV2.Record lastEditorLossRecord;
    boolean editorDisposalBusyV2(){NativeEnvironmentV2.requireMain();return outstandingEditorNativeCalls!=0||outstandingFieldPreservations!=0||editorDrain!=null||editorFinishing!=null||editorReplacement!=null;}
    private boolean retainedEditorV2(NativeAppearanceViewsV2.Record record) {
        if(record==null)return false;
        for(int i=0;i<v2RosterCount;i++)if(v2Roster[i]==record)return true;
        Candidate pending=v2Pending;
        if(pending!=null){for(int i=0;i<pending.targetCount;i++)if(pending.targetRoster[i]==record)return true;
            for(int i=0;i<pending.detachedCount;i++)if(pending.detachedRoster[i]==record)return true;}
        return false;
    }
    private void requireEditorsAvailableV2(){
        for(int i=0;i<v2RosterCount;i++)if(v2Roster[i]!=null)v2Roster[i].editorAvailable(true);
        Candidate pending=v2Pending;
        if(pending!=null){for(int i=0;i<pending.targetCount;i++)if(pending.targetRoster[i]!=null)pending.targetRoster[i].editorAvailable(true);
            for(int i=0;i<pending.detachedCount;i++)if(pending.detachedRoster[i]!=null)pending.detachedRoster[i].editorAvailable(true);}
    }
    private void retireEditorsV2(){
        NativeAppearanceViewsV2.Record[] current=v2Roster;int count=v2RosterCount;Candidate pending=v2Pending;
        retireEditorRosterV2(current,count);
        if(pending!=null){retireEditorRosterV2(pending.targetRoster,pending.targetCount);retireEditorRosterV2(pending.detachedRoster,pending.detachedCount);}
    }
    private void retireEditorRosterV2(NativeAppearanceViewsV2.Record[] records,int count){
        for(int i=0;i<count;i++)if(records[i]!=null)try{records[i].retireEditor();}catch(RuntimeException|java.lang.Error failure){rememberV2(failure);}
    }
    static final class CleanupLedger {
        private Throwable primary;
        private Error firstFatal;
        private long consumedSerial,requestedSerial,pass;
        private int attempts;
        private boolean inProgress;
        private NativeEnvironmentV2.RendererCause cause,deferredCause;
        Throwable primary(){NativeEnvironmentV2.requireMain();return primary;}
        Error firstFatal(){NativeEnvironmentV2.requireMain();return firstFatal;}
        long consumedSerial(){NativeEnvironmentV2.requireMain();return consumedSerial;}
        int attempts(){NativeEnvironmentV2.requireMain();return attempts;}
        boolean inProgress(){NativeEnvironmentV2.requireMain();return inProgress;}
    }
    private final CleanupLedger v2Cleanup=new CleanupLedger();
    CleanupLedger cleanupLedger(){NativeEnvironmentV2.requireMain();return v2Cleanup;}
    NativeAppearanceViewsV2.Mutation mutationV2(){
        NativeEnvironmentV2.requireMain();
        if(v2Mutation!=null)return v2Mutation;
        return NativeAppearanceViewsV2.Mutation.live(v2Fence);
    }
    boolean drawAllowedV2(){return v2Fence!=null&&!v2Fence.terminal&&v2Fence.drawAllowed;}
    private NativeAppearanceViewsV2.Input inputV2(){if(v2Input==null)v2Input=new NativeAppearanceViewsV2.Input(){
        public NativeAppearanceViewsV2.Mutation mutation(){return mutationV2();}
        public boolean editorDispatchAvailable(NativeAppearanceViewsV2.Record record){NativeEnvironmentV2.requireMain();return editorReplacement==null&&retainedEditorV2(record);}
        public boolean editorRetained(NativeAppearanceViewsV2.Record record){NativeEnvironmentV2.requireMain();return retainedEditorV2(record);}
        public long editorLossObservation(){
            NativeEnvironmentV2.requireMain();
            if(editorLossSerial==Long.MAX_VALUE){IllegalStateException failure=new IllegalStateException("editor loss observation exhausted");terminalV2(NativeEnvironmentV2.RendererCause.CANCELLATION_FAILED,failure,null);throw failure;}
            return editorLossSerial;
        }
        public void editorLossObserved(NativeAppearanceViewsV2.Record record){
            NativeEnvironmentV2.requireMain();
            if(record==null||record.editorFence!=v2Fence||!(record.view instanceof NativeAppearanceViewsV2.NativeField)||
                !retainedEditorV2(record)&&!record.editorConstruction()||!capturedLossSuffixV2(record))throw Json.bad("foreign editor loss observation");
            if(editorLossSerial==Long.MAX_VALUE){IllegalStateException failure=new IllegalStateException("editor loss observation exhausted");terminalV2(NativeEnvironmentV2.RendererCause.CANCELLATION_FAILED,failure,null);throw failure;}
            editorLossSerial++;lastEditorLossRecord=record;
            if(editorReplacement!=null)editorReplacement.lost=true;
            if(editorLossSerial==Long.MAX_VALUE){IllegalStateException failure=new IllegalStateException("editor loss observation exhausted");terminalV2(NativeEnvironmentV2.RendererCause.CANCELLATION_FAILED,failure,null);throw failure;}
        }
        public void fieldPreservationBegin(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.FieldPreservation preservation){
            NativeEnvironmentV2.requireMain();
            if(preservation==null||record==null||record.input!=this||!fieldPreservationIdentityV2(preservation.candidate,preservation.journal,record,preservation)||
                record.fieldPreservation!=preservation||preservation.entered||preservation.ended||preservation.counted||preservation.released||
                preservation.phase!=NativeAppearanceViewsV2.FieldPreservation.CAPTURED||preservation.callbacks!=0||!preservation.hooks.isEmpty()||preservation.checking||
                !retainedEditorV2(record)||!preservation.field.needsFieldPreservation()||record.editorCallbackLease!=null||editorReplacement!=null||editorDrain!=null||editorFinishing!=null||v2Fence.commitFinish||
                !preservation.original.current()||!fieldPreservationCurrent(preservation.candidate,preservation.journal,record,preservation)||
                outstandingEditorNativeCalls<0||outstandingEditorNativeCalls==Integer.MAX_VALUE||!preservationCohortV2(preservation.candidate)||
                preservation.candidate.heldPreservations>=preservation.journal.stateCount)
                throw Json.bad("invalid field preservation entry");
            // All callable validation/refusal precedes this nonthrowing scalar acquisition tail.
            preservation.entered=true;preservation.counted=true;preservation.phase=NativeAppearanceViewsV2.FieldPreservation.ATTACHING;
            preservation.candidate.heldPreservations++;outstandingFieldPreservations++;outstandingEditorNativeCalls++;
        }
        public void fieldPreservationEnd(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.FieldPreservation preservation){
            NativeEnvironmentV2.requireMain();
            if(preservation==null||record==null||record.input!=this||!fieldPreservationIdentityV2(preservation.candidate,preservation.journal,record,preservation)||
                !preservationEndReadyV2(preservation)||!preservationCohortV2(preservation.candidate)||outstandingEditorNativeCalls<preservation.candidate.heldPreservations)
                throw Json.bad("unfinished field preservation");
            preservation.counted=false;preservation.released=true;preservation.phase=NativeAppearanceViewsV2.FieldPreservation.RELEASED;
            preservation.candidate.heldPreservations--;outstandingFieldPreservations--;outstandingEditorNativeCalls--;
        }
        public void replacementEvent(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Replacement replacement){
            NativeEnvironmentV2.requireMain();
            // Scalar exact provenance precedes the no-call same-operation exclusion.
            if(replacement==null||record==null||replacement.record!=record||record.input!=this||record.view!=replacement.field||replacement.field.record!=record||
                !replacement.completed||replacement.eventValue==null||replacement.stage!=NativeAppearanceViewsV2.Replacement.Stage.DONE||!replacement.endReady()||
                replacement.original.fence!=v2Fence||replacement.original.editorLease!=null||replacement.original.replacementLease!=null||replacement.original.fieldLease!=null)
                throw Json.bad("invalid completed replacement provenance");
            if(replacement.eventEvaluating||replacement.eventClaimed)return;
            replacement.eventEvaluating=true;
            try{
                if(editorReplacement!=null||!replacement.field.completedReplacementEligible(replacement))throw Json.bad("invalid completed replacement event");
                if(!open(record)||editorReplacement!=null||!replacement.field.completedReplacementEligible(replacement))throw Json.bad("replacement event authority changed after getter");
                replacement.eventClaimed=true;
            }finally{replacement.eventEvaluating=false;}
            interaction();
            if(v2Fence.terminal||!replacement.original.current()||!replacement.unchangedLoss())throw Json.bad("replacement event interaction unavailable");
            events.send(packet.event(record.id,record.generation,"textChange",replacement.eventValue));
            // Delivery completed. No native observation or continuation postcheck here.
        }
        public void editorEnter(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
            NativeEnvironmentV2.requireMain();
            if(lease==null||lease.record!=record||record.view!=lease.field||!retainedEditorV2(record)||lease.entered||lease.ended||outstandingEditorNativeCalls==Integer.MAX_VALUE)
                throw Json.bad("invalid editor native lease entry");
            outstandingEditorNativeCalls++;
        }
        public void editorLeave(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
            NativeEnvironmentV2.requireMain();
            if(lease==null||lease.record!=record||!lease.entered||!lease.ended||outstandingEditorNativeCalls<=0)
                throw Json.bad("invalid editor native lease exit");
            outstandingEditorNativeCalls--;
        }
        public boolean editorCloseAllowed(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.NativeField.Attempt attempt){
            NativeEnvironmentV2.requireMain();return outstandingEditorNativeCalls==0&&!v2Fence.commitFinish&&v2Fence.operation==null&&
                (editorReplacement==null||editorReplacement.permitsPredecessor(record,attempt));
        }
        public void replacementBegin(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Replacement replacement){
            NativeEnvironmentV2.requireMain();
            if(editorReplacement!=null||outstandingEditorNativeCalls!=0||editorDrain!=null||editorFinishing!=null||v2Fence.commitFinish||v2Fence.operation!=null||
                replacement==null||replacement.record!=record||record.view!=replacement.field||!retainedEditorV2(record))throw Json.bad("replacement reservation unavailable");
            editorReplacement=replacement;
        }
        public void replacementEnd(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Replacement replacement){
            NativeEnvironmentV2.requireMain();
            if(editorReplacement!=replacement||replacement.record!=record||replacement.nativeExecuting||replacement.setterActive||replacement.callbacks!=0||
                record.replacementCallback!=null||replacement.stage!=NativeAppearanceViewsV2.Replacement.Stage.DONE||!replacement.endReady()||outstandingEditorNativeCalls!=0||editorDrain!=null||editorFinishing!=null)throw Json.bad("unfinished replacement reservation");
            editorReplacement=null;
        }
        public NativeAppearanceViewsV2.Mutation editorCleanupMutation(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
            NativeEnvironmentV2.requireMain();
            if(lease==null||lease.record!=record||record.editorCallbackLease!=lease)throw Json.bad("foreign editor cleanup continuation");
            lease.exact();NativeAppearanceViewsV2.Mutation scope=NativeAppearanceViewsV2.Mutation.editorCleanup(v2Fence,lease);scope.require();return scope;
        }
        public void editorFinishBegin(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
            NativeEnvironmentV2.requireMain();
            if(editorFinishing!=null||lease==null||lease.record!=record||!lease.hook.equals("create")||record.editorCallbackLease!=lease||!lease.entered||lease.ended)
                throw Json.bad("invalid creator finishing guard");
            // Keep already-entered exact creator custody even if its final postcheck is uncertain.
            editorFinishing=lease;
        }
        public void editorFinishEnd(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
            NativeEnvironmentV2.requireMain();
            if(editorFinishing!=lease||lease.record!=record)throw Json.bad("unbalanced creator finishing guard");
            editorFinishing=null;
        }
        public void editorDrainBegin(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
            NativeEnvironmentV2.requireMain();
            if(editorDrain!=null||lease==null||!editorCloseAllowed(record,lease.attempt)||lease.record!=record||record.view!=lease.field||!retainedEditorV2(record))throw Json.bad("editor cleanup unavailable");
            editorDrain=lease;
        }
        public void editorDrainEnd(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
            NativeEnvironmentV2.requireMain();
            if(editorDrain!=lease||lease.record!=record)throw Json.bad("unbalanced editor cleanup");
            editorDrain=null;
        }
        public void editorFailure(Throwable primary,java.lang.Error fatal){NativeEnvironmentV2.requireMain();terminalV2(NativeEnvironmentV2.RendererCause.CANCELLATION_FAILED,primary,fatal);}
        public boolean draw(){return presentationCurrentV2();}
        public boolean open(NativeAppearanceViewsV2.Record record){
            NativeEnvironmentV2.requireMain();
            if(v2Fence.terminal||!v2Fence.inputAllowed)return false;
            OwnerLifecycleV2.Token presentation=v2Fence.presentation;
            try{
                boolean open=presentationCurrentV2()&&v2Records.get(record.id)==record&&record.view.isEnabled()&&
                    record.view.isAttachedToWindow()&&record.view.isShown()&&record.view.hasWindowFocus();
                return open&&!v2Fence.terminal&&v2Fence.inputAllowed&&presentation!=null&&presentation==v2Fence.presentation;
            }catch(java.lang.Error fatal){terminalV2(NativeEnvironmentV2.RendererCause.CURRENT_CHECK_FATAL,fatal,fatal);throw fatal;}
        }
        public void event(NativeAppearanceViewsV2.Record record,String name,Object value){
            if(!record.editorEventsAllowed()||!open(record))return;interaction();if(record.editorEventsAllowed()&&open(record))events.send(packet.event(record.id,record.generation,name,value));
        }
        public void interaction(){NativeEnvironmentV2.requireMain();if(!v2Fence.inputAllowed||v2Fence.terminal||!v2Open)return;
            if(v2Interaction==Long.MAX_VALUE){terminalV2(NativeEnvironmentV2.RendererCause.INTERACTION_EXHAUSTED,null,null);return;}v2Interaction++;}
    };return v2Input;}
    private static boolean lossHookV2(String hook){return hook.equals("focus")||hook.equals("windowFocus")||hook.equals("windowVisibility")||hook.equals("aggregate")||hook.equals("visibility")||hook.equals("detach");}
    private boolean capturedLossSuffixV2(NativeAppearanceViewsV2.Record record){
        if(record.editorConstruction())return true;
        var lease=record.editorCallbackLease;
        if(lease!=null&&lease.record==record&&lease.field==record.view&&lease.entered&&!lease.ended&&lossHookV2(lease.hook))return true;
        var replacement=record.replacementCallback;
        if(replacement!=null&&replacement==editorReplacement&&replacement.record==record&&replacement.nativeExecuting&&replacement.tuple())return true;
        var transition=record.fieldTransition;
        if(transition!=null&&transition.record==record&&transition.registered&&!transition.ended&&!transition.hooks.isEmpty()&&lossHookV2(transition.hooks.peek())&&fieldTransitionIdentity(transition.candidate,transition.journal,record,transition))return true;
        var field=record.fieldPreservation;
        return field!=null&&field.record==record&&field.entered&&field.counted&&!field.ended&&field.callbacks>0&&!field.hooks.isEmpty()&&lossHookV2(field.hooks.peek())&&fieldPreservationIdentityV2(field.candidate,field.journal,record,field);
    }
    InstalledAppearanceV2 captureInstalledV2(){
        NativeEnvironmentV2.requireMain();requireEditorsAvailableV2();requireV2Live();
        OwnerLifecycleV2.Token operation=v2Fence.operation;requireTransactionV2(operation);
        try{InstalledAppearanceV2 capture=InstalledAppearanceV2.capture(context,this);requireTransactionV2(operation);
            v2Installed=capture;return capture;
        }catch(RuntimeException|java.lang.Error failure){terminalV2(NativeEnvironmentV2.RendererCause.CAPTURE_FAILED,failure,failure instanceof java.lang.Error fatal?fatal:null);throw failure;}
    }
    NativeEnvironmentV2 captureEnvironmentV2(android.app.Activity activity,FrameLayout root){
        NativeEnvironmentV2.requireMain();requireEditorsAvailableV2();requireV2Live();
        if(v2Environment.activity!=activity||v2Environment.root!=root)throw Json.bad("foreign V2 window");
        OwnerLifecycleV2.Token operation=v2Fence.operation;requireTransactionV2(operation);
        try{NativeEnvironmentV2 capture=v2Environment.capture();requireTransactionV2(operation);return capture;}catch(RuntimeException|java.lang.Error failure){terminalV2(NativeEnvironmentV2.RendererCause.CAPTURE_FAILED,failure,failure instanceof java.lang.Error fatal?fatal:null);throw failure;}
    }
    void sealScalarV2(){v2Open=false;if(v2Gate!=null)v2Gate.open=false;if(v2Pending!=null)v2Pending.gate.open=false;}
    /** Trusted owner publication after actual clean core completion; no native work or capture. */
    void publishScalarV2(OwnerLifecycleV2.Token presentation){
        if(v2Fence==null||v2Fence.terminal||v2Fence.commitFinish||v2Retired||v2Disposed||
            !v2Fence.drawAllowed||presentation==null||presentation!=v2Fence.presentation||
            v2Gate==null||v2Pending!=null||packet==null||v2CommittedEnvironment==null)
            throw Json.bad("invalid V2 presentation publication");
        v2Open=true;v2Gate.open=true;
    }
    void environmentInvalidatedV2(){NativeEnvironmentV2.requireMain();sealScalarV2();if(v2Environment!=null)v2Environment.invalidate();}
    boolean presentationCurrentV2(){
        NativeEnvironmentV2.requireMain();if(v2Fence==null||v2Fence.terminal||!v2Fence.drawAllowed||!v2Open||v2Retired)return false;
        try{
            if(v2CommittedEnvironment==null||!v2CommittedEnvironment.current(this)){
                v2Fence.drawAllowed=false;v2Fence.inputAllowed=false;sealScalarV2();v2Environment.invalidate();return false;}
            return !v2Fence.terminal&&v2Fence.drawAllowed;
        }catch(java.lang.Error fatal){terminalV2(NativeEnvironmentV2.RendererCause.CURRENT_CHECK_FATAL,fatal,fatal);throw fatal;}
    }
    private void requireTransactionV2(OwnerLifecycleV2.Token operation){
        if(v2Fence==null||v2Fence.terminal||operation==null||operation!=v2Fence.operation)throw Json.bad("V2 transaction authority lost");
    }
    static final class Candidate {
        private final NativeRenderer owner;
        private final UiPacket base,next;
        private final byte[] bytes;
        private final Map<String,NativeAppearanceViewsV2.Record> baseRecords,targets,detached;
        private final AppearanceResolverV2.Plan plan;
        private final InstalledAppearanceV2 installed;
        private final NativeEnvironmentV2 environment;
        private final long interaction;
        private final OwnerLifecycleV2.Token operation;
        private final NativeAppearanceViewsV2.Record[] targetRoster,detachedRoster;
        private final int targetCount,detachedCount;
        private final NativeAppearanceViewsV2.Gate gate;
        private final AttachmentJournal journal;
        private NativeAppearanceViewsV2.Mutation originalMutation;
        private int heldPreservations;
        private boolean used,attached,nativeAttachStarted;
        private Candidate(NativeRenderer owner,UiPacket next,byte[] bytes,Map<String,NativeAppearanceViewsV2.Record> targets,
                          Map<String,NativeAppearanceViewsV2.Record> detached,AppearanceResolverV2.Plan plan,
                          InstalledAppearanceV2 installed,NativeEnvironmentV2 environment,NativeAppearanceViewsV2.Gate gate){
            this.owner=owner;this.base=owner.packet;this.next=next;this.bytes=bytes;this.baseRecords=owner.v2Records;
            this.targets=targets;this.detached=detached;this.plan=plan;this.installed=installed;
            this.environment=environment;this.interaction=owner.v2Interaction;this.gate=gate;
            operation=owner.v2Fence.operation;
            targetRoster=targets.values().toArray(new NativeAppearanceViewsV2.Record[4096]);targetCount=targets.size();
            detachedRoster=detached.values().toArray(new NativeAppearanceViewsV2.Record[4096]);detachedCount=detached.size();
            journal=new AttachmentJournal(this);
        }
    }
    static final class AttachmentJournal {
        private final Candidate candidate;
        private final List<NativeState> previous;
        private final List<ParentState> parents;
        private final View[] rootChildren;
        private final NativeAppearanceViewsV2.Gate oldGate;
        private final int rootWidth,rootHeight,oldCanvas;
        static final int OPEN=0,SUCCESS_IN_PROGRESS=1,SUCCESS_DONE=2,FAILED_IN_PROGRESS=3,FAILED_DONE=4;
        private final NativeState[] states;private final int stateCount;
        private int completion=OPEN;private boolean failedInvoked;
        private final TransitionMembership[] transitionRoster;
        private boolean transitionsStarted,transitionsSealed;private int transitionCount;private long transitionLoss;
        private boolean complete;
        private AttachmentJournal(Candidate candidate){
            this.candidate=candidate;previous=new ArrayList<>();parents=new ArrayList<>();
            for(var record:candidate.baseRecords.values()){
                previous.add(new NativeState(this,previous.size(),record));
                if(record.group!=null)parents.add(new ParentState(record.group));
            }
            states=previous.toArray(new NativeState[previous.size()]);stateCount=states.length;
            transitionRoster=new TransitionMembership[stateCount];
            FrameLayout root=candidate.environment.root();rootChildren=childrenV2(root);
            rootWidth=root.getWidth();rootHeight=root.getHeight();oldGate=candidate.owner.v2Gate;oldCanvas=oldGate==null?0:oldGate.canvasColor;if(oldGate!=null)parents.add(new ParentState(oldGate));
        }
    }
    private enum FieldUpdateV3 { ORDINARY, PRESERVE, HANDOFF, RETIRE, SETTLED }
    private static final class NativeState {
        final AttachmentJournal journal;final int position;
        final NativeAppearanceViewsV2.Record record;
        final NativeAppearanceViewsV2.Binding binding;
        final NativeAppearanceViewsV2.Geometry geometry;
        final FieldUpdateV3 update;
        final NativeAppearanceViewsV2.NativeField.Attempt predecessor;
        final CharSequence text,nativeBuffer;
        final List<CompositionSpan> composition;
        final int[] drawableState,windowPosition;
        final int left,top,right,bottom,measuredWidth,measuredHeight;
        final boolean enabled;
        final int selectionStart,selectionEnd,scrollX,scrollY;final boolean active,checked,focused,pressed;
        boolean forwardPreserved;
        NativeAppearanceViewsV2.FieldPreservation preservation;
        NativeAppearanceViewsV2.FieldTransition transition;
        private TransitionMembership transitionMembership;
        private PreservationMembership membership;
        NativeState(AttachmentJournal journal,int position,NativeAppearanceViewsV2.Record record){
            this.journal=journal;this.position=position;this.record=record;binding=record.binding;geometry=record.geometry;active=record.view instanceof EditText e&&(e.hasFocus()||android.view.inputmethod.BaseInputConnection.getComposingSpanStart(e.getText())>=0)||record.view instanceof TextView t&&t.isTextSelectable()&&t.getSelectionStart()>=0;
            nativeBuffer=record.view instanceof TextView t?t.getText():null;
            // Copy only text value. Copying native watcher spans can notify the live editor.
            text=nativeBuffer==null?null:nativeBuffer.toString();
            composition=compositionV2(nativeBuffer);
            drawableState=record.view.getDrawableState().clone();windowPosition=new int[2];record.view.getLocationInWindow(windowPosition);
            left=record.view.getLeft();top=record.view.getTop();right=record.view.getRight();bottom=record.view.getBottom();
            measuredWidth=record.view.getMeasuredWidth();measuredHeight=record.view.getMeasuredHeight();enabled=record.view.isEnabled();
            selectionStart=record.view instanceof TextView t?t.getSelectionStart():-1;
            selectionEnd=record.view instanceof TextView t?t.getSelectionEnd():-1;
            scrollX=record.view.getScrollX();scrollY=record.view.getScrollY();checked=record.view instanceof Switch value&&value.isChecked();focused=record.view.hasFocus();pressed=record.view.isPressed();
            predecessor=record.view instanceof NativeAppearanceViewsV2.NativeField field?field.attempt:null;
            update=journal.candidate.owner.fieldUpdateV3(journal.candidate,record);
        }
    }
    /** Captured once before Begin, so replacing a mutable scope slot cannot grant custody. */
    private static final class PreservationMembership {
        final NativeState state;final NativeAppearanceViewsV2.FieldPreservation scope;
        PreservationMembership(NativeState state,NativeAppearanceViewsV2.FieldPreservation scope){this.state=state;this.scope=scope;}
    }
    private static final class TransitionMembership {
        final NativeState state;final NativeAppearanceViewsV2.FieldTransition scope;
        private boolean focusLossClaimed,detachLossClaimed;
        TransitionMembership(NativeState state,NativeAppearanceViewsV2.FieldTransition scope){this.state=state;this.scope=scope;}
    }
    private record CompositionSpan(Object object,int start,int end,int flags) {}
    private static List<CompositionSpan> compositionV2(CharSequence value){
        List<CompositionSpan> result=new ArrayList<>();
        if(value instanceof android.text.Spanned spans)for(Object span:spans.getSpans(0,spans.length(),Object.class)){
            int flags=spans.getSpanFlags(span);if((flags&android.text.Spanned.SPAN_COMPOSING)!=0)
                result.add(new CompositionSpan(span,spans.getSpanStart(span),spans.getSpanEnd(span),flags));
        }return result;
    }
    private static boolean sameNativeBaseV2(NativeState state){
        var record=state.record;View view=record.view;int[] position=new int[2];view.getLocationInWindow(position);
        if(record.binding!=state.binding||record.geometry!=state.geometry||view.isEnabled()!=state.enabled||view.hasFocus()!=state.focused||view.isPressed()!=state.pressed||
            view.getLeft()!=state.left||view.getTop()!=state.top||view.getRight()!=state.right||view.getBottom()!=state.bottom||
            view.getMeasuredWidth()!=state.measuredWidth||view.getMeasuredHeight()!=state.measuredHeight||
            view.getScrollX()!=state.scrollX||view.getScrollY()!=state.scrollY||!Arrays.equals(position,state.windowPosition)||!Arrays.equals(view.getDrawableState(),state.drawableState))return false;
        if(view instanceof NativeAppearanceViewsV2.NativeField field&&field.attempt!=state.predecessor)return false;
        if(view instanceof Switch toggle&&toggle.isChecked()!=state.checked)return false;
        if(view instanceof TextView text){
            if(text.getText()!=state.nativeBuffer||!text.getText().toString().contentEquals(state.text)||
                text.getSelectionStart()!=state.selectionStart||text.getSelectionEnd()!=state.selectionEnd)return false;
            List<CompositionSpan> current=compositionV2(text.getText());if(current.size()!=state.composition.size())return false;
            for(int i=0;i<current.size();i++){CompositionSpan a=current.get(i),b=state.composition.get(i);
                if(a.object()!=b.object()||a.start()!=b.start()||a.end()!=b.end()||a.flags()!=b.flags())return false;}
        }return true;
    }
    private static boolean sameNativeBaseV2(AttachmentJournal journal){
        if(!Arrays.equals(childrenV2(journal.candidate.environment.root()),journal.rootChildren))throw Json.bad("stale native root membership");
        for(ParentState parent:journal.parents)if(!Arrays.equals(childrenV2(parent.parent),parent.children))throw Json.bad("stale native parent membership");
        for(NativeState state:journal.previous)if(!sameNativeBaseV2(state))throw Json.bad("stale native snapshot: "+state.record.id+" "+snapshotDifferenceV2(state));
        return journal.oldGate==null||journal.oldGate.canvasColor==journal.oldCanvas;
    }
    private static String snapshotDifferenceV2(NativeState state){
        var r=state.record;View v=r.view;int[] p=new int[2];v.getLocationInWindow(p);
        return "binding="+(r.binding==state.binding)+",geometry="+(r.geometry==state.geometry)+",enabled="+(v.isEnabled()==state.enabled)+
            ",focus="+(v.hasFocus()==state.focused)+",pressed="+(v.isPressed()==state.pressed)+",frame="+(v.getLeft()==state.left&&v.getTop()==state.top&&v.getRight()==state.right&&v.getBottom()==state.bottom)+
            ",measure="+(v.getMeasuredWidth()==state.measuredWidth&&v.getMeasuredHeight()==state.measuredHeight)+",scroll="+(v.getScrollX()==state.scrollX&&v.getScrollY()==state.scrollY)+
            ",position="+Arrays.equals(p,state.windowPosition)+",drawable="+Arrays.equals(v.getDrawableState(),state.drawableState)+
            (v instanceof TextView t?",buffer="+(t.getText()==state.nativeBuffer)+",text="+t.getText().toString().contentEquals(state.text)+",selection="+(t.getSelectionStart()==state.selectionStart&&t.getSelectionEnd()==state.selectionEnd):"");
    }
    private record ParentState(ViewGroup parent,View[] children) {
        ParentState(ViewGroup parent){this(parent,childrenV2(parent));}
    }
    private static View[] childrenV2(ViewGroup parent){View[] result=new View[parent.getChildCount()];for(int i=0;i<result.length;i++)result[i]=parent.getChildAt(i);return result;}
    Candidate prepareV2(byte[] bytes,InstalledAppearanceV2 installed,NativeEnvironmentV2 environment){
        NativeEnvironmentV2.requireMain();requireEditorsAvailableV2();requireV2Live();
        OwnerLifecycleV2.Token operation=v2Fence.operation;requireTransactionV2(operation);
        NativeAppearanceViewsV2.Mutation previousMutation=v2Mutation;
        v2Mutation=NativeAppearanceViewsV2.Mutation.transaction(v2Fence,operation);
        NativeAppearanceViewsV2.Mutation mutation=v2Mutation;
        try {
        if(v2Pending!=null)throw Json.bad("V2 candidate already pending");
        if(installed==null||installed!=v2Installed||!installed.belongsTo(this)||environment==null||!environment.current(this))throw Json.bad("stale/foreign V2 capture");
        if(bytes==null||bytes.length>1048576)throw Json.bad("V2 packet byte limit");byte[] owned=bytes.clone();UiPacket next=UiPacket.decode(owned,v2Profile);
        boolean environmentOnly=v2Plan!=null&&Arrays.equals(owned,v2PacketBytes);
        if(environmentOnly)next=packet;else next.requireSuccessor(packet);
        AppearanceResolverV2.Plan plan=AppearanceResolverV2.prepare(owned,installed.descriptorCopy(),environment.value,AppearanceResolverV2.Platform.android,v2Profile);
        for(var node:plan.nodes)NativeAppearanceViewsV2.requireViewOperations(node,next.nodes.get(node.identity().id()));
        for(var node:plan.nodes)if(node.recipe() instanceof AppearanceResolverV2.ButtonRecipe||node.recipe() instanceof AppearanceResolverV2.FieldRecipe||node.recipe() instanceof AppearanceResolverV2.ToggleRecipe){
            String ancestor=parentV2(next,node.identity().id());while(ancestor!=null){if(plan.node(ancestor).rowPlacement()!=null)throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);ancestor=parentV2(next,ancestor);}}
        for(var node:plan.nodes)if(node.recipe() instanceof AppearanceResolverV2.NavigationRecipe){UiPacket.Node child=next.nodes.get(node.childIDs().get(0));
            if(!child.kind.equals("list")&&containsKindV2(child,"list"))throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);}
        for(var old:v2Records.values()) {
            UiPacket.Node source=next.nodes.get(old.id);
            if(source!=null&&source.kind.equals("textField")&&old.kind.equals(source.kind)&&old.generation.equals(source.generation)&&
                !old.binding.source().text("axis","horizontal").equals(source.text("axis","horizontal")))
                throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);
        }
        preflightEditorPlanV2(next,plan,installed);
        Map<String,NativeAppearanceViewsV2.Record> detached=new LinkedHashMap<>(),targets=new LinkedHashMap<>();
        for(var node:plan.nodes){UiPacket.Node source=next.nodes.get(node.identity().id());
            NativeAppearanceViewsV2.Record shadow=new NativeAppearanceViewsV2.Record(context,source,inputV2(),mutation);mutation.require();

            NativeAppearanceViewsV2.Geometry geometry=new NativeAppearanceViewsV2.Geometry();
            var old=v2Records.get(source.id);var binding=new NativeAppearanceViewsV2.Binding(plan,node,source,installed.configuration.android);
            if(environmentOnly&&old!=null)binding=new NativeAppearanceViewsV2.Binding(plan,node,source,installed.configuration.android,
                old.view instanceof EditText editor?editor.getText().toString():binding.nativeFieldValue(),
                old.view instanceof Switch toggle?Boolean.valueOf(toggle.isChecked()):binding.nativeToggleValue());
            shadow.bind(binding,geometry,false,mutation);
            detached.put(source.id,shadow);
            if(old!=null)shadow.preparedScrollY=old.view.getScrollY();targets.put(source.id,old!=null&&old.kind.equals(source.kind)&&old.generation.equals(source.generation)?old:shadow);
        }
        for(var record:detached.values())NativeAppearanceViewsV2.installChildren(record,detached,mutation);
        var safe=environment.value.safeArea64();long width=environment.value.viewport().width64()-safe.leading()-safe.trailing();
        long height=environment.value.viewport().height64()-safe.top()-safe.bottom();
        NativeAppearanceViewsV2.measure(detached.get(next.root.id),detached,width,height,mutation);mutation.require();

        NativeAppearanceViewsV2.layoutRoot(detached.get(next.root.id),environment.width,environment.height,safe,mutation);
        NativeAppearanceViewsV2.Gate gate=v2Gate==null?new NativeAppearanceViewsV2.Gate(context,this):v2Gate;
        Candidate candidate=new Candidate(this,next,owned,Collections.unmodifiableMap(targets),Collections.unmodifiableMap(detached),plan,installed,environment,gate);
        preflightEditorsV2(candidate);
        requireTransactionV2(operation);v2Pending=candidate;return candidate;
        }finally{v2Mutation=previousMutation;}
    }
    /** Reject incompatible retained connection preparation before shadow View construction. */
    private void preflightEditorPlanV2(UiPacket next,AppearanceResolverV2.Plan plan,InstalledAppearanceV2 installed){
        for(int i=0;i<v2RosterCount;i++){
            var old=v2Roster[i];
            if(old==null||!(old.view instanceof NativeAppearanceViewsV2.NativeField field))continue;
            UiPacket.Node source=next.nodes.get(old.id);
            if(v2Profile.retirement()&&source==null){
                if(frameRetirementV3(old,null))continue;
                throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);
            }
            if(!field.hasLiveTarget())continue;
            if(frameRetirementV3(old,source))continue;
            if(source==null||!source.kind.equals(old.kind)||!source.generation.equals(old.generation))
                throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);
            var proposed=plan.node(old.id);var a=old.binding;
            if(!(a.node().recipe() instanceof AppearanceResolverV2.FieldRecipe before)||!(proposed.recipe() instanceof AppearanceResolverV2.FieldRecipe after))
                throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);
            Map<String,Object> left=new HashMap<>(a.source().properties),right=new HashMap<>(source.properties);left.remove("value");right.remove("value");
            boolean disabling=modelHandoffValueV3(old,source);
            if(disabling){left.remove("disabled");right.remove("disabled");}
            boolean same=before.label().equals(after.label())&&before.metrics().equals(after.metrics())&&before.text().role()==after.text().role()&&
                before.text().metrics().equals(after.text().metrics())&&before.text().selectable()==after.text().selectable()&&
                Objects.equals(before.text().maximumLines(),after.text().maximumLines())&&(disabling||a.node().disabled()==proposed.disabled())&&left.equals(right)&&
                a.source().actions.equals(source.actions)&&a.plan().environment.scheme()==plan.environment.scheme()&&a.plan().environment.profile()==plan.environment.profile()&&
                a.plan().environment.direction()==plan.environment.direction()&&a.plan().environment.density1024()==plan.environment.density1024()&&
                a.plan().environment.localeIdentifier().equals(plan.environment.localeIdentifier())&&a.theme().equals(installed.configuration.android);
            String current=old.id;
            while(same&&current!=null){String beforeParent=parentV2(packet,current),afterParent=parentV2(next,current);same=Objects.equals(beforeParent,afterParent);
                if(beforeParent!=null){UiPacket.Node beforeNode=packet.nodes.get(beforeParent),afterNode=next.nodes.get(afterParent);
                    same=same&&afterNode!=null&&beforeNode.kind.equals(afterNode.kind)&&beforeNode.generation.equals(afterNode.generation);
                    if(v2Profile.retirement()){
                        // Sibling reconciliation requires the complete measured candidate below.
                        same=same&&beforeNode.properties.equals(afterNode.properties)&&beforeNode.actions.equals(afterNode.actions);
                    }else if(same){List<String> beforeChildren=new ArrayList<>(),afterChildren=new ArrayList<>();for(var child:beforeNode.children)beforeChildren.add(child.id);for(var child:afterNode.children)afterChildren.add(child.id);same=beforeChildren.equals(afterChildren);}}
                current=beforeParent;}
            if(!same)throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);
        }
    }
    private void preflightEditorsV2(Candidate c){
        for(var state:c.journal.previous){
            var previous=state.record;
            if(v2Profile.retirement()&&previous.view instanceof NativeAppearanceViewsV2.NativeField field&&
                (field.attempt!=state.predecessor||fieldUpdateV3(c,previous)!=state.update||
                 !c.next.nodes.containsKey(previous.id)&&state.update!=FieldUpdateV3.RETIRE))
                throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);
            if(state.update==FieldUpdateV3.HANDOFF||state.update==FieldUpdateV3.RETIRE||state.update==FieldUpdateV3.SETTLED)continue;
            if(v2Profile.retirement()&&previous.view instanceof NativeAppearanceViewsV2.NativeField){
                if(!retainedFieldUpdateV3(c,previous,c.detached.get(previous.id)))
                    throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);
                continue;
            }
            if(state.update==FieldUpdateV3.PRESERVE){
                var shadow=c.detached.get(previous.id);
                if(c.targets.get(previous.id)!=previous||shadow==null||!sameEditorBindingV2(previous,shadow))
                    throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);
            }
            boolean active=previous.view instanceof EditText edit&&(edit.hasFocus()||android.view.inputmethod.BaseInputConnection.getComposingSpanStart(edit.getText())>=0);
            boolean selecting=previous.view instanceof TextView text&&text.isTextSelectable()&&text.getSelectionStart()>=0;
            if(!active&&!selecting)continue;
            var shadow=c.detached.get(previous.id);
            if(c.targets.get(previous.id)!=previous||shadow==null||!sameEditorBindingV2(previous,shadow)||!sameAncestorsV2(c,previous.id)||
                !sameFrameV2(previous.view,shadow.view,previous.verticalInput?v2Profile:AndroidUIProfile.LEGACY_HORIZONTAL))throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);
        }
    }
    private static boolean sameEditorBindingV2(NativeAppearanceViewsV2.Record old,NativeAppearanceViewsV2.Record next){
        // Engine echo can acknowledge the current native buffer without calling setText or replacing Editable.
        if(!(old.view instanceof TextView text)||!text.getText().toString().equals(((TextView)next.view).getText().toString()))return false;
        return sameEditorConfigurationV2(old,next);
    }
    private static boolean sameEditorConfigurationV2(NativeAppearanceViewsV2.Record old,NativeAppearanceViewsV2.Record next){
        return sameEditorConfigurationV2(old,next,false);
    }
    private static boolean sameEditorConfigurationV2(NativeAppearanceViewsV2.Record old,NativeAppearanceViewsV2.Record next,boolean disabling){
        var a=old.binding;var b=next.binding;
        if(old.view instanceof Switch value&&value.isChecked()!=b.nativeToggleValue())return false;
        boolean recipe=a.node().recipe().equals(b.node().recipe());
        Map<String,Object> ap=new HashMap<>(a.source().properties),bp=new HashMap<>(b.source().properties);
        if(a.node().recipe() instanceof AppearanceResolverV2.FieldRecipe x&&b.node().recipe() instanceof AppearanceResolverV2.FieldRecipe y){
            recipe=x.label().equals(y.label())&&x.metrics().equals(y.metrics())&&x.text().role()==y.text().role()&&x.text().metrics().equals(y.text().metrics());ap.remove("value");bp.remove("value");}
        if(disabling){ap.remove("disabled");bp.remove("disabled");}
        return recipe&&(disabling||a.node().disabled()==b.node().disabled())&&ap.equals(bp)&&
            a.plan().environment.scheme()==b.plan().environment.scheme()&&a.plan().environment.profile()==b.plan().environment.profile()&&
            a.plan().environment.direction()==b.plan().environment.direction()&&a.plan().environment.density1024()==b.plan().environment.density1024()&&
            a.plan().environment.localeIdentifier().equals(b.plan().environment.localeIdentifier())&&a.theme().equals(b.theme());
    }
    // Model authority acknowledges the complete native buffer, never an unreported edit.
    private boolean modelHandoffValueV3(NativeAppearanceViewsV2.Record old,UiPacket.Node source){
        if(!v2Profile.retirement()||source==null||
            !source.id.equals(old.id)||!source.kind.equals(old.kind)||!source.generation.equals(old.generation)||
            !(old.view instanceof NativeAppearanceViewsV2.NativeField field)||!field.modelHandoffEligible()||
            !old.binding.nativeFieldValue().equals(field.nativeEditable().toString()))return false;
        String before=old.binding.nativeFieldValue(),after=source.text("value","");
        return (before.equals(after)||!before.isEmpty()&&after.isEmpty())&&
            (old.binding.node().disabled()!=source.disabled||!before.equals(after));
    }
    private boolean modelHandoffV3(Candidate c,NativeAppearanceViewsV2.Record old,NativeAppearanceViewsV2.Record next){
        if(c.owner!=this||c.baseRecords.get(old.id)!=old||c.targets.get(old.id)!=old||next==null||
            !modelHandoffValueV3(old,next.binding.source()))return false;
        var field=(NativeAppearanceViewsV2.NativeField)old.view;
        boolean consumed=field.modelHandoffConsumed();
        // A consumed predecessor grants no live horizontal buffer authority. Its
        // retained recipe still fixes X, width and horizontal height after reflow.
        AndroidUIProfile geometry=old.verticalInput||consumed?v2Profile:AndroidUIProfile.LEGACY_HORIZONTAL;
        return sameEditorConfigurationV2(old,next,true)&&old.binding.source().actions.equals(next.binding.source().actions)&&
            (sameModelAncestorsV3(c,old.id,false)||consumed&&sameModelAncestorsV3(c,old.id,true))&&
            sameFrameV2(old.view,next.view,geometry)&&(old.verticalInput||old.view.getHeight()==next.view.getHeight());
    }
    // A retained field acknowledges its own complete native buffer. Sibling edits
    // grant no authority over its target, input contract or source lineage.
    private boolean retainedFieldUpdateV3(Candidate c,NativeAppearanceViewsV2.Record old,NativeAppearanceViewsV2.Record next){
        if(c.owner!=this||c.base!=packet||c.baseRecords!=v2Records||c.baseRecords.get(old.id)!=old||
            old.editorFence!=v2Fence||old.input!=v2Input||old.binding.source()!=c.base.nodes.get(old.id)||
            c.targets.get(old.id)!=old||next==null||!sameSourceIdentityV3(old.binding.source(),next.binding.source())||
            !sameEditorBindingV2(old,next)||!old.binding.source().actions.equals(next.binding.source().actions))return false;
        var field=(NativeAppearanceViewsV2.NativeField)old.view;
        if(!field.modelHandoffEligible())return false;
        return (sameModelAncestorsV3(c,old.id,false)||sameModelAncestorsV3(c,old.id,true))&&
            (old.verticalInput? sameFrameV2(old.view,next.view,v2Profile):retainedMeasuredFrameV3(c,old,next));
    }
    // Both states must still occupy their own prepared source frames. A new
    // native text measurement can change row centering and rounded edge height
    // even when the logical hit envelope is unchanged.
    private boolean retainedMeasuredFrameV3(Candidate c,NativeAppearanceViewsV2.Record old,NativeAppearanceViewsV2.Record next){
        if(!completeCandidateV3(c)||!sourceFrameV3(c.base,c.baseRecords,old.id)||!sourceFrameV3(c.next,c.detached,next.id))return false;
        String id=old.id;
        while(id!=null){
            var a=c.baseRecords.get(id).geometry.box;var b=c.detached.get(id).geometry.box;
            if(a.x()!=b.x()||a.width()!=b.width())return false;
            id=parentV2(c.base,id);
        }
        int[] a=positionV2(old.view),b=positionV2(next.view);
        if(a[0]!=b[0]||old.view.getWidth()!=next.view.getWidth())return false;
        if(a[1]==b[1]&&old.view.getHeight()==next.view.getHeight())return true;
        for(var before:c.baseRecords.values()){
            var after=c.detached.get(before.id);
            if(after!=null&&sameSourceIdentityV3(before.binding.source(),after.binding.source())&&
                before.geometry.nativeTextHeightPx>=0&&after.geometry.nativeTextHeightPx>=0&&
                before.geometry.nativeTextHeightPx!=after.geometry.nativeTextHeightPx&&
                !before.binding.source().properties.equals(after.binding.source().properties))return true;
        }
        return false;
    }
    private static boolean sourceFrameV3(UiPacket packet,Map<String,NativeAppearanceViewsV2.Record> records,String id){
        while(id!=null){
            var record=records.get(id);if(record==null||record.binding.source()!=packet.nodes.get(id))return false;
            var g=record.geometry;var f=g.preparedFrame;if(f==null||!f.box().equals(g.box)||
                f.nativeParent()!=record.view.getParent()||f.contentHeight()!=g.contentHeight)return false;
            String parent=parentV2(packet,id);
            if(parent==null){
                if(f.absoluteX()!=g.box.x()||f.absoluteY()!=g.box.y()||f.parentX()!=0||f.parentY()!=0)return false;
            }else{
                var ancestor=records.get(parent);if(ancestor==null||ancestor.geometry.preparedFrame==null||
                    ancestor.group==null||record.view.getParent()!=ancestor.group||
                    !g.box.equals(ancestor.geometry.children.get(id)))return false;
                var p=ancestor.geometry.preparedFrame;
                if(f.parentX()!=p.absoluteX()||f.parentY()!=p.absoluteY()||
                    f.absoluteX()!=p.absoluteX()+g.box.x()||f.absoluteY()!=p.absoluteY()+g.box.y())return false;
            }
            var binding=record.binding;
            int left=NativeAppearanceViewsV2.px(f.absoluteX(),binding)-NativeAppearanceViewsV2.px(f.parentX(),binding);
            int top=NativeAppearanceViewsV2.px(f.absoluteY(),binding)-NativeAppearanceViewsV2.px(f.parentY(),binding);
            int width=NativeAppearanceViewsV2.px(f.absoluteX()+g.box.width(),binding)-NativeAppearanceViewsV2.px(f.absoluteX(),binding);
            int height=NativeAppearanceViewsV2.px(f.absoluteY()+g.box.height(),binding)-NativeAppearanceViewsV2.px(f.absoluteY(),binding);
            if(record.view.getLeft()!=left||record.view.getTop()!=top||record.view.getRight()!=left+width||record.view.getBottom()!=top+height)return false;
            if(record.group!=null){
                if(record.group.absoluteX!=f.absoluteX()||record.group.absoluteY!=f.absoluteY())return false;
                if(record.group!=record.view&&(record.group.getParent()!=record.view||
                    record.group.getLeft()!=0||record.group.getTop()!=0||record.group.getRight()!=width||
                    record.group.getBottom()!=NativeAppearanceViewsV2.px(f.contentHeight(),binding)))return false;
            }
            id=parent;
        }
        return true;
    }
    private boolean completeCandidateV3(Candidate c){
        if(c.owner!=this||c.base!=packet||c.baseRecords!=v2Records||c.installed!=v2Installed||
            !c.targets.keySet().equals(c.next.nodes.keySet())||!c.detached.keySet().equals(c.next.nodes.keySet()))return false;
        for(var source:c.next.nodes.values()){
            var shadow=c.detached.get(source.id);var target=c.targets.get(source.id);var old=c.baseRecords.get(source.id);
            if(shadow==null||target==null||shadow.binding.source()!=source||shadow.binding.plan()!=c.plan||
                shadow.editorFence!=v2Fence||shadow.input!=v2Input)return false;
            if(old!=null&&old.kind.equals(source.kind)&&old.generation.equals(source.generation)){
                if(target!=old)return false;
            }else if(target!=shadow)return false;
        }
        return true;
    }
    private static boolean sameSourceIdentityV3(UiPacket.Node a,UiPacket.Node b){
        return a!=null&&b!=null&&a.id.equals(b.id)&&a.kind.equals(b.kind)&&a.generation.equals(b.generation);
    }
    // The ordered prefix through this editor's branch is immutable. A complete
    // candidate may change its owned tail while retaining source lineage/order;
    // every old editor still has its own journal plan and transition membership.
    private boolean sameModelAncestorsV3(Candidate c,String id,boolean tail){
        if(tail&&!completeCandidateV3(c))return false;
        String current=id;
        while(current!=null){
            String before=parentV2(c.base,current),after=parentV2(c.next,current);
            if(!Objects.equals(before,after))return false;
            if(before!=null){
                var a=c.base.nodes.get(before);var b=c.next.nodes.get(after);
                if(!sameSourceIdentityV3(a,b)||!a.properties.equals(b.properties)||!a.actions.equals(b.actions))return false;
                int prefix=0;
                while(prefix<a.children.size()&&prefix<b.children.size()&&sameSourceIdentityV3(a.children.get(prefix),b.children.get(prefix))){
                    prefix++;if(a.children.get(prefix-1).id.equals(current))break;
                }
                if(prefix==0||!a.children.get(prefix-1).id.equals(current))return false;
                if(!tail){
                    if(a.children.size()!=b.children.size())return false;
                    for(int i=prefix;i<a.children.size();i++)if(!sameSourceIdentityV3(a.children.get(i),b.children.get(i)))return false;
                }else{
                    List<String> left=new ArrayList<>(),right=new ArrayList<>();
                    for(int i=prefix;i<a.children.size();i++){
                        var n=a.children.get(i);
                        if(!ownedTailV3(c,n,true))return false;
                        if(c.next.nodes.containsKey(n.id))left.add(n.id);
                    }
                    for(int i=prefix;i<b.children.size();i++){
                        var n=b.children.get(i);
                        if(!ownedTailV3(c,n,false))return false;
                        if(c.base.nodes.containsKey(n.id))right.add(n.id);
                    }
                    if(!left.equals(right))return false;
                }
            }
            current=before;
        }
        return true;
    }
    private boolean ownedTailV3(Candidate c,UiPacket.Node source,boolean old){
        var other=(old?c.next:c.base).nodes.get(source.id);
        if(other!=null&&(!sameSourceIdentityV3(source,other)||
            !Objects.equals(parentV2(c.base,source.id),parentV2(c.next,source.id))))return false;
        // Adding editor contracts is not authority derived from another editor.
        if(!old&&other==null&&source.kind.equals("textField"))return false;
        for(var child:source.children)if(!ownedTailV3(c,child,old))return false;
        return true;
    }
    private FieldUpdateV3 fieldUpdateV3(Candidate c,NativeAppearanceViewsV2.Record record){
        if(!v2Profile.retirement()||!(record.view instanceof NativeAppearanceViewsV2.NativeField field))return FieldUpdateV3.ORDINARY;
        var shadow=c.detached.get(record.id);
        if(frameRetirementV3(record,c.next.nodes.get(record.id))&&c.baseRecords.get(record.id)==record&&
            c.targets.get(record.id)==null&&c.detached.get(record.id)==null&&completeCandidateV3(c))return FieldUpdateV3.RETIRE;
        if(modelHandoffV3(c,record,shadow))return FieldUpdateV3.HANDOFF;
        if(record.verticalInput&&field.transitionInactive()&&retainedFieldUpdateV3(c,record,shadow))return FieldUpdateV3.SETTLED;
        return field.needsFieldPreservation()?FieldUpdateV3.PRESERVE:FieldUpdateV3.ORDINARY;
    }
    // Called only after exact target reuse, current-buffer echo, binding and ancestry checks.
    // V3 multiline layout may translate vertically as its measured height changes.
    // Horizontal fields and earlier profiles retain their existing frame policy.
    private static boolean sameFrameV2(View a,View b,AndroidUIProfile fieldProfile){
        int[] ap=positionV2(a),bp=positionV2(b);
        if(ap[0]!=bp[0]||a.getWidth()!=b.getWidth())return false;
        return switch(fieldProfile){
            case LEGACY_HORIZONTAL -> ap[1]==bp[1]&&a.getHeight()==b.getHeight();
            case MEASURED_MULTILINE_V2 -> ap[1]==bp[1];
            case MEASURED_MULTILINE_RETIREMENT_V3, MEASURED_MULTILINE_LONG_NOTES_V4 -> true;
        };
    }
    private static int[] positionV2(View view){int x=view.getLeft(),y=view.getTop();for(var parent=view.getParent();parent instanceof View v;parent=v.getParent()){
        if(v instanceof NativeAppearanceViewsV2.Gate||v instanceof FrameLayout)break;x+=v.getLeft();y+=v.getTop();}return new int[]{x,y};}
    private static String parentV2(UiPacket packet,String id){if(packet==null)return null;for(var n:packet.nodes.values())for(var c:n.children)if(c.id.equals(id))return n.id;return null;}
    private static boolean containsKindV2(UiPacket.Node node,String kind){if(node.kind.equals(kind))return true;for(var child:node.children)if(containsKindV2(child,kind))return true;return false;}
    private static boolean sameAncestorsV2(Candidate c,String id){String current=id;
        while(current!=null){String before=parentV2(c.base,current),after=parentV2(c.next,current);if(!Objects.equals(before,after))return false;
            if(before!=null){UiPacket.Node a=c.base.nodes.get(before),b=c.next.nodes.get(after);if(b==null||!a.kind.equals(b.kind)||!a.generation.equals(b.generation))return false;
                List<String> ac=new ArrayList<>(),bc=new ArrayList<>();for(var n:a.children)ac.add(n.id);for(var n:b.children)bc.add(n.id);if(!ac.equals(bc))return false;}
            current=before;}return true;}
    private void validateV2(Candidate c,boolean attached){
        NativeEnvironmentV2.requireMain();requireEditorsAvailableV2();requireV2Live();
        if(c==null||c.owner!=this||v2Pending!=c||c.used||c.attached!=attached||packet!=c.base||v2Records!=c.baseRecords||v2Installed!=c.installed)throw Json.bad("stale/foreign/consumed V2 candidate");
        requireTransactionV2(c.operation);
        if(v2Interaction!=c.interaction)throw Json.bad("stale V2 native interaction epoch "+c.interaction+" -> "+v2Interaction);
        if(!c.environment.current(this))throw Json.bad("stale V2 native environment");
        if(!attached&&!sameNativeBaseV2(c.journal))throw Json.bad("stale V2 native canvas");
    }
    AttachmentJournal attachV2(Candidate c,FrameLayout root){
        requireEditorsAvailableV2();validateV2(c,false);if(root!=c.environment.root())throw Json.bad("foreign V2 root");preflightEditorsV2(c);
        NativeAppearanceViewsV2.Mutation previousMutation=v2Mutation;
        if(c.originalMutation!=null)throw Json.bad("V2 original mutation already captured");
        c.originalMutation=NativeAppearanceViewsV2.Mutation.transaction(v2Fence,c.operation);
        v2Mutation=c.originalMutation;
        NativeAppearanceViewsV2.Mutation mutation=c.originalMutation;
        sealScalarV2();c.gate.open=false;c.gate.canvasColor=NativeAppearanceViewsV2.color(c.plan.canvas);v2Steps=0;
        try {
            beginFieldTransitionsV3(c,mutation);beginFieldPreservationsV2(c,mutation);c.nativeAttachStarted=true;
            for(var state:c.journal.previous)if(state.transition!=null)state.transition.prepareAttachment();
            for(var entry:c.targets.entrySet()){
                var target=entry.getValue();var shadow=c.detached.get(entry.getKey());
                if(target!=shadow){boolean preserve=target.view instanceof TextView&&sameEditorBindingV2(target,shadow);
                    target.bind(shadow.binding,shadow.geometry,preserve&&target.fieldTransition==null,target.fieldTransition==null?mutation:target.fieldTransition.mutation);}
                faultV2();
            }
            for(var target:c.targets.values()){NativeAppearanceViewsV2.installChildren(target,c.targets,mutation);faultV2();}
            View desired=c.targets.get(c.next.root.id).view;
            if(desired.getParent()!=c.gate){if(desired.getParent() instanceof ViewGroup previous)previous.removeView(desired);mutation.require();
c.gate.addView(desired);mutation.require();
}
            for(int i=c.gate.getChildCount()-1;i>=0;i--)if(c.gate.getChildAt(i)!=desired){NativeAppearanceViewsV2.FieldRemoval.remove(c.gate,i,mutation);mutation.require();}

            faultV2();
            if(c.gate.getParent()!=root){if(c.gate.getParent() instanceof ViewGroup previous)previous.removeView(c.gate);mutation.require();
root.addView(c.gate,new FrameLayout.LayoutParams(-1,-1));mutation.require();
}
            for(int i=root.getChildCount()-1;i>=0;i--)if(root.getChildAt(i)!=c.gate){NativeAppearanceViewsV2.FieldRemoval.remove(root,i,mutation);mutation.require();}

            c.gate.measure(View.MeasureSpec.makeMeasureSpec(root.getWidth(),View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(root.getHeight(),View.MeasureSpec.EXACTLY));mutation.require();

            c.gate.layout(0,0,root.getWidth(),root.getHeight());mutation.require();

            NativeAppearanceViewsV2.layoutRoot(c.targets.get(c.next.root.id),root.getWidth(),root.getHeight(),c.environment.value.safeArea64(),mutation);
            checkFieldPreservationsV2(c);
            for(var state:c.journal.previous)if(state.transition!=null)state.transition.validateAttached();
            faultV2();c.attached=true;
            for(int i=0;i<c.journal.stateCount;i++){var scope=c.journal.states[i].preservation;if(scope!=null)scope.phase=NativeAppearanceViewsV2.FieldPreservation.ATTACHED;}
            return c.journal;
        }catch(RuntimeException|java.lang.Error failure){
            // Observe native F before any restoration/report G and later coordinator abort H.
            rememberV2(failure);
            if(c.nativeAttachStarted&&!v2Fence.terminal)try{restoreV2(c);revokePreservationsV2(c,NativeAppearanceViewsV2.FieldPreservation.RESTORED_HELD);}
            catch(RuntimeException|java.lang.Error rollback){
                rememberV2(rollback);
                try{terminalV2(NativeEnvironmentV2.RendererCause.ROLLBACK_FAILED,failure,v2Cleanup.firstFatal);}
                catch(RuntimeException|java.lang.Error report){rememberV2(report);}
            }
            // Count custody survives transport to the coordinator's sole failure completion.
            c.used=true;v2Pending=null;if(v2Cleanup.firstFatal!=null)throw v2Cleanup.firstFatal;throw failure;
        }finally{v2Mutation=previousMutation;}
    }
    private boolean frameRetirementV3(NativeAppearanceViewsV2.Record record,UiPacket.Node incoming){
        return v2Profile.retirement()&&incoming==null&&
            v2Records.get(record.id)==record&&record.editorFence==v2Fence&&record.input==v2Input&&
            packet.nodes.get(record.id)==record.binding.source()&&
            record.view instanceof NativeAppearanceViewsV2.NativeField field&&field.modelHandoffEligible()&&
            record.binding.nativeFieldValue().equals(field.nativeEditable().toString());
    }
    private boolean transitionMembershipV3(AttachmentJournal j){
        if(j==null||j.states==null||j.stateCount!=j.states.length||j.previous.size()!=j.stateCount||j.transitionRoster.length!=j.stateCount)return false;
        int count=0;
        for(int i=0;i<j.stateCount;i++){
            var state=j.states[i];if(state==null||state.journal!=j||state.position!=i||j.previous.get(i)!=state)return false;
            var member=j.transitionRoster[i];
            if(member==null){if(state.transition!=null||state.transitionMembership!=null)return false;continue;}
            count++;
            if(member.state!=state||state.transitionMembership!=member||state.transition!=member.scope||member.scope.record!=state.record||member.scope.journal!=j)return false;
        }
        return count==j.transitionCount;
    }
    private boolean fieldTransitionIdentity(Candidate c,AttachmentJournal j,NativeAppearanceViewsV2.Record r,NativeAppearanceViewsV2.FieldTransition scope){
        if(c==null||c.owner!=this||j==null||j!=c.journal||j.candidate!=c||r==null||scope==null||scope.candidate!=c||scope.journal!=j||scope.renderer!=this||
            scope.record!=r||r.view!=scope.field||r.editorFence!=v2Fence||r.input!=v2Input||scope.original!=c.originalMutation||scope.original.token!=c.operation||
            !transitionMembershipV3(j))return false;
        for(int i=0;i<j.stateCount;i++){var state=j.states[i];if(state.record==r)return state.transition==scope&&state.binding==scope.before&&c.baseRecords.get(r.id)==r;}
        return false;
    }
    boolean fieldTransitionCurrent(Candidate c,AttachmentJournal j,NativeAppearanceViewsV2.Record r,NativeAppearanceViewsV2.FieldTransition scope){
        return fieldTransitionIdentity(c,j,r,scope)&&v2Profile.retirement()&&v2Pending==c&&!c.used&&packet==c.base&&v2Records==c.baseRecords&&
            c.operation==v2Fence.operation&&!v2Fence.terminal&&j.completion==AttachmentJournal.OPEN&&
            (scope.removal?c.targets.get(r.id)==null:c.targets.get(r.id)==r&&c.detached.get(r.id)!=null&&c.detached.get(r.id).binding==scope.selected);
    }
    boolean transitionLossCurrentV3(AttachmentJournal j){return j!=null&&j.transitionLoss==editorLossSerial;}
    void accountTransitionLossV3(NativeAppearanceViewsV2.FieldTransition scope,long prior,NativeAppearanceViewsV2.FieldLifecycle event,boolean ownedRemoval){
        String hook=event.hook;
        Candidate c=scope.candidate;AttachmentJournal j=scope.journal;
        if(!fieldTransitionCurrent(c,j,scope.record,scope)||!j.transitionsSealed||j.transitionLoss!=prior||prior==Long.MAX_VALUE||editorLossSerial!=prior+1||
            scope.hooks.size()!=1||!hook.equals(scope.hooks.peek())||scope.checking||!scope.identityScalar()||lastEditorLossRecord!=scope.record)throw Json.bad("unowned transition loss");
        TransitionMembership claimed=null;
        for(var member:j.transitionRoster)if(member!=null&&member.scope==scope)claimed=member;
        if(claimed==null||!(event==NativeAppearanceViewsV2.FieldLifecycle.FOCUS&&scope.retire&&scope.phase==NativeAppearanceViewsV2.FieldTransition.FOCUS&&scope.focusClaimed&&!claimed.focusLossClaimed||
            ownedRemoval&&scope.removalCall!=null&&scope.removalCall.owns(scope)&&scope.removalLoss(event)))throw Json.bad("replayed transition loss");
        int count=0;
        for(var member:j.transitionRoster)if(member!=null){var s=member.scope;count++;
            if(!fieldTransitionCurrent(c,j,s.record,s)||!s.identityScalar()||s.checking||s!=scope&&!s.hooks.isEmpty())throw Json.bad("changed transition loss cohort");
        }
        if(count!=outstandingFieldTransitions||outstandingEditorNativeCalls<count+c.heldPreservations)throw Json.bad("unfunded transition loss cohort");
        if(!ownedRemoval)claimed.focusLossClaimed=true;
        j.transitionLoss=editorLossSerial;
    }
    private void beginFieldTransitionsV3(Candidate c,NativeAppearanceViewsV2.Mutation mutation){
        if(!v2Profile.retirement())return;
        AttachmentJournal j=c.journal;
        if(j.transitionsStarted||j.transitionsSealed||j.transitionCount!=0||outstandingFieldTransitions!=0||!transitionMembershipV3(j))throw Json.bad("reentered transition capture");
        j.transitionsStarted=true;j.transitionLoss=editorLossSerial;
        for(var state:j.previous){
            var record=state.record;if(!(record.view instanceof NativeAppearanceViewsV2.NativeField field))continue;
            var shadow=c.detached.get(record.id);
            var update=state.update;
            if(update!=FieldUpdateV3.HANDOFF&&update!=FieldUpdateV3.RETIRE&&update!=FieldUpdateV3.SETTLED)continue;
            boolean retire=update!=FieldUpdateV3.SETTLED;
            if(record.fieldTransition!=null||record.fieldPreservation!=null||state.transition!=null||!sameNativeBaseV2(state)||
                shadow!=null&&c.targets.get(record.id)!=record||outstandingEditorNativeCalls==Integer.MAX_VALUE||fieldUpdateV3(c,record)!=update)
                throw Json.bad("invalid settled attachment source");
            var scope=new NativeAppearanceViewsV2.FieldTransition(this,c,j,record,shadow==null?null:shadow.binding,mutation,retire);
            if(!sameNativeBaseV2(state)||fieldUpdateV3(c,record)!=update||!transitionLossCurrentV3(j)||!transitionMembershipV3(j))throw Json.bad("settled attachment changed during capture");
            var member=new TransitionMembership(state,scope);
            state.transitionMembership=member;j.transitionRoster[state.position]=member;j.transitionCount++;
            state.transition=scope;record.fieldTransition=scope;scope.registered=true;outstandingFieldTransitions++;outstandingEditorNativeCalls++;
            scope.exact();
        }
        j.transitionsSealed=true;
    }
    private boolean transitionsReadyV3(Candidate c){
        AttachmentJournal j=c.journal;
        if(!transitionMembershipV3(j)||j.transitionCount!=0&&!j.transitionsSealed||j.transitionsStarted&&!transitionLossCurrentV3(j))return false;
        int count=0;
        for(var member:j.transitionRoster){if(member==null)continue;var s=member.scope;count++;
            if(!fieldTransitionCurrent(c,j,s.record,s)||!s.readyScalar())return false;
        }
        return count==outstandingFieldTransitions&&outstandingEditorNativeCalls>=count+c.heldPreservations;
    }
    private void failedTransitionsV3(Candidate c){
        AttachmentJournal j=c.journal;
        for(var member:j.transitionRoster)if(member!=null&&(member.scope.irreversible||member.scope.removalCall!=null))nativeInstallFailure=true;
        if(!transitionMembershipV3(j))throw Json.bad("changed failed transition roster");
        int count=0;
        for(var member:j.transitionRoster){if(member==null)continue;var s=member.scope;
            if(s.ended||!fieldTransitionIdentity(c,j,s.record,s)||s.record.fieldTransition!=s||s.checking||!s.hooks.isEmpty()||!s.registered||!s.failedReleaseReady())throw Json.bad("unbalanced failed settled attachment");
            count++;
        }
        if(count!=outstandingFieldTransitions||outstandingEditorNativeCalls<count)throw Json.bad("unfunded failed transition cohort");
        for(var member:j.transitionRoster)if(member!=null){var s=member.scope;
            s.record.fieldTransition=null;s.record.modelSettled=s.wasSettled;s.ended=true;s.registered=false;outstandingFieldTransitions--;outstandingEditorNativeCalls--;
        }
    }
    boolean gatedNativeInstallFailureV3(){return nativeInstallFailure;}
    private void beginFieldPreservationsV2(Candidate c,NativeAppearanceViewsV2.Mutation mutation){
        mutation.requireMutation();
        for(NativeState state:c.journal.previous){
            var record=state.record;
            if(record.fieldTransition!=null)continue;
            if(!(record.view instanceof NativeAppearanceViewsV2.NativeField field)||!field.needsFieldPreservation())continue;
            var shadow=c.detached.get(record.id);
            if(record.fieldPreservation!=null||state.membership!=null||state.preservation!=null||state.forwardPreserved||
                c.targets.get(record.id)!=record||shadow==null||!sameEditorBindingV2(record,shadow)||!sameNativeBaseV2(state))
                throw Json.bad("incompatible settled field preservation");
            var scope=new NativeAppearanceViewsV2.FieldPreservation(field,mutation,shadow.binding,(Editable)state.nativeBuffer,this,c,c.journal);
            // Allocation completes before registration, acquisition, or any publication of this member.
            PreservationMembership membership=new PreservationMembership(state,scope);
            state.membership=membership;record.fieldPreservation=scope;state.preservation=scope;state.forwardPreserved=true;
            try{record.input.fieldPreservationBegin(record,scope);scope.capture();
                if(!sameNativeBaseV2(state))throw Json.bad("preserved field journal changed");scope.exact();}
            catch(RuntimeException|java.lang.Error failure){rememberV2(failure);throw failure;}
        }
    }
    private void checkFieldPreservationsV2(Candidate c){
        for(NativeState state:c.journal.previous)if(state.preservation!=null)state.preservation.exact();
    }
    /** Constructor-bound ordered roster and capture-once exact scope identity; scalar only. */
    private boolean preservationMembershipV2(AttachmentJournal journal){
        if(journal==null||journal.states==null||journal.stateCount!=journal.states.length)return false;
        for(int i=0;i<journal.stateCount;i++){
            NativeState state=journal.states[i];
            if(state==null||state.journal!=journal||state.position!=i)return false;
            PreservationMembership membership=state.membership;
            if(membership==null){if(state.preservation!=null||state.forwardPreserved)return false;}
            else if(membership.state!=state||membership.scope!=state.preservation||!state.forwardPreserved||
                membership.scope.record!=state.record||membership.scope.journal!=journal)return false;
        }
        return true;
    }
    private boolean fieldPreservationCapturedV2(Candidate c,AttachmentJournal journal,NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.FieldPreservation scope){
        return !(c==null||c.owner!=this||journal==null||journal!=c.journal||journal.candidate!=c||scope==null||scope.renderer!=this||scope.candidate!=c||scope.journal!=journal||
            record==null||scope.record!=record||record.view!=scope.field||scope.field.record!=record||record.input!=v2Input||record.editorFence!=v2Fence||
            c.originalMutation==null||scope.original!=c.originalMutation||scope.original.fence!=v2Fence||scope.original.mode!=NativeAppearanceViewsV2.Mutation.Mode.TRANSACTION||
            scope.original.token!=c.operation||scope.original.editorLease!=null||scope.original.replacementLease!=null||scope.original.fieldLease!=null);
    }
    /** Foreign captured authority refuses without claiming an own malformed completion. */
    private boolean preservationProvenanceV2(Candidate c,AttachmentJournal journal){
        if(journal.states==null)return true; // Malformed own roster, never release authority.
        for(int i=0;i<journal.states.length;i++){
            NativeState state=journal.states[i];if(state==null||state.journal!=journal)continue;
            PreservationMembership membership=state.membership;
            if(membership!=null&&!fieldPreservationCapturedV2(c,journal,state.record,membership.scope))return false;
            var scope=state.preservation;
            if(scope!=null&&(!fieldPreservationCapturedV2(c,journal,state.record,scope)||
                state.record.fieldPreservation!=null&&state.record.fieldPreservation!=scope&&
                (membership==null||state.record.fieldPreservation!=membership.scope)))return false;
        }
        return true;
    }
    boolean fieldPreservationIdentityV2(Candidate c,AttachmentJournal journal,NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.FieldPreservation scope){
        if(!fieldPreservationCapturedV2(c,journal,record,scope)||!preservationMembershipV2(journal))return false;
        for(int i=0;i<journal.stateCount;i++){NativeState state=journal.states[i];if(state.record==record)return state.forwardPreserved&&state.preservation==scope;}
        return false;
    }
    private boolean preservationCohortV2(Candidate c){
        if(!preservationMembershipV2(c.journal))return false;
        int held=0;for(int i=0;i<c.journal.stateCount;i++){var scope=c.journal.states[i].preservation;if(scope!=null&&scope.counted)held++;}
        return c.heldPreservations==held&&outstandingFieldPreservations==held&&held>=0&&held<=c.journal.stateCount&&outstandingEditorNativeCalls>=held;
    }
    private boolean preservationFailureFundedV2(Candidate c){
        if(!preservationMembershipV2(c.journal))return false;
        int represented=0;for(int i=0;i<c.journal.stateCount;i++){var scope=c.journal.states[i].preservation;if(scope!=null&&scope.counted)represented++;}
        return c.heldPreservations>=represented&&c.heldPreservations>=0&&c.heldPreservations<=c.journal.stateCount&&
            outstandingFieldPreservations==c.heldPreservations&&outstandingEditorNativeCalls>=c.heldPreservations;
    }
    private boolean preservationEndReadyV2(NativeAppearanceViewsV2.FieldPreservation scope){
        return scope.entered&&scope.counted&&!scope.released&&scope.endReady()&&
            (scope.phase==NativeAppearanceViewsV2.FieldPreservation.RESTORED_HELD||scope.phase==NativeAppearanceViewsV2.FieldPreservation.FAILED_HELD)&&
            outstandingEditorNativeCalls>0;
    }
    boolean fieldPreservationCurrent(Candidate c,AttachmentJournal journal,NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.FieldPreservation scope){
        NativeEnvironmentV2.requireMain();
        return fieldPreservationIdentityV2(c,journal,record,scope)&&v2Pending==c&&!c.used&&c.targets.get(record.id)==record&&
            c.operation==v2Fence.operation&&!v2Fence.terminal&&journal.completion==AttachmentJournal.OPEN;
    }
    private void revokePreservationsV2(Candidate c,int phase){
        if(!preservationMembershipV2(c.journal))return;
        for(int i=0;i<c.journal.stateCount;i++){var state=c.journal.states[i];var scope=state.preservation;
            if(scope!=null&&fieldPreservationIdentityV2(c,c.journal,state.record,scope)&&!scope.released){
                if(state.record.fieldPreservation==scope)state.record.fieldPreservation=null;
                scope.ended=true;scope.phase=phase;
            }
        }
    }
    /** Once-only post-interval reporting, then exact scalar release of every balanced own hold. */
    void completeFailedV2(Candidate c,Throwable primary,java.lang.Error firstFatal){
        NativeEnvironmentV2.requireMain();
        if(v2Fence.commitFinish||c==null||c.owner!=this||c.journal.candidate!=c||c.journal.failedInvoked||c.journal.completion==AttachmentJournal.SUCCESS_DONE)
            throw Json.bad("invalid V2 failed completion");
        AttachmentJournal journal=c.journal;
        if(!preservationProvenanceV2(c,journal))throw Json.bad("foreign V2 failed preservation provenance");
        if(!preservationMembershipV2(journal)){
            // The candidate is our own, but its roster cannot authorize any scope effect or retry.
            journal.failedInvoked=true;journal.completion=AttachmentJournal.FAILED_IN_PROGRESS;
            rememberV2(primary);rememberV2(firstFatal);
            RuntimeException failure=Json.bad("invalid V2 failed preservation membership");rememberV2(failure);
            try{terminalV2(NativeEnvironmentV2.RendererCause.CANCELLATION_FAILED,v2Cleanup.primary,v2Cleanup.firstFatal);}
            catch(RuntimeException|java.lang.Error report){rememberV2(report);}
            journal.completion=AttachmentJournal.FAILED_DONE;
            if(v2Cleanup.firstFatal!=null)throw v2Cleanup.firstFatal;throw failure;
        }
        for(int i=0;i<journal.stateCount;i++){NativeState state=journal.states[i];var scope=state.preservation;
            if(scope!=null&&(!fieldPreservationIdentityV2(c,journal,state.record,scope)||state.record.fieldPreservation!=null&&state.record.fieldPreservation!=scope))
                throw Json.bad("foreign V2 failed preservation provenance");
        }
        journal.failedInvoked=true;journal.completion=AttachmentJournal.FAILED_IN_PROGRESS;
        rememberV2(primary);rememberV2(firstFatal);
        boolean funded=preservationFailureFundedV2(c);boolean failed=!funded;
        for(int i=0;i<journal.stateCount;i++){
            if(!preservationMembershipV2(journal)){rememberV2(Json.bad("changed V2 reporting preservation membership"));failed=true;break;}
            NativeState state=journal.states[i];var scope=state.preservation;if(scope==null)continue;
            if(!fieldPreservationIdentityV2(c,journal,state.record,scope)){rememberV2(Json.bad("foreign V2 preservation completion"));failed=true;continue;}
            if(scope.released){if(scope.counted){rememberV2(Json.bad("released V2 scope remains counted"));failed=true;}continue;}
            boolean registered=state.record.fieldPreservation==scope;
            boolean cleanRegistration=registered||state.record.fieldPreservation==null;
            boolean balanced=cleanRegistration&&scope.callbacks==0&&scope.hooks.isEmpty()&&!scope.checking;
            if(registered)state.record.fieldPreservation=null;
            scope.ended=true;
            if(!scope.entered&&!scope.counted&&scope.phase==NativeAppearanceViewsV2.FieldPreservation.CAPTURED&&balanced){
                scope.released=true;scope.phase=NativeAppearanceViewsV2.FieldPreservation.RELEASED;continue;
            }
            scope.phase=NativeAppearanceViewsV2.FieldPreservation.FAILED_HELD;
            scope.releaseReady=balanced&&scope.entered&&scope.counted&&funded;
            if(!scope.releaseReady){rememberV2(Json.bad("unbalanced V2 preservation completion"));failed=true;}
            // No reporter executes after the release phase starts. Unentered refusal has no native prefix.
            if(scope.entered){
                Throwable observed=primary!=null?primary:v2Cleanup.primary;
                if(observed!=null)try{scope.field.preservationFailure(observed);}catch(RuntimeException|java.lang.Error report){rememberV2(report);}
            }
        }
        if(failed)try{terminalV2(NativeEnvironmentV2.RendererCause.CANCELLATION_FAILED,v2Cleanup.primary,v2Cleanup.firstFatal);}
        catch(RuntimeException|java.lang.Error report){rememberV2(report);}
        // Reporters may reenter hostile fixtures; preflight all final identities before any decrement.
        boolean members=preservationMembershipV2(journal);
        if(!members){
            rememberV2(Json.bad("changed V2 failed preservation membership"));
            try{terminalV2(NativeEnvironmentV2.RendererCause.CANCELLATION_FAILED,v2Cleanup.primary,v2Cleanup.firstFatal);}
            catch(RuntimeException|java.lang.Error report){rememberV2(report);}
        }
        // An unproven roster never enters either release loop, including after reporter reentry.
        if(members){
        funded=preservationFailureFundedV2(c);
        for(int i=0;i<journal.stateCount;i++){NativeState state=journal.states[i];var scope=state.preservation;
            if(scope!=null&&scope.releaseReady&&(!funded||!fieldPreservationIdentityV2(c,journal,state.record,scope)||!preservationEndReadyV2(scope)))scope.releaseReady=false;
        }
        for(int i=0;i<journal.stateCount;i++){var scope=journal.states[i].preservation;if(scope!=null&&scope.releaseReady){
            scope.releaseReady=false;scope.counted=false;scope.released=true;scope.phase=NativeAppearanceViewsV2.FieldPreservation.RELEASED;
            c.heldPreservations--;outstandingFieldPreservations--;outstandingEditorNativeCalls--;
        }}
        }
        failedTransitionsV3(c);
        journal.completion=AttachmentJournal.FAILED_DONE;
        if(v2Cleanup.firstFatal!=null)throw v2Cleanup.firstFatal;
    }
    /** Entire cohort preflight, followed by a nonthrowing direct scalar/reference success tail. */
    void finishV2(Candidate c,AttachmentJournal journal){
        if(c==null||c.owner!=this||v2Pending!=c||c.used||!c.attached||journal!=c.journal||journal.complete||journal.failedInvoked||journal.completion!=AttachmentJournal.OPEN)
            throw Json.bad("invalid V2 finish");
        if(!preservationProvenanceV2(c,journal))throw Json.bad("foreign V2 finish preservation");
        boolean members=preservationMembershipV2(journal);
        boolean valid=members&&!v2Retired&&!v2Fence.terminal&&c.operation!=null&&c.operation==v2Fence.operation&&preservationCohortV2(c);
        if(members)for(int i=0;i<journal.stateCount;i++){NativeState state=journal.states[i];var scope=state.preservation;if(scope==null)continue;
            if(!fieldPreservationIdentityV2(c,journal,state.record,scope))throw Json.bad("foreign V2 finish preservation");
            if(!scope.entered||!scope.counted||scope.released||scope.ended||
                scope.phase!=NativeAppearanceViewsV2.FieldPreservation.PRECOMMIT_READY||state.record.fieldPreservation!=scope||state.record.binding!=scope.selected||
                scope.callbacks!=0||!scope.hooks.isEmpty()||scope.checking||editorLossSerial!=scope.lossObservation)valid=false;
        }
        valid=valid&&transitionsReadyV3(c);
        if(!valid){
            v2Fence.terminal=true;v2Fence.drawAllowed=false;v2Fence.inputAllowed=false;sealScalarV2();
            if(v2Cleanup.deferredCause==null)v2Cleanup.deferredCause=NativeEnvironmentV2.RendererCause.TERMINAL_VALIDATION_FAILED;
            throw Json.bad("invalid V2 terminal finish");
        }
        // No call, allocation, throwing guard, reporter, getter or callback below this boundary.
        journal.completion=AttachmentJournal.SUCCESS_IN_PROGRESS;
        for(int i=0;i<journal.stateCount;i++){var member=journal.transitionRoster[i];if(member!=null){var s=member.scope;s.record.fieldTransition=null;s.record.modelSettled=true;s.field.attempt=null;s.registered=false;s.ended=true;outstandingFieldTransitions--;outstandingEditorNativeCalls--;}}
        for(int i=0;i<journal.stateCount;i++){var scope=journal.states[i].preservation;if(scope!=null){
            scope.record.fieldPreservation=null;scope.ended=true;scope.phase=NativeAppearanceViewsV2.FieldPreservation.COMMITTED;
        }}
        packet=c.next;v2PacketBytes=c.bytes;v2Records=c.targets;v2Plan=c.plan;v2Gate=c.gate;v2CommittedEnvironment=c.environment;
        c.used=true;journal.complete=true;v2Pending=null;v2Open=false;c.gate.open=false;
        v2Roster=c.targetRoster;v2RosterCount=c.targetCount;
        for(int i=0;i<journal.stateCount;i++){var scope=journal.states[i].preservation;if(scope!=null){
            scope.counted=false;scope.released=true;c.heldPreservations--;outstandingFieldPreservations--;outstandingEditorNativeCalls--;
        }}
        journal.completion=AttachmentJournal.SUCCESS_DONE;
    }
    void validateAttachedV2(Candidate c,AttachmentJournal journal){
        validateV2(c,true);
        for(var state:c.journal.previous)if(state.transition!=null)state.transition.validateAttached();
        if(journal!=c.journal||journal.complete||journal.failedInvoked||journal.completion!=AttachmentJournal.OPEN||!preservationMembershipV2(journal))throw Json.bad("foreign V2 journal");
        for(int i=0;i<journal.stateCount;i++){NativeState state=journal.states[i];var scope=state.preservation;if(scope==null)continue;
            scope.exact();
            if(!fieldPreservationIdentityV2(c,journal,state.record,scope)||!scope.original.current()||v2Pending!=c||c.used||!c.attached||
                c.operation!=v2Fence.operation||v2Fence.terminal||state.record.binding!=scope.selected||editorLossSerial!=scope.lossObservation||
                !scope.entered||!scope.counted||scope.ended||scope.released||scope.callbacks!=0||!scope.hooks.isEmpty()||scope.checking||!preservationCohortV2(c))
                throw Json.bad("invalid V2 precommit preservation");
        }
        if(!preservationCohortV2(c))throw Json.bad("invalid V2 precommit cohort");
        for(int i=0;i<journal.stateCount;i++){NativeState state=journal.states[i];var scope=state.preservation;if(scope!=null&&
            (!fieldPreservationIdentityV2(c,journal,state.record,scope)||state.record.fieldPreservation!=scope||state.record.binding!=scope.selected||
             scope.ended||scope.released||!scope.entered||!scope.counted||scope.callbacks!=0||!scope.hooks.isEmpty()||scope.checking||editorLossSerial!=scope.lossObservation))
                throw Json.bad("changed V2 final precommit cohort");}
        for(int i=0;i<journal.stateCount;i++){var scope=journal.states[i].preservation;if(scope!=null)scope.phase=NativeAppearanceViewsV2.FieldPreservation.PRECOMMIT_READY;}
    }
    void rollbackV2(Candidate c,AttachmentJournal journal){
        NativeEnvironmentV2.requireMain();if(c==null||c.owner!=this||v2Pending!=c||c.used||journal!=c.journal||journal.complete||c.originalMutation==null)throw Json.bad("invalid V2 rollback");
        NativeAppearanceViewsV2.Mutation previousMutation=v2Mutation;
        v2Mutation=c.originalMutation;
        sealScalarV2();c.gate.open=false;
        try{restoreV2(c);revokePreservationsV2(c,NativeAppearanceViewsV2.FieldPreservation.RESTORED_HELD);c.used=true;journal.complete=true;v2Pending=null;}
        catch(RuntimeException|java.lang.Error failure){
            rememberV2(failure);
            try{terminalV2(NativeEnvironmentV2.RendererCause.ROLLBACK_FAILED,failure,v2Cleanup.firstFatal);}catch(RuntimeException|java.lang.Error report){rememberV2(report);}
            c.used=true;v2Pending=null;if(v2Cleanup.firstFatal!=null)throw v2Cleanup.firstFatal;throw failure;
        }finally{v2Mutation=previousMutation;}
    }
    void discardV2(Candidate c){NativeEnvironmentV2.requireMain();if(c==null||c.owner!=this||v2Pending!=c||c.used||c.attached)throw Json.bad("invalid V2 discard");c.used=true;v2Pending=null;}
    private void restoreV2(Candidate c){
        requireTransactionV2(c.operation);
        NativeAppearanceViewsV2.Mutation mutation=c.originalMutation;
        if(mutation==null||mutation!=v2Mutation||mutation.fence!=v2Fence||mutation.token!=c.operation)throw Json.bad("missing exact V2 restore original");
        mutation.require();
        if(v2RollbackFault)throw new IllegalStateException("test-only rollback fault");
        for(NativeState state:c.journal.previous){var r=state.record;boolean preserve=state.transition==null&&(state.active||state.forwardPreserved);
            if(state.transition!=null)state.transition.phase=NativeAppearanceViewsV2.FieldTransition.RESTORING;
            if(state.forwardPreserved){if(state.preservation==null||state.preservation.ended||r.fieldPreservation!=state.preservation)throw Json.bad("preserved field restoration authority ended");state.preservation.phase=NativeAppearanceViewsV2.FieldPreservation.RESTORING;state.preservation.exact();}
            r.bind(state.binding,state.geometry,preserve,state.transition==null?mutation:state.transition.mutation);
            if(!preserve&&r.view instanceof TextView text&&state.text!=null){r.changing=true;try{if(state.transition==null)text.setText(state.text);else state.transition.restoreText();mutation.require();

                if(text instanceof EditText edit&&state.selectionStart>=0)edit.setSelection(state.selectionStart,state.selectionEnd);mutation.require();
}finally{r.changing=false;}}
        }
        for(NativeState state:c.journal.previous){var r=state.record;
            r.changing=true;try{if(r.view instanceof Switch value)value.setChecked(state.checked);mutation.require();
r.view.setPressed(state.pressed);mutation.require();
}finally{r.changing=false;}
            r.cancelToggleInput();}
        for(ParentState parent:c.journal.parents)restoreParentV2(parent.parent,parent.children,mutation);
        for(var old:c.baseRecords.values())if(old.group!=null)old.group.records=c.baseRecords;
        restoreParentV2(c.environment.root(),c.journal.rootChildren,mutation);
        if(c.journal.oldGate!=null)c.journal.oldGate.canvasColor=c.journal.oldCanvas;
        if(c.journal.oldGate!=null&&c.base!=null){var old=v2Records.get(c.base.root.id);
            NativeAppearanceViewsV2.layoutRoot(old,c.journal.rootWidth,c.journal.rootHeight,old.binding.plan().environment.safeArea64(),mutation);}
        for(NativeState state:c.journal.previous)if(state.transition!=null)state.transition.restoreSnapshot();
        for(NativeState state:c.journal.previous)if(state.focused&&!state.record.view.hasFocus()){state.record.view.requestFocus();mutation.require();}

        for(NativeState state:c.journal.previous)if(state.record.view.getScrollX()!=state.scrollX||state.record.view.getScrollY()!=state.scrollY){
            state.record.view.scrollTo(state.scrollX,state.scrollY);mutation.require();}

        sealScalarV2();
    }
    private static void restoreParentV2(ViewGroup parent,View[] children,NativeAppearanceViewsV2.Mutation mutation){mutation.require();
        for(int i=parent.getChildCount()-1;i>=0;i--)if(!Arrays.asList(children).contains(parent.getChildAt(i))){parent.removeViewAt(i);mutation.require();}

        for(int i=0;i<children.length;i++){View view=children[i];if(i<parent.getChildCount()&&parent.getChildAt(i)==view)continue;
            if(view.getParent() instanceof ViewGroup previous)previous.removeView(view);mutation.require();
parent.addView(view,i);mutation.require();
}
    }
    static final class DisposalEffect {
        final View gate;final NativeAppearanceViewsV2.Record[] roster;final int count;final Candidate pending;
        final NativeAppearanceViewsV2.Record[] targets,detached;final int targetCount,detachedCount;
        DisposalEffect(View gate,NativeRenderer renderer){
            this.gate=gate;roster=renderer.v2Roster;count=renderer.v2RosterCount;pending=renderer.v2Pending;
            targets=pending==null?null:pending.targetRoster;targetCount=pending==null?0:pending.targetCount;
            detached=pending==null?null:pending.detachedRoster;detachedCount=pending==null?0:pending.detachedCount;
        }
    }
    private DisposalEffect disposalEffect;
    boolean fieldDisposalCurrent(NativeAppearanceViewsV2.FieldDisposal scope) {
        DisposalEffect effect=disposalEffect;
        if(effect==null||scope.effect!=effect||scope.renderer!=this||scope.record.editorFence!=v2Fence||scope.record.input!=v2Input||
            !v2Disposed||!v2Retired||!v2Fence.terminal||v2Fence.drawAllowed||v2Fence.inputAllowed||
            effect.roster!=v2Roster||effect.count!=v2RosterCount||effect.pending!=v2Pending||
            effect.pending!=null&&(effect.targets!=effect.pending.targetRoster||effect.targetCount!=effect.pending.targetCount||
                effect.detached!=effect.pending.detachedRoster||effect.detachedCount!=effect.pending.detachedCount)||
            effect.gate!=v2Gate&&(v2Pending==null||effect.gate!=v2Pending.gate)||!retainedEditorV2(scope.record))return false;
        View cursor=scope.field;
        for(int i=0;i<effect.count+effect.targetCount+effect.detachedCount+2;i++){
            if(cursor==effect.gate)return true;
            if(!(cursor.getParent() instanceof View parent))return false;cursor=parent;
        }
        return false;
    }
    private void hideDisposedGateV2(View gate) {
        if(gate==null)return;
        if(disposalEffect!=null||outstandingEditorNativeCalls!=0)throw Json.bad("disposal effect already active");
        DisposalEffect effect=new DisposalEffect(gate,this);
        ArrayList<NativeAppearanceViewsV2.FieldDisposal> scopes=new ArrayList<>();
        addDisposalFieldsV2(scopes,effect,effect.roster,effect.count);
        addDisposalFieldsV2(scopes,effect,effect.targets,effect.targetCount);
        addDisposalFieldsV2(scopes,effect,effect.detached,effect.detachedCount);
        disposalEffect=effect;outstandingEditorNativeCalls++;
        try {
            for(var scope:scopes)scope.record.fieldDisposal=scope;
            gate.setVisibility(View.INVISIBLE);
        }finally{
            for(var scope:scopes){scope.ended=true;if(scope.record.fieldDisposal==scope)scope.record.fieldDisposal=null;}
            disposalEffect=null;outstandingEditorNativeCalls--;
        }
    }
    private void addDisposalFieldsV2(ArrayList<NativeAppearanceViewsV2.FieldDisposal> scopes,DisposalEffect effect,NativeAppearanceViewsV2.Record[] roster,int count){
        for(int i=0;i<count;i++){
            var record=roster[i];if(record==null||!(record.view instanceof NativeAppearanceViewsV2.NativeField field)||!field.disposalEligible())continue;
            boolean duplicate=false;for(var prior:scopes)if(prior.record==record){duplicate=true;break;}
            if(!duplicate)scopes.add(new NativeAppearanceViewsV2.FieldDisposal(this,effect,record));
        }
    }
    void disposeV2(){
        NativeEnvironmentV2.requireMain();if(v2Disposed)return;v2Disposed=true;
        v2Retired=true;v2Fence.terminal=true;v2Fence.drawAllowed=false;v2Fence.inputAllowed=false;sealScalarV2();
        Throwable failure=null;
        try{cancelInputV2(v2Fence.sealSerial);}catch(RuntimeException|java.lang.Error cleanup){failure=cleanup;rememberV2(cleanup);}
        try{hideDisposedGateV2(v2Gate);}catch(RuntimeException|java.lang.Error cleanup){rememberV2(cleanup);if(failure==null)failure=cleanup;}
        try{if(v2Pending!=null&&v2Pending.gate!=v2Gate)hideDisposedGateV2(v2Pending.gate);}catch(RuntimeException|java.lang.Error cleanup){rememberV2(cleanup);if(failure==null)failure=cleanup;}
        if(v2Cleanup.firstFatal!=null)throw v2Cleanup.firstFatal;
        if(v2Cleanup.primary instanceof RuntimeException ordinary)throw ordinary;
    }
    boolean cancellationInProgressV2(){NativeEnvironmentV2.requireMain();return v2Cleanup.inProgress;}
    void cancelInputV2(long serial){
        NativeEnvironmentV2.requireMain();
        if(serial!=v2Fence.sealSerial||v2Fence.drawAllowed||v2Fence.inputAllowed)throw Json.bad("unsealed V2 cancellation");
        if(v2Fence.terminal||v2Retired)retireEditorsV2();
        if(serial>v2Cleanup.requestedSerial)v2Cleanup.requestedSerial=serial;
        if(v2Cleanup.inProgress||serial<=v2Cleanup.consumedSerial){if(v2Cleanup.firstFatal!=null)throw v2Cleanup.firstFatal;if(v2Cleanup.primary instanceof RuntimeException failure)throw failure;return;}
        v2Cleanup.inProgress=true;v2Cleanup.consumedSerial=serial;
        // Fixed snapshots and consumed record claims survive all recursive notices.
        NativeAppearanceViewsV2.Record[] current=v2Roster;
        int currentCount=v2RosterCount;
        Candidate pending=v2Pending;
        NativeAppearanceViewsV2.Record[] targets=pending==null?null:pending.targetRoster,detached=pending==null?null:pending.detachedRoster;
        int targetCount=pending==null?0:pending.targetCount,detachedCount=pending==null?0:pending.detachedCount;
        try{
            try{if(v2Gate!=null)v2Gate.invalidate();}catch(RuntimeException|java.lang.Error failure){rememberV2(failure);}
            cancelRosterV2(current,currentCount,serial);cancelRosterV2(targets,targetCount,serial);cancelRosterV2(detached,detachedCount,serial);
            v2Cleanup.consumedSerial=v2Cleanup.requestedSerial;
        }finally{v2Cleanup.inProgress=false;}
        if(v2Cleanup.primary!=null&&!v2Disposed)terminalV2(NativeEnvironmentV2.RendererCause.CANCELLATION_FAILED,v2Cleanup.primary,v2Cleanup.firstFatal);
        if(v2Cleanup.firstFatal!=null)throw v2Cleanup.firstFatal;
        if(v2Cleanup.primary instanceof RuntimeException ordinary)throw ordinary;
    }
    private void cancelRosterV2(NativeAppearanceViewsV2.Record[] records,int count,long serial){
        for(int i=0;i<count;i++){
            NativeAppearanceViewsV2.Record record=records[i];if(record==null||record.cancelClaim==serial)continue;
            record.cancelClaim=serial;v2Cleanup.attempts++;
            try{record.cancelToggleInput();}catch(RuntimeException|java.lang.Error failure){
                rememberV2(record.cancellationOrdinary);rememberV2(record.cancellationFatal);rememberV2(failure);
            }
        }
    }
    private void rememberV2(Throwable failure){if(failure==null)return;if(v2Cleanup.primary==null)v2Cleanup.primary=failure;
        if(failure instanceof java.lang.Error fatal&&v2Cleanup.firstFatal==null)v2Cleanup.firstFatal=fatal;}
    private void terminalV2(NativeEnvironmentV2.RendererCause cause,Throwable primary,java.lang.Error firstFatal){
        v2Fence.terminal=true;v2Fence.drawAllowed=false;v2Fence.inputAllowed=false;sealScalarV2();v2Retired=true;
        rememberV2(primary);rememberV2(firstFatal);
        if(v2Cleanup.cause==null)v2Cleanup.cause=cause;
        if(v2Fence.commitFinish){if(v2Cleanup.deferredCause==null)v2Cleanup.deferredCause=cause;return;}
        if(v2ReportClaimed||v2Disposed)return;v2ReportClaimed=true;v2Fence.rendererReportActive=true;
        try{v2Environment.rendererTerminal(this,v2Cleanup.cause,primary,firstFatal);}
        finally{v2Fence.rendererReportActive=false;}
    }
    void reportDeferredTerminalV2(){NativeEnvironmentV2.requireMain();if(v2Fence.commitFinish)throw Json.bad("V2 report inside commit/finish");
        if(v2Cleanup.deferredCause!=null){NativeEnvironmentV2.RendererCause cause=v2Cleanup.deferredCause;v2Cleanup.deferredCause=null;terminalV2(cause,v2Cleanup.primary,v2Cleanup.firstFatal);}}
    void retireV2(){NativeEnvironmentV2.requireMain();terminalV2(NativeEnvironmentV2.RendererCause.TERMINAL_VALIDATION_FAILED,null,null);}
    private void requireV2Live(){
        if(v2Fence==null||v2Environment==null)throw Json.bad("explicit V2 binding required");
        if(Build.VERSION.SDK_INT<36)throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);
        if(v2Retired||v2Fence.terminal)throw Json.bad("V2 owner retired");
        if(packet!=null&&v2Plan==null)throw Json.bad("V2 requires a fresh native owner");
    }
    private void faultV2(){if(v2Fault>=0&&v2Steps++==v2Fault)throw new IllegalStateException("test-only V2 attachment fault");}
    // Package-private fault injection is confined to this concrete owner; it grants no native support authority.
    void testFaultV2(int attachmentStep,boolean rollback){NativeEnvironmentV2.requireMain();v2Fault=attachmentStep;v2RollbackFault=rollback;}
    void testExhaustInteractionV2(){NativeEnvironmentV2.requireMain();v2Interaction=Long.MAX_VALUE;}
    boolean testRetiredV2(){NativeEnvironmentV2.requireMain();return v2Retired;}
    Map<String,NativeAppearanceViewsV2.Record> inspectV2(){NativeEnvironmentV2.requireMain();return v2Records;}

}
