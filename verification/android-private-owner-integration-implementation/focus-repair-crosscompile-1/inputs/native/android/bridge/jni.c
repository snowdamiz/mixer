#include <jni.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "mixer_android.h"
#include "mixer_android_v2.h"
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

/* These decisions return only a scalar. In particular, do not allocate or
 * manufacture a Java exception after the engine has made its decision. */
JNIEXPORT jint JNICALL Java_dev_mixer_android_NativeBridge_commitV2(JNIEnv *env,jclass cls,jlong handle,jlong token) {
    (void)env;(void)cls;
    return (jint)mixer_android_commit_v2((uint64_t)handle,(uint64_t)token);
}
JNIEXPORT jint JNICALL Java_dev_mixer_android_NativeBridge_abortV2(JNIEnv *env,jclass cls,jlong handle,jlong token) {
    (void)env;(void)cls;
    return (jint)mixer_android_abort_v2((uint64_t)handle,(uint64_t)token);
}

/* Called even with a pending Java exception; these C calls do not use JNI.
 * If abort cannot confirm disposal, retiring the session prevents later reuse. */
static void discard_v2(uint64_t handle,uint64_t token) {
    int32_t status=mixer_android_abort_v2(handle,token);
    if(status!=MIXER_ANDROID_V2_OK && status!=MIXER_ANDROID_V2_CLOSED)
        (void)mixer_android_destroy(handle);
}

JNIEXPORT jobject JNICALL Java_dev_mixer_android_NativeBridge_prepareV2(JNIEnv *env,jclass cls,jlong handle,jint operation,jbyteArray input) {
    (void)cls;
    const size_t output_cap=1048576;
    size_t input_len=input?(size_t)(*env)->GetArrayLength(env,input):0;
    if((*env)->ExceptionCheck(env)) return NULL;
    if(input_len>131072 || operation<0 || operation>1 || (operation==0 && input_len!=0)) {
        failure(env,"Mixer invalid input bounds");return NULL;
    }
    uint8_t *in=input_len?malloc(input_len):NULL,*out=malloc(output_cap);
    if(!out || (input_len&&!in)) {
        free(in);free(out);failure(env,"Mixer bridge allocation failed");return NULL;
    }
    if(input_len) (*env)->GetByteArrayRegion(env,input,0,(jsize)input_len,(jbyte *)in);
    if((*env)->ExceptionCheck(env)) { free(in);free(out);return NULL; }
    size_t written=0;uint64_t token=0;
    int32_t status=mixer_android_prepare_v2((uint64_t)handle,(uint32_t)operation,in,input_len,out,output_cap,&written,&token);
    free(in);
    if(status!=MIXER_ANDROID_V2_OK) {
        free(out);char text[80];snprintf(text,sizeof text,"Mixer prepare rejected (status %d)",status);
        failure(env,text);return NULL;
    }
    if(token==0 || written>output_cap) {
        /* An invalid success violates the C contract; do not reuse the session. */
        (void)mixer_android_abort_v2((uint64_t)handle,token);
        (void)mixer_android_destroy((uint64_t)handle);
        free(out);failure(env,"Mixer invalid prepared candidate");return NULL;
    }
    jbyteArray packet=(*env)->NewByteArray(env,(jsize)written);
    jclass type=NULL;jobject result=NULL;
    if(!packet || (*env)->ExceptionCheck(env)) goto delivery_failed;
    (*env)->SetByteArrayRegion(env,packet,0,(jsize)written,(const jbyte *)out);
    if((*env)->ExceptionCheck(env)) goto delivery_failed;
    type=(*env)->FindClass(env,"dev/mixer/android/NativeBridge$Candidate");
    if(!type || (*env)->ExceptionCheck(env)) goto delivery_failed;
    jmethodID constructor=(*env)->GetMethodID(env,type,"<init>","(J[B)V");
    if(!constructor || (*env)->ExceptionCheck(env)) goto delivery_failed;
    /* memcpy avoids an implementation-defined unsigned-to-signed conversion. */
    _Static_assert(sizeof(jlong)==sizeof(uint64_t),"JNI token width");
    jlong java_token;memcpy(&java_token,&token,sizeof java_token);
    result=(*env)->NewObject(env,type,constructor,java_token,packet);
    if(!result || (*env)->ExceptionCheck(env)) goto delivery_failed;
    (*env)->DeleteLocalRef(env,type);
    (*env)->DeleteLocalRef(env,packet);
    free(out);return result;

delivery_failed:
    discard_v2((uint64_t)handle,token);
    /* DeleteLocalRef is permitted while an exception is pending. */
    if(result) (*env)->DeleteLocalRef(env,result);
    if(type) (*env)->DeleteLocalRef(env,type);
    if(packet) (*env)->DeleteLocalRef(env,packet);
    free(out);failure(env,"Mixer candidate delivery failed");return NULL;
}
