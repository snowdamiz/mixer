package dev.mixer.android;
import java.util.*;
/** Passive actual value/reference recorder. It cannot decide product authority. */
public final class OutcomeCapture {
 final List<Object> rows=new ArrayList<>();private boolean ended,latchedClean;
 void begin(){NativeOutcomeProbe.begin(value->{Map<String,Object> row=new LinkedHashMap<>();row.put("method",value.method());row.put("descriptor",value.descriptor());row.put("completion",value.completion());row.put("receiver_identity",DirectBoundaryStates.identity(value.receiver()));row.put("value",actual(value.value()));row.put("original_exception_class",value.originalException()==null?null:value.originalException().getClass().getName());row.put("original_exception_identity",DirectBoundaryStates.identity(value.originalException()));List<Object> frames=new ArrayList<>();for(var f:value.productionFrames())frames.add(Map.of("class",f.className(),"method",f.methodName(),"descriptor",f.descriptor(),"bci",f.bytecodeIndex(),"line",f.line()));row.put("production_frames",frames);rows.add(row);});}
 void end(){NativeOutcomeProbe.end();latchedClean=NativeOutcomeProbe.clean();ended=true;}
 boolean clean(){return ended&&latchedClean;}
 static Object actual(Object value){if(value==null)return Map.of("kind","null");if(value instanceof Boolean)return Map.of("kind","boolean","value",value);if(value instanceof Integer||value instanceof Long||value instanceof Short||value instanceof Byte)return Map.of("kind","integer","value",value);if(value instanceof Float||value instanceof Double)return Map.of("kind","floating","value",value);if(value instanceof Character)return Map.of("kind","character","value",String.valueOf(value));if(value instanceof String)return Map.of("kind","string","value",value,"identity",DirectBoundaryStates.identity(value));return Map.of("kind","reference","class",value.getClass().getName(),"identity",DirectBoundaryStates.identity(value));}
}
