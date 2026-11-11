package dev.mixer.android;
import android.app.Activity;
import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.drawable.Drawable;
import android.widget.FrameLayout;
import java.nio.file.Files;
import java.nio.file.Path;
import java.lang.reflect.*;

public final class EditorOpacityHostTests {
    static int checks;
    static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    static Object get(Object o,String name)throws Exception{var f=o.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(o);}
    static Drawable drawable(String name,NativeAppearanceViewsV2.Record record)throws Exception{
        var c=Class.forName("dev.mixer.android.NativeAppearanceViewsV2$"+name).getDeclaredConstructor(NativeAppearanceViewsV2.Record.class);c.setAccessible(true);return (Drawable)c.newInstance(record);
    }
    static void refuses(Runnable operation,Class<? extends Throwable> type,String message){
        try{operation.run();}catch(Throwable error){check(type.isInstance(error),message+" wrong failure "+error);return;}throw new AssertionError(message+" accepted");
    }
    public static void main(String[] args)throws Exception{
        Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);
        byte[] descriptor=Files.readAllBytes(Path.of(args[0]));activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);
        root.layout(0,0,1206,2622);activity.window.getDecorView().layout(0,0,1206,2622);root.hostAttach(new Object());
        NativeOwnerV2 owner=NativeOwnerV2.external(activity,root,new ExternalFrameSourceV2(e->{}));
        owner.installExternal(Files.readAllBytes(Path.of(args[1])),descriptor);
        NativeRenderer renderer=(NativeRenderer)get(get(owner,"coordinator"),"renderer");
        var record=renderer.inspectV2().get("task.title");check(record!=null&&owner.hasCommittedPresentation(),"live field");
        Drawable cursor=drawable("Cursor",record),handle=drawable("Handle",record);
        if(args.length>2&&args[2].equals("baseline")){
            // Editor.InsertionHandleView.updateDrawable invokes setAlpha during onTouchUpEvent.
            try{handle.setAlpha(0);}catch(IllegalArgumentException expected){check(expected.getMessage().equals("authored alpha only"),"exact native failure");expected.printStackTrace(System.out);System.out.println("BASELINE_REPRODUCED authored alpha only; platform handle fade rejected");owner.close();return;}
            throw new AssertionError("baseline must reject legitimate Editor alpha");
        }
        var compose=cursor.getClass().getSuperclass().getDeclaredMethod("presentationColor",int.class);compose.setAccessible(true);
        for(Drawable d:new Drawable[]{cursor,handle}){
            d.setBounds(2,3,14,19);check(d.getAlpha()==255,"opaque default");
            int authored=NativeAppearanceViewsV2.color(d==cursor?NativeAppearanceViewsV2.fieldPaint(record).caret():NativeAppearanceViewsV2.fieldPaint(record).selection());
            for(int alpha:new int[]{0,1,64,127,128,129,254,255}){
                int before=d.invalidations;int prior=d.getAlpha();d.setAlpha(alpha);check(d.getAlpha()==alpha,"Editor alpha roundtrip");
                check(d.invalidations==before+(prior==alpha?0:1),"changed alpha invalidates once");
                Canvas canvas=new Canvas();d.draw(canvas);check(canvas.draws.size()==1,"one authored shape");
                int expected=(authored&0xffffff)|((int)Math.floor((authored>>>24)*(alpha/255.0)+0.5)<<24);
                check(canvas.draws.get(0).color()==expected,"actual paint composes authored alpha");
                check(canvas.draws.get(0).method().equals(d==cursor?"drawRect":"drawOval"),"shape unchanged");
            }
            for(int bad:new int[]{-1,256,Integer.MIN_VALUE,Integer.MAX_VALUE}){int saved=d.getAlpha(),count=d.invalidations;refuses(()->d.setAlpha(bad),IllegalArgumentException.class,"invalid alpha");check(d.getAlpha()==saved&&d.invalidations==count,"invalid alpha has no effect");}
            d.setColorFilter(null);refuses(()->d.setColorFilter(new ColorFilter()),IllegalArgumentException.class,"editor color filter");
            android.os.Looper.hostSetMain(false);
            try{refuses(()->d.setAlpha(128),IllegalStateException.class,"thread alpha");refuses(()->d.getAlpha(),IllegalStateException.class,"thread read");refuses(()->d.draw(new Canvas()),IllegalStateException.class,"thread draw");refuses(()->d.setColorFilter(null),IllegalStateException.class,"thread filter");}
            finally{android.os.Looper.hostReset();}
        }
        for(int alpha=0;alpha<=255;alpha++){
            cursor.setAlpha(alpha);
            for(int authoredAlpha=0;authoredAlpha<=255;authoredAlpha++){
                int argb=(authoredAlpha<<24)|0x123456;int got=(Integer)compose.invoke(cursor,argb);
                int expected=(int)Math.floor(authoredAlpha*(alpha/255.0)+0.5);
                check((got>>>24)==expected&&(got&0xffffff)==0x123456,"all authored/presentation alpha pairs");
            }
        }
        var emptyCtor=Class.forName("dev.mixer.android.NativeAppearanceViewsV2$Empty").getDeclaredConstructor(int.class,int.class);emptyCtor.setAccessible(true);Drawable empty=(Drawable)emptyCtor.newInstance(12,12);
        var controlCtor=Class.forName("dev.mixer.android.NativeAppearanceViewsV2$ControlDrawable").getDeclaredConstructor(NativeAppearanceViewsV2.Record.class,boolean.class);controlCtor.setAccessible(true);Drawable control=(Drawable)controlCtor.newInstance(record,true);
        for(Drawable d:new Drawable[]{control,empty}){
            d.setAlpha(255);check(d.getAlpha()==255,"authored alpha immutable");
            for(int a:new int[]{-1,0,128,254,256})refuses(()->d.setAlpha(a),IllegalArgumentException.class,"control restriction");
            d.setColorFilter(null);refuses(()->d.setColorFilter(new ColorFilter()),IllegalArgumentException.class,"control colors");
        }
        // Callback may revoke the captured mutation while invalidateSelf is running.
        cursor.setAlpha(255);ConcreteHostProbe.reset();
        ConcreteHostProbe.hook=(method,phase)->{if(method.equals("Drawable.invalidateSelf")&&phase.equals("beforeReturn")){ConcreteHostProbe.hook=null;record.editorFence.terminal=true;}};
        refuses(()->cursor.setAlpha(128),IllegalStateException.class,"post-invalidation captured fence");ConcreteHostProbe.hook=null;
        Canvas sealed=new Canvas();cursor.draw(sealed);handle.draw(sealed);check(sealed.draws.isEmpty(),"terminal draw gate");
        refuses(()->handle.setAlpha(1),IllegalStateException.class,"terminal mutation gate");
        owner.close();
        System.out.println("PASS EditorOpacityHostTests checks="+checks+" exhaustiveAlphaPairs=65536 hostOnly=true");
    }
}
