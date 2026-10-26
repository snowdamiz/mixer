package android.graphics;public final class Color {private Color(){}public static int argb(int a,int r,int g,int b){return (a&255)<<24|(r&255)<<16|(g&255)<<8|(b&255);} }
