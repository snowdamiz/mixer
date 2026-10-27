package dev.mixer.android;
import java.util.*;
/** Actual supplementary stack walk. A saturated old24 prefix is never treated as complete. */
public final class FullFrames {
 private FullFrames(){}private static final int LIMIT=128;private static final StackWalker WALKER=StackWalker.getInstance(StackWalker.Option.RETAIN_CLASS_REFERENCE);
 private static final Set<String> SOURCES=Set.of("NativeEditorConnectionV2","NativeOwnerV2","OwnerLifecycleV2","NativeCoordinatorV2","NativeRenderer","NativeEnvironmentV2","NativeEnvironmentPlatformV2","NativeAppearanceViewsV2","InstalledAppearanceV2","UiPacket","Json","AppearanceDescriptorV2","AppearanceGeometryV2","AppearanceResolverV2","AppearanceNativePathsV2","AuthoredToggleInputV2");
 private static boolean selected(String name){if(!name.startsWith("dev.mixer.android."))return false;return SOURCES.contains(name.substring("dev.mixer.android.".length()).split("\\$",2)[0]);}
 static List<ConcreteHostProbe.Site> complete(List<ConcreteHostProbe.Site> original){
  if(original.size()<24)return original;
  List<ConcreteHostProbe.Site> actual=WALKER.walk(stream->stream.filter(frame->selected(frame.getClassName())).limit(LIMIT+1).map(frame->new ConcreteHostProbe.Site(frame.getClassName(),frame.getMethodName(),frame.getDescriptor(),frame.getByteCodeIndex(),frame.getLineNumber())).toList());
  if(actual.size()>LIMIT)throw new AssertionError("full product frame overflow refuses evidence");int found=-1;
  for(int i=0;i+original.size()<=actual.size();i++)if(actual.subList(i,i+original.size()).equals(original)){if(found>=0)throw new AssertionError("ambiguous actual saturated frame prefix");found=i;}
  if(found<0)throw new AssertionError("saturated old frame prefix absent from actual full stack");return List.copyOf(actual.subList(found,actual.size()));
 }
}
