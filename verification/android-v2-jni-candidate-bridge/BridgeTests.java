package dev.mixer.android;

import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/** Actual JVM JNI into the unmodified checklist Swift dynamic library. */
public final class BridgeTests {
    private static int checks;
    private static void check(boolean condition) {
        checks++;
        if(!condition) throw new AssertionError("check "+checks);
    }
    private static void reject(Runnable action,String message) {
        try { action.run();throw new AssertionError("expected rejection: "+message); }
        catch(IllegalStateException expected) { check(expected.getMessage().contains(message)); }
    }
    private static byte[] render(long handle) { return NativeBridge.exchange(handle,0,null); }
    private static byte[] titleEvent(byte[] packet,String value) {
        UiPacket p=UiPacket.decode(packet);
        return p.event("title",p.nodes.get("title").generation,"textChange",value);
    }
    private static void title(byte[] packet,String revision,String value) {
        UiPacket p=UiPacket.decode(packet);
        check(p.revision.equals(revision));
        check(p.nodes.get("heading").text("text","").equals(value));
        check(p.nodes.get("title").text("value","").equals(value));
    }
    public static void main(String[] args) throws ReflectiveOperationException {
        long h=NativeBridge.create(),other=NativeBridge.create();
        check(h!=0 && other!=0 && h!=other);
        byte[] initial=render(h);
        title(initial,"1","Release checklist");
        NativeBridge.Candidate first=NativeBridge.prepareV2(h,0,null);
        check(first!=null && first.token()!=0);
        check(Arrays.equals(initial,first.packet()));
        byte[] alias=first.packet();
        check(alias!=first.packet());
        Arrays.fill(alias,(byte)0);
        check(Arrays.equals(initial,first.packet()));
        reject(()->NativeBridge.prepareV2(h,0,null),"status 5");
        reject(()->render(h),"status 5");
        check(NativeBridge.commitV2(other,first.token())==6);
        check(NativeBridge.abortV2(other,first.token())==6);
        check(NativeBridge.commitV2(h,0)==6);
        check(NativeBridge.abortV2(h,0)==6);
        check(NativeBridge.commitV2(h,Long.MIN_VALUE)==6);
        check(NativeBridge.abortV2(h,-1)==6);
        check(NativeBridge.abortV2(h,first.token())==0);
        check(NativeBridge.abortV2(h,first.token())==0);
        check(NativeBridge.commitV2(h,first.token())==6);
        check(Arrays.equals(initial,render(h)));

        String value="JNI Café 東京 🧪";
        byte[] event=titleEvent(initial,value);
        NativeBridge.Candidate update=NativeBridge.prepareV2(h,1,event);
        title(update.packet(),"2",value);
        // Both caller input and returned packet can be discarded before decision.
        Arrays.fill(event,(byte)0);
        Arrays.fill(update.packet(),(byte)0);
        check(NativeBridge.abortV2(h,update.token())==0);
        check(Arrays.equals(initial,render(h)));
        event=titleEvent(initial,value);
        NativeBridge.Candidate retry=NativeBridge.prepareV2(h,1,event);
        check(retry.token()!=update.token());
        check(NativeBridge.abortV2(h,update.token())==0);
        reject(()->render(h),"status 5");
        check(NativeBridge.commitV2(h,retry.token())==0);
        check(NativeBridge.commitV2(h,retry.token())==6);
        check(NativeBridge.abortV2(h,retry.token())==6);
        title(render(h),"2",value);
        byte[] stale=event;
        reject(()->NativeBridge.prepareV2(h,1,stale),"status 4");
        title(render(h),"2",value);

        for(int operation:new int[]{-1,2,Integer.MAX_VALUE})
            reject(()->NativeBridge.prepareV2(h,operation,null),"invalid input bounds");
        reject(()->NativeBridge.prepareV2(h,0,new byte[1]),"invalid input bounds");
        reject(()->NativeBridge.prepareV2(h,1,new byte[131073]),"invalid input bounds");
        reject(()->NativeBridge.prepareV2(h,1,new byte[131072]),"status 4");
        reject(()->NativeBridge.prepareV2(h,1,new byte[0]),"status 4");
        reject(()->NativeBridge.prepareV2(h,1,null),"status 4");
        title(render(h),"2",value);

        // Check the constructor and accessor ownership boundary directly,
        // including a nonzero UInt64 with Java's sign bit set.
        Constructor<NativeBridge.Candidate> ctor=NativeBridge.Candidate.class.getDeclaredConstructor(long.class,byte[].class);
        ctor.setAccessible(true);
        byte[] source="owned".getBytes(StandardCharsets.UTF_8);
        NativeBridge.Candidate high=ctor.newInstance(Long.MIN_VALUE,source);
        check(high.token()==Long.MIN_VALUE);
        Arrays.fill(source,(byte)0);
        check(new String(high.packet(),StandardCharsets.UTF_8).equals("owned"));
        for(long token:new long[]{0}) {
            try { ctor.newInstance(token,source);throw new AssertionError("zero token accepted"); }
            catch(InvocationTargetException expected) { check(expected.getCause() instanceof IllegalArgumentException); }
        }
        try { ctor.newInstance(1,null);throw new AssertionError("null packet accepted"); }
        catch(InvocationTargetException expected) { check(expected.getCause() instanceof IllegalArgumentException); }

        // Repetition under -Xcheck:jni exercises local-reference/resource cleanup.
        for(int i=0;i<512;i++) {
            NativeBridge.Candidate c=NativeBridge.prepareV2(h,0,new byte[0]);
            check(c.token()!=0 && NativeBridge.abortV2(h,c.token())==0);
        }
        long[] extras=new long[14];
        for(int i=0;i<extras.length;i++) { extras[i]=NativeBridge.create();check(extras[i]!=0); }
        reject(()->NativeBridge.create(),"session limit");
        for(long extra:extras) NativeBridge.destroy(extra);
        NativeBridge.Candidate pending=NativeBridge.prepareV2(h,0,null);
        NativeBridge.destroy(h);
        check(NativeBridge.commitV2(h,pending.token())==2);
        check(NativeBridge.abortV2(h,pending.token())==2);
        reject(()->NativeBridge.prepareV2(h,0,null),"status 2");
        reject(()->NativeBridge.destroy(h),"stale session");
        NativeBridge.destroy(other);
        long replacement=NativeBridge.create();
        check(replacement!=h && NativeBridge.commitV2(replacement,pending.token())==6);
        NativeBridge.destroy(replacement);
        System.out.println("PASS "+checks+" production JNI assertions");
    }
}
