package dev.mixer.android;
import android.app.Activity;
import android.view.View;
import android.view.ViewGroup;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
/** Separate positive unchanged V1 apply/children baseline; no V2 gates or fault claims. */
public final class IndependentV1Review {
    private IndependentV1Review(){}
    public static void main(String[] args)throws Exception {
        Path inputs=Path.of(args[0]);ConcreteHostProbe.reset();NativeBridge.reset();Activity context=new Activity();
        NativeRenderer renderer=new NativeRenderer(context,ignored->{throw new AssertionError("programmatic V1 binding cannot emit input");});
        Map<String,ConcreteHostProbe.Site> seen=new LinkedHashMap<>();
        ConcreteHostProbe.hook=(method,phase)->{if(!phase.equals("entry"))return;for(var frame:ConcreteHostProbe.lastEvent().productionFrames)if(frame.className().equals("dev.mixer.android.NativeRenderer")&&frame.methodName().equals("children"))seen.putIfAbsent(method+"@"+frame.bytecodeIndex(),frame);};
        View first=renderer.apply(UiPacket.decode(Files.readAllBytes(inputs.resolve("matrix-packet-base.json"))));
        ViewGroup root=(ViewGroup)first;if(root.getChildCount()==0)throw new AssertionError("V1 positive has actual children");
        View second=renderer.apply(UiPacket.decode(Files.readAllBytes(inputs.resolve("v1-packet-remove.json"))));
        if(first!=second)throw new AssertionError("unchanged V1 root identity preserved");
        long removes=seen.keySet().stream().filter(k->k.startsWith("ViewGroup.removeViewAt@")).count();
        long adds=seen.keySet().stream().filter(k->k.startsWith("ViewGroup.addView@")).count();
        long params=seen.keySet().stream().filter(k->k.startsWith("View.setLayoutParams@")).count();
        long margins=seen.keySet().stream().filter(k->k.startsWith("MarginLayoutParams.setMarginEnd@")).count();
        if(removes!=1||adds!=1||params!=2||margins!=1)throw new AssertionError("all five exact positive V1 children call sites required");
        if(NativeBridge.createCalls!=0||NativeBridge.prepareCalls!=0||NativeBridge.commitCalls!=0)throw new AssertionError("V1 renderer baseline has no V2 engine ownership");
        System.out.println("{\"scope\":\"separate V1 positive apply/children baseline\",\"selectedSites\":5,\"assertions\":8}");
        seen.forEach((key,value)->System.out.println(key+" "+value));ConcreteHostProbe.reset();NativeBridge.reset();
    }
}
