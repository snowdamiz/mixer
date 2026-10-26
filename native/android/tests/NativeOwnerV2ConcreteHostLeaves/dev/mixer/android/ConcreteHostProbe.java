package dev.mixer.android;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.BiConsumer;
/** Mechanical host instrumentation. No product authority or expected decisions. */
public final class ConcreteHostProbe {
    private ConcreteHostProbe() {}
    public static BiConsumer<String,String> hook;
    public static final int LIMIT=65536;
    public record Site(String className,String methodName,String descriptor,int bytecodeIndex,int line) {}
    public static final class Event {
        public final String method,phase,productionClass,productionMethod;
        public final int productionLine;
        public final Object receiver;
        public final List<Site> productionFrames;
        Event(String method,String phase,Object receiver,List<Site> frames){
            productionFrames=frames;Site site=frames.isEmpty()?null:frames.get(0);
            this.method=method;this.phase=phase;this.receiver=receiver;
            productionClass=site==null?"":site.className();productionMethod=site==null?"":site.methodName();productionLine=site==null?-1:site.line();
        }
        public String site(){return productionClass+":"+productionLine+":"+productionMethod;}
        @Override public String toString(){return method+"/"+phase+"@"+site();}
    }
    private static final List<Event> history=new ArrayList<>();
    private static final Map<String,Integer> counts=new LinkedHashMap<>();
    private static final StackWalker WALKER=StackWalker.getInstance(StackWalker.Option.RETAIN_CLASS_REFERENCE);
    public static void hit(String method){hit(method,"entry",null);}
    public static void hit(String method,String phase){hit(method,phase,null);}
    public static void hit(String method,String phase,Object receiver){
        if(history.size()>=LIMIT)throw new IllegalStateException("host probe event bound");
        List<Site> sites=WALKER.walk(frames->frames.filter(frame->production(frame.getClassName())).limit(24)
            .map(frame->new Site(frame.getClassName(),frame.getMethodName(),frame.getDescriptor(),frame.getByteCodeIndex(),frame.getLineNumber())).toList());
        history.add(new Event(method,phase,receiver,sites));String key=method+"/"+phase;
        if(!counts.containsKey(key)&&counts.size()>=4096)throw new IllegalStateException("host probe method bound");
        counts.put(key,counts.getOrDefault(key,0)+1);
        BiConsumer<String,String> callback=hook;if(callback!=null)callback.accept(method,phase);
    }
    private static boolean production(String name){
        if(!name.startsWith("dev.mixer.android."))return false;
        String simple=name.substring("dev.mixer.android.".length()).split("\\$",2)[0];
        return switch(simple){case "NativeOwnerV2","OwnerLifecycleV2","NativeCoordinatorV2","NativeRenderer","NativeEnvironmentV2","NativeEnvironmentPlatformV2","NativeAppearanceViewsV2","InstalledAppearanceV2","UiPacket","Json","AppearanceDescriptorV2","AppearanceGeometryV2","AppearanceResolverV2","AppearanceNativePathsV2","AuthoredToggleInputV2"->true;default->false;};
    }
    public static List<Event> events(){return Collections.unmodifiableList(new ArrayList<>(history));}
    public static Event lastEvent(){return history.isEmpty()?null:history.get(history.size()-1);}
    public static int count(String method,String phase){return counts.getOrDefault(method+"/"+phase,0);}
    public static void reset(){hook=null;history.clear();counts.clear();}
    public static void fail(Throwable failure){if(failure instanceof Error error)throw error;if(failure instanceof RuntimeException runtime)throw runtime;if(failure!=null)throw new IllegalArgumentException("host failure must be unchecked",failure);}
}
