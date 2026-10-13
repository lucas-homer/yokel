#import <Foundation/Foundation.h>
#import <Security/Security.h>
#include <unistd.h>
// Fixed reference-count query only. No item data, private key, mutation or selector argv.
int main(void) { @autoreleasepool {
    NSMutableDictionary *r=[@{@"password_data_requested":@NO,@"mutation":@NO,@"interaction_restored":@NO,@"uid":@(getuid())} mutableCopy];
    SecKeychainRef keychain=NULL; CFTypeRef result=NULL;Boolean previous=true;BOOL saved=NO;
    @try {
        if(getuid()!=501) @throw [NSException exceptionWithName:@"Refused" reason:nil userInfo:nil];
        OSStatus s=SecKeychainGetUserInteractionAllowed(&previous);r[@"get_interaction_status"]=@(s);if(s!=0)@throw [NSException exceptionWithName:@"Refused" reason:nil userInfo:nil];saved=YES;
        s=SecKeychainSetUserInteractionAllowed(false);r[@"disable_UI_status"]=@(s);if(s!=0)@throw [NSException exceptionWithName:@"Refused" reason:nil userInfo:nil];
        s=SecKeychainOpen("/Users/home/Library/Keychains/login.keychain-db",&keychain);r[@"open_explicit_keychain_status"]=@(s);if(s!=0||!keychain)@throw [NSException exceptionWithName:@"Refused" reason:nil userInfo:nil];
        NSDictionary *q=@{(__bridge id)kSecClass:(__bridge id)kSecClassGenericPassword,
            (__bridge id)kSecAttrService:@"yokel.docketclock.research.op",(__bridge id)kSecAttrAccount:@"docketclock-research-mini",
            (__bridge id)kSecMatchSearchList:@[(__bridge id)keychain],(__bridge id)kSecMatchLimit:(__bridge id)kSecMatchLimitAll,
            (__bridge id)kSecReturnRef:@YES,(__bridge id)kSecReturnData:@NO};
        s=SecItemCopyMatching((__bridge CFDictionaryRef)q,&result);r[@"reference_query_status"]=@(s);
        if(s==errSecSuccess && result && CFGetTypeID(result)==CFArrayGetTypeID())r[@"exact_match_count"]=@(CFArrayGetCount((CFArrayRef)result));
        else if(s==errSecItemNotFound)r[@"exact_match_count"]=@0;
        else r[@"exact_match_count"]=NSNull.null;
    } @catch(NSException *ignored) {r[@"diagnostic_refused"]=@YES;}
    @finally {
        if(result)CFRelease(result);if(keychain)CFRelease(keychain);
        if(saved){OSStatus restored=SecKeychainSetUserInteractionAllowed(previous);r[@"restore_interaction_status"]=@(restored);r[@"interaction_restored"]=@(restored==0);}
    }
    NSData *data=[NSJSONSerialization dataWithJSONObject:r options:NSJSONWritingPrettyPrinted|NSJSONWritingSortedKeys error:NULL];if(data){fwrite(data.bytes,1,data.length,stdout);putchar('\n');}return 0;
} }
