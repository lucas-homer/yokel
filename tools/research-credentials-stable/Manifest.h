// Included after existing hash/validation helpers. No secret lookup in this module.
static BOOL ExactKeys(NSDictionary *value, NSArray *keys) {
    return [value isKindOfClass:NSDictionary.class] && [[NSSet setWithArray:value.allKeys] isEqualToSet:[NSSet setWithArray:keys]];
}
static BOOL IntegerBetween(id value, long long low, long long high) {
    return [value isKindOfClass:NSNumber.class] && CFGetTypeID((__bridge CFTypeRef)value)!=CFBooleanGetTypeID()
        && [value doubleValue]==[value longLongValue] && [value longLongValue]>=low && [value longLongValue]<=high;
}
static BOOL CanonicalPath(NSString *path) {
    if (!Match(path,@"^/[^\\x00\n\r]+$")) return NO;
    char *real=realpath(path.fileSystemRepresentation,NULL); if(!real) return NO;
    BOOL same=[path isEqual:[NSString stringWithUTF8String:real]]; free(real); return same;
}
static BOOL WithinRoots(NSString *path, NSArray *roots) {
    if(!CanonicalPath(path)) return NO;
    for(NSString *root in roots) if([path hasPrefix:[root stringByAppendingString:@"/"]]) return YES;
    return NO;
}
static void OwnerDirectory(NSString *path) {
    struct stat st; Require(CanonicalPath(path) && lstat(path.fileSystemRepresentation,&st)==0 && S_ISDIR(st.st_mode) && st.st_uid==getuid() && !(st.st_mode&0077));
}
static NSData *OwnerRead(NSString *path, NSUInteger maxBytes) {
    int fd=open(path.fileSystemRepresentation,O_RDONLY|O_NOFOLLOW); Require(fd>=0);
    struct stat st;
    if(fstat(fd,&st)!=0 || !S_ISREG(st.st_mode) || st.st_uid!=getuid() || (st.st_mode&0077) || st.st_size<=0 || st.st_size>maxBytes) { close(fd); Require(NO); }
    NSMutableData *bytes=[NSMutableData dataWithLength:(NSUInteger)st.st_size]; NSUInteger offset=0;
    while(offset<bytes.length) { ssize_t n=read(fd,(char *)bytes.mutableBytes+offset,bytes.length-offset); if(n<=0) { close(fd); Require(NO); } offset+=(NSUInteger)n; }
    close(fd); return bytes;
}
static NSString *DataDigest(NSData *bytes) {
    unsigned char hash[CC_SHA256_DIGEST_LENGTH]; CC_SHA256(bytes.bytes,(CC_LONG)bytes.length,hash);
    NSMutableString *s=[NSMutableString new]; for(NSUInteger i=0;i<sizeof(hash);i++) [s appendFormat:@"%02x",hash[i]]; return s;
}
static NSData *CanonicalJSON(id value, NSUInteger depth) {
    Require(depth<=64); NSMutableData *out=[NSMutableData new];
    if([value isKindOfClass:NSDictionary.class]) {
        [out appendData:[@"{" dataUsingEncoding:NSUTF8StringEncoding]];
        NSArray *keys=[[value allKeys] sortedArrayUsingComparator:^NSComparisonResult(NSString *a,NSString *b) {
            int order=strcmp(a.UTF8String,b.UTF8String); return order<0?NSOrderedAscending:(order>0?NSOrderedDescending:NSOrderedSame);
        }];
        BOOL first=YES; for(NSString *key in keys) { Require([key isKindOfClass:NSString.class]); if(!first) [out appendData:[@"," dataUsingEncoding:NSUTF8StringEncoding]]; first=NO;
            [out appendData:CanonicalJSON(key,depth+1)]; [out appendData:[@":" dataUsingEncoding:NSUTF8StringEncoding]]; [out appendData:CanonicalJSON(value[key],depth+1)]; }
        [out appendData:[@"}" dataUsingEncoding:NSUTF8StringEncoding]];
    } else if([value isKindOfClass:NSArray.class]) {
        [out appendData:[@"[" dataUsingEncoding:NSUTF8StringEncoding]]; BOOL first=YES;
        for(id item in value) { if(!first) [out appendData:[@"," dataUsingEncoding:NSUTF8StringEncoding]]; first=NO; [out appendData:CanonicalJSON(item,depth+1)]; }
        [out appendData:[@"]" dataUsingEncoding:NSUTF8StringEncoding]];
    } else if([value isKindOfClass:NSString.class]) {
        NSData *array=[NSJSONSerialization dataWithJSONObject:@[value] options:NSJSONWritingWithoutEscapingSlashes error:NULL]; Require(array.length>=2);
        [out appendData:[array subdataWithRange:NSMakeRange(1,array.length-2)]];
    } else if([value isKindOfClass:NSNumber.class]) {
        NSString *number;
        if(CFGetTypeID((__bridge CFTypeRef)value)==CFBooleanGetTypeID()) number=[value boolValue]?@"true":@"false";
        else { Require(IntegerBetween(value,-4503599627370495LL,4503599627370495LL)); number=[NSString stringWithFormat:@"%lld",[value longLongValue]]; }
        [out appendData:[number dataUsingEncoding:NSUTF8StringEncoding]];
    } else { Require(value==NSNull.null); [out appendData:[@"null" dataUsingEncoding:NSUTF8StringEncoding]]; }
    return out;
}
static void ValidateCore(void) {
    NSDictionary *c=CoreEnvelope;
    Require(ExactKeys(c,@[@"schema_version",@"base_policy",@"public_key_base64",@"registry_dir",@"journal_dir",@"python_path",@"adapter_roots",@"dependency_roots",@"timeout_max_seconds"]));
    Require([c[@"schema_version"] isEqual:@"yokel.stable-core.v1"] && [c[@"base_policy"][@"jobs"] count]==0);
    Require(IntegerBetween(c[@"timeout_max_seconds"],1,1800));
    OwnerDirectory(c[@"registry_dir"]); OwnerDirectory(c[@"journal_dir"]); Require(![c[@"registry_dir"] isEqual:c[@"journal_dir"]]);
    Require(CanonicalPath(c[@"python_path"]));
    for(NSString *field in @[@"adapter_roots",@"dependency_roots"]) {
        NSArray *roots=c[field]; Require([roots isKindOfClass:NSArray.class] && roots.count>0 && roots.count<=16);
        for(NSString *root in roots) { struct stat st; Require(CanonicalPath(root) && stat(root.fileSystemRepresentation,&st)==0 && S_ISDIR(st.st_mode) && ![root isEqual:@"/"]); }
    }
    Require(WithinRoots(c[@"python_path"],c[@"dependency_roots"]));
    NSData *public=[[NSData alloc] initWithBase64EncodedString:c[@"public_key_base64"] options:0]; Require(public.length==65);
    NSDictionary *attrs=@{(__bridge id)kSecAttrKeyType:(__bridge id)kSecAttrKeyTypeECSECPrimeRandom,(__bridge id)kSecAttrKeyClass:(__bridge id)kSecAttrKeyClassPublic,(__bridge id)kSecAttrKeySizeInBits:@256};
    SecKeyRef key=SecKeyCreateWithData((__bridge CFDataRef)public,(__bridge CFDictionaryRef)attrs,NULL); Require(key!=NULL); CFRelease(key);
}
static NSDictionary *LoadJob(NSDictionary *base, NSString *job, NSString *expectedHash) {
    Require(Match(job,@"^[a-z][a-z0-9-]{0,63}$"));
    NSString *stem=[CoreEnvelope[@"registry_dir"] stringByAppendingPathComponent:job];
    NSData *raw=OwnerRead([stem stringByAppendingString:@".json"],4*1024*1024), *sig=OwnerRead([stem stringByAppendingString:@".sig"],128);
    NSString *digest=DataDigest(raw); if(expectedHash) Require(Match(expectedHash,@"^[a-f0-9]{64}$") && [digest isEqual:expectedHash]);
    NSData *pub=[[NSData alloc] initWithBase64EncodedString:CoreEnvelope[@"public_key_base64"] options:0];
    NSDictionary *attrs=@{(__bridge id)kSecAttrKeyType:(__bridge id)kSecAttrKeyTypeECSECPrimeRandom,(__bridge id)kSecAttrKeyClass:(__bridge id)kSecAttrKeyClassPublic,(__bridge id)kSecAttrKeySizeInBits:@256};
    SecKeyRef key=SecKeyCreateWithData((__bridge CFDataRef)pub,(__bridge CFDictionaryRef)attrs,NULL); Require(key!=NULL);
    static const char domain[]="yokel.research-job.v1\0";
    NSMutableData *message=[NSMutableData dataWithBytes:domain length:sizeof(domain)-1]; [message appendData:raw];
    BOOL verified=SecKeyVerifySignature(key,kSecKeyAlgorithmECDSASignatureMessageX962SHA256,(__bridge CFDataRef)message,(__bridge CFDataRef)sig,NULL); CFRelease(key); Require(verified);
    NSDictionary *m=[NSJSONSerialization JSONObjectWithData:raw options:0 error:NULL];
    Require(ExactKeys(m,@[@"schema_version",@"job_id",@"scope_id",@"project",@"expires_unix",@"provider_variables",@"job",@"budget",@"review"]));
    NSData *canonical=CanonicalJSON(m,0);
    Require([canonical isEqual:raw]);
    Require([m[@"schema_version"] isEqual:@"yokel.research-job.v1"] && [m[@"job_id"] isEqual:job] && [m[@"project"] isEqual:@"yokel.docketclock.research"]);
    Require(Match(m[@"scope_id"],@"^[a-z][a-z0-9-]{0,63}$"));
    long long now=(long long)[NSDate date].timeIntervalSince1970;
    Require(IntegerBetween(m[@"expires_unix"],now+1,now+7*24*3600));
    NSArray *variables=m[@"provider_variables"]; Require([variables isKindOfClass:NSArray.class] && variables.count>0 && variables.count<=2 && [NSSet setWithArray:variables].count==variables.count);
    NSMutableDictionary *refs=[NSMutableDictionary new]; for(NSString *name in variables) { Require([name isKindOfClass:NSString.class] && base[@"references"][name]!=nil); refs[name]=base[@"references"][name]; }
    NSDictionary *j=m[@"job"]; Require(ExactKeys(j,@[@"argv",@"files",@"timeout_seconds"]));
    NSArray *args=j[@"argv"]; Require([args isKindOfClass:NSArray.class] && args.count==6);
    Require([args[0] isEqual:CoreEnvelope[@"python_path"]] && [args[1] isEqual:@"-I"] && [args[2] isEqual:@"-S"] && [args[3] isEqual:@"-B"] && [args[5] isEqual:@"--live-initial"]);
    Require(WithinRoots(args[4],CoreEnvelope[@"adapter_roots"]) && [args[4] hasSuffix:@"/adapter.py"]);
    NSDictionary *files=j[@"files"]; Require([files isKindOfClass:NSDictionary.class] && files.count>0 && files.count<=10000 && files[args[0]] && files[args[4]]);
    for(NSString *path in files) Require(WithinRoots(path,CoreEnvelope[@"dependency_roots"]) && Match(files[path],@"^[a-f0-9]{64}$"));
    Require(IntegerBetween(j[@"timeout_seconds"],1,[CoreEnvelope[@"timeout_max_seconds"] longLongValue]));
    NSDictionary *budget=m[@"budget"]; Require(ExactKeys(budget,@[@"prior_nanousd",@"reservation_nanousd",@"ceiling_nanousd"]));
    // Exact-number safety limit, not a standing spending authorization. The signer
    // supplies the owner's ceiling per release, avoiding a rebuild for budget changes.
    long long safe=4503599627370495LL;
    Require(IntegerBetween(budget[@"prior_nanousd"],0,safe) && IntegerBetween(budget[@"reservation_nanousd"],0,safe) && IntegerBetween(budget[@"ceiling_nanousd"],1,safe));
    Require([budget[@"prior_nanousd"] longLongValue]+[budget[@"reservation_nanousd"] longLongValue]<=[budget[@"ceiling_nanousd"] longLongValue]);
    NSDictionary *review=m[@"review"]; Require(ExactKeys(review,@[@"path",@"sha256"]) && [files[review[@"path"]] isEqual:review[@"sha256"]]);
    NSMutableDictionary *p=[base mutableCopy]; p[@"references"]=refs; p[@"jobs"]=@{job:j}; ValidatePolicy(p);
    ManifestDigest=digest; return p;
}
static void ClaimJob(NSString *job) {
    NSString *path=[CoreEnvelope[@"journal_dir"] stringByAppendingPathComponent:job];
    int fd=open(path.fileSystemRepresentation,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600); Require(fd>=0);
    NSData *bytes=[ManifestDigest dataUsingEncoding:NSUTF8StringEncoding]; BOOL ok=write(fd,bytes.bytes,bytes.length)==bytes.length && fsync(fd)==0; close(fd); Require(ok);
    int dir=open([CoreEnvelope[@"journal_dir"] fileSystemRepresentation],O_RDONLY); Require(dir>=0); ok=fsync(dir)==0; close(dir); Require(ok);
}
