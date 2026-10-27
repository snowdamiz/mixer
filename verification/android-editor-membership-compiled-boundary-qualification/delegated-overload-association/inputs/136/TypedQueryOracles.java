package dev.mixer.android;
import java.util.*;
/** Independent literal value/type/field-order oracles for the explicit hello/cursor5 query fixture. */
public final class TypedQueryOracles {
 private TypedQueryOracles(){}
 private static Map<String,Object> field(String name,String type,Object value){return Map.of("field",name,"type",type,"value",value);}
 private static Map<String,Object> snapshot(String name,List<Object> fields){return Map.of("kind","typed-snapshot","class","android.view.inputmethod."+name,"fields",fields);}
 private static Map<String,Object> surrounding(){return snapshot("SurroundingText",List.of(field("text","java.lang.CharSequence:string","hello"),field("start","int",5),field("end","int",5),field("offset","int",0)));}
 static Object expected(String family){return switch(family){
  case "getCursorCapsMode"->Map.of("kind","integer","value",3);
  case "getSelectedText","getTextAfterCursor"->Map.of("kind","string","value","");
  case "getTextBeforeCursor"->Map.of("kind","string","value","lo");
  case "getExtractedText"->snapshot("ExtractedText",List.of(field("text","java.lang.CharSequence:string","hello"),field("startOffset","int",0),field("partialStartOffset","int",-1),field("partialEndOffset","int",-1),field("selectionStart","int",5),field("selectionEnd","int",5),field("flags","int",0)));
  case "getSurroundingText"->surrounding();
  case "takeSnapshot"->snapshot("TextSnapshot",List.of(field("text","android.view.inputmethod.SurroundingText",surrounding())));
  default->throw new AssertionError("unselected query oracle "+family);
 };}
 static Object contents(Object value){if(value instanceof Map<?,?> map){Map<String,Object> out=new LinkedHashMap<>();for(var entry:map.entrySet())if(!entry.getKey().equals("identity"))out.put((String)entry.getKey(),contents(entry.getValue()));return out;}if(value instanceof List<?> list){List<Object> out=new ArrayList<>();for(Object item:list)out.add(contents(item));return out;}return value;}
}
