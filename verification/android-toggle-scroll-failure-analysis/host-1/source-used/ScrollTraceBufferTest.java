package dev.mixer.android;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

public final class ScrollTraceBufferTest {
    private static int checks;
    private static void need(boolean value){checks++;if(!value)throw new AssertionError("host check "+checks);}
    public static void main(String[] args) throws InterruptedException {
        boolean refused=false;try{new ScrollTraceBuffer(0);}catch(IllegalArgumentException expected){refused=true;}need(refused);
        ScrollTraceBuffer buffer=new ScrollTraceBuffer(2);Map<String,Object> original=new LinkedHashMap<>();original.put("label","initial");buffer.add(original);original.put("label","mutated");
        need(buffer.snapshot().get(0).get("label").equals("initial"));var before=buffer.snapshot();buffer.add(Map.of("label","second"));buffer.add(Map.of("label","dropped"));
        need(before.size()==1&&buffer.snapshot().size()==2&&buffer.dropped()==1);need(buffer.snapshot().get(0).get("sequence").equals(0)&&buffer.snapshot().get(1).get("sequence").equals(1));
        refused=false;try{buffer.snapshot().get(0).put("bad",true);}catch(UnsupportedOperationException expected){refused=true;}need(refused);
        ScrollTraceBuffer concurrent=new ScrollTraceBuffer(100);AtomicReference<Throwable> failure=new AtomicReference<>();Thread[] workers=new Thread[2];
        for(int i=0;i<workers.length;i++){workers[i]=new Thread(()->{try{for(int n=0;n<75;n++)concurrent.add(Map.of("n",n));}catch(Throwable error){failure.set(error);}});workers[i].start();}
        for(Thread worker:workers)worker.join();need(failure.get()==null&&concurrent.snapshot().size()==100&&concurrent.dropped()==50);
        for(int i=0;i<100;i++)need(concurrent.snapshot().get(i).get("sequence").equals(i));
        System.out.println("RESULT {\"status\":\"passed-host-only-trace-buffer\",\"checks\":"+checks+",\"nativeBehaviorVerified\":false}");
    }
}
