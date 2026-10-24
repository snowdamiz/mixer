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
