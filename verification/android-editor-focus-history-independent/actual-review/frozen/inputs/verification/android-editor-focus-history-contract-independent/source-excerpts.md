# Released frozen source excerpts

## NativeRenderer.java:93–109

```java
93:     boolean editorDisposalBusyV2(){NativeEnvironmentV2.requireMain();return outstandingEditorNativeCalls!=0||editorDrain!=null||editorFinishing!=null||editorReplacement!=null;}
94:     private boolean retainedEditorV2(NativeAppearanceViewsV2.Record record) {
95:         if(record==null)return false;
96:         for(int i=0;i<v2RosterCount;i++)if(v2Roster[i]==record)return true;
97:         Candidate pending=v2Pending;
98:         if(pending!=null){for(int i=0;i<pending.targetCount;i++)if(pending.targetRoster[i]==record)return true;
99:             for(int i=0;i<pending.detachedCount;i++)if(pending.detachedRoster[i]==record)return true;}
100:         return false;
101:     }
102:     private void requireEditorsAvailableV2(){
103:         for(int i=0;i<v2RosterCount;i++)if(v2Roster[i]!=null)v2Roster[i].editorAvailable(true);
104:         Candidate pending=v2Pending;
105:         if(pending!=null){for(int i=0;i<pending.targetCount;i++)if(pending.targetRoster[i]!=null)pending.targetRoster[i].editorAvailable(true);
106:             for(int i=0;i<pending.detachedCount;i++)if(pending.detachedRoster[i]!=null)pending.detachedRoster[i].editorAvailable(true);}
107:     }
108:     private void retireEditorsV2(){
109:         NativeAppearanceViewsV2.Record[] current=v2Roster;int count=v2RosterCount;Candidate pending=v2Pending;
```

## NativeRenderer.java:137–173

```java
137:     private NativeAppearanceViewsV2.Input inputV2(){if(v2Input==null)v2Input=new NativeAppearanceViewsV2.Input(){
138:         public NativeAppearanceViewsV2.Mutation mutation(){return mutationV2();}
139:         public boolean editorDispatchAvailable(NativeAppearanceViewsV2.Record record){NativeEnvironmentV2.requireMain();return editorReplacement==null&&retainedEditorV2(record);}
140:         public boolean editorRetained(NativeAppearanceViewsV2.Record record){NativeEnvironmentV2.requireMain();return retainedEditorV2(record);}
141:         public void editorEnter(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
142:             NativeEnvironmentV2.requireMain();
143:             if(lease==null||lease.record!=record||record.view!=lease.field||!retainedEditorV2(record)||lease.entered||lease.ended||outstandingEditorNativeCalls==Integer.MAX_VALUE)
144:                 throw Json.bad("invalid editor native lease entry");
145:             outstandingEditorNativeCalls++;
146:         }
147:         public void editorLeave(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
148:             NativeEnvironmentV2.requireMain();
149:             if(lease==null||lease.record!=record||!lease.entered||!lease.ended||outstandingEditorNativeCalls<=0)
150:                 throw Json.bad("invalid editor native lease exit");
151:             outstandingEditorNativeCalls--;
152:         }
153:         public boolean editorCloseAllowed(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.NativeField.Attempt attempt){
154:             NativeEnvironmentV2.requireMain();return outstandingEditorNativeCalls==0&&!v2Fence.commitFinish&&v2Fence.operation==null&&
155:                 (editorReplacement==null||editorReplacement.permitsPredecessor(record,attempt));
156:         }
157:         public void replacementBegin(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Replacement replacement){
158:             NativeEnvironmentV2.requireMain();
159:             if(editorReplacement!=null||outstandingEditorNativeCalls!=0||editorDrain!=null||editorFinishing!=null||v2Fence.commitFinish||v2Fence.operation!=null||
160:                 replacement==null||replacement.record!=record||record.view!=replacement.field||!retainedEditorV2(record))throw Json.bad("replacement reservation unavailable");
161:             editorReplacement=replacement;
162:         }
163:         public void replacementEnd(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Replacement replacement){
164:             NativeEnvironmentV2.requireMain();
165:             if(editorReplacement!=replacement||replacement.record!=record||replacement.nativeExecuting||replacement.setterActive||replacement.callbacks!=0||
166:                 record.replacementCallback!=null||replacement.stage!=NativeAppearanceViewsV2.Replacement.Stage.DONE||!replacement.endReady()||outstandingEditorNativeCalls!=0||editorDrain!=null||editorFinishing!=null)throw Json.bad("unfinished replacement reservation");
167:             editorReplacement=null;
168:         }
169:         public NativeAppearanceViewsV2.Mutation editorCleanupMutation(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
170:             NativeEnvironmentV2.requireMain();
171:             if(lease==null||lease.record!=record||record.editorCallbackLease!=lease)throw Json.bad("foreign editor cleanup continuation");
172:             lease.exact();NativeAppearanceViewsV2.Mutation scope=NativeAppearanceViewsV2.Mutation.editorCleanup(v2Fence,lease);scope.require();return scope;
173:         }
```

