from pathlib import Path
D=Path(__file__).resolve().parents[1];s=D/'source'
p=s/'NativeAppearanceViewsV2.java';x=p.read_text()
x=x.replace('        Mutation mutation();','''        Mutation mutation();
        boolean editorRetained(Record record);
        void editorEnter(Record record, EditorLease lease);
        void editorLeave(Record record, EditorLease lease);
        boolean editorCloseAllowed();
        Mutation editorCleanupMutation(Record record, EditorLease lease);
        void editorDrainBegin(Record record, EditorLease lease);
        void editorDrainEnd(Record record, EditorLease lease);
        void editorFailure(Throwable primary, java.lang.Error firstFatal);''')
x=x.replace('        private Mutation scoped;\n        Mutation mutation() { NativeEnvironmentV2.requireMain();return scoped!=null?scoped:input.mutation(); }','''        private Mutation scoped;
        private boolean constructed;
        EditorLease editorCallbackLease;
        boolean editorEventsAllowed() {
            NativeEnvironmentV2.requireMain();
            return !(view instanceof NativeField field)||field.eventsAllowed();
        }
        boolean editorConstruction() { return scoped!=null&&!constructed; }
        Mutation mutation() {
            NativeEnvironmentV2.requireMain();
            if(editorCallbackLease!=null)return editorCallbackLease.continuation();
            return scoped!=null?scoped:input.mutation();
        }
        void editorAvailable(boolean preserve) {
            NativeEnvironmentV2.requireMain();
            if(view instanceof NativeField field)field.available(preserve);
        }
        void retireEditor() {
            if(view instanceof NativeField field)field.retirePermanent();
        }''')
x=x.replace('            } finally { scoped=null; }','            constructed=true;\n            } finally { scoped=null; }',1)
x=x.replace('mutation.requireMutation();Mutation previousScope=scoped;scoped=mutation;', 'mutation.requireMutation();editorAvailable(preserveEditor);Mutation previousScope=scoped;scoped=mutation;',1)
x=x.replace('if(input.open(this))input.interaction();','if(editorEventsAllowed()&&input.open(this))input.interaction();')
x=x.replace('                    if(changing)return null;','                    if(changing)return null;\n                    if(!editorEventsAllowed())return dst.subSequence(dstart,dend);')
x=x.replace('if(!changing&&input.open(Record.this))input.event', 'if(!changing&&editorEventsAllowed()&&input.open(Record.this))input.event')
x=x.replace('if(action==EditorInfo.IME_ACTION_DONE&&input.open(this)&&binding.source.actions.containsKey("submit"))', 'if(action==EditorInfo.IME_ACTION_DONE&&editorEventsAllowed()&&input.open(this)&&binding!=null&&binding.source.actions.containsKey("submit"))')
a=x.index('    private static final class NativeField extends EditText {');b=x.index('    private static final class NativeSwitch extends Switch',a)
x=x[:a]+(D/'scripts/field.txt').read_text()+x[b:];p.write_text(x)
p=s/'NativeCoordinatorV2.java';x=p.read_text().replace('return active || cancellation || fence.rendererReportActive;', 'return active || cancellation || fence.rendererReportActive || renderer.editorDisposalBusyV2();').replace('        if (disposed) return;\n        disposed = true;', '        if (disposed || busyForOwnerDisposal()) return;\n        disposed = true;');p.write_text(x)
