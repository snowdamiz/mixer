package android.graphics;
import dev.mixer.android.ConcreteHostProbe;
public class Paint {public static final int ANTI_ALIAS_FLAG=1;public enum Style {FILL,STROKE}public int color;public float strokeWidth;public Style style=Style.FILL;public Paint(){}public Paint(int flags){}
public void setColor(int color){ConcreteHostProbe.hit("Paint.setColor","entry",this);this.color=color;ConcreteHostProbe.hit("Paint.setColor","beforeReturn",this);}
public void setStrokeWidth(float width){ConcreteHostProbe.hit("Paint.setStrokeWidth","entry",this);strokeWidth=width;ConcreteHostProbe.hit("Paint.setStrokeWidth","beforeReturn",this);}
public void setStyle(Style style){ConcreteHostProbe.hit("Paint.setStyle","entry",this);this.style=style;ConcreteHostProbe.hit("Paint.setStyle","beforeReturn",this);}}