## NativeRenderer.java:274–312

```java
274:     }
275:     static final class AttachmentJournal {
276:         private final Candidate candidate;
277:         private final List<NativeState> previous;
278:         private final List<ParentState> parents;
279:         private final View[] rootChildren;
280:         private final NativeAppearanceViewsV2.Gate oldGate;
281:         private final int rootWidth,rootHeight,oldCanvas;
282:         private boolean complete;
283:         private AttachmentJournal(Candidate candidate){
284:             this.candidate=candidate;previous=new ArrayList<>();parents=new ArrayList<>();
285:             for(var record:candidate.baseRecords.values()){
286:                 previous.add(new NativeState(record));
287:                 if(record.group!=null)parents.add(new ParentState(record.group));
288:             }
289:             FrameLayout root=candidate.environment.root();rootChildren=childrenV2(root);
290:             rootWidth=root.getWidth();rootHeight=root.getHeight();oldGate=candidate.owner.v2Gate;oldCanvas=oldGate==null?0:oldGate.canvasColor;if(oldGate!=null)parents.add(new ParentState(oldGate));
291:         }
292:     }
293:     private static final class NativeState {
294:         final NativeAppearanceViewsV2.Record record;
295:         final NativeAppearanceViewsV2.Binding binding;
296:         final NativeAppearanceViewsV2.Geometry geometry;
297:         final CharSequence text,nativeBuffer;
298:         final List<CompositionSpan> composition;
299:         final int[] drawableState,windowPosition;
300:         final int left,top,right,bottom,measuredWidth,measuredHeight;
301:         final boolean enabled;
302:         final int selectionStart,selectionEnd,scrollX,scrollY;final boolean active,checked,focused,pressed;
303:         NativeState(NativeAppearanceViewsV2.Record record){
304:             this.record=record;binding=record.binding;geometry=record.geometry;active=record.view instanceof EditText e&&(e.hasFocus()||android.view.inputmethod.BaseInputConnection.getComposingSpanStart(e.getText())>=0)||record.view instanceof TextView t&&t.isTextSelectable()&&t.getSelectionStart()>=0;
305:             nativeBuffer=record.view instanceof TextView t?t.getText():null;
306:             // Copy only text value. Copying native watcher spans can notify the live editor.
307:             text=nativeBuffer==null?null:nativeBuffer.toString();
308:             composition=compositionV2(nativeBuffer);
309:             drawableState=record.view.getDrawableState().clone();windowPosition=new int[2];record.view.getLocationInWindow(windowPosition);
310:             left=record.view.getLeft();top=record.view.getTop();right=record.view.getRight();bottom=record.view.getBottom();
311:             measuredWidth=record.view.getMeasuredWidth();measuredHeight=record.view.getMeasuredHeight();enabled=record.view.isEnabled();
312:             selectionStart=record.view instanceof TextView t?t.getSelectionStart():-1;
```

