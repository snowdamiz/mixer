package dev.mixer.android;
import android.content.Context;
import android.app.Activity;
import android.widget.FrameLayout;
/** Orchestration leaf only. Concrete renderer behavior belongs to separate mandatory closure B. */
final class NativeRenderer {
 interface Events {void send(byte[] bytes);}
 final Context context;final Events events;final NativeEnvironmentV2.Observer observer;final NativeOwnerV2.Fence fence;
 boolean currentOpen,pendingOpen,disposed,cancelling;int disposals,cancellations,finishes;byte[] preparedReference;
 NativeRenderer(Context context,Events events,NativeEnvironmentV2.Observer observer,NativeOwnerV2.Fence fence){this.context=context;this.events=events;this.observer=observer;this.fence=fence;}
 boolean belongsToV2(Context context,NativeEnvironmentV2.Observer observer){return this.context==context&&this.observer==observer;}
 static final class Candidate {final NativeRenderer owner;final OwnerLifecycleV2.Token operation;final NativeEnvironmentV2 environment;Candidate(NativeRenderer owner,NativeEnvironmentV2 environment){this.owner=owner;this.environment=environment;operation=owner.fence.operation;}}
 static final class AttachmentJournal {}
 InstalledAppearanceV2 captureInstalledV2(){OwnerHostProbe.hit("Renderer.captureInstalled","entry",this);InstalledAppearanceV2 result=InstalledAppearanceV2.capture(context,this);OwnerHostProbe.hit("Renderer.captureInstalled","beforeReturn",this);return result;}
 NativeEnvironmentV2 captureEnvironmentV2(Activity activity,FrameLayout root){OwnerHostProbe.hit("Renderer.captureEnvironment","entry",this);if(observer.activity!=activity||observer.root!=root)throw new IllegalArgumentException("foreign leaf window");NativeEnvironmentV2 result=observer.capture();OwnerHostProbe.hit("Renderer.captureEnvironment","beforeReturn",this);return result;}
 Candidate prepareV2(byte[] packet,InstalledAppearanceV2 installed,NativeEnvironmentV2 environment){OwnerHostProbe.hit("Renderer.prepare","entry",this);preparedReference=packet;AppearanceResolverV2.prepare(packet,installed.descriptorCopy(),environment.value,AppearanceResolverV2.Platform.android);Candidate result=new Candidate(this,environment);pendingOpen=false;OwnerHostProbe.hit("Renderer.prepare","beforeReturn",this);return result;}
 AttachmentJournal attachV2(Candidate candidate,FrameLayout root){OwnerHostProbe.hit("Renderer.attach","entry",this);check(candidate);AttachmentJournal result=new AttachmentJournal();OwnerHostProbe.hit("Renderer.attach","beforeReturn",this);return result;}
 void validateAttachedV2(Candidate candidate,AttachmentJournal journal){OwnerHostProbe.hit("Renderer.validate","entry",this);check(candidate);if(!candidate.environment.current(this))throw new IllegalStateException("actual environment stale in renderer leaf validation");OwnerHostProbe.hit("Renderer.validate","beforeReturn",this);}
 void finishV2(Candidate candidate,AttachmentJournal journal){check(candidate);finishes++;currentOpen=false;pendingOpen=false;}
 void rollbackV2(Candidate candidate,AttachmentJournal journal){OwnerHostProbe.hit("Renderer.rollback","entry",this);check(candidate);OwnerHostProbe.hit("Renderer.rollback","beforeReturn",this);}
 void discardV2(Candidate candidate){OwnerHostProbe.hit("Renderer.discard","entry",this);check(candidate);OwnerHostProbe.hit("Renderer.discard","beforeReturn",this);}
 void sealScalarV2(){currentOpen=false;pendingOpen=false;}
 void publishScalarV2(OwnerLifecycleV2.Token presentation){currentOpen=true;pendingOpen=false;}
 boolean editorDisposalBusyV2(){return false;}
 boolean cancellationInProgressV2(){return cancelling;}
 void cancelInputV2(long serial){cancellations++;cancelling=true;try{OwnerHostProbe.hit("Renderer.cancelInput","entry",this);OwnerHostProbe.hit("Renderer.cancelInput","beforeReturn",this);}finally{cancelling=false;}}
 void reportDeferredTerminalV2(){OwnerHostProbe.hit("Renderer.deferredReport","entry",this);OwnerHostProbe.hit("Renderer.deferredReport","beforeReturn",this);}
 void disposeV2(){if(disposed)return;disposed=true;disposals++;OwnerHostProbe.hit("Renderer.dispose","entry",this);OwnerHostProbe.hit("Renderer.dispose","beforeReturn",this);}
 void emit(byte[] bytes){events.send(bytes);}
 void terminal(NativeEnvironmentV2.RendererCause cause,Throwable primary,Error fatal){fence.terminal=true;fence.drawAllowed=false;fence.inputAllowed=false;sealScalarV2();fence.rendererReportActive=true;try{observer.rendererTerminal(this,cause,primary,fatal);OwnerHostProbe.hit("Renderer.terminal.beforeUnwind","entry",this);}finally{fence.rendererReportActive=false;}}
 private void check(Candidate candidate){if(candidate==null||candidate.owner!=this||fence.terminal||candidate.operation==null||candidate.operation!=fence.operation)throw new IllegalStateException("leaf transaction rejected");}
}
