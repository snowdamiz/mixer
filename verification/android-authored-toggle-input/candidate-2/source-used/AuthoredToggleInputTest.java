package dev.mixer.android;

import java.util.ArrayList;
import java.util.List;

/** Executes production policy bytes; no Android mocks and no second gesture model. */
final class AuthoredToggleInputTest {
    static final List<String> passed=new ArrayList<>();
    static void check(boolean value,String detail){if(!value)throw new AssertionError(detail);}
    static void close(double a,double b){check(Math.abs(a-b)<1e-8,a+" != "+b);}
    static AuthoredToggleInputV2.Geometry geometry(int density,boolean rtl){return AuthoredToggleInputV2.geometry(1200,AppearanceGeometryV2.pixelEdge(44*64,density),density,rtl,4032,1792,2368,1536);}
    static AuthoredToggleInputV2 begin(AuthoredToggleInputV2.Geometry g,boolean initial){
        var t=new AuthoredToggleInputV2();check(t.begin(new Object(),g,11,1,initial?g.onCenter():g.offCenter(),g.height()/2d,initial,8,10,10),"begin");return t;
    }
    static void test(String name,Runnable body){body.run();passed.add(name);System.out.println("PASS "+name);}
    public static void main(String[] args){
        test("geometry exact authored endpoint conversion five densities RTL LTR",()->{
            for(int d:new int[]{512,1024,1536,3072,4096})for(boolean rtl:new boolean[]{false,true}){
                var g=geometry(d,rtl);check(g!=null,"geometry");close(g.onCenter()-g.offCenter(),(rtl?-1:1)*22*d/1024d);
                close(g.offOrigin(),(rtl?24:2)*d/1024d);close(g.onOrigin(),(rtl?2:24)*d/1024d);
                close(g.origin(0),g.offOrigin());close(g.origin(1),g.onOrigin());close(g.carrierBottom()-g.carrierTop(),44*d/1024d);
            }
        });
        test("frozen density3 geometry",()->{var g=geometry(3072,false);close(g.trackX(),1011);close(g.trackY(),24);close(g.carrierTop(),0);close(g.carrierBottom(),132);close(g.corridorTop(),-66);close(g.corridorBottom(),198);close(g.offCenter(),1072.5);close(g.onCenter(),1138.5);});
        test("invalid geometry fails closed",()->{
            check(AuthoredToggleInputV2.geometry(0,132,3072,false,4032,1792,2368,1536)==null,"empty");
            check(AuthoredToggleInputV2.geometry(1200,132,0,false,4032,1792,2368,1536)==null,"density");
            check(AuthoredToggleInputV2.geometry(1200,132,3072,false,4033,1792,2368,1536)==null,"unsupported metrics");
        });
        test("endpoint both ways RTL LTR five densities",()->{
            for(int d:new int[]{512,1024,1536,3072,4096})for(boolean rtl:new boolean[]{false,true})for(boolean initial:new boolean[]{false,true}){
                var g=geometry(d,rtl);var t=begin(g,initial);double end=initial?g.offCenter():g.onCenter();
                check(t.sample(11,1,end,g.height()/2d,160),"sample");close(t.fraction(),initial?0:1);check(t.result(end,g.height()/2d)==(initial?0:1),"endpoint");
            }
        });
        test("crossing sample retains full DOWN displacement",()->{var g=geometry(3072,false);var t=begin(g,false);double x=g.offCenter()+24.75;check(t.sample(11,1,x,66,85),"cross");close(t.fraction(),.375);check(t.phase()==AuthoredToggleInputV2.Phase.drag,"drag");});
        test("sealed P03 schedule ends at authored endpoint after pause",()->{
            var g=geometry(3072,false);var t=begin(g,false);double start=g.offCenter();
            for(int i=1;i<=8;i++)check(t.sample(11,1,start+66*i/8d,66,10+25*i),"move");
            check(t.sample(11,1,start+66,66,360),"paused UP");check(t.result(start+66,66)==1,"on");
        });
        test("strict slop boundary pending",()->{var g=geometry(3072,false);var t=begin(g,false);check(t.sample(11,1,g.offCenter()+8,66,20),"slop");check(t.phase()==AuthoredToggleInputV2.Phase.pending,"no drag at equal slop");});
        test("strict horizontal dominance and vertical tie surrender",()->{var g=geometry(3072,false);var t=begin(g,false);check(!t.sample(11,1,g.offCenter()+9,75,20),"tie");check(!t.ownsRemainder(),"parent remainder");check(!t.pressed(),"pressed cleared");});
        test("vertical slop crossing surrenders before ownership",()->{var g=geometry(3072,false);var t=begin(g,false);check(!t.sample(11,1,g.offCenter()+2,86,20),"vertical");check(t.phase()==AuthoredToggleInputV2.Phase.draining&&!t.ownsRemainder(),"surrender");});
        test("horizontal lock survives temporary vertical excursion",()->{var g=geometry(3072,false);var t=begin(g,false);t.sample(11,1,g.onCenter(),66,20);check(t.sample(11,1,g.onCenter(),1000,30),"locked");check(t.pressed(),"drag pressed");check(t.result(g.onCenter(),66)==1,"return corridor");});
        test("midpoint tie retains each initial side RTL LTR",()->{for(boolean rtl:new boolean[]{false,true})for(boolean initial:new boolean[]{false,true}){var g=geometry(3072,rtl);var t=begin(g,initial);double x=(g.offCenter()+g.onCenter())/2;t.sample(11,1,x,66,20);close(t.fraction(),.5);check(t.result(x,66)==-1,"tie unchanged");check(t.visualChecked()==initial,"tie paint");}});
        test("midpoint epsilon selects both sides",()->{var g=geometry(3072,false);double mid=(g.offCenter()+g.onCenter())/2;var t=begin(g,false);t.sample(11,1,mid+1e-5,66,20);check(t.result(mid+1e-5,66)==1,"above");t=begin(g,true);t.sample(11,1,mid-1e-5,66,20);check(t.result(mid-1e-5,66)==0,"below");});
        test("fast below midpoint no velocity override",()->{var g=geometry(3072,false);var t=begin(g,false);t.sample(11,1,g.offCenter()+30,66,11);check(t.result(g.offCenter()+30,66)==-1,"fast unchanged");});
        test("horizontal clamping outside row allowed",()->{var g=geometry(3072,false);var t=begin(g,false);t.sample(11,1,100000,66,20);close(t.fraction(),1);check(t.result(100000,66)==1,"outside valid");t.sample(11,1,-100000,66,30);close(t.fraction(),0);check(t.result(-100000,66)==-1,"return unchanged");});
        test("corridor inclusive edges and epsilon outside",()->{var g=geometry(3072,false);for(double y:new double[]{-66,198}){var t=begin(g,false);t.sample(11,1,g.onCenter(),66,20);t.sample(11,1,g.onCenter(),y,30);check(t.result(g.onCenter(),y)==1,"inclusive");}for(double y:new double[]{-66-1e-5,198+1e-5}){var t=begin(g,false);t.sample(11,1,g.onCenter(),66,20);t.sample(11,1,g.onCenter(),y,30);check(t.result(g.onCenter(),y)==-1,"outside");}});
        test("tall row does not widen carrier corridor",()->{var g=AuthoredToggleInputV2.geometry(1200,300,3072,false,4032,1792,2368,1536);close(g.carrierTop(),84);close(g.corridorBottom(),282);var t=new AuthoredToggleInputV2();check(t.begin(new Object(),g,1,1,g.offCenter(),150,false,8,10,10),"begin");t.sample(1,1,g.onCenter(),150,20);check(t.result(g.onCenter(),283)==-1,"tall row");});
        test("label tap and arbitrarily held tap",()->{var g=geometry(3072,false);for(long end:new long[]{10,100000000}){var t=new AuthoredToggleInputV2();check(t.begin(new Object(),g,1,1,30,66,false,8,10,10),"label");check(t.sample(1,1,30,66,end),"hold");check(t.result(30,66)==1,"toggle UP");}});
        test("label horizontal drift cancels tap",()->{var g=geometry(3072,false);var t=new AuthoredToggleInputV2();t.begin(new Object(),g,1,1,30,66,false,8,10,10);check(!t.sample(1,1,40,66,20),"label drift");check(t.result(40,66)==-1,"none");});
        test("pending pressed may leave and return inside row before slop",()->{var g=geometry(3072,false);var t=new AuthoredToggleInputV2();t.begin(new Object(),g,1,1,1,66,false,8,10,10);t.sample(1,1,-1,66,20);check(!t.pressed(),"outside paint");t.sample(1,1,1,66,30);check(t.pressed(),"inside paint");});
        test("initial DOWN is bounded row only",()->{var g=geometry(3072,false);for(double x:new double[]{-1,1200,Double.NaN,Double.POSITIVE_INFINITY}){var t=new AuthoredToggleInputV2();check(!t.begin(new Object(),g,1,1,x,66,false,8,10,10),"invalid DOWN");check(t.phase()==AuthoredToggleInputV2.Phase.idle,"idle");}});
        test("stable pointer lost no transfer",()->{var g=geometry(3072,false);var t=begin(g,false);check(!t.sample(12,1,g.onCenter(),66,20),"lost");check(!t.sample(11,1,g.onCenter(),66,30),"no resurrection");});
        test("extra pointer cancels whole attempt",()->{var g=geometry(3072,false);var t=begin(g,false);check(!t.sample(11,2,g.onCenter(),66,20),"extra");check(t.result(g.onCenter(),66)==-1,"none");});
        test("nonfinite sample cancels",()->{var g=geometry(3072,false);for(double x:new double[]{Double.NaN,Double.NEGATIVE_INFINITY,Double.POSITIVE_INFINITY}){var t=begin(g,false);check(!t.sample(11,1,x,66,20),"invalid");check(!t.pressed(),"no pressed");}});
        test("historical positions consumed chronologically crossing then return",()->{var g=geometry(3072,false);var t=begin(g,false);t.sample(11,1,g.offCenter()+24.75,66,20);t.sample(11,1,g.offCenter()+16.5,66,30);close(t.fraction(),.25);check(t.phase()==AuthoredToggleInputV2.Phase.drag,"history crosses");check(t.result(g.offCenter()+16.5,66)==-1,"unchanged");});
        test("backwards history fails closed",()->{var g=geometry(3072,false);var t=begin(g,false);t.sample(11,1,g.onCenter(),66,30);check(!t.sample(11,1,g.onCenter(),66,20),"ordering");check(t.result(g.onCenter(),66)==-1,"none");});
        test("binding identity and checked coherence fence",()->{var g=geometry(3072,false);var t=begin(g,false);Object b=t.binding();check(t.matches(b,false),"same");check(!t.matches(new Object(),false),"equal bytes still different identity");check(!t.matches(b,true),"incoherent");});
        test("cancel draining is idempotent and new DOWN required",()->{var g=geometry(3072,false);var t=begin(g,false);t.sample(11,1,g.onCenter(),66,20);t.cancel();t.cancel();check(!t.active()&&!t.pressed()&&t.ownsRemainder(),"drain");check(t.result(g.onCenter(),66)==-1,"none");t.end();check(!t.ownsRemainder(),"terminal");});
        test("latest binding restoration and callback proposal distinction",()->{var fake=new Checked();fake.nativeValue=true;fake.latest=false;fake.raw=1;fake.proposals=1;AuthoredToggleInputV2.reconcile(fake);check(!fake.nativeValue&&fake.raw==2&&fake.proposals==1&&!fake.guard,"restore suppressed raw callback");});
        test("synchronous newer binding wins over DOWN",()->{var fake=new Checked();fake.nativeValue=false;fake.latest=true;AuthoredToggleInputV2.reconcile(fake);check(fake.nativeValue,"latest true");});
        test("preexisting changing guard preserved",()->{var fake=new Checked();fake.guard=true;fake.nativeValue=true;fake.latest=false;AuthoredToggleInputV2.reconcile(fake);check(fake.guard,"preserved");});
        test("restoration failure preserves guard",()->{var fake=new Checked();fake.nativeValue=true;fake.latest=false;fake.fail=true;try{AuthoredToggleInputV2.reconcile(fake);throw new AssertionError("must fail");}catch(IllegalStateException expected){check(!fake.guard,"finally");}});
        test("retired replacement cleanup uses old view only",()->{var old=new Checked();var replacement=new Checked();old.latest=false;old.nativeValue=true;replacement.latest=true;replacement.nativeValue=true;AuthoredToggleInputV2.reconcile(old);check(replacement.nativeValue&&replacement.raw==0,"replacement untouched");});
        test("null unavailable bound state does not reopen owner",()->{var fake=new Checked();fake.latest=null;fake.nativeValue=true;AuthoredToggleInputV2.reconcile(fake);check(fake.nativeValue&&fake.raw==0,"unavailable");});
        System.out.println("RESULT {\"status\":\"passed-production-policy-only\",\"tests\":"+passed.size()+",\"nativeRuntime\":\"NOT RUN\"}");
    }
    static final class Checked implements AuthoredToggleInputV2.CheckedBinding {
        Boolean latest=false;boolean nativeValue,guard,fail;int raw,proposals;
        public Boolean latestBoundChecked(){return latest;}public boolean nativeChecked(){return nativeValue;}
        public boolean changingGuard(){return guard;}public void changingGuard(boolean value){guard=value;}
        public void restoreChecked(boolean value){if(fail)throw new IllegalStateException("retained failure control");nativeValue=value;raw++;if(!guard)proposals++;}
    }
}
