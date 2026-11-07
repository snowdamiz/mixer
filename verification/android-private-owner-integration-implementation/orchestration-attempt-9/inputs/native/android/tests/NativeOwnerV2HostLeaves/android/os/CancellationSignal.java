package android.os; public final class CancellationSignal {private boolean canceled;public void cancel(){canceled=true;}public boolean isCanceled(){return canceled;}}
