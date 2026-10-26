package dev.mixer.android;
/** Counted JNI boundary; packet bytes are supplied independently by the fixture. */
final class NativeBridge {
 static byte[] preparedPacket;static long createResult=1,preparedToken=1;static int commitStatus,abortStatus;
 static boolean nullCandidate;static int effects;
 static int createCalls,exchangeCalls,prepareCalls,commitCalls,abortCalls,destroyCalls;
 static long lastHandle,lastToken;static int lastOperation;static byte[] lastInput,lastPreparedPacket;static Throwable createFailure,prepareFailure,commitFailure,abortFailure,destroyFailure;
 private NativeBridge(){}
 static final class Candidate {private final long token;private final byte[] packet;Candidate(long token,byte[] packet){if(token==0||packet==null)throw new IllegalArgumentException("host JNI candidate");this.token=token;this.packet=packet.clone();}long token(){OwnerHostProbe.hit("NativeBridge.Candidate.token","entry",this);long result=token;OwnerHostProbe.hit("NativeBridge.Candidate.token","beforeReturn",this);return result;}byte[] packet(){OwnerHostProbe.hit("NativeBridge.Candidate.packet","entry",this);byte[] result=packet.clone();OwnerHostProbe.hit("NativeBridge.Candidate.packet","beforeReturn",this);return result;}}
 static long create(){OwnerHostProbe.hit("NativeBridge.create");createCalls++;OwnerHostProbe.fail(createFailure);long result=createResult;OwnerHostProbe.hit("NativeBridge.create","beforeReturn");return result;}
 static byte[] exchange(long handle,int operation,byte[] input){OwnerHostProbe.hit("NativeBridge.exchange");exchangeCalls++;lastHandle=handle;lastOperation=operation;lastInput=input;byte[] result=preparedPacket;OwnerHostProbe.hit("NativeBridge.exchange","beforeReturn");return result;}
 static Candidate prepareV2(long handle,int operation,byte[] input){OwnerHostProbe.hit("NativeBridge.prepareV2");prepareCalls++;lastHandle=handle;lastOperation=operation;lastInput=input;OwnerHostProbe.fail(prepareFailure);lastPreparedPacket=preparedPacket;Candidate result=nullCandidate?null:new Candidate(preparedToken,preparedPacket);OwnerHostProbe.hit("NativeBridge.prepareV2","beforeReturn");return result;}
 static int commitV2(long handle,long token){OwnerHostProbe.hit("NativeBridge.commitV2");commitCalls++;lastHandle=handle;lastToken=token;OwnerHostProbe.fail(commitFailure);int result=commitStatus;if(result==0)effects++;OwnerHostProbe.hit("NativeBridge.commitV2","beforeReturn");return result;}
 static int abortV2(long handle,long token){OwnerHostProbe.hit("NativeBridge.abortV2");abortCalls++;lastHandle=handle;lastToken=token;OwnerHostProbe.fail(abortFailure);int result=abortStatus;OwnerHostProbe.hit("NativeBridge.abortV2","beforeReturn");return result;}
 static void destroy(long handle){OwnerHostProbe.hit("NativeBridge.destroy");destroyCalls++;lastHandle=handle;OwnerHostProbe.fail(destroyFailure);OwnerHostProbe.hit("NativeBridge.destroy","beforeReturn");}
 static void reset(){nullCandidate=false;effects=0;preparedPacket=null;createResult=preparedToken=1;commitStatus=abortStatus=createCalls=exchangeCalls=prepareCalls=commitCalls=abortCalls=destroyCalls=0;lastHandle=lastToken=lastOperation=0;lastInput=lastPreparedPacket=null;createFailure=prepareFailure=commitFailure=abortFailure=destroyFailure=null;}
}
