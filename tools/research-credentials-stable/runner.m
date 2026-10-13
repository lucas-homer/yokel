#import <Foundation/Foundation.h>
#import <Security/Security.h>
#import <CommonCrypto/CommonDigest.h>
#import <mach-o/dyld.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <readpassphrase.h>
#include <termios.h>
#include <fcntl.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#import "EmbeddedPolicy.h"

static NSString *const Service = @"yokel.docketclock.research.op";
static NSString *const Account = @"docketclock-research-mini";
static NSString *SelfPath;
static NSDictionary *CoreEnvelope;
static NSString *ManifestDigest;
static volatile sig_atomic_t Interrupted = 0;
static void Interrupt(int signalNumber) { Interrupted = signalNumber; }
static void Zero(void *p, size_t n) { volatile unsigned char *v = p; while (n--) *v++ = 0; }
static void Require(BOOL condition) {
    if (!condition) @throw [NSException exceptionWithName:@"RunnerFailure" reason:nil userInfo:nil];
}
#ifdef YOKEL_SYNTHETIC_TESTS
static void TestRequire(BOOL condition,int line) {
    if (!condition) @throw [NSException exceptionWithName:@"RunnerFailure" reason:[NSString stringWithFormat:@"%d",line] userInfo:nil];
}
#define Require(...) TestRequire((__VA_ARGS__),__LINE__)
#endif
static BOOL Match(NSString *s, NSString *pattern) {
    if (![s isKindOfClass:NSString.class]) return NO;
    NSRange range = [s rangeOfString:pattern options:NSRegularExpressionSearch];
    return range.location == 0 && range.length == s.length;
}
static NSDictionary *CleanEnvironment(void) {
    // Do not inherit caller OP_*, provider values, DYLD_*, PATH, proxies,
    // startup hooks, Python/Node options, shell functions, or debug flags.
    return @{@"HOME": NSHomeDirectory(), @"PATH": @"/usr/bin:/bin", @"LANG": @"en_US.UTF-8"};
}
static void ValidatePolicy(NSDictionary *p) {
    Require([p isKindOfClass:NSDictionary.class]);
    Require([[NSSet setWithArray:p.allKeys] isEqualToSet:[NSSet setWithArray:@[
        @"service_account_id", @"vault_id", @"op_path", @"op_sha256", @"references", @"jobs"]]]);
    // Preserve the supplied ID exactly; identity comparison remains case-sensitive.
    Require(Match(p[@"service_account_id"], @"^[A-Za-z0-9]{26}$"));
    Require(Match(p[@"vault_id"], @"^[a-z0-9]{26}$"));
    Require(Match(p[@"op_path"], @"^/[^\\x00\n\r]+$"));
    Require(Match(p[@"op_sha256"], @"^[a-f0-9]{64}$"));
    NSDictionary *refs = p[@"references"];
    Require([refs isKindOfClass:NSDictionary.class] && refs.count > 0 && refs.count <= 2);
    NSSet *allowed = [NSSet setWithArray:@[@"OPENROUTER_API_KEY", @"TYPESAFE_API_KEY"]];
    NSString *pattern = [NSString stringWithFormat:@"^op://%@/[a-z0-9]{26}/credential$", p[@"vault_id"]];
    for (NSString *key in refs) Require([allowed containsObject:key] && Match(refs[key], pattern));
    NSDictionary *jobs = p[@"jobs"];
    Require([jobs isKindOfClass:NSDictionary.class]);
    for (NSString *name in jobs) {
        Require(Match(name, @"^[a-z][a-z0-9-]{0,63}$"));
        NSDictionary *job = jobs[name];
        Require([job isKindOfClass:NSDictionary.class]);
        Require([[NSSet setWithArray:job.allKeys] isEqualToSet:[NSSet setWithArray:@[@"argv", @"files", @"timeout_seconds"]]]);
        NSArray *argv = job[@"argv"];
        NSDictionary *files = job[@"files"];
        NSNumber *timeout = job[@"timeout_seconds"];
        Require([argv isKindOfClass:NSArray.class] && argv.count > 0);
        Require([files isKindOfClass:NSDictionary.class] && files.count > 0);
        Require([timeout isKindOfClass:NSNumber.class] && timeout.doubleValue == timeout.intValue && timeout.intValue >= 1 && timeout.intValue <= 3600);
        for (NSString *arg in argv) Require([arg isKindOfClass:NSString.class] && [arg rangeOfString:[NSString stringWithFormat:@"%C", (unichar)0]].location == NSNotFound);
        Require(Match(argv[0], @"^/[^\\x00\n\r]+$") && files[argv[0]] != nil);
        for (NSString *path in files) Require(Match(path, @"^/[^\\x00\n\r]+$") && Match(files[path], @"^[a-f0-9]{64}$"));
    }
}
static NSDictionary *LoadPolicy(void) {
    NSData *bytes = [[NSData alloc] initWithBase64EncodedString:EmbeddedPolicy options:0];
    Require(bytes != nil);
    CoreEnvelope = [NSJSONSerialization JSONObjectWithData:bytes options:0 error:NULL];
    NSDictionary *policy = CoreEnvelope[@"base_policy"];
    ValidatePolicy(policy);
    return policy;
}
static NSString *Digest(NSString *path) {
    NSInputStream *stream = [NSInputStream inputStreamWithFileAtPath:path];
    [stream open];
    CC_SHA256_CTX ctx; CC_SHA256_Init(&ctx);
    uint8_t buffer[8192]; NSInteger n;
    while ((n = [stream read:buffer maxLength:sizeof buffer]) > 0) CC_SHA256_Update(&ctx, buffer, (CC_LONG)n);
    [stream close]; Require(n == 0);
    unsigned char hash[CC_SHA256_DIGEST_LENGTH]; CC_SHA256_Final(hash, &ctx);
    NSMutableString *result = [NSMutableString string];
    for (size_t i = 0; i < sizeof hash; i++) [result appendFormat:@"%02x", hash[i]];
    return result;
}
static void CheckFile(NSString *path, NSString *hash) { Require([Digest(path) isEqualToString:hash]); }
#import "Manifest.h"