## NativeRenderer.java:460–510

```java
460:         while(current!=null){String before=parentV2(c.base,current),after=parentV2(c.next,current);if(!Objects.equals(before,after))return false;
461:             if(before!=null){UiPacket.Node a=c.base.nodes.get(before),b=c.next.nodes.get(after);if(b==null||!a.kind.equals(b.kind)||!a.generation.equals(b.generation))return false;
462:                 List<String> ac=new ArrayList<>(),bc=new ArrayList<>();for(var n:a.children)ac.add(n.id);for(var n:b.children)bc.add(n.id);if(!ac.equals(bc))return false;}
463:             current=before;}return true;}
464:     private void validateV2(Candidate c,boolean attached){
465:         NativeEnvironmentV2.requireMain();requireEditorsAvailableV2();requireV2Live();
466:         if(c==null||c.owner!=this||v2Pending!=c||c.used||c.attached!=attached||packet!=c.base||v2Records!=c.baseRecords||v2Installed!=c.installed)throw Json.bad("stale/foreign/consumed V2 candidate");
467:         requireTransactionV2(c.operation);
468:         if(v2Interaction!=c.interaction)throw Json.bad("stale V2 native interaction epoch "+c.interaction+" -> "+v2Interaction);
469:         if(!c.environment.current(this))throw Json.bad("stale V2 native environment");
470:         if(!attached&&!sameNativeBaseV2(c.journal))throw Json.bad("stale V2 native canvas");
471:     }
472:     AttachmentJournal attachV2(Candidate c,FrameLayout root){
473:         requireEditorsAvailableV2();validateV2(c,false);if(root!=c.environment.root())throw Json.bad("foreign V2 root");preflightEditorsV2(c);
474:         NativeAppearanceViewsV2.Mutation previousMutation=v2Mutation;
475:         v2Mutation=NativeAppearanceViewsV2.Mutation.transaction(v2Fence,c.operation);
476:         NativeAppearanceViewsV2.Mutation mutation=v2Mutation;
477:         sealScalarV2();c.gate.open=false;c.gate.canvasColor=NativeAppearanceViewsV2.color(c.plan.canvas);v2Steps=0;
478:         try {
479:             for(var entry:c.targets.entrySet()){
480:                 var target=entry.getValue();var shadow=c.detached.get(entry.getKey());
481:                 if(target!=shadow){boolean preserve=target.view instanceof TextView&&sameEditorBindingV2(target,shadow);
482:                     target.bind(shadow.binding,shadow.geometry,preserve,mutation);}
483:                 faultV2();
484:             }
485:             for(var target:c.targets.values()){NativeAppearanceViewsV2.installChildren(target,c.targets,mutation);faultV2();}
486:             View desired=c.targets.get(c.next.root.id).view;
487:             if(desired.getParent()!=c.gate){if(desired.getParent() instanceof ViewGroup previous)previous.removeView(desired);mutation.require();
488: c.gate.addView(desired);mutation.require();
489: }
490:             for(int i=c.gate.getChildCount()-1;i>=0;i--)if(c.gate.getChildAt(i)!=desired){c.gate.removeViewAt(i);mutation.require();}
491: 
492:             faultV2();
493:             if(c.gate.getParent()!=root){if(c.gate.getParent() instanceof ViewGroup previous)previous.removeView(c.gate);mutation.require();
494: root.addView(c.gate,new FrameLayout.LayoutParams(-1,-1));mutation.require();
495: }
496:             for(int i=root.getChildCount()-1;i>=0;i--)if(root.getChildAt(i)!=c.gate){root.removeViewAt(i);mutation.require();}
497: 
498:             c.gate.measure(View.MeasureSpec.makeMeasureSpec(root.getWidth(),View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(root.getHeight(),View.MeasureSpec.EXACTLY));mutation.require();
499: 
500:             c.gate.layout(0,0,root.getWidth(),root.getHeight());mutation.require();
501: 
502:             NativeAppearanceViewsV2.layoutRoot(c.targets.get(c.next.root.id),root.getWidth(),root.getHeight(),c.environment.value.safeArea64(),mutation);
503:             faultV2();c.attached=true;return c.journal;
504:         }catch(RuntimeException|java.lang.Error failure){
505:             if(!v2Fence.terminal)try{restoreV2(c);}catch(RuntimeException|java.lang.Error rollback){
506:                 rememberV2(failure);rememberV2(rollback);terminalV2(NativeEnvironmentV2.RendererCause.ROLLBACK_FAILED,failure,v2Cleanup.firstFatal);}
507:             c.used=true;v2Pending=null;if(v2Cleanup.firstFatal!=null)throw v2Cleanup.firstFatal;throw failure;
508:         }finally{v2Mutation=previousMutation;}
509:     }
510:     /** Scalar/reference checks and prepared swaps only. Coordinator commits engine immediately before this call. */
```

