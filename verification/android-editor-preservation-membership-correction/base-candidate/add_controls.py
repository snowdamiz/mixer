from pathlib import Path
p=Path(__file__).parent/'tests/PreservationCompletionControls.java';s=p.read_text();anchor='    public static void main('
addition=r'''
    private static void refused(Runnable action,Fixture own,Fixture other,NativeAppearanceViewsV2.FieldPreservation scope,String label){
        String before=state(own,scope);int otherCount=other.count(),effects=ConcreteHostProbe.events().size();Object primary=own.renderer.cleanupLedger().primary();
        try{action.run();throw new AssertionError("accepted "+label);}catch(IllegalArgumentException|IllegalStateException expected){check(before.equals(state(own,scope))&&other.count()==otherCount&&ConcreteHostProbe.events().size()==effects&&own.renderer.cleanupLedger().primary()==primary,label+" refuses before endpoint effects on both owners");}
    }
    private static void foreignEndpoints(){try(Fixture f=new Fixture(true,true);Fixture other=new Fixture(true,true)){
        Observation foreign=new Observation(other);ConcreteHostProbe.hook=foreign::event;check(other.edit(),"second real owner prior complete candidate");ConcreteHostProbe.hook=null;
        Observation o=new Observation(f);boolean[] nativeMatrix={false},finishMatrix={false};
        ConcreteHostProbe.hook=(method,phase)->{o.event(method,phase);
            boolean finish=o.captured&&method.equals("NativeBridge.commitV2")&&phase.equals("entry");
            if(o.captured&&((!nativeMatrix[0]&&ConcreteHostProbe.lastEvent().receiver==f.a&&method.equals("View.invalidate")&&phase.equals("entry"))||finish&&!finishMatrix[0])){
                if(finish)finishMatrix[0]=true;else nativeMatrix[0]=true;
                var scope=o.scopes[0];
                for(String identity:new String[]{"renderer","candidate","journal","record","view","input","original","fence","token","membership"}){
                    Object target;String member;Object wrong;
                    switch(identity){case "renderer"->{target=scope;member="renderer";wrong=other.renderer;}case "candidate"->{target=scope;member="candidate";wrong=foreign.candidate;}case "journal"->{target=scope;member="journal";wrong=foreign.journal;}case "record"->{target=scope;member="record";wrong=f.c.record;}case "view"->{target=f.a.record;member="view";wrong=f.c;}case "input"->{target=f.a.record;member="input";wrong=other.a.record.input;}case "original"->{target=o.candidate;member="originalMutation";wrong=foreign.scopes[0].original;}case "fence"->{target=scope.original;member="fence";wrong=other.fence();}case "token"->{target=scope.original;member="token";wrong=foreign.scopes[0].original.token;}default->{Object[] states=(Object[])get(o.journal,"states");target=null;for(Object state:states)if(get(state,"record")==f.a.record)target=state;member="preservation";wrong=foreign.scopes[0];}}
                    Object previous=get(target,member);NativeAppearanceViewsV2.Input input=f.a.record.input;put(target,member,wrong);
                    try{if(finish)refused(()->f.renderer.finishV2(o.candidate,o.journal),f,other,scope,"finish wrong "+identity);
                        else{refused(()->input.fieldPreservationBegin(f.a.record,scope),f,other,scope,"Begin wrong "+identity);refused(()->input.fieldPreservationEnd(f.a.record,scope),f,other,scope,"End wrong "+identity);refused(()->f.renderer.completeFailedV2(o.candidate,null,null),f,other,scope,"failed completion wrong "+identity);}}
                    finally{put(target,member,previous);}
                }
                refused(()->other.a.record.input.fieldPreservationEnd(f.a.record,scope),f,other,scope,"foreign receiving Input");
                refused(()->other.renderer.completeFailedV2(o.candidate,null,null),f,other,scope,"foreign receiving renderer");
                refused(()->f.renderer.finishV2(foreign.candidate,foreign.journal),f,other,scope,"foreign candidate and journal");
            }
        };
        check(f.edit(),"all foreign refusals preserve legitimate owner success");ConcreteHostProbe.hook=null;check(nativeMatrix[0]&&finishMatrix[0]&&f.count()==0&&other.count()==0,"actual callbacks and scalar interval tested with two complete owners");
    }}
    private static void terminalEnd(){try(Fixture f=new Fixture(true,true);Fixture other=new Fixture(true,true)){
        Observation o=new Observation(f);boolean[] injected={false};ConcreteHostProbe.hook=(method,phase)->{o.event(method,phase);if(o.captured&&!injected[0]&&ConcreteHostProbe.lastEvent().receiver==f.a&&method.equals("View.invalidate")&&phase.equals("entry")){injected[0]=true;o.scopes[0].callbacks=1;throw new IllegalStateException("hold real A for direct terminal End tests");}};
        try{f.edit();}catch(RuntimeException expected){check(true,"terminal hold");}ConcreteHostProbe.hook=null;var scope=o.scopes[0];check(scope.ended&&scope.counted&&f.count()==1&&f.fence().operation==null,"held real A after operation loss");scope.callbacks=0;
        for(String identity:new String[]{"renderer","candidate","journal","record","view","input","original","fence","token","membership"}){
            Object target;String member;Object wrong;
            switch(identity){case "renderer"->{target=scope;member="renderer";wrong=other.renderer;}case "candidate"->{target=scope;member="candidate";wrong=null;}case "journal"->{target=scope;member="journal";wrong=null;}case "record"->{target=scope;member="record";wrong=f.c.record;}case "view"->{target=f.a.record;member="view";wrong=f.c;}case "input"->{target=f.a.record;member="input";wrong=other.a.record.input;}case "original"->{target=o.candidate;member="originalMutation";wrong=null;}case "fence"->{target=scope.original;member="fence";wrong=other.fence();}case "token"->{target=scope.original;member="token";wrong=null;}default->{Object[] states=(Object[])get(o.journal,"states");target=null;for(Object state:states)if(get(state,"record")==f.a.record)target=state;member="preservation";wrong=null;}}
            Object previous=get(target,member);NativeAppearanceViewsV2.Input input=f.a.record.input;put(target,member,wrong);
            try{String before=f.count()+":"+scope.counted+":"+scope.ended+":"+get(o.candidate,"heldPreservations");int effects=ConcreteHostProbe.events().size();try{input.fieldPreservationEnd(f.a.record,scope);throw new AssertionError("wrong terminal End "+identity);}catch(IllegalArgumentException expected){check(before.equals(f.count()+":"+scope.counted+":"+scope.ended+":"+get(o.candidate,"heldPreservations"))&&ConcreteHostProbe.events().size()==effects&&other.count()==0,"terminal End provenance "+identity);}}
            finally{put(target,member,previous);}
        }
        for(int count:new int[]{0,-1}){put(f.renderer,"outstandingEditorNativeCalls",count);int effects=ConcreteHostProbe.events().size();try{f.a.record.input.fieldPreservationEnd(f.a.record,scope);throw new AssertionError("unfunded terminal End");}catch(IllegalArgumentException expected){check(scope.counted&&f.count()==count&&f.renderer.editorDisposalBusyV2()&&ConcreteHostProbe.events().size()==effects,"unfunded terminal End retains independent custody");}put(f.renderer,"outstandingEditorNativeCalls",1);}
        int effects=ConcreteHostProbe.events().size();f.a.record.input.fieldPreservationEnd(f.a.record,scope);check(f.count()==0&&scope.released&&!scope.counted&&ConcreteHostProbe.events().size()==effects,"exact End after operation loss uses no current/native probe");
        try{f.a.record.input.fieldPreservationEnd(f.a.record,scope);throw new AssertionError("End replay");}catch(IllegalArgumentException expected){check(f.count()==0&&other.count()==0,"exact End replay leaves both owners unchanged");}
        System.out.println("HOSTILE_REPAIR balanced injected A callback counter before exact captured terminal End");
    }}
    private static void imbalances(){for(String kind:new String[]{"callbacks","hooks","checking","counted-not-entered","entered-not-counted","underfunded","negative","finish-mismatch","post-validation"})try(Fixture f=new Fixture(true,true)){
        Observation o=new Observation(f);boolean[] injected={false};
        ConcreteHostProbe.hook=(method,phase)->{o.event(method,phase);
            if(o.captured&&!injected[0]&&(kind.equals("post-validation")?in("validateAttachedV2")&&method.equals("TextView.getEditableText")&&phase.equals("beforeReturn"):method.equals("NativeBridge.commitV2")&&phase.equals("beforeReturn"))){injected[0]=true;var scope=o.scopes[0];switch(kind){case "callbacks","finish-mismatch"->scope.callbacks=1;case "hooks"->scope.hooks.push("hostile");case "checking"->scope.checking=true;case "counted-not-entered"->scope.entered=false;case "entered-not-counted"->scope.counted=false;case "underfunded"->put(f.renderer,"outstandingEditorNativeCalls",1);case "negative"->put(f.renderer,"outstandingEditorNativeCalls",-1);default->put(f.renderer,"editorLossSerial",scope.lossObservation+1);}}
        };try{f.edit();}catch(RuntimeException|Error expected){check(true,"mismatched completion refused");}ConcreteHostProbe.hook=null;
        check(injected[0]&&f.fence().terminal&&o.scopes[0].ended&&o.scopes[1].ended&&f.a.record.fieldPreservation==null&&f.c.record.fieldPreservation==null,"invalid completion is terminal without callback authority");
        if(kind.equals("post-validation")){check(!o.atCommit&&f.count()==0&&o.scopes[0].released&&o.scopes[1].released,"postvalidation authority loss cleans balanced holds outside commit");}
        else if(kind.equals("underfunded")||kind.equals("negative")){check(o.scopes[0].counted&&o.scopes[1].counted&&!o.scopes[0].released&&!o.scopes[1].released&&f.renderer.editorDisposalBusyV2()&&NativeBridge.destroyCalls==0,"underfunded cohort cannot borrow B or become disposal-ready");}
        else check(!o.scopes[0].released&&o.scopes[1].released&&!o.scopes[1].counted&&f.count()==1&&f.renderer.editorDisposalBusyV2()&&NativeBridge.destroyCalls==0,"one inconsistent scope retains exact custody while C and B release");
        String before=state(f,o.scopes[0]);try{f.renderer.completeFailedV2(o.candidate,null,null);throw new AssertionError("repair by replay");}catch(IllegalArgumentException expected){check(before.equals(state(f,o.scopes[0])),"imbalanced failure replay inert");}
        System.out.println("IMBALANCE "+kind+" shared="+f.count()+" preservation="+get(f.renderer,"outstandingFieldPreservations")+" custody="+get(o.candidate,"heldPreservations")+" no repair/retry");
    }}
'''
assert anchor in s;s=s.replace(anchor,addition+anchor)
s=s.replace('case "chronology"->chronology();default','case "chronology"->chronology();case "foreign-endpoints"->foreignEndpoints();case "terminal-end"->terminalEnd();case "imbalances"->imbalances();default')
p.write_text(s)
