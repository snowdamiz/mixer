#include <jni.h>
#include <stdint.h>

extern void *mixer_compose_editor_open_v1(void);
extern void mixer_compose_editor_close_v1(void *handle);
extern int32_t mixer_compose_editor_call_v1(void *handle, int32_t op,
    const uint8_t *input, intptr_t count, uint8_t *output, intptr_t capacity);

JNIEXPORT jlong JNICALL Java_dev_mixer_compose_SwiftSession_openNative(
    JNIEnv *env, jobject session) {
    (void)env;
    (void)session;
    return (jlong)(intptr_t)mixer_compose_editor_open_v1();
}

JNIEXPORT void JNICALL Java_dev_mixer_compose_SwiftSession_closeNative(
    JNIEnv *env, jobject session, jlong handle) {
    (void)env;
    (void)session;
    if (handle != 0) mixer_compose_editor_close_v1((void *)(intptr_t)handle);
}

JNIEXPORT jbyteArray JNICALL Java_dev_mixer_compose_SwiftSession_callNative(
    JNIEnv *env, jobject session, jlong handle, jint op, jbyteArray data) {
    (void)session;
    jbyte input[8192], output[8192];
    if (handle == 0 || data == NULL) return NULL;
    jsize count = (*env)->GetArrayLength(env, data);
    if ((size_t)count > sizeof input) return NULL;
    (*env)->GetByteArrayRegion(env, data, 0, count, input);
    if ((*env)->ExceptionCheck(env)) return NULL;
    int32_t written = mixer_compose_editor_call_v1((void *)(intptr_t)handle, op,
        (const uint8_t *)input, count, (uint8_t *)output, sizeof output);
    if (written < 0 || (size_t)written > sizeof output) return NULL;
    jbyteArray result = (*env)->NewByteArray(env, written);
    if (result != NULL) (*env)->SetByteArrayRegion(env, result, 0, written, output);
    return result;
}
