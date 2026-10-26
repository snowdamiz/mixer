from pathlib import Path
D=Path(__file__).resolve().parents[1];p=D/'source/NativeAppearanceViewsV2.java';x=p.read_text()
x=x.replace('(info.imeOptions&(EditorInfo.IME_FLAG_NAVIGATE_NEXT|EditorInfo.IME_FLAG_NAVIGATE_PREVIOUS))!=0)revoke(false);', '''(info.imeOptions&(EditorInfo.IME_FLAG_NAVIGATE_NEXT|EditorInfo.IME_FLAG_NAVIGATE_PREVIOUS))!=0||
                            (info.imeOptions&(EditorInfo.IME_FLAG_NO_EXTRACT_UI|EditorInfo.IME_FLAG_NO_FULLSCREEN))!=(EditorInfo.IME_FLAG_NO_EXTRACT_UI|EditorInfo.IME_FLAG_NO_FULLSCREEN)||
                            !info.getSupportedHandwritingGestures().isEmpty()||!info.getSupportedHandwritingGesturePreviews().isEmpty())revoke(false);''')
a=x.index('        private void scrub(EditorInfo info) {');b=x.index('        private void callback(',a)
x=x[:a]+'''        private void resetOutput(EditorInfo info){
            info.inputType=0;info.imeOptions=0;info.actionId=0;info.actionLabel=null;info.label=null;info.hintText=null;
            info.privateImeOptions=null;info.extras=null;info.contentMimeTypes=null;info.hintLocales=null;
            info.initialSelStart=-1;info.initialSelEnd=-1;info.initialCapsMode=0;
        }
        private void scrub(EditorInfo info) {
            resetOutput(info);
            try{
                info.setSupportedHandwritingGestures(java.util.Collections.emptyList());
                info.setSupportedHandwritingGesturePreviews(java.util.Collections.emptySet());
                info.initialSelStart=-1;info.initialSelEnd=-1;
                info.setInitialSurroundingText("");
            }finally{resetOutput(info);}
            // Exact EditorInfo class is admitted before any effects. These are official public getters;
            // a detected failure remains uncertainty, never fabricated private-payload cleanup success.
            if(!info.getSupportedHandwritingGestures().isEmpty()||!info.getSupportedHandwritingGesturePreviews().isEmpty()||
                info.getInitialSurroundingText(0,0,0)!=null||info.inputType!=0||info.imeOptions!=0||info.hintText!=null||
                info.initialSelStart!=-1||info.initialSelEnd!=-1)throw new IllegalStateException("EditorInfo scrub uncertain");
        }
''' +x[b:]
x=x.replace('                record.input.replacementBegin(record,operation);operation.registered=true;', '                try{record.input.replacementBegin(record,operation);}catch(IllegalStateException refused){return false;}\n                operation.registered=true;')
x=x.replace('                operation.stage=Replacement.Stage.NATIVE;operation.nativeExecuting=true;', '                EditorSnapshot postClose=new EditorSnapshot(this,old);\n                operation.stage=Replacement.Stage.NATIVE;operation.nativeExecuting=true;')
x=x.replace('actual==old&&snapshot.same(this,old)', 'actual==old&&postClose.same(this,old)')
x=x.replace('!operation.setterReturned||operation.nextEditable==null', '!operation.setterReturned||!operation.watcherSeen||operation.nextEditable==null')
p.write_text(x)
