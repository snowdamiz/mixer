from pathlib import Path
p=Path(__file__).resolve().parents[1]/'source/NativeAppearanceViewsV2.java';x=p.read_text()
x=x.replace('        boolean entered,ended;','        boolean entered,ended;\n        EditorSnapshot before;')
x=x.replace('        void check() { continuation().require(); }', '''        void check() {
            exact();
            if(original.current()){original.require();return;}
            if(!original.fence.drawAllowed&&!original.fence.inputAllowed){record.input.editorCleanupMutation(record,this).require();return;}
            // A captured exact suffix can observe accepted synchronous Binding continuity.
            // This postcheck supplies no new Mutation or native entry authority.
            if(original.mode==Mutation.Mode.LIVE_PRESENTATION&&original.result(true))return;
            original.require();
        }''')
x=x.replace('    static final class NativeField extends EditText {', '''    static final class EditorSnapshot {
        final String text;final int start,end;final Object[] spans;final int[] bounds;
        EditorSnapshot(NativeField field,Editable editable){
            text=editable.toString();start=field.getSelectionStart();end=field.getSelectionEnd();
            java.util.ArrayList<Object> composing=new java.util.ArrayList<>();
            for(Object span:editable.getSpans(0,editable.length(),Object.class))if((editable.getSpanFlags(span)&android.text.Spanned.SPAN_COMPOSING)!=0)composing.add(span);
            spans=composing.toArray();bounds=new int[spans.length*3];
            for(int i=0;i<spans.length;i++){bounds[i*3]=editable.getSpanStart(spans[i]);bounds[i*3+1]=editable.getSpanEnd(spans[i]);bounds[i*3+2]=editable.getSpanFlags(spans[i]);}
        }
        boolean same(NativeField field,Editable editable){
            EditorSnapshot next=new EditorSnapshot(field,editable);
            return text.equals(next.text)&&start==next.start&&end==next.end&&java.util.Arrays.equals(spans,next.spans)&&java.util.Arrays.equals(bounds,next.bounds);
        }
    }
    static final class NativeField extends EditText {''')
x=x.replace('            T result=refused;\n            try{result=action.get();lease.check();}', '''            T result=refused;
            try{
                lease.before=new EditorSnapshot(this,expected.editable);lease.check();
                result=action.get();lease.check();
                if(!expected.revoked&&(!validBuffer(expected.editable.toString())||getSelectionStart()<0||getSelectionEnd()<0||
                    getSelectionStart()>expected.editable.length()||getSelectionEnd()>expected.editable.length()))
                    throw new IllegalStateException("invalid native editor result");
                if(!expected.revoked&&result instanceof Boolean completed)result=(T)Boolean.valueOf(lease.original.result(completed));
                else if(!expected.revoked){
                    // Queries require strict original authority and an unchanged editor snapshot.
                    if(!lease.original.current()||!lease.before.same(this,expected.editable))result=refused;
                }
            }''')
# Generic result cast is checked logically by runtime Boolean match; isolate lint.
x=x.replace('        <T> T dispatch(Attempt expected', '        @SuppressWarnings("unchecked")\n        <T> T dispatch(Attempt expected')
x=x.replace('        void close(Attempt expected)', '''        <T> T nativeValue(Attempt expected,T refused,java.util.function.Supplier<T> nativeCall) {
            EditorLease lease=record.editorCallbackLease;
            if(lease==null||lease.attempt!=expected||expected.revoked)return refused;
            lease.check();
            if(lease.before==null||!lease.before.same(this,expected.editable)||!lease.original.current()||!live())return refused;
            lease.exact();return nativeCall.get();
        }
        void close(Attempt expected)''')
x=x.replace('if(record!=null&&eventsAllowed())refreshPaint();','if(record!=null&&eventsAllowed()&&(record.editorCallbackLease==null||record.editorCallbackLease.original.current()))refreshPaint();')
x=x.replace('if(phase==Phase.CREATING||phase==Phase.DRAINING||phase==Phase.CLOSING||phase==Phase.QUARANTINED)\n                throw', 'if(denied()||phase==Phase.CREATING||phase==Phase.DRAINING||phase==Phase.CLOSING||phase==Phase.QUARANTINED)\n                throw')
p.write_text(x)
