package dev.mixer.android;

import java.util.Arrays;

/** Regression controls for the observed status-bar failure and screen-space guard. */
public final class FixtureInputBoundsTest {
    private static int checks;
    private FixtureInputBoundsTest() {}
    private static void require(boolean value){checks++;if(!value)throw new AssertionError("input bounds check "+checks);}
    private static void rejects(Runnable body){checks++;try{body.run();}catch(IllegalArgumentException|ArithmeticException expected){return;}throw new AssertionError("invalid bounds accepted");}
    public static void main(String[] arguments){
        int[] frame={0,132,1206,2550},root={0,0,1206,2622},decor={0,0,1206,2622},bars={0,132,0,72};
        int[] owned=FixtureInputBounds.intersect(frame,root,decor,bars);
        require(Arrays.equals(owned,new int[]{0,132,1206,2550}));
        require(Arrays.equals(frame,new int[]{0,132,1206,2550})&&Arrays.equals(root,new int[]{0,0,1206,2622})&&Arrays.equals(decor,new int[]{0,0,1206,2622})&&Arrays.equals(bars,new int[]{0,132,0,72}));
        require(!FixtureInputBounds.contains(owned,932.5,101)); // observed stale-offset DOWN in status bar
        require(FixtureInputBounds.contains(owned,932.5,466));
        require(FixtureInputBounds.contains(owned,932.5,186));
        require(FixtureInputBounds.contains(owned,1012.5,186));
        for(boolean diagonal:new boolean[]{false,true})for(int i=0;i<=8;i++)require(FixtureInputBounds.contains(owned,932.5+(diagonal?i*10:0),466-i*35));
        require(FixtureInputBounds.contains(owned,0,132));
        require(FixtureInputBounds.contains(owned,1205.999,2549.999));
        require(!FixtureInputBounds.contains(owned,1206,1000));
        require(!FixtureInputBounds.contains(owned,1000,2550));
        require(!FixtureInputBounds.contains(owned,-.001,132));
        require(!FixtureInputBounds.contains(owned,0,131.999));
        require(!FixtureInputBounds.contains(owned,Double.NaN,200));
        require(!FixtureInputBounds.contains(owned,200,Double.POSITIVE_INFINITY));
        require(!FixtureInputBounds.contains(new int[]{100,100,100,200},100,100));
        require(!FixtureInputBounds.contains(new int[]{200,200,100,100},150,150));
        require(Arrays.equals(FixtureInputBounds.intersect(new int[]{0,0,1206,2622},new int[]{20,180,1100,2500},decor,bars),new int[]{20,180,1100,2500}));
        require(Arrays.equals(FixtureInputBounds.intersect(new int[]{100,200,1306,2822},new int[]{100,200,1306,2822},new int[]{100,200,1306,2822},bars),new int[]{100,332,1306,2750}));
        require(!FixtureInputBounds.contains(FixtureInputBounds.intersect(frame,new int[]{0,0,1206,100},decor,bars),932.5,101));
        rejects(()->FixtureInputBounds.contains(null,0,0));
        rejects(()->FixtureInputBounds.contains(new int[]{0,0,1},0,0));
        rejects(()->FixtureInputBounds.intersect(frame,root,decor,new int[]{0,-1,0,0}));
        rejects(()->FixtureInputBounds.intersect(frame,root,new int[]{Integer.MAX_VALUE,0,0,0},new int[]{1,0,0,0}));
        System.out.println("RESULT {\"status\":\"passed-host-only-owned-input-bounds\",\"checks\":"+checks+",\"nativeRuntime\":\"NOT RUN\"}");
    }
}