static BOOL IdentityMatches(NSData *bytes, NSString *expected) {
    NSString *text = [[NSString alloc] initWithData:bytes encoding:NSUTF8StringEncoding];
    if (!text) return NO;
    NSMutableDictionary *fields = [NSMutableDictionary dictionary];
    for (NSString *line in [text componentsSeparatedByString:@"\n"]) {
        NSRange colon = [line rangeOfString:@":"];
        if (colon.location == NSNotFound) continue;
        NSString *key = [[line substringToIndex:colon.location] stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceCharacterSet];
        if (![@[@"ID", @"State", @"Type"] containsObject:key]) continue;
        if (fields[key]) return NO;
        fields[key] = [[line substringFromIndex:colon.location + 1] stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceCharacterSet];
    }
    return [fields[@"ID"] isEqual:expected] && [fields[@"State"] isEqual:@"ACTIVE"] && [fields[@"Type"] isEqual:@"SERVICE_ACCOUNT"];
}
static BOOL Resolved(NSDictionary *env, NSDictionary *refs) {
    for (NSString *key in refs) {
        NSString *value = env[key];
        if (![value isKindOfClass:NSString.class] || value.length == 0 || [value hasPrefix:@"op://"]) return NO;
    }
    return YES;
}

// Use ONLY the user's default local file-based Keychain; never scan other vaults.
static SecKeychainRef DefaultKeychain(void) {
    SecKeychainRef keychain = NULL;
    Require(SecKeychainCopyDefault(&keychain) == errSecSuccess && keychain != NULL);
    SecKeychainStatus status = 0;
    OSStatus result = SecKeychainGetStatus(keychain, &status);
    if (result != errSecSuccess || !(status & kSecUnlockStateStatus)) {
        CFRelease(keychain); Require(NO);
    }
    return keychain;
}
static NSData *Lookup(SecKeychainRef keychain, SecKeychainItemRef *outItem) {
    UInt32 length = 0; void *pointer = NULL;
    OSStatus status = SecKeychainFindGenericPassword(keychain,
        (UInt32)strlen(Service.UTF8String), Service.UTF8String,
        (UInt32)strlen(Account.UTF8String), Account.UTF8String, &length, &pointer, outItem);
    Require(status == errSecSuccess && pointer != NULL);
    NSData *bytes = nil;
    if (length > 0 && length <= 8192) bytes = [NSData dataWithBytes:pointer length:length];
    // Best effort zero of Security's returned copy before freeing it.
    if (pointer && length) Zero(pointer, length);
    SecKeychainItemFreeContent(NULL, pointer);
    Require(bytes != nil);
    return bytes;
}
static NSString *Token(void) {
#ifdef YOKEL_SYNTHETIC_TESTS
    Require(NO); // Synthetic binaries must never enter any Keychain API.
#endif
    // Process-local no-UI behavior; never unlock a Keychain or fall back to desktop.
    Require(SecKeychainSetUserInteractionAllowed(false) == errSecSuccess);
    SecKeychainRef keychain = DefaultKeychain();
    NSData *bytes;
    @try { bytes = Lookup(keychain, NULL); } @finally { CFRelease(keychain); }
    NSString *token = [[NSString alloc] initWithData:bytes encoding:NSUTF8StringEncoding];
    Require([token hasPrefix:@"ops_"] && Match(token, @"^[^\\x00\\s]+$"));
    return token;
}
static NSData *HiddenInput(void) {
    // readpassphrase handles signals and restores echo. One extra input byte
    // detects overflow: never silently accept a truncated token. Never stdin.
    Require(isatty(STDIN_FILENO) && isatty(STDOUT_FILENO));
    int terminal = open("/dev/tty", O_RDWR | O_NOCTTY); Require(terminal >= 0);
    struct termios original, inputMode;
    if (tcgetattr(terminal, &original) != 0) { close(terminal); Require(NO); }
    inputMode = original;
    // Avoid canonical line-length truncation of long service tokens. Keep signal
    // handling; readpassphrase handles its signal/echo cleanup, then we restore
    // the complete original mode in the finally block.
    inputMode.c_lflag &= ~(ICANON | ECHO | ECHONL);
    inputMode.c_cc[VMIN] = 1; inputMode.c_cc[VTIME] = 0;
    if (tcsetattr(terminal, TCSANOW, &inputMode) != 0) { close(terminal); Require(NO); }
    char buffer[8194] = {0}; NSData *bytes = nil;
    @try {
        char *input = readpassphrase("Service-account token (hidden; paste here, never in chat): ",
                               buffer, sizeof buffer, RPP_REQUIRE_TTY | RPP_ECHO_OFF);
#ifdef YOKEL_SYNTHETIC_TESTS
        if (!input) perror("synthetic hidden input");
#endif
        Require(input != NULL && !Interrupted);
        size_t n = strlen(buffer); Require(n > 4 && n <= 8192);
        bytes = [NSData dataWithBytes:buffer length:n];
    } @finally { Zero(buffer, sizeof buffer); tcsetattr(terminal, TCSANOW, &original); close(terminal); }
    return bytes;
}
static void Enroll(BOOL replace) {
    SecKeychainRef keychain = DefaultKeychain();
    SecTrustedApplicationRef trusted = NULL; SecAccessRef access = NULL; SecKeychainItemRef item = NULL;
    @try {
        // Trust this compiled executable, NOT security, a shell, or an interpreter.
        Require(SecTrustedApplicationCreateFromPath(SelfPath.fileSystemRepresentation, &trusted) == errSecSuccess);
        Require(SecAccessCreate(CFSTR("DocketClock research service token"),
            (__bridge CFArrayRef)@[(__bridge id)trusted], &access) == errSecSuccess);
        NSData *bytes = HiddenInput();
        NSString *token = [[NSString alloc] initWithData:bytes encoding:NSUTF8StringEncoding];
        Require([token hasPrefix:@"ops_"] && Match(token, @"^[^\\x00\\s]+$"));
        if (replace) {
            Lookup(keychain, &item); // Human authorization may be needed after rebuild.
            Require(SecKeychainItemModifyAttributesAndData(item, NULL, (UInt32)bytes.length, bytes.bytes) == errSecSuccess);
            Require(SecKeychainItemSetAccess(item, access) == errSecSuccess);
        } else {
            NSDictionary *attributes = @{
                (__bridge id)kSecClass: (__bridge id)kSecClassGenericPassword,
                (__bridge id)kSecAttrService: Service, (__bridge id)kSecAttrAccount: Account,
                (__bridge id)kSecAttrLabel: @"DocketClock research service token",
                (__bridge id)kSecValueData: bytes, (__bridge id)kSecAttrAccess: (__bridge id)access,
                (__bridge id)kSecUseKeychain: (__bridge id)keychain
            };
            Require(SecItemAdd((__bridge CFDictionaryRef)attributes, NULL) == errSecSuccess);
        }
        puts("Local enrollment complete. Identity and smoke validation remain required.");
    } @finally {
        if (item) CFRelease(item); if (access) CFRelease(access); if (trusted) CFRelease(trusted); CFRelease(keychain);
    }
}

