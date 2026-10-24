#include <jni.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "mixer_android.h"
#include "mixer_android_v2.h"
#define MIXER_FAULT_DECLARATIONS
/* This file is prepended as declarations and appended as definitions to an
 * exact, retained test-derived jni.c. No hooks enter production source. */
#ifdef MIXER_FAULT_DECLARATIONS
static void *test_malloc(size_t length);
static void test_input(JNIEnv *,jbyteArray,jsize,jsize,jbyte *);
static jbyteArray test_array(JNIEnv *,jsize);
static void test_output(JNIEnv *,jbyteArray,jsize,jsize,const jbyte *);
static jclass test_class(JNIEnv *,const char *);
static jmethodID test_method(JNIEnv *,jclass,const char *,const char *);
static jobject test_object(JNIEnv *,jclass,jmethodID,jlong,jbyteArray);
static int32_t test_prepare(uint64_t,uint32_t,const uint8_t *,size_t,uint8_t *,size_t,size_t *,uint64_t *);
static int32_t test_abort(uint64_t,uint64_t);
static int32_t test_destroy(uint64_t);
#else
static int fault_point,cleanup_mode,malloc_calls;
static jthrowable injected;
static jlong prepares,aborts,destroys,last_token;
static void inject(JNIEnv *env) { (void)(*env)->Throw(env,injected); }
JNIEXPORT void JNICALL Java_dev_mixer_android_FaultControl_configure(JNIEnv *env,jclass cls,jint point,jint cleanup,jthrowable failure) {
    (void)cls;
    if(injected) (*env)->DeleteGlobalRef(env,injected);
    injected=failure?(*env)->NewGlobalRef(env,failure):NULL;
    fault_point=point;cleanup_mode=cleanup;malloc_calls=0;
    prepares=aborts=destroys=last_token=0;
}
JNIEXPORT jlongArray JNICALL Java_dev_mixer_android_FaultControl_stats(JNIEnv *env,jclass cls) {
    (void)cls;jlong values[]={prepares,aborts,destroys,last_token};
    jlongArray result=(*env)->NewLongArray(env,4);
    if(result) (*env)->SetLongArrayRegion(env,result,0,4,values);
    return result;
}
static void *test_malloc(size_t length) {
    malloc_calls++;
    if((fault_point==1 && malloc_calls==1)||(fault_point==2 && malloc_calls==2)) return NULL;
    return malloc(length);
}
static void test_input(JNIEnv *env,jbyteArray array,jsize start,jsize len,jbyte *bytes) {
    if(fault_point==3) { inject(env);return; }
    (*env)->GetByteArrayRegion(env,array,start,len,bytes);
}
static jbyteArray test_array(JNIEnv *env,jsize size) {
    if(fault_point==4) { inject(env);return NULL; }
    if(fault_point==10) return NULL;
    return (*env)->NewByteArray(env,size);
}
static void test_output(JNIEnv *env,jbyteArray array,jsize start,jsize len,const jbyte *bytes) {
    if(fault_point==5) { inject(env);return; }
    (*env)->SetByteArrayRegion(env,array,start,len,bytes);
}
static jclass test_class(JNIEnv *env,const char *name) {
    if(fault_point==6) { inject(env);return NULL; }
    if(fault_point==11) return NULL;
    return (*env)->FindClass(env,name);
}
static jmethodID test_method(JNIEnv *env,jclass type,const char *name,const char *signature) {
    if(fault_point==7) { inject(env);return NULL; }
    return (*env)->GetMethodID(env,type,name,signature);
}
static jobject test_object(JNIEnv *env,jclass type,jmethodID method,jlong token,jbyteArray packet) {
    if(fault_point==8) { inject(env);return NULL; }
    return (*env)->NewObject(env,type,method,token,packet);
}
static int32_t test_prepare(uint64_t handle,uint32_t operation,const uint8_t *input,size_t input_len,uint8_t *output,size_t capacity,size_t *written,uint64_t *token) {
    prepares++;
    int32_t status=mixer_android_prepare_v2(handle,operation,input,input_len,output,capacity,written,token);
    if(status==0) {
        memcpy(&last_token,token,sizeof last_token);
        if(fault_point==12) *written=capacity+1;
        if(fault_point==13) *token=0;
    }
    return status;
}
static int32_t test_abort(uint64_t handle,uint64_t token) {
    aborts++;
    if(cleanup_mode==1) return MIXER_ANDROID_V2_STALE_TOKEN;
    if(cleanup_mode==2) { (void)mixer_android_destroy(handle);return MIXER_ANDROID_V2_CLOSED; }
    return mixer_android_abort_v2(handle,token);
}
static int32_t test_destroy(uint64_t handle) { destroys++;return mixer_android_destroy(handle); }
#endif

