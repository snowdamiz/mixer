#include <jni.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include "mixer_android.h"
static void failure(JNIEnv *env,const char *message) {
    if ((*env)->ExceptionCheck(env)) return;
    jclass type=(*env)->FindClass(env,"java/lang/IllegalStateException");
    if(type) { (*env)->ThrowNew(env,type,message); (*env)->DeleteLocalRef(env,type); }
}
JNIEXPORT jlong JNICALL Java_dev_mixer_android_NativeBridge_create(JNIEnv *env,jclass cls) {
    (void)cls; uint64_t handle=mixer_android_create();
    if(!handle) failure(env,"Mixer engine session limit"); return (jlong)handle;
}
JNIEXPORT void JNICALL Java_dev_mixer_android_NativeBridge_destroy(JNIEnv *env,jclass cls,jlong handle) {
    (void)cls; if(mixer_android_destroy((uint64_t)handle)!=0) failure(env,"Mixer stale session");
}
JNIEXPORT jbyteArray JNICALL Java_dev_mixer_android_NativeBridge_exchange(JNIEnv *env,jclass cls,jlong handle,jint operation,jbyteArray input) {
    (void)cls; const size_t output_cap=1048576; size_t input_len=input?(size_t)(*env)->GetArrayLength(env,input):0;
    if((*env)->ExceptionCheck(env)) return NULL;
    if(input_len>131072 || operation<0 || operation>1) { failure(env,"Mixer invalid input bounds"); return NULL; }
    uint8_t *in=input_len?malloc(input_len):NULL,*out=malloc(output_cap);
    if(!out || (input_len&&!in)) { free(in);free(out);failure(env,"Mixer bridge allocation failed");return NULL; }
    if(input_len) (*env)->GetByteArrayRegion(env,input,0,(jsize)input_len,(jbyte *)in);
    if((*env)->ExceptionCheck(env)) { free(in);free(out);return NULL; }
    size_t written=0;int32_t status=mixer_android_exchange((uint64_t)handle,(uint32_t)operation,in,input_len,out,output_cap,&written);
    free(in);
    if(status!=0 || written>output_cap) { free(out);char text[80];snprintf(text,sizeof text,"Mixer exchange rejected (status %d)",status);failure(env,text);return NULL; }
    jbyteArray result=(*env)->NewByteArray(env,(jsize)written);
    if(result) (*env)->SetByteArrayRegion(env,result,0,(jsize)written,(const jbyte *)out);
    free(out);return result;
}
