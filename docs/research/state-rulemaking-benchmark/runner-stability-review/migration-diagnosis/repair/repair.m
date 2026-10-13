#import <Foundation/Foundation.h>
#import <Security/Security.h>
#import <CommonCrypto/CommonDigest.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>

static NSString *const Reader=@"/Users/home/.local/libexec/yokel/research-credentials-stable-v1";
static NSString *const ReaderSHA=@"821f91b67f4c0c2d2a7f333e1381fab9aec1f9d8a9b8be8c34a0ee135494547e";
static NSString *const ReaderCD=@"e51b17a7a822e62cc4a0ad89c9de7a2602975a6c";
static NSString *const OldPartition=@"cdhash:691cd655aae540caf887bff777bd48c9ef192326";
static NSString *const NewPartition=@"cdhash:e51b17a7a822e62cc4a0ad89c9de7a2602975a6c";
static NSString *const KeychainPath=@"/Users/home/Library/Keychains/login.keychain-db";
static NSString *const PartitionTag=@"ACLAuthorizationPartitionID";
static void Need(BOOL ok) { if(!ok) @throw [NSException exceptionWithName:@"RepairRefused" reason:nil userInfo:nil]; }
static NSString *Hex(NSData *data) { NSMutableString *s=[NSMutableString new]; const unsigned char *p=data.bytes; for(NSUInteger i=0;i<data.length;i++)[s appendFormat:@"%02x",p[i]]; return s; }
static NSString *Hash(NSData *data) { unsigned char h[CC_SHA256_DIGEST_LENGTH];CC_SHA256(data.bytes,(CC_LONG)data.length,h);return Hex([NSData dataWithBytes:h length:sizeof(h)]); }
static int Nibble(unichar c) { if(c>='0' && c<='9')return c-'0';if(c>='a' && c<='f')return c-'a'+10;if(c>='A' && c<='F')return c-'A'+10;return -1; }
static NSDictionary *PartitionPlist(NSString *description,NSPropertyListFormat *format) {
    Need([description isKindOfClass:NSString.class] && description.length>0 && description.length<=32768 && description.length%2==0);
    NSMutableData *data=[NSMutableData new];for(NSUInteger i=0;i<description.length;i+=2) { int a=Nibble([description characterAtIndex:i]),b=Nibble([description characterAtIndex:i+1]);Need(a>=0 && b>=0);unsigned char byte=(unsigned char)(16*a+b);[data appendBytes:&byte length:1]; }
    id value=[NSPropertyListSerialization propertyListWithData:data options:NSPropertyListImmutable format:format error:NULL];
    Need([value isKindOfClass:NSDictionary.class] && [value count]==1 && [value[@"Partitions"] isKindOfClass:NSArray.class]);return value;
}
static NSDictionary *Plan(NSArray *snapshot) {
    Need([snapshot isKindOfClass:NSArray.class] && snapshot.count>0 && snapshot.count<=64);
    NSUInteger index=NSNotFound;
    for(NSUInteger i=0;i<snapshot.count;i++) {
        NSDictionary *row=snapshot[i];Need([row isKindOfClass:NSDictionary.class] && [row[@"tags"] isKindOfClass:NSArray.class]);
        if([row[@"tags"] containsObject:PartitionTag]) { Need(index==NSNotFound && [row[@"tags"] isEqual:@[PartitionTag]]); index=i; }
    }
    Need(index!=NSNotFound);NSDictionary *row=snapshot[index];NSPropertyListFormat format;
    NSDictionary *plist=PartitionPlist(row[@"description"],&format);NSArray *parts=plist[@"Partitions"];
    Need([parts isEqual:@[OldPartition]] || [parts isEqual:@[NewPartition]]);
    BOOL changed=[parts isEqual:@[OldPartition]];NSString *next=row[@"description"];
    if(changed) { NSData *data=[NSPropertyListSerialization dataWithPropertyList:@{@"Partitions":@[NewPartition]} format:format options:0 error:NULL];Need(data!=nil);next=Hex(data); }
    NSMutableArray *expected=[snapshot mutableCopy];NSMutableDictionary *replacement=[row mutableCopy];replacement[@"description"]=next;expected[index]=replacement;
    return @{@"index":@(index),@"changed":@(changed),@"description":next,@"expected":expected};
}
static void ExactReader(NSString *path,NSString *sha,NSString *cdhash) { Need([path isEqual:Reader] && [sha isEqual:ReaderSHA] && [cdhash isEqual:ReaderCD]); }

