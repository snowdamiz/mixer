#include <jni.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
static _Atomic int first_surface_failure;
static int32_t rejected(int code){int empty=0;atomic_compare_exchange_strong(&first_surface_failure,&empty,code);return 1;}
extern int32_t fieldlog_context_create(int64_t);
extern int32_t fieldlog_context_close(int64_t);
extern int32_t fieldlog_submit(int64_t,const uint8_t *,intptr_t);
extern intptr_t fieldlog_poll(int64_t,const uint8_t *,intptr_t,uint8_t *,intptr_t);
extern int32_t fieldlog_has_reply(int64_t,const uint8_t *,intptr_t);
typedef int32_t (*surface_callback)(int64_t,int32_t,const uint8_t *,intptr_t,const uint8_t *,intptr_t,const uint8_t *,intptr_t);
extern void fieldlog_set_surface_callback(surface_callback);
static _Thread_local JNIEnv *pump_env;
typedef struct Context {int64_t id;jobject receiver;int closed;struct Context *next;} Context;
static Context *contexts;
static int64_t next_context;
static Context *bound_context;
static uint8_t bound_owner[64];
static intptr_t bound_owner_n;
static Context *find_context(int64_t id){for(Context *p=contexts;p;p=p->next)if(p->id==id)return p;return NULL;}
static jbyteArray bytes(JNIEnv *e,const uint8_t *p,intptr_t n){if(n<0||n>1048576)return NULL;jbyteArray a=(*e)->NewByteArray(e,(jsize)n);if(a&&n)(*e)->SetByteArrayRegion(e,a,0,(jsize)n,(const jbyte *)p);return a;}
static int32_t surface(int64_t context,int32_t op,const uint8_t *owner,intptr_t owner_n,const uint8_t *packet,intptr_t packet_n,const uint8_t *descriptor,intptr_t descriptor_n){
 JNIEnv *e=pump_env;if(!e)return rejected(101);
 Context *route=find_context(context);if(!route)return rejected(102);
 // App lifetime release is separate from the public SDK's activate/install/revoke.
 if(op==3){
  if(!route->closed||bound_context==route)return rejected(110);
  Context **link=&contexts;while(*link!=route)link=&(*link)->next;
  *link=route->next;(*e)->DeleteGlobalRef(e,route->receiver);free(route);return 0;
 }
 if(owner_n<=0||owner_n>64||!owner)return rejected(103);
 if(op==0){if(route->closed||bound_context)return rejected(104);}
 else if(op==1||op==2){
  if(bound_context!=route||owner_n!=bound_owner_n||memcmp(owner,bound_owner,(size_t)owner_n)!=0)return rejected(105);
  if(op==1&&route->closed)return rejected(111);
 }else return rejected(112);
 jobject receiver=route->receiver;
 jclass c=(*e)->GetObjectClass(e,receiver);if(!c)return rejected(106);
 jmethodID m=(*e)->GetMethodID(e,c,"surface","(I[B[B[B)I");
 jbyteArray a=bytes(e,owner,owner_n),b=bytes(e,packet,packet_n),d=bytes(e,descriptor,descriptor_n);
 jint result=1;if(m&&a&&b&&d&&!(*e)->ExceptionCheck(e))result=(*e)->CallIntMethod(e,receiver,m,op,a,b,d);
 if((*e)->ExceptionCheck(e)){(*e)->ExceptionClear(e);result=rejected(109);}
 if(result==0&&op==0){bound_context=route;memcpy(bound_owner,owner,(size_t)owner_n);bound_owner_n=owner_n;}
 if(result==0&&op==2){bound_context=NULL;bound_owner_n=0;}
 if(a)(*e)->DeleteLocalRef(e,a);if(b)(*e)->DeleteLocalRef(e,b);if(d)(*e)->DeleteLocalRef(e,d);(*e)->DeleteLocalRef(e,c);return result;
}
JNIEXPORT jlong JNICALL Java_dev_mixer_android_FieldLogBridge_createContext(JNIEnv *e,jclass c,jobject receiver){
 (void)c;if(!receiver||next_context==INT64_MAX)return 0;
 Context *p=calloc(1,sizeof(*p));if(!p)return 0;
 p->receiver=(*e)->NewGlobalRef(e,receiver);if(!p->receiver){free(p);return 0;}
 p->id=++next_context;
 if(fieldlog_context_create(p->id)!=0){(*e)->DeleteGlobalRef(e,p->receiver);free(p);return 0;}
 p->next=contexts;contexts=p;return p->id;
}
JNIEXPORT jint JNICALL Java_dev_mixer_android_FieldLogBridge_beginClose(JNIEnv *e,jclass c,jlong context){
 (void)e;(void)c;Context *p=find_context(context);if(!p||p->closed)return 0;
 p->closed=1;return fieldlog_context_close(context);
}
JNIEXPORT jboolean JNICALL Java_dev_mixer_android_FieldLogBridge_contextRetained(JNIEnv *e,jclass c,jlong context){(void)e;(void)c;return find_context(context)?JNI_TRUE:JNI_FALSE;}
JNIEXPORT jint JNICALL Java_dev_mixer_android_FieldLogBridge_submit(JNIEnv *e,jclass c,jlong context,jbyteArray a){
 (void)c;Context *route=find_context(context);if(!route||route->closed||!a)return 1;
 jsize n=(*e)->GetArrayLength(e,a);if(n<=0||n>131072)return 1;
 jbyte *p=(*e)->GetByteArrayElements(e,a,0);if(!p)return 1;
 int32_t r=fieldlog_submit(context,(uint8_t *)p,n);(*e)->ReleaseByteArrayElements(e,a,p,JNI_ABORT);return r;
}
JNIEXPORT jbyteArray JNICALL Java_dev_mixer_android_FieldLogBridge_poll(JNIEnv *e,jclass c,jlong context,jstring request){
 (void)c;if(pump_env||!request)return NULL;
 jsize request_n=(*e)->GetStringUTFLength(e,request);if(request_n>128)return NULL;
 const char *request_p=(*e)->GetStringUTFChars(e,request,NULL);if(!request_p)return NULL;
 uint8_t *p=malloc(1048576);if(!p){(*e)->ReleaseStringUTFChars(e,request,request_p);return NULL;}
 pump_env=e;fieldlog_set_surface_callback(surface);
 intptr_t n=fieldlog_poll(context,(const uint8_t *)request_p,request_n,p,1048576);pump_env=NULL;
 (*e)->ReleaseStringUTFChars(e,request,request_p);
 jbyteArray a=n>=0&&n<=1048576?bytes(e,p,n):NULL;free(p);return a;
}
JNIEXPORT jboolean JNICALL Java_dev_mixer_android_FieldLogBridge_hasReply(JNIEnv *e,jclass c,jlong context,jstring request){
 (void)c;if(!request)return JNI_FALSE;
 jsize n=(*e)->GetStringUTFLength(e,request);if(n>128)return JNI_FALSE;
 const char *p=(*e)->GetStringUTFChars(e,request,NULL);if(!p)return JNI_FALSE;
 int32_t ready=fieldlog_has_reply(context,(const uint8_t *)p,n);(*e)->ReleaseStringUTFChars(e,request,p);return ready?JNI_TRUE:JNI_FALSE;
}
JNIEXPORT jint JNICALL Java_dev_mixer_android_FieldLogBridge_surfaceDiagnostic(JNIEnv *e,jclass c){(void)e;(void)c;return atomic_load(&first_surface_failure);}