## NativeRenderer.java:534–565

```java
534:         finally{v2Mutation=previousMutation;}
535:     }
536:     void discardV2(Candidate c){NativeEnvironmentV2.requireMain();if(c==null||c.owner!=this||v2Pending!=c||c.used||c.attached)throw Json.bad("invalid V2 discard");c.used=true;v2Pending=null;}
537:     private void restoreV2(Candidate c){
538:         requireTransactionV2(c.operation);
539:         NativeAppearanceViewsV2.Mutation mutation=v2Mutation;mutation.require();
540:         if(v2RollbackFault)throw new IllegalStateException("test-only rollback fault");
541:         for(NativeState state:c.journal.previous){var r=state.record;boolean preserve=state.active;r.bind(state.binding,state.geometry,preserve,mutation);
542:             if(!preserve&&r.view instanceof TextView text&&state.text!=null){r.changing=true;try{text.setText(state.text);mutation.require();
543: 
544:                 if(text instanceof EditText edit&&state.selectionStart>=0)edit.setSelection(state.selectionStart,state.selectionEnd);mutation.require();
545: }finally{r.changing=false;}}
546:         }
547:         for(NativeState state:c.journal.previous){var r=state.record;
548:             r.changing=true;try{if(r.view instanceof Switch value)value.setChecked(state.checked);mutation.require();
549: r.view.setPressed(state.pressed);mutation.require();
550: }finally{r.changing=false;}
551:             r.cancelToggleInput();}
552:         for(ParentState parent:c.journal.parents)restoreParentV2(parent.parent,parent.children,mutation);
553:         for(var old:c.baseRecords.values())if(old.group!=null)old.group.records=c.baseRecords;
554:         restoreParentV2(c.environment.root(),c.journal.rootChildren,mutation);
555:         if(c.journal.oldGate!=null)c.journal.oldGate.canvasColor=c.journal.oldCanvas;
556:         if(c.journal.oldGate!=null&&c.base!=null){var old=v2Records.get(c.base.root.id);
557:             NativeAppearanceViewsV2.layoutRoot(old,c.journal.rootWidth,c.journal.rootHeight,old.binding.plan().environment.safeArea64(),mutation);}
558:         for(NativeState state:c.journal.previous)if(state.focused&&!state.record.view.hasFocus()){state.record.view.requestFocus();mutation.require();}
559: 
560:         for(NativeState state:c.journal.previous)if(state.record.view.getScrollX()!=state.scrollX||state.record.view.getScrollY()!=state.scrollY){
561:             state.record.view.scrollTo(state.scrollX,state.scrollY);mutation.require();}
562: 
563:         sealScalarV2();
564:     }
565:     private static void restoreParentV2(ViewGroup parent,View[] children,NativeAppearanceViewsV2.Mutation mutation){mutation.require();
```

## NativeAppearanceViewsV2.java:65–121

