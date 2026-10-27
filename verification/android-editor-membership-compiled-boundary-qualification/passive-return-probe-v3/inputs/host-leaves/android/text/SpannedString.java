package android.text;
/** Authored immutable snapshot preserving span identities/ranges/flags. */
public final class SpannedString implements Spanned {
 private final Editable owned;public SpannedString(CharSequence value){owned=new Editable(value);}
 @Override public int length(){return owned.length();}@Override public char charAt(int i){return owned.charAt(i);}@Override public CharSequence subSequence(int a,int b){return owned.subSequence(a,b);}@Override public String toString(){return owned.toString();}
 @Override public <T>T[] getSpans(int a,int b,Class<T> type){return owned.getSpans(a,b,type);}@Override public int getSpanStart(Object value){return owned.getSpanStart(value);}@Override public int getSpanEnd(Object value){return owned.getSpanEnd(value);}@Override public int getSpanFlags(Object value){return owned.getSpanFlags(value);}
}
