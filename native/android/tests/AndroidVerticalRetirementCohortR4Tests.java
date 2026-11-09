package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.widget.FrameLayout;
import android.widget.EditText;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.EditorInfo;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Candidate-only controlled host evidence. No Android runtime or durable storage. */
public final class AndroidVerticalRetirementCohortR4Tests {
    private static byte[] descriptor;
    private static int checks;
    private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    private static Object get(Object value,String name){try{Field f=value.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(value);}catch(ReflectiveOperationException error){throw new AssertionError(error);}}
    private static void set(Object value,String name,Object next){try{Field f=value.getClass().getDeclaredField(name);f.setAccessible(true);f.set(value,next);}catch(ReflectiveOperationException error){throw new AssertionError(error);}}
    private static void write(StringBuilder out,Object value){
        if(value instanceof List<?> list){out.append('[');for(int i=0;i<list.size();i++){if(i>0)out.append(',');write(out,list.get(i));}out.append(']');}
        else if(value instanceof Map<?,?> map){out.append('{');boolean comma=false;for(var e:map.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,e.getKey());out.append(':');write(out,e.getValue());}out.append('}');}
        else Json.write(out,value);
    }
    private static Object node(String id,String kind,Map<String,Object> props,List<Object> children){
        List<Object> actions=kind.equals("button")?List.of(Json.map("id","modelFrame","event","activate")):kind.equals("textField")?List.of(Json.map("id",id+"Change","event","textChange"),Json.map("id",id+"Submit","event","submit")):List.of();
        return Json.map("id",id,"kind",kind,"properties",props,"children",children,"actions",actions);
    }
    private static byte[] frame(long revision,boolean activeFirst,String aMode,String bMode,String aValue){
        Object a=node("fieldA","textField",Json.map("label","Draft A","value",aValue,"axis","vertical","disabled",aMode.equals("disable")),List.of());
        Object b=node("fieldB","textField",Json.map("label","Draft B","value","second","axis","vertical","disabled",bMode.equals("disable")),List.of());
        List<Object> children=new ArrayList<>();children.add(node("title","text",Json.map("text",aMode.equals("enable")?"Edit":"Saving…"),List.of()));
        if(activeFirst){if(!aMode.equals("remove"))children.add(a);if(!bMode.equals("remove"))children.add(b);}
        else {if(!bMode.equals("remove"))children.add(b);if(!aMode.equals("remove"))children.add(a);}
        children.add(node("button","button",Json.map("label","Model frame driver"),List.of()));
        Object root=node("root","vStack",Map.of(),children);
        List<Object> ids=new ArrayList<>();ids.add(Json.map("id","root","generation",new Json.Num("1")));
        for(Object child:children){String id=(String)Json.object(child).get("id");int generation=switch(id){case "title"->2;case "fieldA"->3;case "fieldB"->4;default->5;};ids.add(Json.map("id",id,"generation",new Json.Num(Integer.toString(generation))));}
        StringBuilder out=new StringBuilder();write(out,Json.map("schemaVersion",new Json.Num("1"),"document",Json.map("schemaVersion",new Json.Num("1"),"revision",new Json.Num(Long.toString(revision)),"root",root),"identities",ids));return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static final class Fixture implements AutoCloseable {
        final NativeOwnerV2 owner;final Handler queue;final boolean activeFirst;boolean retainedAuthority;
        Fixture(boolean activeFirst){
            this.activeFirst=activeFirst;Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());
            NativeBridge.reset();NativeBridge.preparedPacket=frame(1,activeFirst,"enable","enable","hello");owner=new NativeOwnerV2(activity,root,null);queue=(Handler)get(owner,"handler");owner.onResume();owner.start();queue.drainAll(4);live("initial frame");
        }
        NativeRenderer renderer(){return (NativeRenderer)get(get(owner,"coordinator"),"renderer");}
        NativeOwnerV2.Fence fence(){return (NativeOwnerV2.Fence)get(owner,"fence");}
        EditText editor(String id){return (EditText)renderer().view(id);}
        void publish(long revision,String a,String b,String value){NativeBridge.preparedPacket=frame(revision,activeFirst,a,b,value);renderer().view("button").performClick();if(!retainedAuthority)queue.drainAll(4);}
        void live(String label){check(!fence().terminal&&owner.hasCommittedPresentation(),label+": "+owner.cleanupLedger().primary());}
        InputConnection compose(){EditText a=editor("fieldA");a.requestFocus();InputConnection c=a.onCreateInputConnection(new EditorInfo());check(c!=null&&c.setComposingRegion(0,2)&&c.setSelection(1,3),"live composition and selection");return c;}
        @Override public void close(){if(!retainedAuthority){owner.close();queue.drainAll(4);}ConcreteHostProbe.reset();}
    }
    private static void regression(boolean baseline){
        for(boolean activeFirst:List.of(true,false))try(Fixture f=new Fixture(activeFirst)){
            InputConnection old=f.compose();EditText a=f.editor("fieldA"),b=f.editor("fieldB");var buffer=a.getText();int commits=NativeBridge.commitCalls;Object packet=f.renderer().packet;
            f.publish(2,"disable","enable","hello");
            if(baseline){check(f.fence().terminal&&NativeBridge.commitCalls==commits&&f.renderer().packet==packet,"frozen R3 reproduces refusal");check(String.valueOf(f.owner.cleanupLedger().primary()).contains("lost frame-derived editor permit"),"exact cohort defect: "+f.owner.cleanupLedger().primary());System.out.println("REPRODUCED R3 focused disable with unchanged inactive field; activeFirst="+activeFirst+" primary="+f.owner.cleanupLedger().primary());}
            else {f.live("two-field disable activeFirst="+activeFirst);check(NativeBridge.commitCalls==commits+1&&NativeBridge.createCalls==1,"one commit, one owner");check(f.editor("fieldA")==a&&f.editor("fieldB")==b&&a.getText()==buffer&&!a.isEnabled()&&!a.hasFocus()&&b.isEnabled(),"both exact fields retained");check(ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==1,"one consumed close");check(!old.commitText("stale",1),"old adapter fenced");System.out.println("PASS R4 two-field regression activeFirst="+activeFirst);}
        }
    }
    private static void variants(){
        String draft="New task\n世界 😀 مرحبا";
        for(boolean first:List.of(true,false))for(String pair:List.of("disable/disable","remove/remove","disable/remove","remove/disable","remove/enable"))try(Fixture f=new Fixture(first)){
            f.publish(2,"enable","enable",draft);f.live("inactive Unicode update");InputConnection old=f.compose();EditText a=f.editor("fieldA"),b=f.editor("fieldB");var aRecord=f.renderer().inspectV2().get("fieldA");var bRecord=f.renderer().inspectV2().get("fieldB");
            int commits=NativeBridge.commitCalls,prepares=NativeBridge.prepareCalls;String[] modes=pair.split("/");
            f.publish(3,modes[0],modes[1],draft);f.live("two-field "+pair);
            check(NativeBridge.commitCalls==commits+1&&NativeBridge.prepareCalls==prepares+1&&NativeBridge.createCalls==1,"once-only frame and no owner reset");
            check(ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==1,"one old target close");
            for(String id:List.of("fieldA","fieldB")){String mode=id.equals("fieldA")?modes[0]:modes[1];var record=id.equals("fieldA")?aRecord:bRecord;
                if(mode.equals("remove"))check(!f.renderer().inspectV2().containsKey(id),"removed "+id);
                else check(f.renderer().inspectV2().get(id)==record&&f.editor(id).isEnabled()==mode.equals("enable"),"exact retained binding "+id);
            }
            int delegates=ConcreteHostProbe.count("BaseInputConnection.commitText","entry");check(!old.commitText("late",1)&&ConcreteHostProbe.count("BaseInputConnection.commitText","entry")==delegates,"stale callback not forwarded");
            f.publish(4,"enable","enable",draft);f.live("later reenable "+pair);check(NativeBridge.createCalls==1,"same owner after reenable");
            if(!modes[0].equals("remove"))check(f.editor("fieldA")==a,"same A after reenable");if(!modes[1].equals("remove"))check(f.editor("fieldB")==b,"same B after reenable");
            check(f.editor("fieldA").getText().toString().equals(draft)&&f.editor("fieldB").getText().toString().equals("second"),"model values survive");
            f.editor("fieldA").requestFocus();InputConnection fresh=f.editor("fieldA").onCreateInputConnection(new EditorInfo());check(fresh!=null&&fresh!=old&&!old.setSelection(0,0),"fresh attempt never resurrects predecessor");
            System.out.println("PASS cohort lifecycle "+pair+" activeFirst="+first);
        }
    }
    private static void rollback(){
        for(boolean first:List.of(true,false))for(String mode:List.of("preparation","attachment","commit"))try(Fixture f=new Fixture(first)){
            InputConnection old=f.compose();NativeRenderer r=f.renderer();EditText a=f.editor("fieldA"),b=f.editor("fieldB");Object packet=r.packet,bindingA=r.inspectV2().get("fieldA").binding,bindingB=r.inspectV2().get("fieldB").binding;
            Object[] spans=a.getText().getSpans(0,a.getText().length(),Object.class);
            if(mode.equals("preparation"))NativeBridge.prepareFailure=new IllegalStateException("R4 preparation refusal");
            if(mode.equals("attachment"))r.testFaultV2(r.inspectV2().size()*2,false);
            if(mode.equals("commit"))NativeBridge.commitStatus=1;
            f.publish(2,"disable","disable","hello");
            check(f.fence().terminal&&r.packet==packet,"failed frame never published "+mode);
            check(r.inspectV2().get("fieldA").binding==bindingA&&r.inspectV2().get("fieldB").binding==bindingB,"exact two-field bindings restored");
            check(a.getText().toString().equals("hello")&&b.getText().toString().equals("second")&&a.getSelectionStart()==1&&a.getSelectionEnd()==3,"draft/selection restored");
            check(java.util.Arrays.equals(spans,a.getText().getSpans(0,a.getText().length(),Object.class)),"same composing span objects");
            check(!old.commitText("resurrect",1)&&NativeBridge.createCalls==1,"failure has no resurrection or reset");
            if(!mode.equals("preparation"))check(r.gatedNativeInstallFailureV3(),"post-close failure classification");
            System.out.println("PASS cohort rollback "+mode+" activeFirst="+first);
        }
    }
    private static Object state(NativeAppearanceViewsV2.FieldTransition scope){for(Object state:(Object[])get(scope.journal,"states"))if(get(state,"record")==scope.record)return state;throw new AssertionError("missing captured state");}
    private static NativeAppearanceViewsV2.FieldTransition forged(NativeAppearanceViewsV2.FieldTransition s){return new NativeAppearanceViewsV2.FieldTransition(s.renderer,s.candidate,s.journal,s.record,s.selected,s.original,s.retire);}
    private static void replaceScope(NativeAppearanceViewsV2.FieldTransition s){var next=forged(s);next.registered=true;next.phase=s.phase;set(state(s),"transition",next);s.record.fieldTransition=next;}
    private static void callbacks(){
        List<String> boundaries=List.of("BaseInputConnection.finishComposingText","BaseInputConnection.closeConnection","View.clearFocus","View.onFocusChanged","View.onDetachedFromWindow","TextView.getEditableText","View.drawableStateChanged","TextView.setText","TextView.onSelectionChanged");
        for(String boundary:boundaries)for(String when:List.of("entry","beforeReturn"))for(String mode:List.of("nested","foreign","windowLoss","unrelatedDetach","replacement"))try(Fixture f=new Fixture(true)){
            InputConnection old=f.compose();NativeRenderer r=f.renderer();EditText a=f.editor("fieldA"),b=f.editor("fieldB");Object packet=r.packet;int commits=NativeBridge.commitCalls;boolean[] hit={false};String[] caller={null};CapturedAuthority[] capture={null};int prepares=NativeBridge.prepareCalls;
            ConcreteHostProbe.hook=(method,phase)->{
                var s=r.inspectV2().get("fieldA").fieldTransition;
                if(hit[0]||!method.equals(boundary)||!phase.equals(when)||s==null||!(Boolean)get(s.journal,"transitionsSealed"))return;
                if(!method.startsWith("BaseInputConnection")&&ConcreteHostProbe.lastEvent().receiver!=a&&ConcreteHostProbe.lastEvent().receiver!=b)return;
                hit[0]=true;caller[0]=ConcreteHostProbe.lastEvent().toString();ConcreteHostProbe.hook=null;
                if(mode.equals("nested")){int count=ConcreteHostProbe.count("BaseInputConnection.commitText","entry");check(!old.commitText("nested",1)&&count==ConcreteHostProbe.count("BaseInputConnection.commitText","entry"),"nested old target refused");check(a.onCreateInputConnection(new EditorInfo())==null,"nested creator refused");}
                if(mode.equals("foreign")){check(!r.fieldTransitionCurrent(s.candidate,null,s.record,s),"foreign journal refused");check(!r.fieldTransitionCurrent(s.candidate,s.journal,r.inspectV2().get("fieldB"),s),"foreign record refused");var next=forged(s);check(!r.fieldTransitionCurrent(s.candidate,s.journal,s.record,next),"uncaptured new transition refused");}
                if(mode.equals("windowLoss"))b.onWindowFocusChanged(false);
                if(mode.equals("unrelatedDetach"))b.hostDetach();
                if(mode.equals("replacement")){capture[0]=new CapturedAuthority(s);f.retainedAuthority=true;replaceScope(s);}
            };
            boolean removal=boundary.equals("View.onDetachedFromWindow");boolean replace=boundary.equals("TextView.setText")||boundary.equals("TextView.onSelectionChanged");
            try{f.publish(2,removal?"remove":"disable","enable",replace?"saved model":"hello");}finally{ConcreteHostProbe.hook=null;}
            check(hit[0],"fresh callback reached "+boundary+" "+when+" "+mode);
            if(mode.equals("replacement"))capture[0].observeRetained(f,packet,commits,prepares+1,boundary+" "+when);
            if(mode.equals("nested")||mode.equals("foreign")){f.live("safe callback refusal");check(NativeBridge.commitCalls==commits+1,"safe callback keeps single commit");}
            else check(f.fence().terminal&&r.packet==packet&&NativeBridge.commitCalls==commits,"hostile callback refuses successor");
            check(!old.commitText("stale",1),"old connection never resurrects");
            check(ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")<=1,"old target never closes twice");
            System.out.println("PASS new boundary "+boundary+" "+when+" "+mode+" at "+caller[0]);
        }
    }
    private static void scalarFinalization(){
        for(String mode:List.of("stateReplacement","recordReplacement","missingMember","rosterSwap","attempt","target","generation","editable","loss","owner","nested"))try(Fixture f=new Fixture(false)){
            InputConnection old=f.compose();NativeRenderer r=f.renderer();Object packet=r.packet;boolean[] hit={false};int commits=NativeBridge.commitCalls,prepares=NativeBridge.prepareCalls;CapturedAuthority[] capture={null};
            ConcreteHostProbe.hook=(method,phase)->{
                if(hit[0]||!method.equals("NativeBridge.commitV2")||!phase.equals("beforeReturn"))return;
                hit[0]=true;ConcreteHostProbe.hook=null;var s=r.inspectV2().get("fieldA").fieldTransition;
                check(s!=null&&s.phase==NativeAppearanceViewsV2.FieldTransition.READY,"scalar hook has prepared exact scope");
                capture[0]=new CapturedAuthority(s);
                f.retainedAuthority=List.of("stateReplacement","recordReplacement","missingMember","rosterSwap").contains(mode);
                if(mode.equals("stateReplacement"))replaceScope(s);
                if(mode.equals("recordReplacement"))s.record.fieldTransition=forged(s);
                if(mode.equals("missingMember"))set(state(s),"transition",null);
                if(mode.equals("rosterSwap")){Object[] states=(Object[])get(s.journal,"states");Object tmp=states[1];states[1]=states[2];states[2]=tmp;}
                if(mode.equals("attempt"))s.field.attempt=null;
                if(mode.equals("target"))s.predecessor.target=null;
                if(mode.equals("generation"))set(s.record,"generation","foreign-generation");
                if(mode.equals("editable"))s.currentEditable=new android.text.SpannableStringBuilder("hello");
                if(mode.equals("loss"))f.editor("fieldB").onWindowFocusChanged(false);
                if(mode.equals("owner"))f.owner.close();
                if(mode.equals("nested")){check(!old.commitText("nested",1),"old callback refused during scalar publication");check(f.editor("fieldA").onCreateInputConnection(new EditorInfo())==null,"creator refused during publication");}
                check((Integer)get(r,"outstandingFieldTransitions")==2&&(Integer)get(r,"outstandingEditorNativeCalls")==2,"no partial scalar release before commit-return boundary "+mode);
            };
            try{f.publish(2,"disable","enable","hello");}finally{ConcreteHostProbe.hook=null;}
            check(hit[0],"scalar fault hook reached "+mode);check(NativeBridge.commitCalls==commits+1,"one core commit attempt; no replay");
            if(mode.equals("nested")){f.live("safe scalar refusal");check((Integer)get(r,"outstandingFieldTransitions")==0,"all members released once");}
            else {check(f.fence().terminal&&r.packet==packet,"changed scalar identity seals publication "+mode);if(f.retainedAuthority)capture[0].observeRetained(f,packet,commits+1,prepares+1,"scalar "+mode);
                else {check((Integer)get(r,"outstandingFieldTransitions")==0&&(Integer)get(r,"outstandingEditorNativeCalls")==0&&get(f.owner,"pendingCloseResource")==null&&get(f.owner,"pendingCloseToken")==null&&f.queue.queued()==0&&NativeBridge.destroyCalls==1,"intact cleanup authority releases full cohort once "+mode);
                    System.out.println("OBSERVED scalar cleanup "+mode+" outcome="+f.owner.cleanupLedger().coordinator()+" rendererFailure="+f.owner.cleanupLedger().coordinatorFailure());}}
            check(!old.commitText("later",1)&&NativeBridge.createCalls==1,"no post-finalization resurrection/reset");
            System.out.println("PASS scalar finalization "+mode);
        }
    }
    private static void lossCredit(){
        try(Fixture f=new Fixture(true)){
            f.compose();NativeRenderer r=f.renderer();Object packet=r.packet;boolean[] hit={false};
            ConcreteHostProbe.hook=(method,when)->{
                if(hit[0]||!method.equals("View.onFocusChanged")||!when.equals("beforeReturn"))return;
                var s=r.inspectV2().get("fieldA").fieldTransition;if(s==null||s.phase!=NativeAppearanceViewsV2.FieldTransition.FOCUS)return;
                hit[0]=true;ConcreteHostProbe.hook=null;long prior=s.record.input.editorLossObservation();var other=r.inspectV2().get("fieldB");other.input.editorLossObserved(other);
                boolean refused=false;try{r.accountTransitionLossV3(s,prior,"focus");}catch(IllegalArgumentException|IllegalStateException expected){refused=true;}
                check(refused,"sibling loss cannot borrow an already consumed focus credit");
            };
            try{f.publish(2,"disable","enable","hello");}finally{ConcreteHostProbe.hook=null;}
            check(hit[0]&&f.fence().terminal&&r.packet==packet,"unaccounted sibling loss seals transaction");
            System.out.println("PASS exact origin and nonreplayable expected focus-loss credit");
        }
    }

    private static final List<Fixture> retainedSynthetic = new ArrayList<>();
    private static final class CapturedAuthority {
        final NativeAppearanceViewsV2.FieldTransition scope;
        final Object journal;
        final Object[] states,members;
        CapturedAuthority(NativeAppearanceViewsV2.FieldTransition scope){
            this.scope=scope;journal=scope.journal;
            states=((Object[])get(journal,"states")).clone();members=((Object[])get(journal,"transitionRoster")).clone();
            check((Boolean)get(journal,"transitionsSealed")&&(Integer)get(journal,"transitionCount")==2,"exact two-member sealed capture");
        }
        void originalMembers(){
            Object[] roster=(Object[])get(journal,"transitionRoster");check(roster.length==members.length,"same roster length");int count=0;
            for(int i=0;i<members.length;i++){
                check(roster[i]==members[i],"original member retained at "+i);
                if(members[i]==null)continue;count++;
                Object state=get(members[i],"state");var s=(NativeAppearanceViewsV2.FieldTransition)get(members[i],"scope");
                check(state==states[i]&&get(state,"transitionMembership")==members[i]&&get(state,"record")==s.record&&s.journal==journal,"original exact membership graph");
                check(s.registered&&!s.ended,"original member remains registered and held");
            }
            check(count==2,"exact held membership cardinality");
        }
        List<Object> snapshot(Fixture f){
            List<Object> values=new ArrayList<>();NativeRenderer r=f.renderer();
            for(String name:List.of("outstandingFieldTransitions","outstandingEditorNativeCalls","outstandingFieldPreservations","v2Pending"))values.add(get(r,name));
            for(String name:List.of("pendingCloseResource","pendingCloseToken","activeOperation","effectDepth"))values.add(get(f.owner,name));
            values.add(r.packet);values.add(f.fence().presentation);values.add(f.fence().sealSerial);
            for(String name:List.of("completion","failedInvoked","transitionCount","transitionLoss","transitionsSealed"))values.add(get(journal,name));
            Object[] current=(Object[])get(journal,"states");
            for(int i=0;i<current.length;i++){values.add(current[i]);values.add(get(current[i],"transition"));}
            for(Object member:members)if(member!=null){var s=(NativeAppearanceViewsV2.FieldTransition)get(member,"scope");
                values.add(s);values.add(s.record.fieldTransition);values.add(s.registered);values.add(s.ended);values.add(s.phase);
            }
            return values;
        }
        void observeRetained(Fixture f,Object prior,int commits,int prepares,String label){
            NativeRenderer r=f.renderer();originalMembers();
            check(f.fence().terminal&&!f.fence().drawAllowed&&!f.fence().inputAllowed&&r.packet==prior,"synchronous terminal fence and exact prior packet");
            check(NativeBridge.commitCalls==commits&&NativeBridge.prepareCalls==prepares&&NativeBridge.createCalls==1&&NativeBridge.destroyCalls==0,"synchronous counts, no unwanted commit/replay/reset/disposal");
            check((Integer)get(r,"outstandingFieldTransitions")==2&&(Integer)get(r,"outstandingEditorNativeCalls")==2&&(Integer)get(r,"outstandingFieldPreservations")==0,"exact held counters 2/2/0");
            Object pending=get(f.owner,"pendingCloseResource"),token=get(f.owner,"pendingCloseToken");
            check(pending==get(f.owner,"coordinator")&&pending!=null&&token!=null&&f.owner.cleanupLedger().coordinator()==NativeOwnerV2.Outcome.DEFERRED,"exact pending cleanup identity and DEFERRED");
            List<Object> synchronous=snapshot(f);int aborts=NativeBridge.abortCalls,closes=ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry");
            System.out.println("SNAPSHOT synchronous "+label+" terminal=true packet=prior heldTransitions=2 heldNativeCalls=2 preservation=0 commit="+commits+" prepare="+prepares+" coordinator=DEFERRED pendingIdentity=exact originalMembers=2");
            for(int i=0;i<4;i++){
                check(f.queue.queued()==1,"one pending terminal close");Object queued=get(f.owner,"queued");
                check(f.queue.snapshot().get(0)==queued&&get(queued,"resource")==pending&&get(queued,"token")==token&&String.valueOf(get(queued,"kind")).equals("TERMINAL_CLOSE"),"queued work owns exact pending cleanup");
                check(f.queue.drainOne(),"one finite fake-queue delivery");originalMembers();
                check(synchronous.equals(snapshot(f))&&f.queue.queued()==1&&f.owner.cleanupLedger().coordinator()==NativeOwnerV2.Outcome.DEFERRED,"retained authority unchanged after delivery "+(i+1));
                check(f.fence().terminal&&!f.fence().drawAllowed&&!f.fence().inputAllowed&&NativeBridge.commitCalls==commits&&NativeBridge.prepareCalls==prepares&&NativeBridge.abortCalls==aborts&&NativeBridge.createCalls==1&&NativeBridge.destroyCalls==0&&ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==closes,"no replay or disposal during finite observation");
            }
            retainedSynthetic.add(f);
            System.out.println("PASS retained synthetic "+label+" deliveries=4 queued=1 nativeCleanup=UNPROVEN");
        }
    }

    public static void main(String[] args)throws Exception {
        descriptor=Files.readAllBytes(Path.of(args[0]));NativeBridge.testProfile=AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3;
        regression(false);variants();rollback();callbacks();scalarFinalization();lossCredit();
        System.out.println("PASS R4 cohort checks="+checks+"; controlled host only");
    }
}
