package dev.mixer.android;

import android.app.Activity;
import android.os.Build;
import android.os.Looper;
import android.view.View;
import android.widget.EditText;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Finite actual-source component tests with mechanical Android/JNI leaves only.
 * Prepared source; not executed or a claim about ART, Android class loading, IME or TalkBack.
 */
public final class ViewApiBoundaryTests {
    private ViewApiBoundaryTests() {}
    private static byte[] descriptor;
    private static int checks,cases;
    private static final List<String> DRAWABLES=List.of("EditText.setTextCursorDrawable",
        "EditText.setTextSelectHandle","EditText.setTextSelectHandleLeft","EditText.setTextSelectHandleRight");
    private static final String STATE="View.setStateDescription";
    private static final class Fatal extends Error {
        private static final long serialVersionUID=1L;
        Fatal(String message){super(message);}
    }
    private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    private static Object field(Object target,Class<?> declaring,String name){
        try{Field f=declaring.getDeclaredField(name);f.setAccessible(true);return f.get(target);}
        catch(ReflectiveOperationException e){throw new AssertionError(e);}
    }
    private static void set(Object target,Class<?> declaring,String name,Object value){
        try{Field f=declaring.getDeclaredField(name);f.setAccessible(true);f.set(target,value);}
        catch(ReflectiveOperationException e){throw new AssertionError(e);}
    }
    private static void unsupported(Runnable action){
        try{action.run();throw new AssertionError("required-operation refusal missing");}
        catch(AppearanceDescriptorV2.Failure failure){check(failure.code==AppearanceDescriptorV2.Error.unsupportedNativeOperation,"exact capability failure");}
    }
    private static void stale(Runnable action){
        try{action.run();throw new AssertionError("stale Mutation accepted");}
        catch(IllegalStateException expected){check(expected.getMessage().equals("V2 mutation authority lost"),"original stale Mutation refusal");}
    }
    private static void cleanupRefusal(Runnable action){
        try{action.run();throw new AssertionError("cleanup Mutation accepted for construction/bind");}
        catch(IllegalStateException expected){check(expected.getMessage().equals("cleanup cannot authorize V2 bind/layout"),"original cleanup Mutation refusal");}
    }
    private static void write(StringBuilder out,Object value){
        if(value instanceof List<?> values){out.append('[');for(int i=0;i<values.size();i++){if(i>0)out.append(',');write(out,values.get(i));}out.append(']');}
        else if(value instanceof Map<?,?> values){out.append('{');boolean comma=false;for(var entry:values.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,entry.getKey());out.append(':');write(out,entry.getValue());}out.append('}');}
        else Json.write(out,value);
    }
    /** null means omitted; explicit empty remains an actual string property. */
    private static byte[] packet(long revision,String kind,boolean selectable,String accessibilityValue){
        Map<String,Object> properties=new HashMap<>();List<Object> actions=new ArrayList<>();
        switch(kind){
            case "text" -> {properties.put("text","hello");if(selectable)properties.put("selectable",true);}
            case "textField" -> {properties.put("label","Entry");properties.put("value","hello");actions.add(Json.map("id","changed","event","textChange"));}
            case "button" -> {properties.put("label","Go");actions.add(Json.map("id","activate","event","activate"));}
            case "toggle" -> {properties.put("label","Enabled");properties.put("value",false);actions.add(Json.map("id","changed","event","valueChange"));}
            case "vStack" -> { /* empty supported container */ }
            default -> throw new AssertionError(kind);
        }
        if(accessibilityValue!=null)properties.put("accessibilityValue",accessibilityValue);
        Object root=Json.map("id","root","kind",kind,"properties",properties,"children",List.of(),"actions",actions);
        StringBuilder out=new StringBuilder();write(out,Json.map("schemaVersion",new Json.Num("1"),"document",Json.map("schemaVersion",new Json.Num("1"),"revision",new Json.Num(Long.toString(revision)),"root",root),"identities",List.of(Json.map("id","root","generation",new Json.Num("1")))));
        return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static AppearanceResolverV2.Environment environment(){
        return new AppearanceResolverV2.Environment(AppearanceResolverV2.Scheme.light,AppearanceResolverV2.Direction.leftToRight,
            AppearanceDescriptorV2.Profile.m,1024,new AppearanceResolverV2.Viewport(64000,96000),
            new AppearanceResolverV2.SafeArea(0,0,0,0),"en-US",new AppearanceResolverV2.Accessibility(false,false,false),"1");
    }
    private static NativeAppearanceViewsV2.Binding binding(byte[] bytes){
        UiPacket packet=UiPacket.decode(bytes);
        var plan=AppearanceResolverV2.prepare(bytes,descriptor,environment(),AppearanceResolverV2.Platform.android);
        return new NativeAppearanceViewsV2.Binding(plan,plan.node("root"),packet.root,AppearanceDescriptorV2.decode(descriptor).android);
    }
    /** Actual core-issued operation tokens; no synthetic SDK argument or authority substitute. */
    private static final class Authority {
        final Object root=new Object(),window=new Object(),resource=new Object();
        final OwnerLifecycleV2 core;
        final OwnerLifecycleV2.WindowFacts facts;
        final NativeOwnerV2.Fence fence=new NativeOwnerV2.Fence();
        NativeAppearanceViewsV2.Mutation mutation;
        Authority(Activity activity){
            core=new OwnerLifecycleV2(NativeEnvironmentV2::requireMain,activity,root);
            facts=new OwnerLifecycleV2.WindowFacts(activity,root,false,true,window,1000,1500,true);
            core.windowChanged(core.lifetime(),facts);core.drain(core.lifetime(),core.snapshot().pendingDrain(),facts);
            fence.operation=core.snapshot().operation();check(core.permits(fence.operation),"actual initial core operation");
            mutation=NativeAppearanceViewsV2.Mutation.transaction(fence,fence.operation);
        }
        void advance(){
            var original=fence.operation;
            core.complete(original,resource,true,null);core.invalidate(core.lifetime());
            core.drain(core.lifetime(),core.snapshot().pendingDrain(),facts);fence.operation=core.snapshot().operation();
            check(fence.operation!=original&&core.permits(fence.operation),"actual successor core operation");
            mutation=NativeAppearanceViewsV2.Mutation.transaction(fence,fence.operation);
        }
    }
    private static final class Input implements NativeAppearanceViewsV2.Input {
        final Authority authority;int requests,effects;
        Input(Authority authority){this.authority=authority;}
        public boolean open(NativeAppearanceViewsV2.Record record){return true;}
        public boolean draw(){return false;}
        public void event(NativeAppearanceViewsV2.Record record,String event,Object value){effects++;}
        public void interaction(){effects++;}
        public NativeAppearanceViewsV2.Mutation mutation(){requests++;return authority.mutation;}
        public boolean editorRetained(NativeAppearanceViewsV2.Record record){return true;}
        public boolean editorDispatchAvailable(NativeAppearanceViewsV2.Record record){return true;}
        public void editorEnter(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){effects++;}
        public void editorLeave(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){effects++;}
        public boolean editorCloseAllowed(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.NativeField.Attempt attempt){return true;}
        public void replacementBegin(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Replacement replacement){effects++;}
        public void replacementEnd(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Replacement replacement){effects++;}
        public long editorLossObservation(){return 0;}
        public void editorLossObserved(NativeAppearanceViewsV2.Record record){effects++;}
        public void fieldPreservationBegin(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.FieldPreservation preservation){effects++;}
        public void fieldPreservationEnd(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.FieldPreservation preservation){effects++;}
        public void replacementEvent(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Replacement replacement){effects++;}
        public NativeAppearanceViewsV2.Mutation editorCleanupMutation(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){effects++;throw new AssertionError("editor cleanup outside focused component scope");}
        public void editorFinishBegin(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){effects++;}
        public void editorFinishEnd(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){effects++;}
        public void editorDrainBegin(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){effects++;}
        public void editorDrainEnd(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){effects++;}
        public void editorFailure(Throwable primary,Error firstFatal){effects++;}
    }
    private static final class Direct {
        final Activity activity=new Activity();final Authority authority=new Authority(activity);final Input input=new Input(authority);
        final NativeAppearanceViewsV2.Record record;
        Direct(String kind,boolean selectable,String value){
            record=new NativeAppearanceViewsV2.Record(activity,UiPacket.decode(packet(1,kind,selectable,value)).root,input,authority.mutation);
        }
        void bind(NativeAppearanceViewsV2.Binding next){record.bind(next,new NativeAppearanceViewsV2.Geometry(),false,authority.mutation);}
        void reset(){ConcreteHostProbe.reset();input.requests=input.effects=0;NativeBridge.reset();}
    }
    private static List<String> setters(){return ConcreteHostProbe.events().stream().filter(e->e.phase.equals("entry")&&(e.method.equals(STATE)||DRAWABLES.contains(e.method))).map(e->e.method).toList();}
    private static List<String> expected(int sdk){List<String> values=new ArrayList<>();if(sdk>=30)values.add(STATE);values.addAll(DRAWABLES);return values;}
    private static void clean(Direct direct){
        check(!direct.record.changing,"changing restored");
        check(field(direct.record,NativeAppearanceViewsV2.Record.class,"scoped")==null,"captured scope restored");
        check(direct.input.requests==0,"native setters did not reacquire Mutation");
        check(direct.input.effects==0,"no editor/input effects");
    }
    private static void identities(Direct direct){
        EditText edit=(EditText)direct.record.view;
        Object[] drawables={edit.cursorDrawable,edit.selectHandle,edit.selectHandleLeft,edit.selectHandleRight};
        for(int i=0;i<drawables.length;i++){
            check(drawables[i]!=null,"authored drawable "+i);
            check(field(drawables[i],drawables[i].getClass(),"record")==direct.record,"drawable captures exact Record "+i);
            check(drawables[i].getClass().getSimpleName().equals(i==0?"Cursor":"Handle"),"drawable class "+i);
            for(int j=0;j<i;j++)check(drawables[i]!=drawables[j],"distinct authored drawable instances");
        }
    }
    private static void sourceSemantics(){
        var absent=UiPacket.decode(packet(1,"text",false,null)).root;
        var empty=UiPacket.decode(packet(1,"text",false,"")).root;
        check(!absent.properties.containsKey("accessibilityValue")&&absent.text("accessibilityValue",null)==null,"absence maps to native clear");
        check(empty.properties.containsKey("accessibilityValue")&&empty.text("accessibilityValue",null).isEmpty(),"empty remains required and distinct");
    }
    private static void refusals(){
        for(int sdk:new int[]{28,29})for(String kind:List.of("text","textField"))for(String value:new String[]{"required",""}){
            Build.VERSION.SDK_INT=sdk;Activity activity=new Activity();Authority authority=new Authority(activity);Input input=new Input(authority);
            var source=UiPacket.decode(packet(1,kind,false,value)).root;ConcreteHostProbe.reset();
            unsupported(()->new NativeAppearanceViewsV2.Record(activity,source,input,authority.mutation));
            check(ConcreteHostProbe.events().isEmpty()&&input.effects==0&&input.requests==0,"pre-widget presence refusal API"+sdk+kind);
        }
        for(String kind:List.of("textField","text")){
            Build.VERSION.SDK_INT=28;Activity activity=new Activity();Authority authority=new Authority(activity);Input input=new Input(authority);
            var source=UiPacket.decode(packet(1,kind,true,null)).root;ConcreteHostProbe.reset();
            unsupported(()->new NativeAppearanceViewsV2.Record(activity,source,input,authority.mutation));
            check(ConcreteHostProbe.events().isEmpty()&&input.effects==0&&input.requests==0,"pre-widget API28 selection refusal");
        }
        // Direct bind preflight precedes editorAvailable, changing, binding, preparation and native calls.
        for(String kind:List.of("textField","text")){
            Build.VERSION.SDK_INT=30;Direct direct=new Direct(kind,false,null);var before=direct.record.binding;
            var geometry=direct.record.geometry;var next=binding(packet(2,kind,true,null));
            if(kind.equals("textField"))set(direct.record.view,NativeAppearanceViewsV2.NativeField.class,"phase",NativeAppearanceViewsV2.NativeField.Phase.QUARANTINED);
            Build.VERSION.SDK_INT=28;direct.reset();unsupported(()->direct.bind(next));
            check(direct.record.binding==before&&direct.record.geometry==geometry,"bind state untouched before API28 refusal");
            check(ConcreteHostProbe.events().isEmpty(),"zero native effects on API28 bind refusal");clean(direct);
        }
        for(String value:new String[]{"required",""}){
            Build.VERSION.SDK_INT=30;Direct direct=new Direct("text",false,null);var next=binding(packet(2,"text",false,value));
            Build.VERSION.SDK_INT=29;direct.reset();unsupported(()->direct.bind(next));
            check(direct.record.binding==null&&direct.record.geometry==null&&ConcreteHostProbe.events().isEmpty(),"zero API29 required-value bind effects");clean(direct);
        }
        Build.VERSION.SDK_INT=28;Direct ordinary=new Direct("text",false,null);ordinary.reset();ordinary.bind(binding(packet(2,"text",false,null)));
        check(setters().isEmpty(),"API28 ordinary absent text has no later native operation");clean(ordinary);
    }
    private static void supported(int sdk){
        Build.VERSION.SDK_INT=sdk;Direct direct=new Direct("textField",false,sdk>=30?"ready":null);direct.reset();
        direct.bind(binding(packet(2,"textField",false,sdk>=30?"ready":null)));
        check(setters().equals(expected(sdk)),"setter order API"+sdk);identities(direct);clean(direct);
        for(var event:ConcreteHostProbe.events())if(event.phase.equals("entry")&&(DRAWABLES.contains(event.method)||event.method.equals(STATE))){
            check(event.receiver==direct.record.view,"exact setter receiver");
            check(event.productionClass.equals("dev.mixer.android.NativeAppearanceViewsV2$"+(event.method.equals(STATE)?"Api30":"Api29")),"separately emitted helper call site");
        }
        if(sdk>=30){
            check(field(direct.record.view,View.class,"stateDescription").equals("ready"),"state value set");
            direct.reset();direct.bind(binding(packet(3,"textField",false,null)));
            check(field(direct.record.view,View.class,"stateDescription")==null,"omission clears native state to actual null");
            check(setters().equals(expected(sdk)),"clear preserves order");identities(direct);clean(direct);
            direct.reset();direct.bind(binding(packet(4,"textField",false,"")));
            check(field(direct.record.view,View.class,"stateDescription").equals(""),"empty remains native empty");identities(direct);clean(direct);
        }
    }
    private static void authorityEntry(){
        for(int sdk:new int[]{28,29,30,36,37}){
            Build.VERSION.SDK_INT=30;Direct direct=new Direct("textField",false,null);
            var original=direct.authority.mutation;direct.authority.advance();
            var next=binding(packet(2,"textField",false,"required"));
            Build.VERSION.SDK_INT=sdk;direct.reset();
            stale(()->new NativeAppearanceViewsV2.Record(direct.activity,next.source(),direct.input,original));
            stale(()->direct.record.bind(next,new NativeAppearanceViewsV2.Geometry(),false,original));
            check(ConcreteHostProbe.events().isEmpty(),"stale entry refusal precedes unsupported capability and native effects API"+sdk);
            check(direct.record.binding==null&&direct.record.geometry==null,"stale entry keeps binding/geometry");clean(direct);
            var cleanup=NativeAppearanceViewsV2.Mutation.cleanup(direct.authority.fence);direct.reset();
            cleanupRefusal(()->new NativeAppearanceViewsV2.Record(direct.activity,next.source(),direct.input,cleanup));
            cleanupRefusal(()->direct.record.bind(next,new NativeAppearanceViewsV2.Geometry(),false,cleanup));
            check(ConcreteHostProbe.events().isEmpty(),"cleanup entry refusal precedes unsupported capability and native effects API"+sdk);
            check(direct.record.binding==null&&direct.record.geometry==null,"cleanup entry keeps binding/geometry");clean(direct);
        }
    }
    private static void interruptions(int sdk){
        for(String target:expected(sdk))for(String mode:List.of("ordinary","fatal","stale","stale-reentry"))for(String phase:List.of("entry","beforeReturn")){
            Build.VERSION.SDK_INT=sdk;Direct direct=new Direct("textField",false,sdk>=30?"ready":null);
            var next=binding(packet(2,"textField",false,sdk>=30?"ready":null));var original=direct.authority.mutation;
            Throwable sentinel=mode.equals("fatal")?new Fatal(target):new IllegalStateException(target);boolean[] fired={false};
            direct.reset();ConcreteHostProbe.hook=(method,observed)->{
                if(!fired[0]&&method.equals(target)&&observed.equals(phase)){
                    fired[0]=true;check(direct.record.mutation()==original,"exact original Mutation at setter");
                    if(mode.startsWith("stale")){
                        direct.authority.advance();check(!original.current(),"original Mutation stale during setter");
                        if(mode.equals("stale-reentry")){
                            int count=ConcreteHostProbe.events().size();
                            stale(()->direct.record.bind(next,new NativeAppearanceViewsV2.Geometry(),false,original));
                            check(ConcreteHostProbe.events().size()==count,"stale nested bind has no native effect");
                            check(direct.record.changing&&direct.record.mutation()==original,"outer captured scope survives nested refusal");
                        }
                    }else ConcreteHostProbe.fail(sentinel);
                }
            };
            try{direct.bind(next);throw new AssertionError("setter interruption hidden "+sdk+target+mode+phase);}
            catch(RuntimeException|Error actual){
                if(mode.startsWith("stale"))check(actual instanceof IllegalStateException&&actual.getMessage().equals("V2 mutation authority lost"),"same-Mutation postcheck catches reentry");
                else check(actual==sentinel,"ordinary/fatal original identity");
            }finally{ConcreteHostProbe.hook=null;}
            check(fired[0],"selected setter hook reached");
            check(setters().equals(expected(sdk).subList(0,expected(sdk).indexOf(target)+1)),"no later setter after interruption");clean(direct);
        }
    }
    private static void lowerGuards(){
        for(int sdk:new int[]{28,29,30,35}){
            Build.VERSION.SDK_INT=36;Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);
            Authority authority=new Authority(activity);
            var observer=new NativeEnvironmentV2.Observer(activity,root,(source,change,cause,primary,fatal)->{});
            var renderer=new NativeRenderer(activity,bytes->{throw new AssertionError("unexpected event");},observer,authority.fence);
            Build.VERSION.SDK_INT=sdk;ConcreteHostProbe.reset();NativeBridge.reset();
            unsupported(()->new NativeEnvironmentV2.Observer(activity,root,(source,change,cause,primary,fatal)->{}));
            check(ConcreteHostProbe.events().isEmpty(),"observer <36 rejects before capture/listener effects");
            unsupported(()->renderer.prepareV2(null,null,null));
            check(ConcreteHostProbe.events().isEmpty(),"renderer <36 rejects before native preparation");
            check(NativeBridge.prepareCalls==0&&NativeBridge.createCalls==0,"no bridge preparation on lower-API denial");
        }
    }
    private static void legacy(){
        for(int sdk:new int[]{28,29})for(String value:new String[]{"required",""}){
            Build.VERSION.SDK_INT=sdk;var renderer=new NativeRenderer(new Activity(),bytes->{});ConcreteHostProbe.reset();
            try{renderer.apply(UiPacket.decode(packet(1,"text",false,value)));throw new AssertionError("V1 property-presence refusal missing");}
            catch(IllegalArgumentException failure){check(failure.getMessage().equals("accessibilityValue requires API30"),"V1 exact refusal message");}
            check(ConcreteHostProbe.events().isEmpty(),"V1 presence refusal before widget effects");
        }
        for(int sdk:new int[]{28,29,30,36,37})for(String kind:List.of("text","textField","button","toggle","vStack")){
            Build.VERSION.SDK_INT=sdk;var renderer=new NativeRenderer(new Activity(),bytes->{});ConcreteHostProbe.reset();
            View view=renderer.apply(UiPacket.decode(packet(1,kind,kind.equals("text"),sdk>=30?"ready":null)));
            check(renderer.view("root")==view,"V1 identity "+kind+sdk);
            check(ConcreteHostProbe.count(STATE,"entry")== (sdk>=30?1:0),"V1 SDK-selected setter "+kind+sdk);
            if(sdk>=30){
                check(field(view,View.class,"stateDescription").equals("ready"),"V1 supported state result");
                renderer.apply(UiPacket.decode(packet(2,kind,kind.equals("text"),null)));
                check(field(view,View.class,"stateDescription")==null,"V1 supported omission clear");
                renderer.apply(UiPacket.decode(packet(3,kind,kind.equals("text"),"")));
                check(field(view,View.class,"stateDescription").equals(""),"V1 supported empty result");
                check(renderer.view("root")==view,"V1 successor retains widget");
                var stateEvent=ConcreteHostProbe.events().stream().filter(e->e.method.equals(STATE)&&e.phase.equals("entry")).findFirst().orElseThrow();
                check(stateEvent.productionClass.equals("dev.mixer.android.NativeRenderer$Api30"),"V1 API30 helper site");
            }
        }
    }
    private static void run(String name,Runnable test){
        try{test.run();cases++;System.out.println("PASS "+name);}
        finally{ConcreteHostProbe.reset();Build.VERSION.SDK_INT=36;Looper.hostReset();}
    }
    public static void main(String[] args)throws Exception {
        if(args.length!=1)throw new IllegalArgumentException("exact descriptor path required");
        descriptor=Files.readAllBytes(Path.of(args[0]));
        run("source-presence-empty-clear",ViewApiBoundaryTests::sourceSemantics);
        run("API28-29-zero-effect-refusal",ViewApiBoundaryTests::refusals);
        run("original-authority-entry-refusals",ViewApiBoundaryTests::authorityEntry);
        for(int sdk:new int[]{29,30,36,37}){run("API"+sdk+"-direct-setter-results",()->supported(sdk));run("API"+sdk+"-setter-interruption",()->interruptions(sdk));}
        run("observer-and-renderer-lower-API-guards",ViewApiBoundaryTests::lowerGuards);
        run("V1-preserved-results-and-refusal",ViewApiBoundaryTests::legacy);
        System.out.println("PASS "+cases+" focused actual-source groups / "+checks+" assertions; mechanical host leaves only");
    }
}
