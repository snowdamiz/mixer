package dev.mixer.android;

/** Direct typed constructor tests, bypassing the JSON oracle transport. */
public final class EnvironmentProbe {
    private EnvironmentProbe() {}
    private static int assertions;
    public static void main(String[] args) {
        for (int scale : new int[] {512,513,1023,1024,1025,4095,4096}) {
            for (int density : new int[] {128,129,1023,1024,1025,16383,16384}) {
                for (AppearanceResolutionV1.Scheme scheme : AppearanceResolutionV1.Scheme.values()) {
                    for (AppearanceResolutionV1.Direction direction : AppearanceResolutionV1.Direction.values()) {
                        var env = new AppearanceResolutionV1.Environment(scheme,direction,scale,density);
                        check(env.scheme()==scheme && env.direction()==direction && env.textScale1024()==scale && env.density1024()==density);
                    }
                }
            }
        }
        for (int scale : new int[] {Integer.MIN_VALUE,-1,0,511,4097,65535,65536,Integer.MAX_VALUE}) {
            reject(()->new AppearanceResolutionV1.Environment(AppearanceResolutionV1.Scheme.light,AppearanceResolutionV1.Direction.leftToRight,scale,1024));
        }
        for (int density : new int[] {Integer.MIN_VALUE,-1,0,127,16385,65535,65536,Integer.MAX_VALUE}) {
            reject(()->new AppearanceResolutionV1.Environment(AppearanceResolutionV1.Scheme.light,AppearanceResolutionV1.Direction.leftToRight,1024,density));
        }
        reject(()->new AppearanceResolutionV1.Environment(null,AppearanceResolutionV1.Direction.leftToRight,1024,1024));
        reject(()->new AppearanceResolutionV1.Environment(AppearanceResolutionV1.Scheme.light,null,1024,1024));
        System.out.println("direct environment assertions="+assertions+" status=passed");
    }
    private static void check(boolean value) { assertions++;if(!value)throw new AssertionError("environment changed"); }
    private static void reject(Runnable call) {
        assertions++;try{call.run();}catch(IllegalArgumentException expected){return;}throw new AssertionError("invalid environment accepted");
    }
}
