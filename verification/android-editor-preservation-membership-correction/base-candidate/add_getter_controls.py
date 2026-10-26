from pathlib import Path
p=Path(__file__).parent/'tests/PreservationCompletionControls.java';s=p.read_text();anchor='    public static void main('
addition=r'''
    private static final class GetterEditable extends Editable {
        Runnable onGetter;String selected;boolean armed;
        GetterEditable(Editable value){super(value);}
        private void before(String method){if(!armed||!method.equals(selected))return;boolean validate=false;for(StackTraceElement frame:Thread.currentThread().getStackTrace())if(frame.getClassName().equals("dev.mixer.android.NativeRenderer")&&frame.getMethodName().equals("validateAttachedV2"))validate=true;if(validate){armed=false;onGetter.run();}}
        @Override public String toString(){before("toString");return super.toString();}
        @Override public <T>T[] getSpans(int start,int end,Class<T> type){before("getSpans");return super.getSpans(start,end,type);}
        @Override public int getSpanStart(Object object){before("getSpanStart");return super.getSpanStart(object);}
        @Override public int getSpanEnd(Object object){before("getSpanEnd");return super.getSpanEnd(object);}
        @Override public int getSpanFlags(Object object){before("getSpanFlags");return super.getSpanFlags(object);}
    }
    private static void getterLoss(){for(String getter:new String[]{"TextView.getEditableText","TextView.getSelectionStart","TextView.getSelectionEnd","toString","getSpans","getSpanStart","getSpanEnd","getSpanFlags"})for(boolean foreign:new boolean[]{false,true})for(boolean repeated:new boolean[]{false,true})try(Fixture f=new Fixture(true,true)){
        boolean custom=!getter.startsWith("TextView.");GetterEditable editable=custom?new GetterEditable(f.a.getText()):null;
        if(custom){Object composition=new Object();editable.setSpan(composition,1,3,Spanned.SPAN_COMPOSING|Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);try{Field text=android.widget.TextView.class.getDeclaredField("text");text.setAccessible(true);text.set(f.a,editable);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
        Observation o=new Observation(f);NativeAppearanceViewsV2.NativeField changed=foreign?f.c:f.a;long before=(Long)get(f.renderer,"editorLossSerial");boolean[] fired={false};int[] supers={0};Fatal first=new Fatal("getter lifecycle native superclass F"),later=new Fatal("getter reporter G");boolean fatal=getter.equals("getSpanEnd")&&!repeated;
        Runnable lose=()->{if(fired[0])return;fired[0]=true;for(int i=0;i<(repeated?2:1);i++)try{changed.onWindowFocusChanged(false);}catch(RuntimeException|Error expected){/* field/renderer retain the first native or reporting failure */}if(repeated)try{changed.onWindowFocusChanged(true);}catch(RuntimeException|Error expected){/* gain must not recover successful authority */}};
        if(custom){editable.selected=getter;editable.onGetter=lose;editable.armed=true;}
        ConcreteHostProbe.hook=(method,phase)->{var entry=ConcreteHostProbe.lastEvent();o.event(method,phase);
            if(!custom&&!fired[0]&&o.captured&&entry.receiver==f.a&&method.equals(getter)&&phase.equals("beforeReturn")&&in("validateAttachedV2"))lose.run();
            if(fired[0]&&entry.receiver==changed&&method.equals("View.onWindowFocusChanged")&&phase.equals("entry")){supers[0]++;check(f.count()==3,"getter lifecycle uses existing exact A/C/B holds");if(fatal)throw first;}
            if(fired[0]&&fatal&&method.equals("Handler.post")&&phase.equals("entry")){check(f.count()==3,"later getter reporter still under all holds");throw later;}
        };
        Throwable escaped=null;try{f.edit();}catch(RuntimeException|Error failure){escaped=failure;}ConcreteHostProbe.hook=null;
        System.out.println("GETTER_LOSS getter="+getter+" foreign="+foreign+" repeat="+repeated+" fired="+fired[0]+" supers="+supers[0]+" observationDelta="+((Long)get(f.renderer,"editorLossSerial")-before)+" terminal="+f.fence().terminal+" shared="+f.count()+" escaped="+escaped);
        check(fired[0]&&supers[0]==(repeated?3:1)&&(Long)get(f.renderer,"editorLossSerial")==before+(repeated?2:1),"each getter loss occurrence retains denial observation and exact superclass suffix");
        check(f.fence().terminal&&!o.atCommit&&f.count()==0&&(Boolean)get(changed,"permanent")&&NativeBridge.commitCalls==1,"getter loss/gain cannot commit or revive native authority; balanced scope cleanup");if(fatal)check(escaped==first,"getter native first fatal survives later report while other scopes release");
        int events=ConcreteHostProbe.events().size();long marker=(Long)get(f.renderer,"editorLossSerial");try{o.scopes[0].lifecycle("windowFocus",true,()->{throw new AssertionError("replayed denial");},()->{},()->{throw new AssertionError("replayed native suffix");});throw new AssertionError("ended scope lifecycle replay");}catch(IllegalStateException expected){check(ConcreteHostProbe.events().size()==events&&(Long)get(f.renderer,"editorLossSerial")==marker,"ended captured lifecycle replay inert");}
    }}
'''
assert anchor in s;s=s.replace(anchor,addition+anchor);s=s.replace('case "imbalances"->imbalances();default','case "imbalances"->imbalances();case "getter-loss"->getterLoss();default');p.write_text(s)
