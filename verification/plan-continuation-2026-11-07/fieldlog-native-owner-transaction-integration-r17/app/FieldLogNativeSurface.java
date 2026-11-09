package dev.mixer.android;
import android.app.Activity;
import android.view.View;
import android.widget.FrameLayout;

/** Public-host transport delegates every lifecycle effect to the real native owner. */
final class FieldLogNativeSurface implements AutoCloseable {
 private final String identity;
 private final NativeOwnerV2 nativeOwner;
 private boolean closed;
 private int installs;
 FieldLogNativeSurface(Activity activity,FrameLayout root,String owner,NativeRenderer.Events events,Runnable invalidated,java.util.function.Consumer<String> failed) {
  NativeEnvironmentV2.requireMain();identity=owner;
  nativeOwner=NativeOwnerV2.external(activity,root,new ExternalFrameSourceV2(events));
 }
 String owner(){return identity;}
 int installs(){return installs;}
 boolean current(){return nativeOwner.externalCurrent();}
 void resume(){nativeOwner.onResume();}
 void pause(){nativeOwner.onPause();}
 void stop(){nativeOwner.onStop();}
 void invalidationControl(){nativeOwner.changed(observer(),NativeEnvironmentV2.Change.INVALIDATED,null,null,null);}
 View view(String id){return nativeOwner.externalView(id);}
 void gateInput(){nativeOwner.gateExternalInput();}
 void install(String owner,byte[] packet,byte[] appearance){
  NativeEnvironmentV2.requireMain();
  if(closed||!identity.equals(owner))throw new IllegalStateException("foreign/closed external owner");
  nativeOwner.installExternal(packet,appearance);installs++;
 }
 NativeEnvironmentV2.Observer observer(){return nativeOwner.externalObserver();}
 String diagnostic(){return nativeOwner.diagnostic();}
 void terminalControl(){nativeOwner.changed(observer(),NativeEnvironmentV2.Change.EPOCH_EXHAUSTED,null,null,null);}
 @Override public void close(){NativeEnvironmentV2.requireMain();if(closed)return;closed=true;nativeOwner.close();}
}
