from pathlib import Path
p=Path(__file__).resolve().parents[1]/'source/NativeRenderer.java';x=p.read_text()
x=x.replace('    private int v2RosterCount;', '''    private int v2RosterCount;
    private int outstandingEditorNativeCalls;
    private NativeAppearanceViewsV2.EditorLease editorDrain;
    boolean editorDisposalBusyV2(){NativeEnvironmentV2.requireMain();return outstandingEditorNativeCalls!=0||editorDrain!=null;}
    private boolean retainedEditorV2(NativeAppearanceViewsV2.Record record) {
        if(record==null)return false;
        for(int i=0;i<v2RosterCount;i++)if(v2Roster[i]==record)return true;
        Candidate pending=v2Pending;
        if(pending!=null){for(int i=0;i<pending.targetCount;i++)if(pending.targetRoster[i]==record)return true;
            for(int i=0;i<pending.detachedCount;i++)if(pending.detachedRoster[i]==record)return true;}
        return false;
    }
    private void requireEditorsAvailableV2(){
        for(int i=0;i<v2RosterCount;i++)if(v2Roster[i]!=null)v2Roster[i].editorAvailable(true);
        Candidate pending=v2Pending;
        if(pending!=null){for(int i=0;i<pending.targetCount;i++)if(pending.targetRoster[i]!=null)pending.targetRoster[i].editorAvailable(true);
            for(int i=0;i<pending.detachedCount;i++)if(pending.detachedRoster[i]!=null)pending.detachedRoster[i].editorAvailable(true);}
    }
    private void retireEditorsV2(){
        NativeAppearanceViewsV2.Record[] current=v2Roster;int count=v2RosterCount;Candidate pending=v2Pending;
        retireEditorRosterV2(current,count);
        if(pending!=null){retireEditorRosterV2(pending.targetRoster,pending.targetCount);retireEditorRosterV2(pending.detachedRoster,pending.detachedCount);}
    }
    private void retireEditorRosterV2(NativeAppearanceViewsV2.Record[] records,int count){
        for(int i=0;i<count;i++)if(records[i]!=null)try{records[i].retireEditor();}catch(RuntimeException|java.lang.Error failure){rememberV2(failure);}
    }''')
x=x.replace('        public NativeAppearanceViewsV2.Mutation mutation(){return mutationV2();}', '''        public NativeAppearanceViewsV2.Mutation mutation(){return mutationV2();}
        public boolean editorRetained(NativeAppearanceViewsV2.Record record){NativeEnvironmentV2.requireMain();return retainedEditorV2(record);}
        public void editorEnter(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
            NativeEnvironmentV2.requireMain();
            if(lease==null||lease.record!=record||record.view!=lease.field||!retainedEditorV2(record)||lease.entered||lease.ended||outstandingEditorNativeCalls==Integer.MAX_VALUE)
                throw Json.bad("invalid editor native lease entry");
            outstandingEditorNativeCalls++;
        }
        public void editorLeave(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
            NativeEnvironmentV2.requireMain();
            if(lease==null||lease.record!=record||!lease.entered||!lease.ended||outstandingEditorNativeCalls<=0)
                throw Json.bad("invalid editor native lease exit");
            outstandingEditorNativeCalls--;
        }
        public boolean editorCloseAllowed(){NativeEnvironmentV2.requireMain();return outstandingEditorNativeCalls==0&&!v2Fence.commitFinish&&v2Fence.operation==null;}
        public NativeAppearanceViewsV2.Mutation editorCleanupMutation(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
            NativeEnvironmentV2.requireMain();
            if(lease==null||lease.record!=record||record.editorCallbackLease!=lease)throw Json.bad("foreign editor cleanup continuation");
            lease.exact();NativeAppearanceViewsV2.Mutation scope=NativeAppearanceViewsV2.Mutation.cleanup(v2Fence);scope.require();return scope;
        }
        public void editorDrainBegin(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
            NativeEnvironmentV2.requireMain();
            if(editorDrain!=null||!editorCloseAllowed()||lease==null||lease.record!=record||record.view!=lease.field||!retainedEditorV2(record))throw Json.bad("editor cleanup unavailable");
            editorDrain=lease;
        }
        public void editorDrainEnd(NativeAppearanceViewsV2.Record record,NativeAppearanceViewsV2.EditorLease lease){
            NativeEnvironmentV2.requireMain();
            if(editorDrain!=lease||lease.record!=record)throw Json.bad("unbalanced editor cleanup");
            editorDrain=null;
        }
        public void editorFailure(Throwable primary,java.lang.Error fatal){NativeEnvironmentV2.requireMain();terminalV2(NativeEnvironmentV2.RendererCause.CANCELLATION_FAILED,primary,fatal);}''')
x=x.replace('NativeEnvironmentV2.requireMain();requireV2Live();','NativeEnvironmentV2.requireMain();requireEditorsAvailableV2();requireV2Live();')
x=x.replace('        validateV2(c,false);if(root!=c.environment.root())','        requireEditorsAvailableV2();validateV2(c,false);if(root!=c.environment.root())')
x=x.replace('        if(serial>v2Cleanup.requestedSerial)', '        if(v2Fence.terminal||v2Retired)retireEditorsV2();\n        if(serial>v2Cleanup.requestedSerial)')
x=x.replace('        if(v2Cleanup.inProgress||serial<=v2Cleanup.consumedSerial)return;', '        if(v2Cleanup.inProgress||serial<=v2Cleanup.consumedSerial){if(v2Cleanup.firstFatal!=null)throw v2Cleanup.firstFatal;if(v2Cleanup.primary instanceof RuntimeException failure)throw failure;return;}')
x=x.replace('        if(failure instanceof RuntimeException ordinary)throw ordinary;\n    }\n    boolean cancellationInProgressV2', '        if(v2Cleanup.primary instanceof RuntimeException ordinary)throw ordinary;\n    }\n    boolean cancellationInProgressV2')
p.write_text(x)
p=Path(__file__).resolve().parents[1]/'source/NativeAppearanceViewsV2.java';x=p.read_text()
x=x.replace('        final Input input;','        final Input input;\n        final NativeOwnerV2.Fence editorFence;')
x=x.replace('this.input=input;','this.input=input;editorFence=mutation.fence;',1)
x=x.replace('Mutation.cleanup(record.input.mutation().fence)','Mutation.cleanup(record.editorFence)')
x=x.replace('Mutation mutation=parent==null?entryMutation():parent.original;','Mutation mutation=parent==null?((!record.editorFence.drawAllowed&&!record.editorFence.inputAllowed)?Mutation.cleanup(record.editorFence):entryMutation()):parent.original;')
p.write_text(x)
