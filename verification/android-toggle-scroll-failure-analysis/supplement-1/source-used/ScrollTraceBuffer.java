package dev.mixer.android;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Private bounded observation storage. Saturation never changes event delivery. */
final class ScrollTraceBuffer {
    private final int limit;
    private final List<Map<String,Object>> rows=new ArrayList<>();
    private int dropped;
    ScrollTraceBuffer(int limit){if(limit<1)throw new IllegalArgumentException("positive limit");this.limit=limit;}
    synchronized void add(Map<String,Object> row){
        if(rows.size()==limit){dropped++;return;}
        Map<String,Object> copy=new LinkedHashMap<>(row);copy.put("sequence",rows.size());
        rows.add(Collections.unmodifiableMap(copy));
    }
    synchronized List<Map<String,Object>> snapshot(){return List.copyOf(rows);}
    synchronized int dropped(){return dropped;}
}