// Explicit user-only migration: request only the item reference, never password bytes.
static void AuthorizeExisting(void) {
#ifdef YOKEL_SYNTHETIC_TESTS
    Require(NO); // Before any TTY or Keychain API; tests cannot mutate live trust.
#endif
    Require(isatty(STDIN_FILENO) && isatty(STDOUT_FILENO));
    int terminal=open("/dev/tty",O_RDWR|O_NOCTTY); Require(terminal>=0);
    BOOL actualTerminal=isatty(terminal); close(terminal); Require(actualTerminal);
    SecKeychainRef keychain=DefaultKeychain();
    SecTrustedApplicationRef trusted=NULL; SecAccessRef access=NULL; SecKeychainItemRef item=NULL;
    Boolean previous=true; BOOL havePrevious=NO;
    @try {
        Require(SecKeychainGetUserInteractionAllowed(&previous)==errSecSuccess); havePrevious=YES;
        Require(SecKeychainSetUserInteractionAllowed(true)==errSecSuccess);
        Require(SecKeychainFindGenericPassword(keychain,
            (UInt32)strlen(Service.UTF8String),Service.UTF8String,
            (UInt32)strlen(Account.UTF8String),Account.UTF8String,
            NULL,NULL,&item)==errSecSuccess && item!=NULL);
        Require(SecTrustedApplicationCreateFromPath(SelfPath.fileSystemRepresentation,&trusted)==errSecSuccess);
        Require(SecAccessCreate(CFSTR("DocketClock research service token"),
            (__bridge CFArrayRef)@[(__bridge id)trusted],&access)==errSecSuccess);
        Require(SecKeychainItemSetAccess(item,access)==errSecSuccess);
        puts("Exact runner access updated; token data was not requested. Validate identity and smoke.");
    } @finally {
        if(havePrevious) SecKeychainSetUserInteractionAllowed(previous);
        if(item) CFRelease(item); if(access) CFRelease(access); if(trusted) CFRelease(trusted); CFRelease(keychain);
    }
}

