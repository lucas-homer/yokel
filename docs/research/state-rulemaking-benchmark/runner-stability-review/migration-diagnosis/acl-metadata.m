#import <Foundation/Foundation.h>
#import <Security/Security.h>
#include <dlfcn.h>
#include <unistd.h>

// One exact-item, no-UI metadata diagnostic. No password buffer, item mutation,
// token parse, op call, or arbitrary item/path selector.
typedef OSStatus (*ValidatePath)(SecTrustedApplicationRef,const char *);
typedef OSStatus (*CopyRequirement)(SecTrustedApplicationRef,SecRequirementRef *);
static NSArray *PartitionIDs(CFStringRef description) {
    if(!description) return @[];
    NSString *s=(__bridge NSString *)description;
    if(s.length>32768 || s.length%2) return @[];
    NSMutableData *bytes=[NSMutableData new];
    for(NSUInteger i=0;i<s.length;i+=2) {
        unsigned int value=0; NSScanner *scan=[NSScanner scannerWithString:[s substringWithRange:NSMakeRange(i,2)]];
        if(![scan scanHexInt:&value] || !scan.isAtEnd) return @[];
        unsigned char byte=(unsigned char)value; [bytes appendBytes:&byte length:1];
    }
    id p=[NSPropertyListSerialization propertyListWithData:bytes options:NSPropertyListImmutable format:NULL error:NULL];
    if(![p isKindOfClass:NSDictionary.class]) return @[];
    id array=p[@"Partitions"]; if(![array isKindOfClass:NSArray.class] || [array count]>32) return @[];
    NSMutableArray *safe=[NSMutableArray new];
    for(id part in array) if([part isKindOfClass:NSString.class] && [part length]<128 && [part rangeOfString:@"^(apple:|apple-tool:|teamid:[A-Z0-9]+|cdhash:[a-fA-F0-9]+)$" options:NSRegularExpressionSearch].location==0) [safe addObject:part];
    return safe;
}
int main(void) { @autoreleasepool {
    const char *target="/Users/home/.local/libexec/yokel/research-credentials-stable-v1";
    NSMutableDictionary *report=[@{@"password_data_requested":@NO,@"UI_enabled":@NO,@"item_mutation":@NO,@"uid":@(getuid())} mutableCopy];
    SecKeychainRef keychain=NULL; SecKeychainItemRef item=NULL; SecAccessRef access=NULL; CFArrayRef acls=NULL;
    OSStatus status=SecKeychainSetUserInteractionAllowed(false); report[@"disable_UI_status"]=@(status);
    if(status!=errSecSuccess) goto done;
    status=SecKeychainCopyDefault(&keychain); report[@"default_keychain_status"]=@(status); if(status!=errSecSuccess || !keychain) goto done;
    SecKeychainStatus bits=0; status=SecKeychainGetStatus(keychain,&bits); report[@"keychain_state_status"]=@(status); report[@"keychain_state_bits"]=@(bits);
    if(status!=errSecSuccess || !(bits&kSecUnlockStateStatus)) goto done;
    status=SecKeychainFindGenericPassword(keychain,strlen("yokel.docketclock.research.op"),"yokel.docketclock.research.op",strlen("docketclock-research-mini"),"docketclock-research-mini",NULL,NULL,&item);
    report[@"metadata_item_lookup_status"]=@(status); if(status!=errSecSuccess || !item) goto done;
    status=SecKeychainItemCopyAccess(item,&access); report[@"copy_access_status"]=@(status); if(status!=errSecSuccess || !access) goto done;
    status=SecAccessCopyACLList(access,&acls); report[@"ACL_list_status"]=@(status); if(status!=errSecSuccess || !acls) goto done;
    {
        ValidatePath validate=(ValidatePath)dlsym(RTLD_DEFAULT,"SecTrustedApplicationValidateWithPath");
        CopyRequirement copyRequirement=(CopyRequirement)dlsym(RTLD_DEFAULT,"SecTrustedApplicationCopyRequirement");
        report[@"validate_path_symbol_available"]=@(validate!=NULL); report[@"copy_requirement_symbol_available"]=@(copyRequirement!=NULL);
        report[@"ACL_count"]=@(CFArrayGetCount(acls)); NSMutableArray *rows=[NSMutableArray new];
        for(CFIndex i=0;i<MIN(CFArrayGetCount(acls),32);i++) {
            SecACLRef acl=(SecACLRef)CFArrayGetValueAtIndex(acls,i); CFArrayRef apps=NULL; CFStringRef description=NULL; SecKeychainPromptSelector selector=0;
            OSStatus contents=SecACLCopyContents(acl,&apps,&description,&selector); CFArrayRef auth=SecACLCopyAuthorizations(acl);
            NSMutableDictionary *row=[@{@"index":@(i),@"contents_status":@(contents),@"prompt_selector":@(selector),@"application_list_is_null":@(apps==NULL),@"application_count":@(apps?CFArrayGetCount(apps):0),@"partition_ids":PartitionIDs(description)} mutableCopy];
            NSMutableArray *tags=[NSMutableArray new]; if(auth) for(id value in (__bridge NSArray *)auth) if([value isKindOfClass:NSString.class] || [value isKindOfClass:NSNumber.class]) [tags addObject:value];
            row[@"authorization_tags"]=tags; NSMutableArray *matches=[NSMutableArray new];
            if(contents==errSecSuccess && apps) for(CFIndex j=0;j<MIN(CFArrayGetCount(apps),16);j++) {
                SecTrustedApplicationRef app=(SecTrustedApplicationRef)CFArrayGetValueAtIndex(apps,j); NSMutableDictionary *m=[@{@"index":@(j)} mutableCopy];
                if(validate) m[@"installed_binary_validation_status"]=@(validate(app,target));
                if(copyRequirement) {
                    SecRequirementRef requirement=NULL; OSStatus copied=copyRequirement(app,&requirement); m[@"requirement_copy_status"]=@(copied);
                    if(copied==errSecSuccess && requirement) {
                        CFStringRef text=NULL; OSStatus printed=SecRequirementCopyString(requirement,kSecCSDefaultFlags,&text); m[@"requirement_string_status"]=@(printed);
                        if(printed==errSecSuccess && text) m[@"code_requirement"]=(__bridge NSString *)text;
                        if(text) CFRelease(text); CFRelease(requirement);
                    }
                }
                [matches addObject:m];
            }
            row[@"trusted_application_validation"]=matches; [rows addObject:row];
            if(auth) CFRelease(auth); if(apps) CFRelease(apps); if(description) CFRelease(description);
        }
        report[@"ACL_entries"]=rows;
    }
done:
    if(acls) CFRelease(acls); if(access) CFRelease(access); if(item) CFRelease(item); if(keychain) CFRelease(keychain);
    NSData *data=[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted|NSJSONWritingSortedKeys error:NULL];
    if(data) { fwrite(data.bytes,1,data.length,stdout); putchar('\n'); } return 0;
} }
