from pathlib import Path
D=Path(__file__).resolve().parents[1]
p=D/'source/NativeAppearanceViewsV2.java';x=p.read_text()
x=x.replace('        boolean editorCloseAllowed();','        boolean editorCloseAllowed(Record record,NativeField.Attempt attempt);\n        void replacementBegin(Record record,Replacement replacement);\n        void replacementEnd(Record record,Replacement replacement);')
x=x.replace('        final EditorLease editorLease;','        final EditorLease editorLease;\n        final Replacement replacementLease;')
x=x.replace('            this.mode=mode;this.fence=fence;this.token=token;this.editorLease=editorLease;', '            this(mode,fence,token,editorLease,null);\n        }\n        private Mutation(Mode mode,NativeOwnerV2.Fence fence,OwnerLifecycleV2.Token token,EditorLease editorLease,Replacement replacementLease){\n            this.mode=mode;this.fence=fence;this.token=token;this.editorLease=editorLease;this.replacementLease=replacementLease;')
x=x.replace('        static Mutation editorContinuation(', '        static Mutation replacement(Mutation original,Replacement lease,boolean cleanup){return new Mutation(cleanup?Mode.CLEANUP:original.mode,original.fence,cleanup?null:original.token,null,lease);}\n        static Mutation editorContinuation(')
x=x.replace('            if(editorLease!=null)editorLease.exact();', '            if(editorLease!=null)editorLease.exact();\n            if(replacementLease!=null)replacementLease.exact();')
x=x.replace('        void requireMutation() {\n            if(mode', '        void requireMutation() {\n            if(replacementLease!=null)throw new IllegalStateException("replacement cannot authorize bind/layout");\n            if(mode')
x=x.replace('        EditorLease editorCallbackLease;', '        EditorLease editorCallbackLease;\n        Replacement replacementCallback;\n        InputFilter editorFilter;')
x=x.replace('            if(editorCallbackLease!=null)return editorCallbackLease.continuation();', '            if(replacementCallback!=null)return replacementCallback.continuation();\n            if(editorCallbackLease!=null)return editorCallbackLease.continuation();')
x=x.replace('edit.setFilters(new InputFilter[]{(src,start,end,dst,dstart,dend)-> {', 'editorFilter=(src,start,end,dst,dstart,dend)-> {\n                    if(replacementCallback!=null)return replacementCallback.filter(src,start,end,dst,dstart,dend);')
x=x.replace('                }});mutation.require();\n\n                edit.addTextChangedListener', '                };edit.setFilters(new InputFilter[]{editorFilter});mutation.require();\n\n                edit.addTextChangedListener',1)
x=x.replace('public void afterTextChanged(Editable value){if(!changing&&editorEventsAllowed()', 'public void afterTextChanged(Editable value){if(replacementCallback!=null){replacementCallback.watch(value);return;}if(!changing&&editorEventsAllowed()')
# Callable passive getter precedes the final exact tuple checks; retain captured target.
a=x.index('        void exact() {',x.index('static final class EditorLease'));b=x.index('        Mutation continuation()',a)
x=x[:a]+'''        void exact() {
            boolean onStack=false;int bound=0;
            for(EditorLease cursor=record.editorCallbackLease;cursor!=null&&bound++<16;cursor=cursor.parent)if(cursor==this){onStack=true;break;}
            if(!onStack||!entered||ended||record.view!=field||field.attempt!=attempt||editable==null)
                throw new IllegalStateException("lost exact editor continuation");
            Editable actual=field.nativeEditable();
            if(!entered||ended||record.view!=field||field.attempt!=attempt||!record.input.editorRetained(record)||actual!=editable||
                attempt!=null&&attempt.target!=target||record.editorCallbackLease==null)
                throw new IllegalStateException("lost exact editor continuation after getter");
        }
''' +x[b:]
x=x.replace('    static final class NativeField extends EditText {', (D/'scripts/replacement.txt').read_text()+'    static final class NativeField extends EditText {')
x=x.replace('        private Attempt attempt;','        private Attempt attempt;\n        private Replacement replacement;')
x=x.replace('Editable nativeEditable(){return super.getText();}', 'Editable nativeEditable(){return super.getEditableText();}')
x=x.replace('return record!=null&&!finishing&&!denied()', 'return record!=null&&replacement==null&&!finishing&&!denied()')
x=x.replace('record.binding!=null&&!record.changing&&!finishing&&!denied()', 'record.binding!=null&&!record.changing&&replacement==null&&!finishing&&!denied()')
x=x.replace('if(finishing||denied()||phase==Phase.CREATING', 'if(replacement!=null||finishing||denied()||phase==Phase.CREATING')
x=x.replace('if(!record.input.editorCloseAllowed())', 'if(!record.input.editorCloseAllowed(record,old))')
x=x.replace('                if(record.view!=this||!record.input.editorRetained(record)||nativeEditable()!=old.editable||old.editable==null)\n                    throw new IllegalStateException("close lost retained exact Editable");\n                phase=Phase.CLOSING;old.close=Close.ATTEMPTED;\n                old.target.closeConnection();', '                lease.exact();\n                phase=Phase.CLOSING;old.close=Close.ATTEMPTED;\n                lease.target.closeConnection();')
x=x.replace('if(info==null||finishing||depth!=0', 'if(info==null||info.getClass()!=EditorInfo.class||replacement!=null||finishing||depth!=0')
x=x.replace('            if(record==null){nativeCall.run();return;}\n            if(construction())', '            if(record==null){nativeCall.run();return;}\n            if(replacement!=null&&replacement.nativeExecuting){try{replacement.callback(hook,nativeCall);}catch(RuntimeException|java.lang.Error failure){uncertain(failure);surface();}return;}\n            if(construction())',1)
x=x.replace('            if(record==null){nativeCall.run();return;}\n            if(construction())', '            if(record==null){nativeCall.run();return;}\n            if(replacement!=null&&replacement.nativeExecuting){\n                try{if(loss){denial.run();revoke(false);}else gain.run();replacement.callback(hook,nativeCall);}\n                catch(RuntimeException|java.lang.Error failure){uncertain(failure);surface();}return;\n            }\n            if(construction())',1)
x=x.replace('            if(record==null){super.setText(value,type);return;}\n            if(construction())', '            if(record==null){super.setText(value,type);return;}\n            if(replacement!=null){replacement.setter(value,type,()->super.setText(value,type));return;}\n            if(construction())')
x=x.replace('            return widget("accessibility",()->{', '            if(action==android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT)return replaceAccessibility(arguments);\n            return widget("accessibility",()->{')
x=x.replace('        @Override public boolean performAccessibilityAction(int action,android.os.Bundle arguments) {', (D/'scripts/replace_method.txt').read_text()+'        @Override public boolean performAccessibilityAction(int action,android.os.Bundle arguments) {')
p.write_text(x)
p=D/'source/NativeRenderer.java';x=p.read_text()
x=x.replace('private NativeAppearanceViewsV2.EditorLease editorDrain,editorFinishing;', 'private NativeAppearanceViewsV2.EditorLease editorDrain,editorFinishing;\n    private NativeAppearanceViewsV2.Replacement editorReplacement;')
x=x.replace('||editorFinishing!=null;', '||editorFinishing!=null||editorReplacement!=null;',1)
x=x.replace('public boolean editorCloseAllowed(){NativeEnvironmentV2.requireMain();return outstandingEditorNativeCalls==0&&!v2Fence.commitFinish&&v2Fence.operation==null;}', '''public boolean editorCloseAllowed(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.NativeField.Attempt attempt){
            NativeEnvironmentV2.requireMain();return outstandingEditorNativeCalls==0&&!v2Fence.commitFinish&&v2Fence.operation==null&&
                (editorReplacement==null||editorReplacement.permitsPredecessor(record,attempt));
        }
        public void replacementBegin(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Replacement replacement){
            NativeEnvironmentV2.requireMain();
            if(editorReplacement!=null||outstandingEditorNativeCalls!=0||editorDrain!=null||editorFinishing!=null||v2Fence.commitFinish||v2Fence.operation!=null||
                replacement==null||replacement.record!=record||record.view!=replacement.field||!retainedEditorV2(record))throw Json.bad("replacement reservation unavailable");
            editorReplacement=replacement;
        }
        public void replacementEnd(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.Replacement replacement){
            NativeEnvironmentV2.requireMain();
            if(editorReplacement!=replacement||replacement.record!=record||replacement.nativeExecuting||replacement.setterActive||replacement.callbacks!=0||
                record.replacementCallback!=null||replacement.stage!=NativeAppearanceViewsV2.Replacement.Stage.DONE)throw Json.bad("unfinished replacement reservation");
            editorReplacement=null;
        }''')
x=x.replace('!editorCloseAllowed()||lease==null', 'lease==null||!editorCloseAllowed(record,lease.attempt)')
x=x.replace('            if(!open(record))return;interaction();if(open(record))events.send', '            if(!record.editorEventsAllowed()||!open(record))return;interaction();if(record.editorEventsAllowed()&&open(record))events.send')
p.write_text(x)