static void Execute(NSArray *argv, NSDictionary *env) __attribute__((noreturn));
static void Execute(NSArray *argv, NSDictionary *env) {
    char **a = calloc(argv.count + 1, sizeof(char *));
    char **e = calloc(env.count + 1, sizeof(char *)); Require(a != NULL && e != NULL);
    for (NSUInteger i = 0; i < argv.count; i++) a[i] = strdup([argv[i] UTF8String]);
    NSUInteger i = 0;
    for (NSString *key in env) e[i++] = strdup([[NSString stringWithFormat:@"%@=%@", key, env[key]] UTF8String]);
    execve(a[0], a, e); _exit(1);
}
static void Stage(NSDictionary *p, NSString *kind, NSString *job) {
    Require(setpgid(0, 0) == 0); // before exec, so supervisor can kill descendants
    NSMutableDictionary *env = [CleanEnvironment() mutableCopy];
    NSString *token = NSProcessInfo.processInfo.environment[@"OP_SERVICE_ACCOUNT_TOKEN"];
    Require([token hasPrefix:@"ops_"]);
    env[@"OP_SERVICE_ACCOUNT_TOKEN"] = token;
    env[@"OP_BIOMETRIC_UNLOCK_ENABLED"] = @"false"; env[@"OP_CACHE"] = @"false";
    CheckFile(p[@"op_path"], p[@"op_sha256"]);
    if ([kind isEqual:@"identity"]) Execute(@[p[@"op_path"], @"user", @"get", @"--me"], env);
    [env addEntriesFromDictionary:p[@"references"]];
    NSMutableArray *argv = [@[p[@"op_path"], @"run", @"--", SelfPath, job ? @"_payload-job" : @"_payload-smoke"] mutableCopy];
    if (job) { [argv addObject:job]; [argv addObject:ManifestDigest]; }
    Execute(argv, env);
}
static void Payload(NSDictionary *p, NSString *job) {
    NSDictionary *inherited = NSProcessInfo.processInfo.environment;
    Require(Resolved(inherited, p[@"references"]));
    NSMutableDictionary *env = [CleanEnvironment() mutableCopy];
    for (NSString *key in p[@"references"]) env[key] = inherited[key];
    // The token exists briefly in this op child. The actual job gets only keys.
    if (job) {
        NSDictionary *j = p[@"jobs"][job]; Require(j != nil);
        for (NSString *path in j[@"files"]) CheckFile(path, j[@"files"][path]);
        Execute(j[@"argv"], env);
    }
    _exit(0);
}
static NSData *Subprocess(NSArray *arguments, NSDictionary *env, double timeout, BOOL capture) {
    NSTask *task = [NSTask new]; task.executableURL = [NSURL fileURLWithPath:SelfPath];
    task.arguments = arguments; task.environment = env; task.currentDirectoryURL = [NSURL fileURLWithPath:@"/"];
    NSFileHandle *null = [NSFileHandle fileHandleForUpdatingAtPath:@"/dev/null"];
    Require(null != nil);
    task.standardInput = null; task.standardError = null;
    NSPipe *pipe = capture ? [NSPipe pipe] : nil;
    task.standardOutput = capture ? (id)pipe : (id)null;
    NSMutableData *bytes = [NSMutableData data]; NSLock *lock = [NSLock new];
    __block BOOL oversized = NO;
    dispatch_semaphore_t drained = dispatch_semaphore_create(0), done = dispatch_semaphore_create(0);
    task.terminationHandler = ^(NSTask *ignored) { (void)ignored; dispatch_semaphore_signal(done); };
    Require([task launchAndReturnError:NULL]);
    if (capture) {
        [pipe.fileHandleForWriting closeFile];
        dispatch_async(dispatch_get_global_queue(QOS_CLASS_UTILITY, 0), ^{
            @try {
                while (YES) {
                    NSData *chunk = [pipe.fileHandleForReading readDataOfLength:4096];
                    if (!chunk.length) break;
                    [lock lock];
                    if (bytes.length + chunk.length <= 65536) [bytes appendData:chunk]; else oversized = YES;
                    [lock unlock];
                }
            } @catch (NSException *ignored) { [lock lock]; oversized = YES; [lock unlock]; }
            dispatch_semaphore_signal(drained);
        });
    }
    pid_t pid = task.processIdentifier;
    uint64_t deadline = clock_gettime_nsec_np(CLOCK_MONOTONIC) + (uint64_t)(timeout * NSEC_PER_SEC);
    BOOL finished = NO;
    while (!Interrupted && clock_gettime_nsec_np(CLOCK_MONOTONIC) < deadline) {
        if (dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, 100 * NSEC_PER_MSEC)) == 0) { finished = YES; break; }
    }
    BOOL timedOut = !finished;
    if (timedOut) {
        kill(-pid, SIGTERM); kill(pid, SIGTERM);
        if (dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, NSEC_PER_SEC)) != 0) {
            kill(-pid, SIGKILL); kill(pid, SIGKILL);
            Require(dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, 2 * NSEC_PER_SEC)) == 0);
        }
    }
    kill(-pid, SIGKILL); // clean up ordinary descendants on successful exits too
    if (capture) {
        Require(dispatch_semaphore_wait(drained, dispatch_time(DISPATCH_TIME_NOW, 2 * NSEC_PER_SEC)) == 0);
        [pipe.fileHandleForReading closeFile];
    }
    [null closeFile];
    Require(!timedOut && task.terminationReason == NSTaskTerminationReasonExit && task.terminationStatus == 0 && !oversized);
    return [bytes copy];
}
static void Authenticated(NSDictionary *p, NSString *job, BOOL identityOnly, NSString *token) {
    if (job) {
        NSDictionary *j = p[@"jobs"][job]; Require(j != nil);
        for (NSString *path in j[@"files"]) CheckFile(path, j[@"files"][path]);
    }
    CheckFile(p[@"op_path"], p[@"op_sha256"]);
    if (job) ClaimJob(job);
    NSMutableDictionary *env = [CleanEnvironment() mutableCopy]; env[@"OP_SERVICE_ACCOUNT_TOKEN"] = token ?: Token();
    NSData *identity = Subprocess(@[@"_stage-identity"], env, 30, YES);
    Require(IdentityMatches(identity, p[@"service_account_id"]));
    if (!identityOnly) Subprocess(job ? @[@"_stage-job", job, ManifestDigest] : @[@"_stage-smoke"], env,
                                  job ? [p[@"jobs"][job][@"timeout_seconds"] doubleValue] : 30, NO);
    puts(identityOnly ? "Service-account identity OK." : (job ? "Approved research job completed." : "Credential injection OK; no provider calls."));
}
static void SelfTest(void) {
    NSString *id = @"aaaaaaaaaaaaaaaaaaaaaaaaaa";
    NSString *upperID = @"AAAAAAAAAAAAAAAAAAAAAAAAAA";
    NSMutableDictionary *fixture = [@{
        @"service_account_id": id, @"vault_id": id,
        @"op_path": @"/synthetic/op", @"op_sha256": @"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        @"references": @{@"OPENROUTER_API_KEY": @"op://aaaaaaaaaaaaaaaaaaaaaaaaaa/aaaaaaaaaaaaaaaaaaaaaaaaaa/credential"},
        @"jobs": @{}
    } mutableCopy];
    for (NSString *valid in @[id, upperID, @"AaAaAaAaAaAaAaAaAaAaAaAaAa"]) {
        fixture[@"service_account_id"] = valid;
        ValidatePolicy(fixture);
        Require([fixture[@"service_account_id"] isEqual:valid]);
    }
    for (NSString *invalid in @[@"aaaaaaaaaaaaaaaaaaaaaaaaa", @"aaaaaaaaaaaaaaaaaaaaaaaaaaa",
                               @" aaaaaaaaaaaaaaaaaaaaaaaaaa", @"aaaaaaaaaaaaaaaaaaaaaaaaaa\n",
                               @"aaaaaaaaaaaa_aaaaaaaaaaaaa"]) {
        fixture[@"service_account_id"] = invalid;
        BOOL rejected = NO;
        @try { ValidatePolicy(fixture); } @catch (NSException *ignored) { rejected = YES; }
        Require(rejected);
    }
    NSData *upperIdentity = [[NSString stringWithFormat:@"ID: %@\nState: ACTIVE\nType: SERVICE_ACCOUNT\n", upperID] dataUsingEncoding:NSUTF8StringEncoding];
    Require(IdentityMatches(upperIdentity, upperID));
    Require(!IdentityMatches(upperIdentity, id));
    Require(!IdentityMatches([[NSString stringWithFormat:@"ID: %@\nState: ACTIVE\nType: SERVICE_ACCOUNT\n", id] dataUsingEncoding:NSUTF8StringEncoding], upperID));
    Require(IdentityMatches([[NSString stringWithFormat:@"ID: %@\nState: ACTIVE\nType: SERVICE_ACCOUNT\n", id] dataUsingEncoding:NSUTF8StringEncoding], id));
    Require(!IdentityMatches([[NSString stringWithFormat:@"ID: %@\nState: ACTIVE\nType: USER\n", id] dataUsingEncoding:NSUTF8StringEncoding], id));
    Require(!IdentityMatches([[NSString stringWithFormat:@"ID: %@\nID: %@\nState: ACTIVE\nType: SERVICE_ACCOUNT\n", id, id] dataUsingEncoding:NSUTF8StringEncoding], id));
    NSDictionary *ref = @{@"OPENROUTER_API_KEY": @"op://synthetic"};
    Require(!Resolved(@{}, ref) && !Resolved(ref, ref) && Resolved(@{@"OPENROUTER_API_KEY": @"synthetic-only"}, ref));
    NSDictionary *env = CleanEnvironment(); Require(env.count == 3 && env[@"OP_SERVICE_ACCOUNT_TOKEN"] == nil);
    Require([Subprocess(@[@"_test-output"], env, 5, YES) isEqualToData:[@"synthetic-output\n" dataUsingEncoding:NSUTF8StringEncoding]]);
    for (NSString *name in @[@"_test-fail", @"_test-oversize", @"_test-timeout"]) {
        BOOL failed = NO;
        @try { Subprocess(@[name], env, [name isEqual:@"_test-timeout"] ? 0.2 : 5, [name isEqual:@"_test-oversize"]); }
        @catch (NSException *ignored) { failed = YES; }
        Require(failed);
    }
    puts("Synthetic identity, injection, environment, output bounds, failure and timeout tests passed; no Keychain access.");
}
int main(int argc, const char *argv[]) {
    @autoreleasepool {
        @try {
            signal(SIGINT, Interrupt); signal(SIGTERM, Interrupt);
            struct rlimit core = {0, 0}; Require(setrlimit(RLIMIT_CORE, &core) == 0); umask(0077);
            uint32_t n = 0; _NSGetExecutablePath(NULL, &n); char *path = calloc(n, 1); Require(path != NULL);
            Require(_NSGetExecutablePath(path, &n) == 0); char *real = realpath(path, NULL); free(path); Require(real != NULL);
            SelfPath = [NSString stringWithUTF8String:real]; free(real);
            Require(argc >= 2 && argc <= 4);
            NSString *command = [NSString stringWithUTF8String:argv[1]];
            NSString *job = argc >= 3 ? [NSString stringWithUTF8String:argv[2]] : nil;
            NSString *expected = argc == 4 ? [NSString stringWithUTF8String:argv[3]] : nil;
            NSSet *bound = [NSSet setWithArray:@[@"_stage-job", @"_payload-job", @"_test-check-boundary"]];
            Require(expected ? [bound containsObject:command] : ![bound containsObject:command]);
            if ([command isEqual:@"self-test"] && !job) { SelfTest(); return 0; }
            if ([command isEqual:@"_test-output"] && !job) { puts("synthetic-output"); return 0; }
            if ([command isEqual:@"_test-fail"] && !job) return 1;
            if ([command isEqual:@"_test-oversize"] && !job) { for (int i=0;i<70000;i++) putchar('x'); return 0; }
            if ([command isEqual:@"_test-timeout"] && !job) { Require(setpgid(0,0)==0); sleep(10); return 0; }
#ifdef YOKEL_SYNTHETIC_TESTS
            if (([command isEqual:@"_test-input"] || [command isEqual:@"_test-input-limit"]) && !job) {
                NSData *bytes = HiddenInput(); NSString *input = [[NSString alloc] initWithData:bytes encoding:NSUTF8StringEncoding];
                Require([input isEqual:[@"synthetic-" stringByPaddingToLength:([command isEqual:@"_test-input-limit"] ? 8192 : 509) withString:@"x" startingAtIndex:0]]);
                puts("Long hidden input OK."); return 0;
            }
#endif
            NSDictionary *p = LoadPolicy();
            ValidateCore();
            if (job) {
                Require([@[@"run", @"check-job", @"_stage-job", @"_payload-job", @"_test-auth-job", @"_test-check-boundary"] containsObject:command]);
                p = LoadJob(p, job, expected);
            }
            if ([command isEqual:@"check-job"] && job) {
                for (NSString *path in p[@"jobs"][job][@"files"]) CheckFile(path, p[@"jobs"][job][@"files"][path]);
                CheckFile(p[@"op_path"], p[@"op_sha256"]);
                puts("Signed fixed job and pins valid; no credentials read."); return 0;
            }
#ifdef YOKEL_SYNTHETIC_TESTS
            if ([command isEqual:@"_test-check-boundary"] && job) { puts("Bound manifest valid; no credentials read."); return 0; }
#endif
            if ([command isEqual:@"check-policy"] && !job) { puts("Embedded nonsecret policy valid."); return 0; }
#ifdef YOKEL_SYNTHETIC_TESTS
            if ([command isEqual:@"_test-auth-smoke"] && !job) { Authenticated(p, nil, NO, @"ops_synthetic-only"); return 0; }
            if ([command isEqual:@"_test-auth-job"] && job) { Authenticated(p, job, NO, @"ops_synthetic-only"); return 0; }
#endif
            #ifdef YOKEL_SYNTHETIC_TESTS
            Require(![command isEqual:@"enroll"] && ![command isEqual:@"rotate-local"]);
#endif
            if ([command isEqual:@"enroll"] && !job) { Enroll(NO); return 0; }
            if ([command isEqual:@"rotate-local"] && !job) { Enroll(YES); return 0; }
            if ([command isEqual:@"authorize-existing"] && !job) { AuthorizeExisting(); return 0; }
            if ([command isEqual:@"identity"] && !job) { Authenticated(p, nil, YES, nil); return 0; }
            if ([command isEqual:@"smoke"] && !job) { Authenticated(p, nil, NO, nil); return 0; }
            if ([command isEqual:@"run"] && job && p[@"jobs"][job]) { Authenticated(p, job, NO, nil); return 0; }
            if ([command isEqual:@"_stage-identity"] && !job) Stage(p, @"identity", nil);
            else if ([command isEqual:@"_stage-smoke"] && !job) Stage(p, @"smoke", nil);
            else if ([command isEqual:@"_stage-job"] && job && p[@"jobs"][job]) Stage(p, @"job", job);
            else if ([command isEqual:@"_payload-smoke"] && !job) Payload(p, nil);
            else if ([command isEqual:@"_payload-job"] && job && p[@"jobs"][job]) Payload(p, job);
            else Require(NO);
        } @catch (NSException *ignored) {
#ifdef YOKEL_SYNTHETIC_TESTS
            if ([ignored.name isEqual:@"RunnerFailure"] && Match(ignored.reason,@"^[0-9]+$")) fprintf(stderr,"Synthetic failed check: %s\n",ignored.reason.UTF8String);
#endif
            // No underlying Foundation errors, op output, policy values or token.
            fputs("Research runner failed: check policy, integrity, unlocked Keychain, account identity, or timeout. No desktop-auth fallback.\n", stderr);
            return 1;
        }
    }
    return 0;
}
