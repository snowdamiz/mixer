package dev.mixer.android;
import java.util.List;
/** Tool-only independent A/B/A, phase, repeated and duplicate-frame controls. */
public final class TraceEncodingReview {
    private TraceEncodingReview(){}
    public static void main(String[] args){
        IndependentTraceEncoding trace=new IndependentTraceEncoding();
        List<String> duplicate=List.of("Actual#call()V@3:12","Actual#call()V@3:12");
        trace.add("Leaf.A","entry",duplicate);trace.add("Leaf.A","entry",duplicate);
        trace.add("Leaf.B","beforeReturn",List.of("Actual#other(I)Z@19:27"));
        trace.add("Leaf.A","entry",duplicate);trace.add("Leaf.A","beforeReturn",duplicate);
        trace.add("Leaf.B","entry",List.of());trace.add("Leaf.A","entry",duplicate);
        List<String> expected=List.of("Leaf.A/entry:Actual#call()V@3:12|Actual#call()V@3:12","Leaf.A/entry:Actual#call()V@3:12|Actual#call()V@3:12","Leaf.B/beforeReturn:Actual#other(I)Z@19:27","Leaf.A/entry:Actual#call()V@3:12|Actual#call()V@3:12","Leaf.A/beforeReturn:Actual#call()V@3:12|Actual#call()V@3:12","Leaf.B/entry:","Leaf.A/entry:Actual#call()V@3:12|Actual#call()V@3:12");
        if(!trace.expand().equals(expected))throw new AssertionError("lossless ordered A/B/A phase/frame expansion failed");
        System.out.println(trace.json());
    }
}
