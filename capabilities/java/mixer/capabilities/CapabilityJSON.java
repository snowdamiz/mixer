package mixer.capabilities;

import java.nio.*;
import java.nio.charset.*;
import java.util.*;

/** Owned bounded JSON grammar. Never delegates duplicate handling to org.json. */
final class CapabilityJSON {
    private final String text;
    private int index, values;
    private CapabilityJSON(String text) { this.text = text; }
    static IllegalArgumentException bad(String reason) { return new IllegalArgumentException("capability wire: " + reason); }
    static Set<String> keys(String... values) { return new HashSet<>(Arrays.asList(values)); }
    static Map<String,Object> map(Object... pairs) {
        Map<String,Object> result=new LinkedHashMap<>(); for(int i=0;i<pairs.length;i+=2) result.put((String)pairs[i],pairs[i+1]); return result;
    }
    static List<Object> headerValues(List<CapabilityModels.Header> headers) {
        List<Object> result=new ArrayList<>();for(CapabilityModels.Header header:headers)result.add(header.wire());return result;
    }
    static Map<String,Object> parse(byte[] bytes) {
        if(bytes==null || bytes.length > 524288) throw bad("bytes");
        bytes=bytes.clone();
        final String text;
        try { text = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString(); }
        catch(CharacterCodingException e) { throw bad("UTF8"); }
        CapabilityJSON parser = new CapabilityJSON(text);
        Map<String,Object> result = object(parser.value(0)); parser.space();
        if(parser.index != text.length()) throw bad("trailing input");
        return result;
    }
    private void space() { while(index < text.length() && " \t\r\n".indexOf(text.charAt(index)) >= 0) index++; }
    private boolean take(char c) { if(index < text.length() && text.charAt(index) == c) { index++; return true; } return false; }
    private void need(char c) { if(!take(c)) throw bad("syntax"); }
    private Object value(int depth) {
        if(++values > 8192) throw bad("values"); space(); if(index >= text.length()) throw bad("truncated");
        char c = text.charAt(index);
        if(c == '{') {
            if(depth >= 8) throw bad("depth"); index++; space(); Map<String,Object> map = new LinkedHashMap<>(); if(take('}')) return map;
            while(true) { space(); String key = string(64); space(); need(':'); Object val = value(depth+1);
                if(map.containsKey(key)) throw bad("duplicate key"); map.put(key,val); space(); if(take('}')) return map; need(','); }
        }
        if(c == '[') {
            if(depth >= 8) throw bad("depth"); index++; space(); List<Object> list = new ArrayList<>(); if(take(']')) return list;
            while(true) { list.add(value(depth+1)); space(); if(take(']')) return list; need(','); }
        }
        if(c == '"') return string(350000);
        if(text.startsWith("true",index)) { index+=4; return Boolean.TRUE; }
        if(text.startsWith("false",index)) { index+=5; return Boolean.FALSE; }
        if(c >= '0' && c <= '9') {
            int start=index; while(index < text.length() && text.charAt(index)>='0' && text.charAt(index)<='9') index++;
            String token=text.substring(start,index); if(token.length()>10 || (token.length()>1 && token.charAt(0)=='0')) throw bad("integer");
            long n; try { n=Long.parseLong(token); } catch(NumberFormatException e) { throw bad("integer"); }
            if(n>4294967295L) throw bad("integer"); return n;
        }
        throw bad("type/syntax");
    }
    private int hex() {
        if(index+4>text.length()) throw bad("escape"); int result=0;
        for(int j=0;j<4;j++) { char c=text.charAt(index++); int n=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:c>='A'&&c<='F'?c-'A'+10:-1;
            if(n<0) throw bad("escape"); result=result*16+n; }
        return result;
    }
    private String string(int maximum) {
        need('"'); StringBuilder result=new StringBuilder(); boolean ended=false;
        while(index<text.length()) {
            char c=text.charAt(index++); boolean pair=false; if(c=='"') { ended=true; break; } if(c<32) throw bad("control");
            if(c=='\\') {
                if(index>=text.length()) throw bad("escape"); char e=text.charAt(index++);
                switch(e) {
                    case '"': c='"'; break; case '\\': c='\\'; break; case '/': c='/'; break;
                    case 'b': c='\b'; break; case 'f': c='\f'; break; case 'n': c='\n'; break; case 'r': c='\r'; break; case 't': c='\t'; break;
                    case 'u':
                        c=(char)hex(); if(Character.isHighSurrogate(c)) { need('\\'); need('u'); char low=(char)hex(); if(!Character.isLowSurrogate(low)) throw bad("surrogate"); result.append(c).append(low); pair=true; }
                        else if(Character.isLowSurrogate(c)) throw bad("surrogate"); break;
                    default: throw bad("escape");
                }
            } else if(Character.isHighSurrogate(c)) {
                if(index>=text.length() || !Character.isLowSurrogate(text.charAt(index))) throw bad("surrogate"); result.append(c).append(text.charAt(index++)); pair=true;
            } else if(Character.isLowSurrogate(c)) throw bad("surrogate");
            if(!pair) result.append(c);
            if(result.length()>maximum) throw bad("string");
        }
        String value=result.toString(); if(!ended || value.getBytes(StandardCharsets.UTF_8).length>maximum) throw bad("string"); return value;
    }
    static Map<String,Object> object(Object value) {
        if(!(value instanceof Map<?,?>)) throw bad("object");
        Map<String,Object> result=new LinkedHashMap<>();
        for(Map.Entry<?,?> entry:((Map<?,?>)value).entrySet()) { if(!(entry.getKey() instanceof String)) throw bad("key"); result.put((String)entry.getKey(),entry.getValue()); }
        return result;
    }
    static void exact(Map<String,Object> object, Set<String> keys) { if(!object.keySet().equals(keys)) throw bad("fields"); }
    static long number(Map<String,Object> object,String key,long minimum,long maximum) { Object value=object.get(key); if(!(value instanceof Long) || (Long)value<minimum || (Long)value>maximum) throw bad(key); return (Long)value; }
    static boolean bool(Map<String,Object> object,String key) { Object value=object.get(key); if(!(value instanceof Boolean)) throw bad(key); return (Boolean)value; }
    static String text(Map<String,Object> object,String key,String rule,int maximum) {
        Object raw=object.get(key); if(!(raw instanceof String)) throw bad(key); String value=(String)raw;
        if(rule.equals("base64")) {
            if(value.length()>((maximum+2)/3)*4) throw bad(key); byte[] bytes;
            try { bytes=Base64.getDecoder().decode(value); } catch(IllegalArgumentException e) { throw bad(key); }
            if(bytes.length>maximum || !Base64.getEncoder().encodeToString(bytes).equals(value)) throw bad(key); return value;
        }
        if(value.length()>maximum) throw bad(key); for(int j=0;j<value.length();j++) if(value.charAt(j)<32||value.charAt(j)>126) throw bad(key);
        switch(rule) {
            case "ascii": break;
            case "identifier": if(!value.matches("[A-Za-z0-9_-]+")) throw bad(key); break;
            case "uuid": try { if(!UUID.fromString(value).toString().equals(value)) throw bad(key); } catch(IllegalArgumentException e) { throw bad(key); } break;
            case "method": if(!CapabilityJSON.keys("GET","POST","PUT","PATCH","DELETE","HEAD").contains(value)) throw bad(key); break;
            case "headerName": if(!value.matches("[a-z0-9-]+") || CapabilityJSON.keys("host","connection","content-length","transfer-encoding","proxy-authorization","proxy-authenticate","cookie","set-cookie").contains(value)) throw bad(key); break;
            case "httpsURL": origin(value); break;
            default: throw bad("rule");
        }
        return value;
    }
    static String origin(String url) {
        if(!url.startsWith("https://") || url.length()>4096) throw bad("URL");
        for(int j=0;j<url.length();j++) { char c=url.charAt(j); if(c<33||c>126||c=='#'||c=='\\') throw bad("URL"); if(c=='%') { if(j+2>=url.length()||!url.substring(j+1,j+3).matches("[0-9A-F]{2}")) throw bad("percent"); j+=2; } }
        String rest=url.substring(8); int end=rest.length(); for(char c:new char[]{'/','?'}) { int j=rest.indexOf(c); if(j>=0) end=Math.min(j,end); }
        String authority=rest.substring(0,end); String[] parts=authority.split(":",-1);
        if(parts.length<1||parts.length>2||parts[0].isEmpty()||parts[0].length()>253) throw bad("origin");
        for(String label:parts[0].split("\\.",-1)) if(label.isEmpty()||label.length()>63||!label.matches("[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")) throw bad("host");
        if(parts.length==2) { int port; try { port=Integer.parseInt(parts[1]); } catch(NumberFormatException e) { throw bad("port"); } if(port<1||port>65535||port==443||!Integer.toString(port).equals(parts[1])) throw bad("port"); }
        return "https://"+authority;
    }
    static List<CapabilityModels.Header> headers(Map<String,Object> object,String key,int maximum) {
        Object raw=object.get(key); if(!(raw instanceof List<?>)||((List<?>)raw).size()>maximum) throw bad(key);
        List<CapabilityModels.Header> headers=new ArrayList<>(); Set<String> names=new HashSet<>();
        for(Object value:(List<?>)raw) { CapabilityModels.Header header=(CapabilityModels.Header)CapabilityModels.decode("Header",object(value)); if(!names.add(header.name)) throw bad("duplicate header"); headers.add(header); }
        return Collections.unmodifiableList(headers);
    }
    static byte[] encode(Map<String,Object> object) { StringBuilder text=new StringBuilder(); append(text,object); byte[] bytes=text.toString().getBytes(StandardCharsets.UTF_8); parse(bytes); return bytes; }
    private static void append(StringBuilder out,Object value) {
        if(value instanceof String) { out.append('"'); for(char c:((String)value).toCharArray()) { if(c=='"'||c=='\\') out.append('\\'); if(c<32) { out.append(String.format("\\u%04x",(int)c)); } else out.append(c); } out.append('"'); }
        else if(value instanceof Long || value instanceof Boolean) out.append(value);
        else if(value instanceof Map<?,?>) { out.append('{'); boolean first=true; for(Map.Entry<String,Object> entry:new TreeMap<>(object(value)).entrySet()) { if(!first)out.append(',');first=false;append(out,entry.getKey());out.append(':');append(out,entry.getValue()); } out.append('}'); }
        else if(value instanceof List<?>) { out.append('['); boolean first=true;for(Object item:(List<?>)value) { if(!first)out.append(',');first=false;append(out,item); }out.append(']'); }
        else throw bad("encode type");
    }
}