```java
65:     static final class Mutation {
66:         enum Mode { TRANSACTION, LIVE_PRESENTATION, CLEANUP }
67:         final Mode mode;
68:         final NativeOwnerV2.Fence fence;
69:         final OwnerLifecycleV2.Token token;
70:         final EditorLease editorLease;
71:         final Replacement replacementLease;
72:         private Mutation(Mode mode, NativeOwnerV2.Fence fence, OwnerLifecycleV2.Token token) {
73:             this(mode,fence,token,null);
74:         }
75:         private Mutation(Mode mode, NativeOwnerV2.Fence fence, OwnerLifecycleV2.Token token,EditorLease editorLease) {
76:             this(mode,fence,token,editorLease,null);
77:         }
78:         private Mutation(Mode mode,NativeOwnerV2.Fence fence,OwnerLifecycleV2.Token token,EditorLease editorLease,Replacement replacementLease){
79:             this.mode=mode;this.fence=fence;this.token=token;this.editorLease=editorLease;this.replacementLease=replacementLease;
80:         }
81:         static Mutation replacement(Mutation original,Replacement lease,boolean cleanup){return new Mutation(cleanup?Mode.CLEANUP:original.mode,original.fence,cleanup?null:original.token,null,lease);}
82:         static Mutation editorContinuation(Mutation original,EditorLease lease){return new Mutation(original.mode,original.fence,original.token,lease);}
83:         static Mutation editorCleanup(NativeOwnerV2.Fence fence,EditorLease lease){return new Mutation(Mode.CLEANUP,fence,null,lease);}
84:         static Mutation transaction(NativeOwnerV2.Fence fence, OwnerLifecycleV2.Token token) {
85:             Mutation result=new Mutation(Mode.TRANSACTION,fence,token); result.require(); return result;
86:         }
87:         static Mutation live(NativeOwnerV2.Fence fence) {
88:             Mutation result=new Mutation(Mode.LIVE_PRESENTATION,fence,fence.presentation); result.require(); return result;
89:         }
90:         static Mutation cleanup(NativeOwnerV2.Fence fence) { return new Mutation(Mode.CLEANUP,fence,null); }
91:         boolean current() {
92:             if(editorLease!=null)editorLease.exact();
93:             if(replacementLease!=null)replacementLease.exact();
94:             return mode==Mode.CLEANUP ? !fence.drawAllowed&&!fence.inputAllowed :
95:                 !fence.terminal&&token!=null&&(mode==Mode.TRANSACTION ? token==fence.operation : token==fence.presentation&&fence.drawAllowed);
96:         }
97:         void require() {
98:             if(editorLease!=null)editorLease.exact();
99:             if(replacementLease!=null)replacementLease.exact();
100:             if(mode==Mode.CLEANUP) {
101:                 if(fence.drawAllowed||fence.inputAllowed)throw new IllegalStateException("cleanup requires sealed authority");
102:             } else if(fence.terminal||token==null||(mode==Mode.TRANSACTION ? token!=fence.operation :
103:                 token!=fence.presentation||!fence.drawAllowed))throw new IllegalStateException("V2 mutation authority lost");
104:         }
105:         void requireMutation() {
106:             if(replacementLease!=null)throw new IllegalStateException("replacement cannot authorize bind/layout");
107:             if(mode==Mode.CLEANUP)throw new IllegalStateException("cleanup cannot authorize V2 bind/layout");
108:             require();
109:         }
110:         boolean result(boolean result) {
111:             if(editorLease!=null)editorLease.exact();
112:             if(replacementLease!=null)replacementLease.exact();
113:             // Observe the original captured scope after the delegate. A completed result is not a new mutation.
114:             if(mode!=Mode.LIVE_PRESENTATION){require();return result;}
115:             boolean same=!fence.terminal&&token!=null&&token==fence.presentation&&fence.drawAllowed;
116:             if(same)return result;
117:             // A synchronous accepted feature event can publish a successor before the delegate returns.
118:             // No native call, event, mutation, or replacement scope is acquired on this return path.
119:             return token!=null&&!fence.terminal&&fence.drawAllowed&&fence.presentation!=null&&token!=fence.presentation&&result;
120:         }
121:         <T> T result(T result) { require(); return result; }
```

