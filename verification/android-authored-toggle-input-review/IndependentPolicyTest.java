package dev.mixer.android;

/** Independent geometric and interruption checks against the production policy. */
final class IndependentPolicyTest {
    static int checks;
    static void require(boolean value, String reason) {
        checks++;
        if (!value) throw new AssertionError(reason);
    }
    static void near(double actual, double expected) {
        require(Math.abs(actual-expected)<1e-7,"coordinate/fraction differs");
    }
    public static void main(String[] args) {
        for(int density:new int[]{128,257,1024,1537,3072,8191,16384})
        for(boolean rtl:new boolean[]{false,true})
        for(boolean initial:new boolean[]{false,true}) {
            int height=AppearanceGeometryV2.pixelEdge(44*64,density);
            var g=AuthoredToggleInputV2.geometry(4096,height,density,rtl,4032,1792,2368,1536);
            require(g!=null,"supported geometry");
            double travel=(rtl?-22:22)*density/1024d;
            near(g.onCenter()-g.offCenter(),travel);
            double start=initial?g.onCenter():g.offCenter(), y=height/2d;
            for(double fraction:new double[]{-2,-.01,0,.25,.5,.75,1,1.01,3}) {
                var t=new AuthoredToggleInputV2();Object binding=new Object();
                require(t.begin(binding,g,7,1,start,y,initial,0,100,100),"DOWN");
                double crossing=initial?g.offCenter():g.onCenter();
                require(t.sample(7,1,crossing,y,101),"acquire drag");
                double x=start+(fraction-(initial?1:0))*travel;
                require(t.sample(7,1,x,y,102),"return/clamp sample");
                double clamped=Math.max(0,Math.min(1,fraction));near(t.fraction(),clamped);
                boolean desired=clamped==.5?initial:clamped>.5;
                int expected=desired==initial?-1:desired?1:0;
                require(t.result(x,y)==expected,"midpoint selection");
                require(t.result(x,Math.nextDown(g.corridorTop()))==-1,"above corridor");
                require(t.result(x,Math.nextUp(g.corridorBottom()))==-1,"below corridor");
                require(t.result(x,g.corridorTop())==expected,"inclusive top");
                require(t.result(x,g.corridorBottom())==expected,"inclusive bottom");
                require(t.matches(binding,initial)&&!t.matches(new Object(),initial),"binding identity");
                t.cancel();require(!t.active()&&t.binding()==null&&t.geometry()==null&&!t.pressed(),"cancel clears");
                require(!t.sample(7,1,crossing,y,103)&&t.result(crossing,y)==-1,"cancel cannot resurrect");
                t.end();require(!t.ownsRemainder(),"terminal clears ownership");
            }
            for(int badCount:new int[]{0,2,16}) {
                var t=new AuthoredToggleInputV2();
                require(t.begin(new Object(),g,7,1,start,y,initial,0,100,100),"pointer setup");
                require(!t.sample(7,badCount,start+travel,y,101)&&!t.active(),"pointer count refuses");
            }
            var tie=new AuthoredToggleInputV2();
            require(tie.begin(new Object(),g,7,1,start,y,initial,1,100,100),"tie setup");
            require(!tie.sample(7,1,start+2,y+2,101)&&!tie.ownsRemainder(),"diagonal yields parent");
        }
        System.out.println("PASS independent production-policy assertions="+checks+"; native behavior remains unrun");
    }
}
