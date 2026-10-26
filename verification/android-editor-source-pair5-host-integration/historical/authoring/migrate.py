from pathlib import Path
D=Path(__file__).resolve().parent;C=D/'candidate';T=C/'native/android/tests'
p=T/'NativeOwnerV2HostLeaves/dev/mixer/android/NativeRenderer.java';s=p.read_text();s=s.replace(' boolean cancellationInProgressV2()', ' // Mechanical orchestration-only stub; does not model editor busy behavior.\n boolean editorDisposalBusyV2(){return false;}\n boolean cancellationInProgressV2()');p.write_text(s)
p=T/'NativeOwnerV2ConcreteHostLeaves/dev/mixer/android/ConcreteHostProbe.java';s=p.read_text().replace('"NativeOwnerV2","OwnerLifecycleV2"','"NativeOwnerV2","NativeEditorConnectionV2","OwnerLifecycleV2"');p.write_text(s)
p=T/'NativeOwnerV2ConcreteHostTests.java';s=p.read_text()
s=s.replace('Fixture(String scene,Runnable completionFault){','Fixture(String scene,Runnable completionFault){this(scene,completionFault,"hello");}\n        Fixture(String scene,Runnable completionFault,String initialValue){').replace('NativeBridge.preparedPacket=packet(1,scene);','NativeBridge.preparedPacket=packet(1,scene,initialValue);')
s=s.replace('new ImeFamily("sendKeyEvent","sendKeyEvent",c->c.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN,KeyEvent.KEYCODE_SPACE))),\n        ','')
s=s.replace('OwnerLifecycleV2.Token before=f.fence().presentation;NativeBridge.preparedPacket=packet(2,"field","helloz");','appendCursor(editor);OwnerLifecycleV2.Token before=f.fence().presentation;NativeBridge.preparedPacket=packet(2,"field","helloz");')
s=s.replace('InputConnection connection=editor.onCreateInputConnection(new EditorInfo());NativeBridge.preparedPacket=packet(2,"field","helloz");NativeBridge.commitStatus=1;','InputConnection connection=editor.onCreateInputConnection(new EditorInfo());appendCursor(editor);NativeBridge.preparedPacket=packet(2,"field","helloz");NativeBridge.commitStatus=1;')
start=s.index('    private static void imeControls(){');end=s.index('    private static void actualObserverControls()',start)
original=s[start:end]
# Preserve all unsupported/close controls, replacing only obsolete family loop.
tail=original[original.index('        for(String state:List.of("current","terminal","dirty","stale"))'):]
new=(D/'ime-migration.java.fragment').read_text()
s=s[:start]+new+'\n'+tail+s[end:]
s=s.replace('private static void imeControls(){','private static void imeControls(){')
# Targeted section enables bounded independent execution without omitting baseline suites.
s=s.replace('descriptor=Files.readAllBytes(Path.of(args[0]));if(args.length>2)loadBarriers(Path.of(args[2]));','''descriptor=Files.readAllBytes(Path.of(args[0]));
        if(args.length>3&&args[2].equals("--section")){
            scenario=args[3];
            if(scenario.equals("imeControls"))imeControls();
            else if(scenario.equals("platformGuards"))platformGuards();
            else if(scenario.equals("v1"))v1Baselines();
            else throw new IllegalArgumentException("unknown host section");
            if(args.length>4){StringBuilder report=new StringBuilder();write(report,Json.map("scope","mechanical host leaves; injected successors labeled separately; no native equivalence", "familyRows",imeRows,"sendKeyRefusals",keyRows));Files.writeString(Path.of(args[4]),report);}
            collect();System.out.println("PASS concrete actual16 section="+scenario+" checks="+checks+"; native runtime pending");return;
        }
        if(args.length>2)loadBarriers(Path.of(args[2]));''')
s=s.replace('PASS concrete actual14 host checks=', 'PASS concrete actual16 host checks=')
p.write_text(s)
