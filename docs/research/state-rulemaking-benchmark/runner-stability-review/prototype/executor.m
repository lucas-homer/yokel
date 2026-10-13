#import <Foundation/Foundation.h>
#import <Security/Security.h>
#import <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#import "FixturePolicy.h"

// Synthetic prototype: no Keychain APIs, op, real provider references or token.
static void NeedAt(BOOL ok,int line) { if (!ok) @throw [NSException exceptionWithName:@"Denied" reason:[NSString stringWithFormat:@"%d",line] userInfo:nil]; }
#define Need(x) NeedAt((x),__LINE__)
static BOOL Match(id value, NSString *pattern) {
    if (![value isKindOfClass:NSString.class]) return NO;
    NSRange r=[value rangeOfString:pattern options:NSRegularExpressionSearch];
    return r.location==0 && r.length==[value length];
}
static NSString *Hash(NSData *bytes) {
    unsigned char out[CC_SHA256_DIGEST_LENGTH]; CC_SHA256(bytes.bytes,(CC_LONG)bytes.length,out);
    NSMutableString *s=[NSMutableString new]; for (int i=0;i<sizeof(out);i++) [s appendFormat:@"%02x",out[i]]; return s;
}
static NSData *Read(NSString *path, NSUInteger limit) {
    int fd=open(path.fileSystemRepresentation,O_RDONLY|O_NOFOLLOW); Need(fd>=0);
    struct stat st; BOOL valid=fstat(fd,&st)==0 && S_ISREG(st.st_mode) && st.st_size>0 && st.st_size<=limit;
    if (!valid) { close(fd); Need(NO); }
    NSMutableData *d=[NSMutableData dataWithLength:(NSUInteger)st.st_size]; NSUInteger offset=0;
    while(offset<d.length) { ssize_t n=read(fd,(char *)d.mutableBytes+offset,d.length-offset); if(n<=0) { close(fd); Need(NO); } offset+=(NSUInteger)n; }
    close(fd); return d;
}
static BOOL Keys(NSDictionary *d, NSArray *keys) {
    return [d isKindOfClass:NSDictionary.class] && [[NSSet setWithArray:d.allKeys] isEqualToSet:[NSSet setWithArray:keys]];
}
static BOOL Number(id n) { return [n isKindOfClass:NSNumber.class] && CFGetTypeID((__bridge CFTypeRef)n)!=CFBooleanGetTypeID(); }
static NSDictionary *Validate(NSString *job, NSString *expected) {
    Need(Match(job,@"^[a-z][a-z0-9-]{0,31}$"));
    NSString *base=[Registry stringByAppendingPathComponent:job];
    NSData *raw=Read([base stringByAppendingString:@".json"],1024*1024);
    if(expected) Need([Hash(raw) isEqual:expected]);
    NSData *sig=Read([base stringByAppendingString:@".sig"],128);
    NSData *keyBytes=[[NSData alloc] initWithBase64EncodedString:PublicKey options:0];
    NSDictionary *attrs=@{(__bridge id)kSecAttrKeyType:(__bridge id)kSecAttrKeyTypeECSECPrimeRandom,
                         (__bridge id)kSecAttrKeyClass:(__bridge id)kSecAttrKeyClassPublic,(__bridge id)kSecAttrKeySizeInBits:@256};
    SecKeyRef key=SecKeyCreateWithData((__bridge CFDataRef)keyBytes,(__bridge CFDictionaryRef)attrs,NULL); Need(key!=NULL);
    static const char domain[]="yokel.synthetic.jobs.v1\0";
    NSMutableData *message=[NSMutableData dataWithBytes:domain length:sizeof(domain)-1]; [message appendData:raw];
    BOOL verified=SecKeyVerifySignature(key,kSecKeyAlgorithmECDSASignatureMessageX962SHA256,(__bridge CFDataRef)message,(__bridge CFDataRef)sig,NULL); CFRelease(key); Need(verified);
    NSDictionary *m=[NSJSONSerialization JSONObjectWithData:raw options:0 error:NULL];
    Need(Keys(m,@[@"schema_version",@"job_id",@"project",@"provider_scope",@"argv",@"files",@"timeout_seconds",@"prior_microusd",@"reservation_microusd",@"shared_budget_microusd"]));
    // Exact canonical bytes reject duplicate keys and noncanonical alternate encodings.
    NSData *canonical=[NSJSONSerialization dataWithJSONObject:m options:NSJSONWritingSortedKeys|NSJSONWritingWithoutEscapingSlashes error:NULL];
    Need([canonical isEqual:raw]);
    Need([m[@"schema_version"] isEqual:@"synthetic.fixed-job.v1"] && [m[@"job_id"] isEqual:job] && [m[@"project"] isEqual:@"synthetic-research"]);
    Need([m[@"provider_scope"] isEqual:@[@"SYNTHETIC_PROVIDER"]]);
    NSArray *argv=m[@"argv"]; Need([argv isKindOfClass:NSArray.class] && argv.count==3);
    Need([argv[0] isEqual:Payload] && [argv[1] isEqual:@"--fixture"] && Match(argv[2],@"^(alpha|beta)$"));
    Need(Keys(m[@"files"],@[Payload]));
    Need([Hash(Read(Payload,1024*1024)) isEqual:m[@"files"][Payload]]);
    Need(Number(m[@"timeout_seconds"]) && [m[@"timeout_seconds"] doubleValue]==[m[@"timeout_seconds"] intValue] && [m[@"timeout_seconds"] intValue]>=1 && [m[@"timeout_seconds"] intValue]<=5);
    Need(Number(m[@"prior_microusd"]) && [m[@"prior_microusd"] doubleValue]==540000);
    Need(Number(m[@"shared_budget_microusd"]) && [m[@"shared_budget_microusd"] doubleValue]==2000000);
    Need(Number(m[@"reservation_microusd"]) && [m[@"reservation_microusd"] doubleValue]==[m[@"reservation_microusd"] intValue] && [m[@"reservation_microusd"] intValue]>0 && [m[@"reservation_microusd"] intValue]<=160000);
    Need([m[@"prior_microusd"] intValue]+[m[@"reservation_microusd"] intValue]<=[m[@"shared_budget_microusd"] intValue]);
    return @{@"manifest":m,@"hash":Hash(raw)};
}
int main(int argc,char **argv) { @autoreleasepool { @try {
    umask(0077); Need(argc==3 || argc==4);
    NSString *mode=[NSString stringWithUTF8String:argv[1]], *job=[NSString stringWithUTF8String:argv[2]];
    Need(([mode isEqual:@"check"]||[mode isEqual:@"run"]) ? argc==3 : ([mode isEqual:@"stage-check"] && argc==4));
    NSDictionary *approved=Validate(job,argc==4?[NSString stringWithUTF8String:argv[3]]:nil);
    if (![mode isEqual:@"run"]) { puts("Synthetic manifest accepted."); return 0; }
    // Atomic one-shot claim before dispatch, never auto-cleared on failure.
    NSString *claim=[Journal stringByAppendingPathComponent:job]; int fd=open(claim.fileSystemRepresentation,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600); Need(fd>=0);
    NSData *digest=[approved[@"hash"] dataUsingEncoding:NSUTF8StringEncoding]; Need(write(fd,digest.bytes,digest.length)==digest.length && fsync(fd)==0); close(fd);
    int directory=open(Journal.fileSystemRepresentation,O_RDONLY); Need(directory>=0 && fsync(directory)==0); close(directory);
    NSDictionary *same=Validate(job,approved[@"hash"]); NSArray *args=same[@"manifest"][@"argv"];
    NSTask *task=[NSTask new]; task.executableURL=[NSURL fileURLWithPath:args[0]]; task.arguments=[args subarrayWithRange:NSMakeRange(1,2)]; task.currentDirectoryURL=[NSURL fileURLWithPath:@"/"];
    task.environment=@{@"PATH":@"/usr/bin:/bin",@"LANG":@"en_US.UTF-8",@"SYNTHETIC_PROVIDER":@"fixture-value"};
    task.standardOutput=[NSFileHandle fileHandleWithNullDevice]; task.standardError=[NSFileHandle fileHandleWithNullDevice];
    Need([task launchAndReturnError:NULL]); NSDate *deadline=[NSDate dateWithTimeIntervalSinceNow:[same[@"manifest"][@"timeout_seconds"] doubleValue]];
    while(task.running && deadline.timeIntervalSinceNow>0) [NSThread sleepForTimeInterval:0.01];
    if(task.running) { [task terminate]; [task waitUntilExit]; Need(NO); }
    Need(task.terminationReason==NSTaskTerminationReasonExit && task.terminationStatus==0);
    puts("Synthetic fixed job completed."); return 0;
 } @catch(NSException *error) { fprintf(stderr,"Synthetic job rejected at check %s.\n",error.reason.UTF8String ?: "unknown"); return 1; } } }