## NativeAppearanceViewsV2.java:180–203

```java
180:             return !(view instanceof NativeField field)||field.eventsAllowed();
181:         }
182:         boolean editorConstruction() { return scoped!=null&&!constructed; }
183:         Mutation mutation() {
184:             NativeEnvironmentV2.requireMain();
185:             if(replacementCallback!=null)return replacementCallback.continuation();
186:             if(editorCallbackLease!=null)return editorCallbackLease.continuation();
187:             return scoped!=null?scoped:input.mutation();
188:         }
189:         void editorAvailable(boolean preserve) {
190:             NativeEnvironmentV2.requireMain();
191:             if(view instanceof NativeField field)field.available(preserve);
192:         }
193:         void retireEditor() {
194:             if(view instanceof NativeField field)field.retirePermanent();
195:         }
196:         Record(Context context, UiPacket.Node source, Input input, Mutation mutation) {
197:             mutation.requireMutation();scoped=mutation;
198:             id=source.id; generation=source.generation; kind=source.kind; this.input=input;editorFence=mutation.fence;
199:             try {
200:             Group container=null; TextView title=null, small=null;
201:             switch(kind) {
202:                 case "text" -> { view=new TextView(context);mutation.require(); }
203:                 case "button" -> { view=new NativeButton(context,this);mutation.require(); }
```

## NativeAppearanceViewsV2.java:282–300

```java
282:         void bind(Binding next, Geometry measured, boolean preserveEditor, Mutation mutation) {
283:             mutation.requireMutation();editorAvailable(preserveEditor);Mutation previousScope=scoped;scoped=mutation;
284:             boolean previousChanging=changing;
285:             try {
286:                 cancelToggleInput();mutation.require();changing=true;
287:                 binding=next; geometry=measured;
288:                 if(!preserveEditor) {
289:                     view.setEnabled(!next.node.disabled());mutation.require();
290: 
291:                     view.setLayoutDirection(next.rtl()?View.LAYOUT_DIRECTION_RTL:View.LAYOUT_DIRECTION_LTR);mutation.require();
292: 
293:                     view.setTag(next.source.text("accessibilityIdentifier",id));mutation.require();
294: 
295:                     view.setContentDescription(next.source.text("accessibilityLabel",kind.equals("textField")?next.source.text("label",""):null));mutation.require();
296: 
297:                     view.setTooltipText(next.source.text("accessibilityHint",null));mutation.require();
298: 
299:                     if(android.os.Build.VERSION.SDK_INT>=30)view.setStateDescription(next.source.text("accessibilityValue",null));mutation.require();
300: 
```

## NativeAppearanceViewsV2.java:358–365

```java
358: compact.setVisibility(measured.collapsed&&r.compactTitle()!=null?View.VISIBLE:View.INVISIBLE);mutation.require();
359: 
360:                 }
361:                 view.invalidate();mutation.require();
362: 
363:             } finally { changing=previousChanging; scoped=previousScope; }
364:         }
365:     }
```

## NativeAppearanceViewsV2.java:946–978

