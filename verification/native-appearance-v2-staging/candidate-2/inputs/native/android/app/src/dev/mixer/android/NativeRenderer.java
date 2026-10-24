package dev.mixer.android;
import android.content.Context;
import android.os.Build;
import android.text.*;
import android.view.*;
import android.view.inputmethod.EditorInfo;
import android.widget.*;
import java.util.*;

/** Native Android widget toolkit adapter. All state/actions remain in Swift. */
final class NativeRenderer {
    interface Events { void send(byte[] envelope); }
    static final class Record {
        final View view;final ViewGroup children;final TextView title;final String kind,generation;boolean binding;TextWatcher watcher;
        Record(View v,ViewGroup c,TextView t,UiPacket.Node n){view=v;children=c;title=t;kind=n.kind;generation=n.generation;}
    }
    private final Context context;private final Events events;private Map<String,Record>records=new HashMap<>();UiPacket packet;
    NativeRenderer(Context c,Events e){context=c;events=e;}
    private int dp(double value){return(int)Math.round(value*context.getResources().getDisplayMetrics().density);}
    View view(String id){Record r=records.get(id);if(r==null)throw Json.bad("missing native ID "+id);return r.view;}
    View apply(UiPacket next){
        if(android.os.Looper.myLooper()!=android.os.Looper.getMainLooper())throw new IllegalStateException("renderer requires UI thread");next.requireSuccessor(packet);
        if(Build.VERSION.SDK_INT<30)for(UiPacket.Node n:next.nodes.values())if(n.properties.containsKey("accessibilityValue"))throw Json.bad("accessibilityValue requires API30");
        Map<String,Record>candidate=new HashMap<>();for(UiPacket.Node n:next.nodes.values()){Record old=records.get(n.id);candidate.put(n.id,old!=null&&old.kind.equals(n.kind)&&old.generation.equals(n.generation)?old:create(n));}
        for(UiPacket.Node n:next.nodes.values())bind(candidate.get(n.id),n,next);
        for(UiPacket.Node n:next.nodes.values()){Record r=candidate.get(n.id);if(r.children!=null)children(r,n,candidate);}
        packet=next;records=candidate;return records.get(next.root.id).view;
    }
    private Record create(UiPacket.Node n){
        View v;ViewGroup children=null;TextView title=null;
        switch(n.kind){
            case "text":v=new TextView(context);break;
            case "textField":EditText e=new EditText(context);e.setSingleLine(true);e.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);e.setImeOptions(EditorInfo.IME_ACTION_DONE);v=e;break;
            case "button":Button b=new Button(context);b.setAllCaps(false);v=b;break;
            case "toggle":v=new Switch(context);break;
            case "zStack":FrameLayout z=new FrameLayout(context);v=z;children=z;break;
            case "list":ScrollView scroll=new ScrollView(context);scroll.setFillViewport(true);LinearLayout content=new LinearLayout(context);content.setOrientation(LinearLayout.VERTICAL);content.setPadding(dp(16),dp(8),dp(16),dp(24));scroll.addView(content,new ScrollView.LayoutParams(-1,-2));v=scroll;children=content;break;
            case "section":case "navigation":LinearLayout outer=new LinearLayout(context);outer.setOrientation(LinearLayout.VERTICAL);title=new TextView(context);title.setTextSize(n.kind.equals("navigation")?22:15);title.setTypeface(null,android.graphics.Typeface.BOLD);title.setPadding(dp(8),dp(16),dp(8),dp(12));outer.addView(title,new LinearLayout.LayoutParams(-1,-2));LinearLayout inner=new LinearLayout(context);inner.setOrientation(LinearLayout.VERTICAL);outer.addView(inner,new LinearLayout.LayoutParams(-1,n.kind.equals("navigation")?-1:-2));v=outer;children=inner;break;
            default:LinearLayout layout=new LinearLayout(context);layout.setOrientation(n.kind.equals("hStack")?LinearLayout.HORIZONTAL:LinearLayout.VERTICAL);v=layout;children=layout;break;
        }
        v.setId(View.generateViewId());v.setTag(n.id);return new Record(v,children,title,n);
    }
    private void send(UiPacket source,UiPacket.Node n,String event,Object value){events.send(source.event(n.id,n.generation,event,value));}
    private void bind(Record r,UiPacket.Node n,UiPacket source){
        r.binding=true;View v=r.view;v.setTag(n.text("accessibilityIdentifier",n.id));v.setEnabled(!n.disabled);String label=n.text("accessibilityLabel",n.kind.equals("textField")?n.text("label",""):null);v.setContentDescription(label);
        v.setTooltipText(n.text("accessibilityHint",null));if(Build.VERSION.SDK_INT>=30)v.setStateDescription(n.text("accessibilityValue",null));
        if(r.title!=null){String title=n.text("title","");r.title.setText(title);r.title.setVisibility(title.isEmpty()?View.GONE:View.VISIBLE);}
        switch(n.kind){
            case "text":TextView text=(TextView)v;text.setText(n.text("text",""));String style=n.text("style","body");text.setTextSize(style.equals("title")?26:style.equals("headline")?19:style.equals("caption")?14:16);text.setTypeface(null,style.equals("headline")||style.equals("title")?android.graphics.Typeface.BOLD:android.graphics.Typeface.NORMAL);text.setTextIsSelectable(n.flag("selectable",false));text.setMaxLines((int)n.number("maxLines",Integer.MAX_VALUE));text.setPadding(dp(4),dp(6),dp(4),dp(6));break;
            case "button":Button button=(Button)v;button.setText(n.text("label",""));String role=n.text("role","normal");button.setTextColor(n.disabled?0xff777777:role.equals("destructive")?0xffa52020:0xff304ffe);button.setOnClickListener(ignored->send(source,n,"activate",null));break;
            case "textField":EditText edit=(EditText)v;edit.setHint(n.text("label",""));String value=n.text("value","");if(!edit.getText().toString().equals(value)){int cursor=edit.getSelectionStart();edit.setText(value);edit.setSelection(Math.max(0,Math.min(cursor,value.length())));}edit.setFilters(new InputFilter[]{(src,start,end,dst,dstart,dend)->{String candidate=dst.subSequence(0,dstart).toString()+src.subSequence(start,end)+dst.subSequence(dend,dst.length());return candidate.getBytes(java.nio.charset.StandardCharsets.UTF_8).length<=16384?null:"";}});edit.setOnEditorActionListener((field,action,event)->{if(action==EditorInfo.IME_ACTION_DONE&&n.actions.containsKey("submit")){send(source,n,"submit",null);return true;}return false;});
                if(r.watcher!=null)edit.removeTextChangedListener(r.watcher);TextWatcher next=new TextWatcher(){public void beforeTextChanged(CharSequence s,int st,int count,int after){}public void onTextChanged(CharSequence s,int st,int before,int count){}public void afterTextChanged(Editable s){if(!r.binding)send(source,n,"textChange",s.toString());}};edit.addTextChangedListener(next);r.watcher=next;break;
            case "toggle":Switch toggle=(Switch)v;toggle.setOnCheckedChangeListener(null);toggle.setText(n.text("label",""));toggle.setChecked(n.flag("value",false));toggle.setPadding(dp(4),dp(12),dp(4),dp(12));toggle.setOnCheckedChangeListener((buttonView,checked)->{if(!r.binding)send(source,n,"valueChange",checked);});break;
            case "vStack":case "hStack":LinearLayout stack=(LinearLayout)v;String alignment=n.text("alignment","center");stack.setGravity(alignment.equals("center")?(n.kind.equals("hStack")?Gravity.CENTER_VERTICAL:Gravity.CENTER_HORIZONTAL):gravity(alignment));break;
            default:break;
        }r.binding=false;
    }
    private int gravity(String a){switch(a){case "leading":return Gravity.START;case "trailing":return Gravity.END;case "top":return Gravity.TOP;case "bottom":return Gravity.BOTTOM;case "topLeading":return Gravity.TOP|Gravity.START;case "topTrailing":return Gravity.TOP|Gravity.END;case "bottomLeading":return Gravity.BOTTOM|Gravity.START;case "bottomTrailing":return Gravity.BOTTOM|Gravity.END;default:return Gravity.CENTER;}}
    private void children(Record r,UiPacket.Node n,Map<String,Record>candidate){
        ViewGroup parent=r.children;Set<View>desired=new HashSet<>();for(UiPacket.Node child:n.children)desired.add(candidate.get(child.id).view);for(int i=parent.getChildCount()-1;i>=0;i--)if(!desired.contains(parent.getChildAt(i)))parent.removeViewAt(i);
        for(int i=0;i<n.children.size();i++){View view=candidate.get(n.children.get(i).id).view;if(i>=parent.getChildCount()||parent.getChildAt(i)!=view){if(view.getParent()instanceof ViewGroup)((ViewGroup)view.getParent()).removeView(view);parent.addView(view,i);}
            if(parent instanceof FrameLayout){FrameLayout.LayoutParams lp=new FrameLayout.LayoutParams(-2,-2,gravity(n.text("alignment","center")));view.setLayoutParams(lp);}else{boolean horizontal=n.kind.equals("hStack");int height=n.kind.equals("navigation")?-1:-2;LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(horizontal?-2:-1,height);int spacing=dp(n.number("spacing",n.kind.equals("list")?8:0));if(i+1<n.children.size()){if(horizontal)lp.setMarginEnd(spacing);else lp.bottomMargin=spacing;}view.setLayoutParams(lp);}}
    }
}
