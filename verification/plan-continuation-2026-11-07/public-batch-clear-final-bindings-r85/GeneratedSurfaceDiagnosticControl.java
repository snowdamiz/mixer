import java.util.ArrayDeque;
import java.util.Arrays;
public final class GeneratedSurfaceDiagnosticControl {
    static final ArrayDeque<String> effects=new ArrayDeque<>();
    static final class android { static final class util { static final class Log {
        static int calls; static String tag,message; static Throwable error;
        static int e(String t,String m,Throwable e){calls++;tag=t;message=m;error=e;effects.add("log");return 0;}
    } } }
    static final class Looper { static boolean main=true; static final Object MAIN=new Object(); static Object myLooper(){return main?MAIN:null;} static Object getMainLooper(){return MAIN;} }
    static final class AndroidUINativeSurface {
        static final class Frame { Frame(byte[] a,byte[] b,byte[] c){} }
        RuntimeException failure,gateFailure; int gates,operations;
        void activate(byte[] token){operate();} void install(Frame frame){operate();} void revoke(byte[] token){operate();}
        void operate(){operations++;if(failure!=null)throw failure;}
        void gateInput(){gates++;effects.add("gate");if(gateFailure!=null)throw gateFailure;}
    }
    AndroidUINativeSurface surface=new AndroidUINativeSurface(); long context=7;
    boolean destroyed,failed; byte[] owner; int eventBytes=9; final ArrayDeque<String> events=new ArrayDeque<>();
        private void invalidateEvents() { events.clear(); eventBytes = 2; }
        public int surface(long capturedContext, int operation, byte[] token, byte[] packet, byte[] descriptor) {
            if (Looper.myLooper() != Looper.getMainLooper()) return 1;
            // During open, the native bridge has not returned this lifetime's id.
            if (context == 0 && operation == 0 && !destroyed && !failed) context = capturedContext;
            if (capturedContext != context || surface == null || (destroyed && operation != 2)) return 1;
            try {
                switch (operation) {
                    case 0: if (owner != null) return 1; surface.activate(token); owner = token.clone(); break;
                    case 1: surface.install(new AndroidUINativeSurface.Frame(token, packet, descriptor)); break;
                    case 2: invalidateEvents(); surface.revoke(token); owner = null; break;
                    default: return 1;
                }
                return 0;
            } catch (RuntimeException error) { android.util.Log.e("MixerAndroidHost", "Native surface operation failed: " + operation, error); fail(); return 1; }
        }
        private void fail() { failed = true; invalidateEvents(); if (surface != null) surface.gateInput(); }

    static int checks;
    static void check(boolean b,String m){checks++;if(!b)throw new AssertionError(m);}
    static void reset(){effects.clear();android.util.Log.calls=0;android.util.Log.tag=null;android.util.Log.message=null;android.util.Log.error=null;Looper.main=true;}
    public static void main(String[] args){
        byte[] token={1,2};byte[] payload={80,82,73,86,65,84,69};
        reset();GeneratedSurfaceDiagnosticControl f=new GeneratedSurfaceDiagnosticControl();f.events.add("queued");
        RuntimeException primary=new IllegalStateException("controlled native failure");f.surface.failure=primary;
        check(f.surface(7,1,token,payload,payload)==1,"operation failure still returns refusal");
        check(f.failed&&f.events.isEmpty()&&f.eventBytes==2&&f.surface.gates==1,"failure still invalidates and gates");
        check(android.util.Log.calls==1&&android.util.Log.tag.equals("MixerAndroidHost")&&android.util.Log.message.equals("Native surface operation failed: 1")&&android.util.Log.error==primary,"exact error-boundary arguments");
        check(effects.toString().equals("[log, gate]"),"diagnostic precedes existing fail");
        for(int mode=0;mode<4;mode++){
            reset();f=new GeneratedSurfaceDiagnosticControl();
            if(mode==0)Looper.main=false;
            if(mode==1)f.context=8;
            if(mode==2)f.destroyed=true;
            check(f.surface(7,mode==3?99:1,token,payload,payload)==1,"precondition refusal retained");
            check(android.util.Log.calls==0&&f.surface.operations==0&&!f.failed,"precondition refusal has no new effects");
        }
        reset();f=new GeneratedSurfaceDiagnosticControl();
        check(f.surface(7,0,token,payload,payload)==0&&Arrays.equals(f.owner,token),"activation success");
        check(f.surface(7,1,token,payload,payload)==0,"install success");
        check(android.util.Log.calls==0&&!f.failed&&f.surface.gates==0,"no success logging");
        reset();f=new GeneratedSurfaceDiagnosticControl();f.surface.failure=primary;RuntimeException gate=new IllegalStateException("controlled fail boundary");f.surface.gateFailure=gate;
        try{f.surface(7,1,token,payload,payload);throw new AssertionError("existing fail throw suppressed");}catch(RuntimeException e){check(e==gate,"existing fail exception preserved");}
        check(android.util.Log.error==primary&&f.failed,"primary diagnostic and failed state retained");
        System.out.println("PASS generated surface diagnostic checks="+checks+" exact extracted method; controlled Log/Looper/surface leaves; no Android runtime");
    }
}
