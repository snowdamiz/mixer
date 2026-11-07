package android.graphics;
import dev.mixer.android.OwnerHostProbe;
public class Paint {public static final int ANTI_ALIAS_FLAG=1;public enum Style {FILL,STROKE}public int color;public float strokeWidth;public Style style=Style.FILL;public Paint(){}public Paint(int flags){}
public void setColor(int color){OwnerHostProbe.hit("Paint.setColor","entry",this);this.color=color;OwnerHostProbe.hit("Paint.setColor","beforeReturn",this);}
public void setStrokeWidth(float width){OwnerHostProbe.hit("Paint.setStrokeWidth","entry",this);strokeWidth=width;OwnerHostProbe.hit("Paint.setStrokeWidth","beforeReturn",this);}
public void setStyle(Style style){OwnerHostProbe.hit("Paint.setStyle","entry",this);this.style=style;OwnerHostProbe.hit("Paint.setStyle","beforeReturn",this);}}
