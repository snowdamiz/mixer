package dev.mixer.android;

/** Pure private-fixture screen bounds; no event injection or platform privileges. */
final class FixtureInputBounds {
    private FixtureInputBounds() {}
    private static void tuple(int[] value){if(value==null||value.length!=4)throw new IllegalArgumentException("four screen coordinates required");}
    static int[] intersect(int[] windowVisible,int[] rootVisible,int[] decorScreen,int[] bars){
        tuple(windowVisible);tuple(rootVisible);tuple(decorScreen);tuple(bars);
        for(int inset:bars)if(inset<0)throw new IllegalArgumentException("negative system inset");
        int left=Math.max(Math.max(windowVisible[0],rootVisible[0]),Math.addExact(decorScreen[0],bars[0]));
        int top=Math.max(Math.max(windowVisible[1],rootVisible[1]),Math.addExact(decorScreen[1],bars[1]));
        int right=Math.min(Math.min(windowVisible[2],rootVisible[2]),Math.subtractExact(decorScreen[2],bars[2]));
        int bottom=Math.min(Math.min(windowVisible[3],rootVisible[3]),Math.subtractExact(decorScreen[3],bars[3]));
        return new int[]{left,top,right,bottom};
    }
    static boolean contains(int[] bounds,double x,double y){
        tuple(bounds);
        return Double.isFinite(x)&&Double.isFinite(y)&&bounds[0]<bounds[2]&&bounds[1]<bounds[3]&&x>=bounds[0]&&x<bounds[2]&&y>=bounds[1]&&y<bounds[3];
    }
}
