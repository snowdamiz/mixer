package dev.mixer.android;
import java.nio.*;
import java.nio.charset.*;
import java.math.BigInteger;
import java.util.*;
/** Independently authored bounded JSON codec. Rejects duplicate keys, malformed
 * UTF-8/surrogates, non-finite numbers and excessive construction depth/values. */
final class Json {
    static final class Num {
        final String raw; Num(String raw){this.raw=raw;}
        String unsigned(){if(raw.length()>20||!raw.matches("0|[1-9][0-9]*")||new BigInteger(raw).bitLength()>64)throw bad("unsigned integer");return raw;}
        double number(){double d=Double.parseDouble(raw);if(!Double.isFinite(d))throw bad("finite number");return d;}
    }
    static IllegalArgumentException bad(String text){return new IllegalArgumentException(text);}
    static Object parse(byte[] data){
        if(data==null||data.length>1048576)throw bad("message bytes");
        String text;try{text=StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(data)).toString();}catch(CharacterCodingException e){throw bad("UTF-8");}
        Parser p=new Parser(text);Object value=p.value(0);p.space();if(p.i!=text.length())throw bad("trailing JSON");return value;
    }
    static final class Parser {
        final String s;int i,count;Parser(String s){this.s=s;}
        void space(){while(i<s.length()&&" \t\r\n".indexOf(s.charAt(i))>=0)i++;}
        char take(){if(i==s.length())throw bad("truncated JSON");return s.charAt(i++);}
        Object value(int depth){
            if(depth>196||++count>100000)throw bad("JSON construction limit");space();char c=take();
            if(c=='"')return string();
            if(c=='{'){Map<String,Object> m=new LinkedHashMap<>();space();if(i<s.length()&&s.charAt(i)=='}'){i++;return m;}while(true){space();if(take()!='"')throw bad("object key");String k=string();if(m.containsKey(k)||m.size()>=16384)throw bad("duplicate/too many keys");space();if(take()!=':')throw bad("object colon");m.put(k,value(depth+1));space();c=take();if(c=='}')return m;if(c!=',')throw bad("object comma");}}
            if(c=='['){List<Object>a=new ArrayList<>();space();if(i<s.length()&&s.charAt(i)==']'){i++;return a;}while(true){if(a.size()>=16384)throw bad("array bound");a.add(value(depth+1));space();c=take();if(c==']')return a;if(c!=',')throw bad("array comma");}}
            if(c=='t'){literal("rue");return true;}if(c=='f'){literal("alse");return false;}if(c=='n'){literal("ull");return null;}
            int start=--i;if(s.charAt(i)=='-')i++;if(i>=s.length())throw bad("number");if(s.charAt(i)=='0')i++;else{int b=i;while(i<s.length()&&digit(s.charAt(i)))i++;if(i==b)throw bad("number");}
            if(i<s.length()&&s.charAt(i)=='.'){i++;int b=i;while(i<s.length()&&digit(s.charAt(i)))i++;if(i==b)throw bad("fraction");}
            if(i<s.length()&&(s.charAt(i)=='e'||s.charAt(i)=='E')){i++;if(i<s.length()&&(s.charAt(i)=='+'||s.charAt(i)=='-'))i++;int b=i;while(i<s.length()&&digit(s.charAt(i)))i++;if(i==b)throw bad("exponent");}
            Num n=new Num(s.substring(start,i));n.number();return n;
        }
        static boolean digit(char c){return c>='0'&&c<='9';}
        void literal(String suffix){for(int j=0;j<suffix.length();j++)if(take()!=suffix.charAt(j))throw bad("literal");}
        String string(){StringBuilder b=new StringBuilder();while(true){char c=take();if(c=='"')break;if(c<' ')throw bad("string control");if(c=='\\'){c=take();switch(c){case '"':case '\\':case '/':break;case 'b':c='\b';break;case 'f':c='\f';break;case 'n':c='\n';break;case 'r':c='\r';break;case 't':c='\t';break;case 'u':int n=0;for(int k=0;k<4;k++){int h=Character.digit(take(),16);if(h<0)throw bad("unicode escape");n=(n<<4)|h;}c=(char)n;break;default:throw bad("string escape");}}b.append(c);if(b.length()>1048576)throw bad("string allocation");}String text=b.toString();for(int j=0;j<text.length();j++){char c=text.charAt(j);if(Character.isHighSurrogate(c)){if(++j==text.length()||!Character.isLowSurrogate(text.charAt(j)))throw bad("unpaired surrogate");}else if(Character.isLowSurrogate(c))throw bad("unpaired surrogate");}return text;}
    }
    static byte[] encode(Object value){StringBuilder out=new StringBuilder();write(out,value);byte[] b=out.toString().getBytes(StandardCharsets.UTF_8);if(b.length>1048576)throw bad("encoded message bytes");return b;}
    static void write(StringBuilder out,Object v){if(v==null){out.append("null");return;}if(v instanceof Boolean){out.append(v);return;}if(v instanceof Num){out.append(((Num)v).raw);return;}if(v instanceof String){out.append('"');String s=(String)v;for(int j=0;j<s.length();j++){char u=s.charAt(j);if(Character.isHighSurrogate(u)){if(++j==s.length()||!Character.isLowSurrogate(s.charAt(j)))throw bad("unpaired surrogate");}else if(Character.isLowSurrogate(u))throw bad("unpaired surrogate");}for(int i=0;i<s.length();i++){char c=s.charAt(i);switch(c){case '"':out.append("\\\"");break;case '\\':out.append("\\\\");break;case '\n':out.append("\\n");break;case '\r':out.append("\\r");break;case '\t':out.append("\\t");break;default:if(c<' ')out.append(String.format(Locale.ROOT,"\\u%04x",(int)c));else out.append(c);}}out.append('"');return;}if(v instanceof Map){out.append('{');boolean comma=false;for(Object e:((Map<?,?>)v).entrySet()){Map.Entry<?,?> entry=(Map.Entry<?,?>)e;if(comma)out.append(',');comma=true;write(out,entry.getKey());out.append(':');write(out,entry.getValue());}out.append('}');return;}throw bad("unencodable value");}
    @SuppressWarnings("unchecked")static Map<String,Object> object(Object v){if(!(v instanceof Map))throw bad("object expected");return(Map<String,Object>)v;}
    @SuppressWarnings("unchecked")static List<Object> array(Object v){if(!(v instanceof List))throw bad("array expected");return(List<Object>)v;}
    static String string(Object v){if(!(v instanceof String))throw bad("string expected");return(String)v;}
    static String uint(Object v){if(!(v instanceof Num))throw bad("integer expected");return((Num)v).unsigned();}
    static boolean bool(Object v){if(!(v instanceof Boolean))throw bad("bool expected");return(Boolean)v;}
    static void keys(Map<String,Object> m,String... names){if(!m.keySet().equals(new HashSet<>(Arrays.asList(names))))throw bad("unknown/missing fields");}
    static Map<String,Object> map(Object... pairs){Map<String,Object>m=new LinkedHashMap<>();for(int i=0;i<pairs.length;i+=2)m.put((String)pairs[i],pairs[i+1]);return m;}
}
