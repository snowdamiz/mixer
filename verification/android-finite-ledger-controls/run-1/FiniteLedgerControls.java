package dev.mixer.android;

import android.app.Activity;
import android.widget.FrameLayout;
import java.io.InputStream;
import java.lang.reflect.Array;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Ordinary finite JVM controls: invokes the exact selected emitted methods without altering them. */
public final class FiniteLedgerControls {
    private static int checks;
    private static final List<String> rows = new ArrayList<>();
    private static final IdentityHashMap<Object,String> identities = new IdentityHashMap<>();
    private static final class Ordinary extends RuntimeException {
        private static final long serialVersionUID = 1L;
        Ordinary(String name) { super(name); }
        @Override public boolean equals(Object other) { return other instanceof Ordinary; }
        @Override public int hashCode() { return 7; }
    }
    private static final class Fatal extends Error {
        private static final long serialVersionUID = 1L;
        Fatal(String name) { super(name); }
        @Override public boolean equals(Object other) { return other instanceof Fatal; }
        @Override public int hashCode() { return 9; }
    }
    private static void check(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message);
    }
    private static Field field(Class<?> type, String name) throws Exception {
        Field value=type.getDeclaredField(name); value.setAccessible(true); return value;
    }
    private static Object get(Object receiver, String name) throws Exception {
        return field(receiver.getClass(),name).get(receiver);
    }
    private static String quote(String value) {
        return "\""+value.replace("\\","\\\\").replace("\"","\\\"")+"\"";
    }
    private static String label(Object object) {
        return object==null?"null":identities.getOrDefault(object,"unlabelled");
    }
    private static String sha(Class<?> type) throws Exception {
        String resource="/"+type.getName().replace('.','/')+".class";
        try (InputStream input=type.getResourceAsStream(resource)) {
            check(input!=null,"actual loaded class resource exists");
            byte[] digest=MessageDigest.getInstance("SHA-256").digest(input.readAllBytes());
            return java.util.HexFormat.of().formatHex(digest);
        }
    }
    private static final class Snapshot {
        final Object receiver;
        final Map<Field,Object> fields=new LinkedHashMap<>();
        final Map<Field,List<Object>> arrays=new LinkedHashMap<>();
        Snapshot(Object receiver, String... excluded) throws Exception {
            this.receiver=receiver;
            List<String> omitted=List.of(excluded);
            for (Field f:receiver.getClass().getDeclaredFields()) {
                if (Modifier.isStatic(f.getModifiers())||omitted.contains(f.getName())) continue;
                f.setAccessible(true); Object value=f.get(receiver); fields.put(f,value);
                if (value!=null&&value.getClass().isArray()) {
                    List<Object> contents=new ArrayList<>();
                    for(int i=0;i<Array.getLength(value);i++) contents.add(Array.get(value,i));
                    arrays.put(f,contents);
                }
            }
        }
        int assertUnchanged() throws Exception {
            int observed=0;
            for(var entry:fields.entrySet()) {
                Field f=entry.getKey(); Object before=entry.getValue(),after=f.get(receiver);
                check(f.getType().isPrimitive()?java.util.Objects.equals(before,after):before==after,
                    "unchanged field "+f); observed++;
                if(arrays.containsKey(f)) {
                    List<Object> contents=arrays.get(f);
                    check(Array.getLength(after)==contents.size(),"unchanged array length "+f);
                    for(int i=0;i<contents.size();i++) {
                        Object old=contents.get(i),next=Array.get(after,i);
                        boolean primitive=after.getClass().getComponentType().isPrimitive();
                        check(primitive?java.util.Objects.equals(old,next):old==next,"unchanged array element "+f+"["+i+"]");
                    }
                }
            }
            return observed;
        }
    }
    private static final class Fixture {
        final Object subject,ledger;
        final Field primary,fatal,diagnostics;
        final Method method;
        final String id,classHash;
        final Snapshot objectUnchanged,ledgerUnchanged;
        int callbacks;
        Fixture(int kind) throws Exception {
            Activity activity=new Activity(); FrameLayout root=new FrameLayout(activity);
            if(kind==0) {
                NativeEnvironmentV2.Observer observer=new NativeEnvironmentV2.Observer(activity,root,(s,c,r,p,f)->callbacks++);
                subject=new NativeCoordinatorV2(activity,root,observer,new NativeOwnerV2.Fence(),envelope->callbacks++);
                ledger=get(subject,"ledger"); primary=field(ledger.getClass(),"primary"); fatal=field(ledger.getClass(),"firstFatal"); diagnostics=null;
                // Seed an explicitly held local state. This does not simulate a successful enclosing cleanup.
                field(subject.getClass(),"active").setBoolean(subject,true);
                field(subject.getClass(),"cancellation").setBoolean(subject,true);
                field(subject.getClass(),"session").setLong(subject,37L);
                field(ledger.getClass(),"renderer").set(ledger,NativeCoordinatorV2.Outcome.ATTEMPTED);
                field(ledger.getClass(),"abortFailure").set(ledger,new Ordinary("held-abort"));
                classHash="6f42dde051726b4ce6d736c38646056ebf2a47a6eea24e58c55f582416ade289";
            } else if(kind==1) {
                subject=new NativeEnvironmentV2.Observer(activity,root,(s,c,r,p,f)->callbacks++);ledger=subject;
                primary=field(subject.getClass(),"primaryFailure");fatal=field(subject.getClass(),"fatalFailure");diagnostics=field(subject.getClass(),"diagnosticsAttached");
                field(subject.getClass(),"pending").setInt(subject,129);
                field(subject.getClass(),"acquiring").setInt(subject,7);
                ((int[])get(subject,"cleanup"))[7]=NativeEnvironmentV2.Observer.POSSIBLY_OWNED;
                ((Throwable[])get(subject,"cleanupFailures"))[7]=new Ordinary("held-observer");
                classHash="723f7d10f690d62e5c6f1fea5ac9e94e0d6e934ef0a6c097d176ad9fed737ad7";
            } else {
                subject=new NativeOwnerV2(activity,root);ledger=get(subject,"ledger");
                primary=field(ledger.getClass(),"primary");fatal=field(ledger.getClass(),"firstFatal");diagnostics=null;
                field(subject.getClass(),"effectDepth").setInt(subject,3);
                field(subject.getClass(),"registering").setBoolean(subject,true);
                field(ledger.getClass(),"unregister").set(ledger,NativeOwnerV2.Outcome.DEFERRED);
                field(ledger.getClass(),"unregisterFailure").set(ledger,new Ordinary("held-owner"));
                field(ledger.getClass(),"coreCompletionUnreported").setBoolean(ledger,true);
                classHash="f591013acfc0c216c001e97d3078970635d6f5975b7de32e63d7eea3895b73bb";
            }
            id=subject.getClass().getName().replace('.','/')+"#remember(Ljava/lang/Throwable;)V";
            method=subject.getClass().getDeclaredMethod("remember",Throwable.class);method.setAccessible(true);
            check(method.getReturnType()==void.class,"typed void descriptor");
            check(Modifier.isPrivate(method.getModifiers()),"exact private subject");
            check(subject.getClass().getClassLoader()==FiniteLedgerControls.class.getClassLoader(),"same ordinary classloader");
            check(sha(subject.getClass()).equals(classHash),"actual loaded class exact selected identity "+id);
            objectUnchanged=new Snapshot(subject,kind==1?new String[]{"primaryFailure","fatalFailure","diagnosticsAttached"}:new String[]{});
            ledgerUnchanged=ledger==subject?null:new Snapshot(ledger,"primary","firstFatal");
            ConcreteHostProbe.reset(); NativeBridge.reset();
        }
        void invoke(String sequence,int step,Throwable input,Throwable expectedPrimary,Error expectedFatal,boolean diagnosticsBefore) throws Exception {
            if(diagnostics!=null) diagnostics.setBoolean(subject,diagnosticsBefore);
            int beforeChecks=checks;
            Object result=method.invoke(subject,new Object[]{input});
            check(result==null,"typed void returns normally without rethrow/wrapper");
            check(primary.get(ledger)==expectedPrimary,"exact independent primary identity "+id);
            check(fatal.get(ledger)==expectedFatal,"exact independent first Error identity "+id);
            if(diagnostics!=null) check(!diagnostics.getBoolean(subject),"Observer always clears diagnostics including null");
            int fields=objectUnchanged.assertUnchanged();if(ledgerUnchanged!=null)fields+=ledgerUnchanged.assertUnchanged();
            check(callbacks==0,"no sink/event delivery");
            check(ConcreteHostProbe.events().isEmpty(),"no concrete leaf invocation during remember");
            check(NativeBridge.createCalls==0&&NativeBridge.exchangeCalls==0&&NativeBridge.prepareCalls==0&&NativeBridge.commitCalls==0&&NativeBridge.abortCalls==0&&NativeBridge.destroyCalls==0,"no bridge effects");
            for(Throwable failure:new Throwable[]{input,expectedPrimary,expectedFatal})if(failure!=null)check(failure.getSuppressed().length==0,"no diagnostic mutation of original exception");
            rows.add("{\"subject_id\":"+quote(id)+",\"class_sha256\":"+quote(classHash)+",\"sequence\":"+quote(sequence)+",\"step\":"+step+",\"input\":"+quote(label(input))+",\"typed_result\":\"void-normal-return\",\"primary\":"+quote(label(primary.get(ledger)))+",\"first_fatal\":"+quote(label(fatal.get(ledger)))+",\"diagnostics_before\":"+(diagnostics==null?"null":Boolean.toString(diagnosticsBefore))+",\"diagnostics_after\":"+(diagnostics==null?"null":"false")+",\"unchanged_fields\":"+fields+",\"leaf_events\":0,\"bridge_effects\":0,\"checks\":"+(checks-beforeChecks)+"}");
        }
    }
    private static Throwable named(Throwable failure,String name) { identities.put(failure,name);return failure; }
    private static void sequence(int kind,String name,Throwable[] input,Throwable[] primary,Error[] fatal) throws Exception {
        Fixture fixture=new Fixture(kind);
        check(input.length==primary.length&&primary.length==fatal.length,"independent oracle roster lengths");
        for(int i=0;i<input.length;i++)fixture.invoke(name,i,input[i],primary[i],fatal[i],i%2==0);
    }
    public static void main(String[] args) throws Exception {
        check(args.length==1,"one closed output path");
        for(int kind=0;kind<3;kind++) {
            Throwable a=named(new Ordinary("ordinary-A"),"ordinary-A"),b=named(new Ordinary("ordinary-B"),"ordinary-B");
            Error x=(Error)named(new Fatal("Error-A"),"Error-A"),y=(Error)named(new Fatal("Error-B"),"Error-B"),z=(Error)named(new Fatal("Error-C"),"Error-C");
            check(a!=b&&a.equals(b)&&x!=y&&x.equals(y),"value-equal objects must remain reference-distinct");
            sequence(kind,"null-empty",new Throwable[]{null},new Throwable[]{null},new Error[]{null});
            sequence(kind,"ordinary-primary-preserved",new Throwable[]{a,b,null},new Throwable[]{a,a,a},new Error[]{null,null,null});
            sequence(kind,"ordinary-then-error",new Throwable[]{a,x,b,y,null},new Throwable[]{a,a,a,a,a},new Error[]{null,x,x,x,x});
            sequence(kind,"error-then-ordinary",new Throwable[]{x,a,y,b,null},new Throwable[]{x,x,x,x,x},new Error[]{x,x,x,x,x});
            sequence(kind,"repeated-distinct-errors",new Throwable[]{x,y,x,z},new Throwable[]{x,x,x,x},new Error[]{x,x,x,x});
            sequence(kind,"null-then-ordinary-and-error",new Throwable[]{null,null,a,x},new Throwable[]{null,null,a,a},new Error[]{null,null,null,x});
        }
        String output="{\"schema\":1,\"scope\":\"three-exact-finite-JVM-ledger-methods-only\",\"checks\":"+checks+",\"invocations\":"+rows.size()+",\"rows\":[\n"+String.join(",\n",rows)+"\n]}\n";
        Files.writeString(Path.of(args[0]),output,StandardCharsets.UTF_8);
        System.out.println("PASS finite ledger controls: "+rows.size()+" invocations, "+checks+" independent identity/state checks; native/enclosing cleanup pending");
    }
}