#undef MIXER_FAULT_DECLARATIONS
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
    (void)cls; if(test_destroy((uint64_t)handle)!=0) failure(env,"Mixer stale session");
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
    return (jint)test_abort((uint64_t)handle,(uint64_t)token);
}

/* Called even with a pending Java exception; these C calls do not use JNI.
 * If abort cannot confirm disposal, retiring the session prevents later reuse. */
static void discard_v2(uint64_t handle,uint64_t token) {
    int32_t status=test_abort(handle,token);
    if(status!=MIXER_ANDROID_V2_OK && status!=MIXER_ANDROID_V2_CLOSED)
        (void)test_destroy(handle);
}

JNIEXPORT jobject JNICALL Java_dev_mixer_android_NativeBridge_prepareV2(JNIEnv *env,jclass cls,jlong handle,jint operation,jbyteArray input) {
    (void)cls;
    const size_t output_cap=1048576;
    size_t input_len=input?(size_t)(*env)->GetArrayLength(env,input):0;
    if((*env)->ExceptionCheck(env)) return NULL;
    if(input_len>131072 || operation<0 || operation>1 || (operation==0 && input_len!=0)) {
        failure(env,"Mixer invalid input bounds");return NULL;
    }
    uint8_t *in=input_len?test_malloc(input_len):NULL,*out=test_malloc(output_cap);
    if(!out || (input_len&&!in)) {
        free(in);free(out);failure(env,"Mixer bridge allocation failed");return NULL;
    }
    if(input_len) test_input(env,input,0,(jsize)input_len,(jbyte *)in);
    if((*env)->ExceptionCheck(env)) { free(in);free(out);return NULL; }
    size_t written=0;uint64_t token=0;
    int32_t status=test_prepare((uint64_t)handle,(uint32_t)operation,in,input_len,out,output_cap,&written,&token);
    free(in);
    if(status!=MIXER_ANDROID_V2_OK) {
        free(out);char text[80];snprintf(text,sizeof text,"Mixer prepare rejected (status %d)",status);
        failure(env,text);return NULL;
    }
    if(token==0 || written>output_cap) {
        /* An invalid success violates the C contract; do not reuse the session. */
        (void)test_abort((uint64_t)handle,token);
        (void)test_destroy((uint64_t)handle);
        free(out);failure(env,"Mixer invalid prepared candidate");return NULL;
    }
    jbyteArray packet=test_array(env,(jsize)written);
    jclass type=NULL;jobject result=NULL;
    if(!packet || (*env)->ExceptionCheck(env)) goto delivery_failed;
    test_output(env,packet,0,(jsize)written,(const jbyte *)out);
    if((*env)->ExceptionCheck(env)) goto delivery_failed;
    type=test_class(env,"dev/mixer/android/NativeBridge$Candidate");
    if(!type || (*env)->ExceptionCheck(env)) goto delivery_failed;
    jmethodID constructor=test_method(env,type,"<init>","(J[B)V");
    if(!constructor || (*env)->ExceptionCheck(env)) goto delivery_failed;
    /* memcpy avoids an implementation-defined unsigned-to-signed conversion. */
    _Static_assert(sizeof(jlong)==sizeof(uint64_t),"JNI token width");
    jlong java_token;memcpy(&java_token,&token,sizeof java_token);
    result=test_object(env,type,constructor,java_token,packet);
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

/* This file is prepended as declarations and appended as definitions to an
 * exact, retained test-derived jni.c. No hooks enter production source. */
#ifdef MIXER_FAULT_DECLARATIONS
static void *test_malloc(size_t length);
static void test_input(JNIEnv *,jbyteArray,jsize,jsize,jbyte *);
static jbyteArray test_array(JNIEnv *,jsize);
static void test_output(JNIEnv *,jbyteArray,jsize,jsize,const jbyte *);
static jclass test_class(JNIEnv *,const char *);
static jmethodID test_method(JNIEnv *,jclass,const char *,const char *);
static jobject test_object(JNIEnv *,jclass,jmethodID,jlong,jbyteArray);
static int32_t test_prepare(uint64_t,uint32_t,const uint8_t *,size_t,uint8_t *,size_t,size_t *,uint64_t *);
static int32_t test_abort(uint64_t,uint64_t);
static int32_t test_destroy(uint64_t);
#else
static int fault_point,cleanup_mode,malloc_calls;
static jthrowable injected;
static jlong prepares,aborts,destroys,last_token;
static void inject(JNIEnv *env) { (void)(*env)->Throw(env,injected); }
JNIEXPORT void JNICALL Java_dev_mixer_android_FaultControl_configure(JNIEnv *env,jclass cls,jint point,jint cleanup,jthrowable failure) {
    (void)cls;
    if(injected) (*env)->DeleteGlobalRef(env,injected);
    injected=failure?(*env)->NewGlobalRef(env,failure):NULL;
    fault_point=point;cleanup_mode=cleanup;malloc_calls=0;
    prepares=aborts=destroys=last_token=0;
}
JNIEXPORT jlongArray JNICALL Java_dev_mixer_android_FaultControl_stats(JNIEnv *env,jclass cls) {
    (void)cls;jlong values[]={prepares,aborts,destroys,last_token};
    jlongArray result=(*env)->NewLongArray(env,4);
    if(result) (*env)->SetLongArrayRegion(env,result,0,4,values);
    return result;
}
static void *test_malloc(size_t length) {
    malloc_calls++;
    if((fault_point==1 && malloc_calls==1)||(fault_point==2 && malloc_calls==2)) return NULL;
    return malloc(length);
}
static void test_input(JNIEnv *env,jbyteArray array,jsize start,jsize len,jbyte *bytes) {
    if(fault_point==3) { inject(env);return; }
    (*env)->GetByteArrayRegion(env,array,start,len,bytes);
}
static jbyteArray test_array(JNIEnv *env,jsize size) {
    if(fault_point==4) { inject(env);return NULL; }
    if(fault_point==10) return NULL;
    return (*env)->NewByteArray(env,size);
}
static void test_output(JNIEnv *env,jbyteArray array,jsize start,jsize len,const jbyte *bytes) {
    if(fault_point==5) { inject(env);return; }
    (*env)->SetByteArrayRegion(env,array,start,len,bytes);
}
static jclass test_class(JNIEnv *env,const char *name) {
    if(fault_point==6) { inject(env);return NULL; }
    if(fault_point==11) return NULL;
    return (*env)->FindClass(env,name);
}
static jmethodID test_method(JNIEnv *env,jclass type,const char *name,const char *signature) {
    if(fault_point==7) { inject(env);return NULL; }
    return (*env)->GetMethodID(env,type,name,signature);
}
static jobject test_object(JNIEnv *env,jclass type,jmethodID method,jlong token,jbyteArray packet) {
    if(fault_point==8) { inject(env);return NULL; }
    return (*env)->NewObject(env,type,method,token,packet);
}
static int32_t test_prepare(uint64_t handle,uint32_t operation,const uint8_t *input,size_t input_len,uint8_t *output,size_t capacity,size_t *written,uint64_t *token) {
    prepares++;
    int32_t status=mixer_android_prepare_v2(handle,operation,input,input_len,output,capacity,written,token);
    if(status==0) {
        memcpy(&last_token,token,sizeof last_token);
        if(fault_point==12) *written=capacity+1;
        if(fault_point==13) *token=0;
    }
    return status;
}
static int32_t test_abort(uint64_t handle,uint64_t token) {
    aborts++;
    if(cleanup_mode==1) return MIXER_ANDROID_V2_STALE_TOKEN;
    if(cleanup_mode==2) { (void)mixer_android_destroy(handle);return MIXER_ANDROID_V2_CLOSED; }
    return mixer_android_abort_v2(handle,token);
}
static int32_t test_destroy(uint64_t handle) { destroys++;return mixer_android_destroy(handle); }
#endif