#ifdef SYNTHETIC_FIXTURES
static int FixtureTests(void) {
    int checks=0;NSData *xml=[NSPropertyListSerialization dataWithPropertyList:@{@"Partitions":@[OldPartition]} format:NSPropertyListXMLFormat_v1_0 options:0 error:NULL];
    NSArray *before=@[@{@"tags":@[@"ACLAuthorizationDecrypt"],@"apps":@[@"stable-reader",@"historic-reader"],@"null_apps":@NO,@"description":@"unchanged label",@"prompt":@0},
                     @{@"tags":@[PartitionTag],@"apps":@[],@"null_apps":@YES,@"description":Hex(xml),@"prompt":@0},
                     @{@"tags":@[@"ACLAuthorizationChangeACL"],@"apps":@[],@"null_apps":@NO,@"description":@"unchanged owner",@"prompt":@1}];
    NSDictionary *plan=Plan(before);Need([plan[@"changed"] boolValue]);checks++;
    NSArray *after=plan[@"expected"];Need([after[0] isEqual:before[0]] && [after[2] isEqual:before[2]]);checks++;
    for(NSString *key in @[@"tags",@"apps",@"null_apps",@"prompt"])Need([after[1][key] isEqual:before[1][key]]);checks++;
    Need([PartitionPlist(after[1][@"description"],NULL)[@"Partitions"] isEqual:@[NewPartition]]);checks++;
    Need(![Plan(after)[@"changed"] boolValue] && [Plan(after)[@"expected"] isEqual:after]);checks++;
    NSArray *badDescriptions=@[@"00z0",@"1",Hex([NSPropertyListSerialization dataWithPropertyList:@{@"Partitions":@[@"apple:"]} format:NSPropertyListXMLFormat_v1_0 options:0 error:NULL]),Hex([NSPropertyListSerialization dataWithPropertyList:@{@"Partitions":@[OldPartition,NewPartition]} format:NSPropertyListXMLFormat_v1_0 options:0 error:NULL]),Hex([NSPropertyListSerialization dataWithPropertyList:@{@"Partitions":@[OldPartition],@"unknown":@1} format:NSPropertyListXMLFormat_v1_0 options:0 error:NULL])];
    for(NSString *description in badDescriptions) { NSMutableArray *bad=[before mutableCopy];NSMutableDictionary *row=[before[1] mutableCopy];row[@"description"]=description;bad[1]=row;BOOL refused=NO;@try { Plan(bad); }@catch(NSException *e){refused=YES;}Need(refused);checks++; }
    for(int variant=0;variant<3;variant++) { NSMutableArray *bad=[before mutableCopy];if(variant==0)[bad removeObjectAtIndex:1];if(variant==1)[bad addObject:before[1]];if(variant==2){NSMutableDictionary *row=[before[1] mutableCopy];row[@"tags"]=@[PartitionTag,@"ACLAuthorizationDecrypt"];bad[1]=row;}BOOL refused=NO;@try{Plan(bad);}@catch(NSException *e){refused=YES;}Need(refused);checks++; }
    ExactReader(Reader,ReaderSHA,ReaderCD);checks++;
    for(int variant=0;variant<3;variant++){BOOL refused=NO;@try{ExactReader(variant==0?@"/wrong":Reader,variant==1?@"wrong":ReaderSHA,variant==2?@"wrong":ReaderCD);}@catch(NSException *e){refused=YES;}Need(refused);checks++;}
    NSMutableArray *corrupt=[after mutableCopy];NSMutableDictionary *row=[after[0] mutableCopy];row[@"apps"]=@[@"repair-helper"];corrupt[0]=row;Need(![corrupt isEqual:plan[@"expected"]]);checks++;
    NSData *binary=[NSPropertyListSerialization dataWithPropertyList:@{@"Partitions":@[OldPartition]} format:NSPropertyListBinaryFormat_v1_0 options:0 error:NULL];NSMutableArray *binaryBefore=[before mutableCopy];row=[before[1] mutableCopy];row[@"description"]=Hex(binary);binaryBefore[1]=row;NSDictionary *binaryPlan=Plan(binaryBefore);NSPropertyListFormat preserved;PartitionPlist(binaryPlan[@"description"],&preserved);Need(preserved==NSPropertyListBinaryFormat_v1_0);checks++;
    printf("{\"state\":\"passed\",\"fixture_checks\":%d,\"keychain_access\":false,\"live_mutation\":false}\n",checks);return 0;
}
#else
typedef OSStatus (*ValidatePath)(SecTrustedApplicationRef,const char *);
typedef OSStatus (*CopyRequirement)(SecTrustedApplicationRef,SecRequirementRef *);
static void ValidateInstalledReader(void) {
    char *actual=realpath(Reader.fileSystemRepresentation,NULL);Need(actual!=NULL);NSString *path=[NSString stringWithUTF8String:actual];free(actual);
    NSData *bytes=[NSData dataWithContentsOfFile:Reader options:NSDataReadingMappedIfSafe error:NULL];Need(bytes!=nil);
    SecStaticCodeRef code=NULL;CFDictionaryRef info=NULL;
    @try { Need(SecStaticCodeCreateWithPath((__bridge CFURLRef)[NSURL fileURLWithPath:Reader],kSecCSDefaultFlags,&code)==errSecSuccess);
        Need(SecStaticCodeCheckValidity(code,kSecCSStrictValidate,NULL)==errSecSuccess);
        Need(SecCodeCopySigningInformation(code,kSecCSSigningInformation,&info)==errSecSuccess);
        NSData *cd=(__bridge NSData *)CFDictionaryGetValue(info,kSecCodeInfoUnique);Need([cd isKindOfClass:NSData.class]);ExactReader(path,Hash(bytes),Hex(cd));
    } @finally { if(info)CFRelease(info);if(code)CFRelease(code); }
}
static NSArray *Snapshot(SecAccessRef access,SecACLRef *selected,BOOL *readerTrusted) {
    CFArrayRef acls=NULL;Need(SecAccessCopyACLList(access,&acls)==errSecSuccess && acls!=NULL);NSMutableArray *rows=[NSMutableArray new];
    ValidatePath validate=(ValidatePath)dlsym(RTLD_DEFAULT,"SecTrustedApplicationValidateWithPath");CopyRequirement copy=(CopyRequirement)dlsym(RTLD_DEFAULT,"SecTrustedApplicationCopyRequirement");Need(validate && copy);
    @try { Need(CFArrayGetCount(acls)>0 && CFArrayGetCount(acls)<=64);
        for(CFIndex i=0;i<CFArrayGetCount(acls);i++) {
            SecACLRef acl=(SecACLRef)CFArrayGetValueAtIndex(acls,i);CFArrayRef tags=SecACLCopyAuthorizations(acl),apps=NULL;CFStringRef description=NULL;SecKeychainPromptSelector prompt=0;
            @try { Need(tags!=NULL && SecACLCopyContents(acl,&apps,&description,&prompt)==errSecSuccess);
                NSArray *sorted=[(__bridge NSArray *)tags sortedArrayUsingSelector:@selector(compare:)];NSMutableArray *appIdentities=[NSMutableArray new];
                if(apps) for(CFIndex n=0;n<CFArrayGetCount(apps);n++) {
                    SecTrustedApplicationRef app=(SecTrustedApplicationRef)CFArrayGetValueAtIndex(apps,n);SecRequirementRef req=NULL;CFStringRef text=NULL;CFDataRef path=NULL;
                    @try { Need(copy(app,&req)==errSecSuccess && req!=NULL && SecRequirementCopyString(req,kSecCSDefaultFlags,&text)==errSecSuccess && text!=NULL);
                        Need(SecTrustedApplicationCopyData(app,&path)==errSecSuccess && path!=NULL);
                        [appIdentities addObject:@{@"requirement":(__bridge NSString *)text,@"path_hash":Hash((__bridge NSData *)path)}];
                        if([sorted containsObject:@"ACLAuthorizationDecrypt"] && validate(app,Reader.fileSystemRepresentation)==errSecSuccess)*readerTrusted=YES;
                    } @finally { if(path)CFRelease(path);if(text)CFRelease(text);if(req)CFRelease(req); }
                }
                if([sorted containsObject:@"ACLAuthorizationDecrypt"])Need(apps!=NULL && CFArrayGetCount(apps)>0);
                NSDictionary *row=@{@"tags":sorted,@"apps":appIdentities,@"null_apps":@(apps==NULL),@"description":description?(__bridge id)description:(id)NSNull.null,@"prompt":@(prompt)};[rows addObject:row];
                if([sorted containsObject:PartitionTag] && selected) { Need(*selected==NULL);*selected=(SecACLRef)CFRetain(acl); }
            } @finally {if(tags)CFRelease(tags);if(apps)CFRelease(apps);if(description)CFRelease(description);}
        }
    } @finally {CFRelease(acls);}return rows;
}
static int Repair(int argc,const char **argv) {
    Need(argc==2 && strcmp(argv[1],"--repair-known-partition")==0 && getuid()==501 && geteuid()==501);
    Need(isatty(STDIN_FILENO) && isatty(STDOUT_FILENO));int tty=open("/dev/tty",O_RDWR|O_NOCTTY);Need(tty>=0);BOOL realTTY=isatty(tty);close(tty);Need(realTTY);
    ValidateInstalledReader();SecKeychainRef keychain=NULL;SecKeychainItemRef item=NULL;SecAccessRef access=NULL,readback=NULL;SecACLRef partition=NULL;
    Boolean prior=true;BOOL saved=NO,committed=NO;const char *phase="preflight";
    @try {
        Need(SecKeychainGetUserInteractionAllowed(&prior)==errSecSuccess);saved=YES;Need(SecKeychainSetUserInteractionAllowed(false)==errSecSuccess);
        Need(SecKeychainCopyDefault(&keychain)==errSecSuccess && keychain!=NULL);UInt32 size=4096;char path[4096]={0};Need(SecKeychainGetPath(keychain,&size,path)==errSecSuccess && [KeychainPath isEqual:[NSString stringWithUTF8String:path]]);
        SecKeychainStatus bits=0;Need(SecKeychainGetStatus(keychain,&bits)==errSecSuccess && (bits&kSecUnlockStateStatus));
        Need(SecKeychainFindGenericPassword(keychain,strlen("yokel.docketclock.research.op"),"yokel.docketclock.research.op",strlen("docketclock-research-mini"),"docketclock-research-mini",NULL,NULL,&item)==errSecSuccess && item!=NULL);
        Need(SecKeychainItemCopyAccess(item,&access)==errSecSuccess && access!=NULL);BOOL trusted=NO;NSArray *before=Snapshot(access,&partition,&trusted);Need(trusted && partition!=NULL);NSDictionary *plan=Plan(before);
        if(![plan[@"changed"] boolValue]) {puts("Exact partition already matches stable-v1; no change made.");return 0;}
        CFArrayRef apps=NULL;CFStringRef description=NULL;SecKeychainPromptSelector prompt=0;
        @try {Need(SecACLCopyContents(partition,&apps,&description,&prompt)==errSecSuccess);
            Need(SecACLSetContents(partition,apps,(__bridge CFStringRef)plan[@"description"],prompt)==errSecSuccess);
        } @finally {if(apps)CFRelease(apps);if(description)CFRelease(description);}
        BOOL stillTrusted=NO;Need([Snapshot(access,NULL,&stillTrusted) isEqual:plan[@"expected"]] && stillTrusted);ValidateInstalledReader();
        phase="authorization-and-commit";Need(SecKeychainSetUserInteractionAllowed(true)==errSecSuccess);
        // Only the copied access object's one modified ACL is committed; no item data.
        Need(SecKeychainItemSetAccess(item,access)==errSecSuccess);committed=YES;
        phase="readback";Need(SecKeychainSetUserInteractionAllowed(false)==errSecSuccess);
        Need(SecKeychainItemCopyAccess(item,&readback)==errSecSuccess && readback!=NULL);BOOL afterTrusted=NO;
        Need([Snapshot(readback,NULL,&afterTrusted) isEqual:plan[@"expected"]] && afterTrusted);ValidateInstalledReader();
        puts("Exact stale partition repaired and metadata readback matched. Token data was not requested. Validate stable-v1 identity and smoke.");return 0;
    } @catch(NSException *e) {fprintf(stderr,"Partition repair stopped at %s; commit completed=%s. Inspect metadata before further action. No automatic retry or rollback.\n",phase,committed?"yes":"no");return 1;}
    @finally {if(saved)SecKeychainSetUserInteractionAllowed(prior);if(partition)CFRelease(partition);if(readback)CFRelease(readback);if(access)CFRelease(access);if(item)CFRelease(item);if(keychain)CFRelease(keychain);}
}
#endif
int main(int argc,const char **argv) {@autoreleasepool {@try {
#ifdef SYNTHETIC_FIXTURES
    if(argc!=2 || strcmp(argv[1],"--synthetic-fixtures"))return 1;return FixtureTests();
#else
    return Repair(argc,argv);
#endif
} @catch(NSException *e) {fputs("Partition repair refused before commit. Fixed target/TTY/metadata requirements not satisfied.\n",stderr);return 1;}}}