```java
946:         private boolean denied(){return permanent||focusLost||windowFocusLost||windowHidden||aggregateHidden||viewHidden||detached;}
947:         boolean eventsAllowed() {
948:             NativeEnvironmentV2.requireMain();
949:             return record!=null&&replacement==null&&!finishing&&!denied()&&phase!=Phase.CREATING&&phase!=Phase.DRAINING&&phase!=Phase.CLOSING&&phase!=Phase.QUARANTINED&&
950:                 (attempt==null||!attempt.revoked);
951:         }
952:         private boolean live() {
953:             return record!=null&&record.view==this&&record.constructed&&record.binding!=null&&!record.changing&&replacement==null&&!finishing&&!denied()&&
954:                 phase!=Phase.CREATING&&phase!=Phase.DRAINING&&phase!=Phase.CLOSING&&phase!=Phase.QUARANTINED&&
955:                 record.input.editorDispatchAvailable(record)&&record.input.editorRetained(record)&&record.input.open(record)&&hasFocus();
956:         }
957:         private boolean replacementLive(){
958:             return record!=null&&record.view==this&&record.constructed&&record.binding!=null&&!record.changing&&replacement==null&&!finishing&&!denied()&&
959:                 phase!=Phase.CREATING&&phase!=Phase.DRAINING&&phase!=Phase.CLOSING&&phase!=Phase.QUARANTINED&&
960:                 record.input.editorDispatchAvailable(record)&&record.input.editorRetained(record)&&record.input.open(record);
961:         }
962:         boolean hasLiveTarget(){return attempt!=null&&attempt.target!=null&&!attempt.revoked&&attempt.close==Close.NOT_REQUESTED;}
963:         void available(boolean preserve) {
964:             NativeEnvironmentV2.requireMain();
965:             if(construction())return;
966:             if(replacement!=null||finishing||denied()||phase==Phase.CREATING||phase==Phase.DRAINING||phase==Phase.CLOSING||phase==Phase.QUARANTINED)
967:                 throw new IllegalStateException("editor replacement unavailable");
968:             if(depth!=0&&!preserve)throw new IllegalStateException("editor native frame active");
969:             if(!preserve&&attempt!=null&&attempt.close!=Close.RETURNED&&attempt.close!=Close.NO_TARGET) {
970:                 revoke(false);drain();
971:                 if(phase!=Phase.IDLE)throw new IllegalStateException("editor predecessor not closed");
972:             }
973:         }
974:         void retirePermanent() {NativeEnvironmentV2.requireMain();revoke(true);if(depth==0)drain();surface();}
975:         private EditorLease begin(Attempt expected,Mutation mutation,String hook,boolean nested) {
976:             if(depth>=MAX_DEPTH) {uncertain(new IllegalStateException("editor continuation depth exhausted"));return null;}
977:             EditorLease parent=record.editorCallbackLease;
978:             if(depth!=0&&!nested)return null;
```

## NativeAppearanceViewsV2.java:1170–1210

