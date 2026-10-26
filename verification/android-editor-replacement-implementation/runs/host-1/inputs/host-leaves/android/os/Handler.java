package android.os;
import java.util.ArrayDeque;import java.util.ArrayList;import java.util.List;
import dev.mixer.android.ConcreteHostProbe;
/** Posts enqueue only. Tests explicitly deliver queued or retained stale identities. */
public class Handler {
    public static Handler latest;
    public boolean postResult=true,removeEffective=true;public Throwable postFailure,removeFailure;
    public int postCalls,removeCalls;private final ArrayDeque<Runnable> work=new ArrayDeque<>();private final Looper looper;
    public Handler(){this(Looper.myLooper());}public Handler(Looper looper){this.looper=looper;latest=this;}
    public Looper getLooper(){return looper;}
    public boolean post(Runnable runnable){ConcreteHostProbe.hit("Handler.post","entry",this);postCalls++;ConcreteHostProbe.fail(postFailure);if(postResult)work.addLast(runnable);ConcreteHostProbe.hit("Handler.post","beforeReturn",this);return postResult;}
    public void removeCallbacks(Runnable runnable){ConcreteHostProbe.hit("Handler.removeCallbacks","entry",this);removeCalls++;ConcreteHostProbe.fail(removeFailure);if(removeEffective)work.removeIf(item->item==runnable);ConcreteHostProbe.hit("Handler.removeCallbacks","beforeReturn",this);}
    public int queued(){return work.size();}public List<Runnable> snapshot(){return new ArrayList<>(work);}
    public boolean drainOne(){Runnable next=work.pollFirst();if(next==null)return false;next.run();return true;}
    public int drainAll(int limit){int count=0;while(count<limit&&drainOne())count++;if(!work.isEmpty())throw new IllegalStateException("host queue delivery bound");return count;}
}
