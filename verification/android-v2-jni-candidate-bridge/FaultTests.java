package dev.mixer.android;

import java.util.Arrays;

/** Fault runs are derived/instrumented evidence, separate from production runs. */
public final class FaultTests {
    private static int checks;
    private static void check(boolean condition) {
        checks++;if(!condition) throw new AssertionError("fault check "+checks);
    }
    private static byte[] event(byte[] packet) {
        UiPacket p=UiPacket.decode(packet);
        return p.event("title",p.nodes.get("title").generation,"textChange","must abort");
    }
    public static void main(String[] args) {
        // 1/2 malloc; 3 input copy; 4 array allocation; 5 array delivery;
        // 6 class lookup; 7 constructor lookup; 8 NewObject; 9 ctor clone;
        // 10 array null/no exception; 11 class null/no exception;
        // 12/13 invalid successful C metadata (oversized output / zero token).
        for(int point=1;point<=13;point++) {
            for(int cleanup=0;cleanup<3;cleanup++) {
                if(point<4 && cleanup!=0) continue;
                FaultControl.arm(0,0,null);
                long h=NativeBridge.create();
                byte[] initial=NativeBridge.exchange(h,0,null),input=event(initial);
                OutOfMemoryError original=new OutOfMemoryError("injected "+point+" cleanup "+cleanup);
                FaultControl.arm(point,cleanup,original);
                try { NativeBridge.prepareV2(h,1,input);throw new AssertionError("fault did not fire "+point); }
                catch(Throwable caught) {
                    if(point>=3 && point<=9) check(caught==original);
                    else check(caught instanceof IllegalStateException);
                }
                long[] stats=FaultControl.stats();
                check(stats[0]==(point<4?0:1));
                check(stats[1]==(point<4?0:1));
                // cleanup=1 is unknown/stale abort: destroy must retire.
                // cleanup=2 simulates C's already-closed outcome, with the
                // wrapper closing the real session before returning CLOSED.
                boolean closed=point>=12 || (point>=4 && cleanup!=0);
                if(point>=4 && cleanup==1) check(stats[2]>=1);
                if(point>=4 && point<12 && cleanup==2) check(stats[2]==0);
                FaultControl.arm(0,0,null);
                if(closed) {
                    check(NativeBridge.commitV2(h,stats[3])==2);
                    check(NativeBridge.abortV2(h,stats[3])==2);
                } else {
                    check(Arrays.equals(initial,NativeBridge.exchange(h,0,null)));
                    NativeBridge.Candidate retry=NativeBridge.prepareV2(h,1,input);
                    check(NativeBridge.abortV2(h,retry.token())==0);
                    NativeBridge.destroy(h);
                }
            }
        }
        // Arm every allocating delivery seam after successful prepare. Scalar
        // decisions must make no Java allocation/lookup/copy/exception call.
        for(int point=4;point<=11;point++) {
            for(boolean commit:new boolean[]{false,true}) {
                FaultControl.arm(0,0,null);
                long h=NativeBridge.create();
                NativeBridge.Candidate candidate=NativeBridge.prepareV2(h,0,null);
                FaultControl.arm(point,0,new OutOfMemoryError("scalar must not touch JNI"));
                check((commit?NativeBridge.commitV2(h,candidate.token()):NativeBridge.abortV2(h,candidate.token()))==0);
                FaultControl.arm(0,0,null);NativeBridge.destroy(h);
            }
        }
        System.out.println("PASS "+checks+" derived JNI fault assertions");
    }
}