```java
1170:             try{nativeCall.run();lease.check();if(interaction&&eventsAllowed()&&!record.changing&&record.input.open(record))record.input.interaction();}
1171:             catch(RuntimeException|java.lang.Error failure){uncertain(failure);}
1172:             finally{end(lease);}
1173:             surface();
1174:         }
1175:         void refreshPaint(){if(record!=null&&record.binding!=null){Mutation mutation=record.mutation();mutation.require();setHighlightColor(color(fieldPaint(record).selection()));mutation.require();}}
1176:         @Override protected void drawableStateChanged(){callback("drawable",()->{super.drawableStateChanged();if(record!=null&&eventsAllowed()&&(record.editorCallbackLease==null||record.editorCallbackLease.original.current()))refreshPaint();},false);}
1177:         @Override protected void onSelectionChanged(int start,int end){callback("selection",()->super.onSelectionChanged(start,end),true);}
1178:         private void lifecycle(String hook,boolean loss,Runnable denial,Runnable gain,Runnable nativeCall) {
1179:             NativeEnvironmentV2.requireMain();
1180:             if(record==null){nativeCall.run();return;}
1181:             if(replacement!=null&&replacement.nativeExecuting){
1182:                 try{if(loss){replacement.lost=true;denial.run();revoke(false);}else gain.run();replacement.callback(hook,nativeCall);}
1183:                 catch(RuntimeException|java.lang.Error failure){uncertain(failure);surface();}return;
1184:             }
1185:             if(construction()){Mutation mutation=record.scoped;mutation.requireMutation();nativeCall.run();mutation.require();return;}
1186:             EditorLease parent=record.editorCallbackLease;
1187:             // A public lifecycle entry owns its native super, even with no admitted target.
1188:             Mutation mutation=parent==null?((!record.editorFence.drawAllowed&&!record.editorFence.inputAllowed)?Mutation.cleanup(record.editorFence):entryMutation()):parent.original;
1189:             EditorLease lease=begin(attempt,mutation,hook,true);if(lease==null){surface();return;}
1190:             try {
1191:                 if(loss){denial.run();revoke(false);}else gain.run();
1192:                 nativeCall.run();lease.check();
1193:             }catch(RuntimeException|java.lang.Error failure){uncertain(failure);}
1194:             finally{end(lease);}
1195:             surface();
1196:         }
1197:         @Override protected void onFocusChanged(boolean focused,int direction,android.graphics.Rect old) {
1198:             lifecycle("focus",!focused,()->focusLost=true,()->focusLost=false,()->super.onFocusChanged(focused,direction,old));
1199:         }
1200:         @Override public void onWindowFocusChanged(boolean focused) {
1201:             lifecycle("windowFocus",!focused,()->windowFocusLost=true,()->windowFocusLost=false,()->super.onWindowFocusChanged(focused));
1202:         }
1203:         @Override protected void onWindowVisibilityChanged(int visibility) {
1204:             lifecycle("windowVisibility",visibility!=View.VISIBLE,()->windowHidden=true,()->windowHidden=false,()->super.onWindowVisibilityChanged(visibility));
1205:         }
1206:         @Override public void onVisibilityAggregated(boolean visible) {
1207:             lifecycle("aggregate",!visible,()->aggregateHidden=true,()->aggregateHidden=false,()->super.onVisibilityAggregated(visible));
1208:         }
1209:         @Override protected void onVisibilityChanged(View changed,int visibility) {
1210:             lifecycle("visibility",visibility!=View.VISIBLE,()->viewHidden=true,()->viewHidden=false,()->super.onVisibilityChanged(changed,visibility));
```

## NativeOwnerV2.java:290–327

```java
290:             }
291:         }
292:     }
293:     private void operate(OwnerLifecycleV2.Decision decision, byte[] input) {
294:         activeOperation = decision.token(); fence.operation = decision.token();
295:         NativeCoordinatorV2 owned = coordinator;
296:         Throwable failure = null; boolean committed = false;
297:         effectDepth++;
298:         try {
299:             if (decision.kind() == OwnerLifecycleV2.Kind.OPEN_INITIAL) {
300:                 owned = new NativeCoordinatorV2(activity, root, observer, fence, this::nativeInput);
301:                 opening = owned;
302:                 owned.sealGatesScalar();
303:                 if (!fence.terminal) owned.renderInitial();
304:             } else if (decision.resource() != owned || owned == null) throw new IllegalStateException("foreign coordinator effect");
305:             else if (decision.kind() == OwnerLifecycleV2.Kind.REFRESH_COMMITTED) owned.refreshEnvironment();
306:             else owned.dispatchInput(input);
307:             committed = !fence.terminal && owned != null && owned.hasCommittedPresentation();
308:         } catch (RuntimeException | Error caught) {
309:             failure = caught;
310:             if (owned != null) remember(owned.cleanupLedger().primary());
311:             remember(caught);
312:         }
313:         finally {
314:             effectDepth--;
315:             try {
316:                 if(completionFault!=null)completionFault.run();
317:                 List<OwnerLifecycleV2.Decision> completion = core.complete(activeOperation, owned, committed, failure);
318:                 if (owned != null) coordinator = owned;
319:                 process(completion, null);
320:                 publish();
321:             } catch (RuntimeException | Error caught) { fallback(caught); }
322:             finally { opening = null; activeOperation = null; fence.operation = null; }
323:         }
324:         if (failure != null && !fence.terminal) fail(failure, Cause.OPERATION_FAILED);
325:     }
326:     private void publish() {
327:         OwnerLifecycleV2.Snapshot state = core.snapshot();
```
