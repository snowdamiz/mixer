package android.view.inputmethod;
/** Controlled unsupported-result carrier. No native text-bound query is modeled. */
public final class TextBoundsInfoResult {
    public static final int CODE_UNSUPPORTED=0;
    public final int code;
    public TextBoundsInfoResult(int code){this.code=code;}
}
