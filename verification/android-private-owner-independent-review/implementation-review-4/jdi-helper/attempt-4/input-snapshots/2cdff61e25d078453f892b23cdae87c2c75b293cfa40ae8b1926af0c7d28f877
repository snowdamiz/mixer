package dev.mixer.android;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Review-owned lossless ordered trace encoding; no product decisions or dependencies. */
final class IndependentTraceEncoding {
    private final Map<String,Integer> frames=new LinkedHashMap<>(), events=new LinkedHashMap<>();
    private final List<Integer> counts=new ArrayList<>();
    private final List<int[]> runs=new ArrayList<>();
    private final MessageDigest digest;
    private int length;
    IndependentTraceEncoding(){try{digest=MessageDigest.getInstance("SHA-256");}catch(NoSuchAlgorithmException unavailable){throw new AssertionError(unavailable);}}
    private static String q(String value){return "\""+value.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n")+"\"";}
    void add(String method,String phase,List<String> stack){
        StringBuilder ids=new StringBuilder();for(String frame:stack){if(ids.length()>0)ids.append('|');ids.append(frames.computeIfAbsent(frame,ignored->frames.size()));}
        String key=method+"/"+phase+":"+ids;Integer id=events.get(key);
        if(id==null){id=events.size();events.put(key,id);counts.add(0);}
        counts.set(id,counts.get(id)+1);
        if(!runs.isEmpty()&&runs.get(runs.size()-1)[0]==id)runs.get(runs.size()-1)[1]++;else runs.add(new int[]{id,1});
        digest.update((method+"/"+phase+":"+String.join("|",stack)+"\n").getBytes(StandardCharsets.UTF_8));length++;
    }
    List<String> expand(){
        List<String> fs=new ArrayList<>(frames.keySet()),es=new ArrayList<>(events.keySet()),out=new ArrayList<>();
        for(int[] run:runs){String event=es.get(run[0]);int separator=event.indexOf(':');String tail=event.substring(separator+1);List<String> stack=new ArrayList<>();
            if(!tail.isEmpty())for(String id:tail.split("\\|",-1))stack.add(fs.get(Integer.parseInt(id)));
            String decoded=event.substring(0,separator+1)+String.join("|",stack);for(int i=0;i<run[1];i++)out.add(decoded);
        }return out;
    }
    String json(){
        StringBuilder result=new StringBuilder("{\"schema\":1,\"frames\":[");
        for(String frame:frames.keySet()){if(result.charAt(result.length()-1)!='[')result.append(',');result.append(q(frame));}
        result.append("],\"events\":[");int position=0;
        for(String event:events.keySet()){if(position>0)result.append(',');result.append("{\"identity\":").append(q(event)).append(",\"count\":").append(counts.get(position++)).append('}');}
        result.append("],\"runs\":[");position=0;for(int[] run:runs){if(position++>0)result.append(',');result.append('[').append(run[0]).append(',').append(run[1]).append(']');}
        return result.append("],\"length\":").append(length).append(",\"expanded_sha256\":").append(q(HexFormat.of().formatHex(digest.digest()))).append('}').toString();
    }
}
