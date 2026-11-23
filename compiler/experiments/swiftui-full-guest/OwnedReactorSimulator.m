#import <UIKit/UIKit.h>
#include "OwnedReactorSimulator.h"
#include <mach/mach.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>

extern int mixer_s2a_replay(const char *path, bool fixed34);

static uint64_t mainStarted;

void mixer_s2a_checkpoint(const char *stage, size_t length, uint64_t elapsedMicros) {
    const uint64_t sinceMain = (clock_gettime_nsec_np(CLOCK_UPTIME_RAW) - mainStarted) / 1000;
    mach_task_basic_info_data_t memory;
    mach_msg_type_number_t count = MACH_TASK_BASIC_INFO_COUNT;
    const kern_return_t rssStatus = task_info(mach_task_self(), MACH_TASK_BASIC_INFO,
                                             (task_info_t)&memory, &count);
    struct rusage usage;
    const int peakStatus = getrusage(RUSAGE_SELF, &usage);
    char rss[32] = "unavailable";
    char peak[32] = "unavailable";
    if (rssStatus == KERN_SUCCESS) {
        snprintf(rss, sizeof(rss), "%llu", (unsigned long long)memory.resident_size);
    }
    if (peakStatus == 0 && usage.ru_maxrss > 0) {
        snprintf(peak, sizeof(peak), "%lld", (long long)usage.ru_maxrss);
    }
    fprintf(stderr, "s2a_stage=%.*s elapsed_us=%llu since_main_us=%llu rss_bytes=%s peak_rss_bytes=%s\n",
            (int)length, stage, (unsigned long long)elapsedMicros,
            (unsigned long long)sinceMain, rss, peak);
}

_Noreturn void mixer_s2a_finish(int status) {
    mixer_s2a_checkpoint("pre_exit", sizeof("pre_exit") - 1, 0);
    fprintf(stderr, "s2a_exit=%d pid=%d\n", status, getpid());
    fflush(stderr);
    exit(status);
}

static void runDiagnostic(NSString *systemVersion) {
    NSArray<NSString *> *arguments = NSProcessInfo.processInfo.arguments;
    NSString *mode = arguments.count == 2 ? arguments[1] : nil;
    const bool fixed34 = [mode isEqualToString:@"fixed34"];
    const bool native = [mode isEqualToString:@"native"];
    if (!fixed34 && !native && ![mode isEqualToString:@"ui256"]) {
        fprintf(stderr, "Expected exactly one diagnostic mode: native, fixed34 or ui256\n");
        mixer_s2a_finish(11);
    }
    fprintf(stderr, "s2a_start=%s pid=%d ios=%s\n", mode.UTF8String, getpid(), systemVersion.UTF8String);
    mixer_s2a_checkpoint("baseline", sizeof("baseline") - 1, 0);
    if (native) {
        mixer_s2a_start_native();
        return;
    }
    NSURL *payload = [NSBundle.mainBundle URLForResource:@"reactor-base" withExtension:@"wasm"];
    if (!payload.fileSystemRepresentation) {
        fprintf(stderr, "Bundled reactor-base.wasm is missing\n");
        mixer_s2a_finish(11);
    }
    mixer_s2a_finish(mixer_s2a_replay(payload.fileSystemRepresentation, fixed34));
}

@interface S2aSceneDelegate : UIResponder <UIWindowSceneDelegate>
@property(nonatomic, strong) UIWindow *window;
@end

@implementation S2aSceneDelegate
- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session
      options:(UISceneConnectionOptions *)options {
    (void)session;
    (void)options;
    self.window = [[UIWindow alloc] initWithWindowScene:(UIWindowScene *)scene];
    self.window.rootViewController = [[UIViewController alloc] init];
    self.window.rootViewController.view.backgroundColor = UIColor.systemBackgroundColor;
    [self.window makeKeyAndVisible];
    static dispatch_once_t start;
    dispatch_once(&start, ^{
        NSString *systemVersion = UIDevice.currentDevice.systemVersion;
        NSThread *worker = [[NSThread alloc] initWithBlock:^{
            @autoreleasepool {
                runDiagnostic(systemVersion);
            }
        }];
        // Keep the VM off the UI thread and give its validator a dedicated stack.
        worker.stackSize = 8 * 1024 * 1024;
        [worker start];
    });
}
@end

@interface S2aAppDelegate : UIResponder <UIApplicationDelegate>
@end
@implementation S2aAppDelegate
@end

int main(int argc, char *argv[]) {
    mainStarted = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
    @autoreleasepool {
        return UIApplicationMain(argc, argv, nil, NSStringFromClass(S2aAppDelegate.class));
    }
}
