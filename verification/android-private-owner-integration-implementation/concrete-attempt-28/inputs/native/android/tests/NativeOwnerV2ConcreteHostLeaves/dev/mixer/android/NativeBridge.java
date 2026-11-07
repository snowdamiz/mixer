package dev.mixer.android;
/** Counted JNI boundary; packet bytes are supplied independently by the fixture. */
final class NativeBridge {
 static byte[] preparedPacket;static long createResult=1,preparedToken=1;static int commitStatus,abortStatus;
 static int createCalls,exchangeCalls,prepareCalls,commitCalls,abortCalls,destroyCalls;
 static long lastHandle,lastToken;static int lastOperation;static byte[] lastInput,lastPreparedPacket;static Throwable createFailure,prepareFailure,commitFailure,abortFailure,destroyFailure;
 private NativeBridge(){}
 static final class Candidate {private final long token;private final byte[] packet;Candidate(long token,byte[] packet){if(token==0||packet==null)throw new IllegalArgumentException("host JNI candidate");this.token=token;this.packet=packet.clone();}long token(){return token;}byte[] packet(){return packet.clone();}}
 static long create(){ConcreteHostProbe.hit("NativeBridge.create");createCalls++;ConcreteHostProbe.fail(createFailure);long result=createResult;ConcreteHostProbe.hit("NativeBridge.create","beforeReturn");return result;}
 static byte[] exchange(long handle,int operation,byte[] input){ConcreteHostProbe.hit("NativeBridge.exchange");exchangeCalls++;lastHandle=handle;lastOperation=operation;lastInput=input;byte[] result=preparedPacket;ConcreteHostProbe.hit("NativeBridge.exchange","beforeReturn");return result;}
 static Candidate prepareV2(long handle,int operation,byte[] input){ConcreteHostProbe.hit("NativeBridge.prepareV2");prepareCalls++;lastHandle=handle;lastOperation=operation;lastInput=input;ConcreteHostProbe.fail(prepareFailure);lastPreparedPacket=preparedPacket;Candidate result=new Candidate(preparedToken,preparedPacket);ConcreteHostProbe.hit("NativeBridge.prepareV2","beforeReturn");return result;}
 static int commitV2(long handle,long token){ConcreteHostProbe.hit("NativeBridge.commitV2");commitCalls++;lastHandle=handle;lastToken=token;ConcreteHostProbe.fail(commitFailure);int result=commitStatus;ConcreteHostProbe.hit("NativeBridge.commitV2","beforeReturn");return result;}
 static int abortV2(long handle,long token){ConcreteHostProbe.hit("NativeBridge.abortV2");abortCalls++;lastHandle=handle;lastToken=token;ConcreteHostProbe.fail(abortFailure);int result=abortStatus;ConcreteHostProbe.hit("NativeBridge.abortV2","beforeReturn");return result;}
 static void destroy(long handle){ConcreteHostProbe.hit("NativeBridge.destroy");destroyCalls++;lastHandle=handle;ConcreteHostProbe.fail(destroyFailure);ConcreteHostProbe.hit("NativeBridge.destroy","beforeReturn");}
 static void reset(){preparedPacket=null;createResult=preparedToken=1;commitStatus=abortStatus=createCalls=exchangeCalls=prepareCalls=commitCalls=abortCalls=destroyCalls=0;lastHandle=lastToken=lastOperation=0;lastInput=lastPreparedPacket=null;createFailure=prepareFailure=commitFailure=abortFailure=destroyFailure=null;}
}
