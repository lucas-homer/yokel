#include <stdlib.h>
#include <string.h>
extern char **environ;
int main(int argc,char **argv) {
    if(argc!=3 || strcmp(argv[1],"--fixture") || (strcmp(argv[2],"alpha") && strcmp(argv[2],"beta"))) return 1;
    int count=0; for(char **p=environ;*p;p++) count++;
    return !(count==3 && getenv("PATH") && getenv("LANG") && getenv("SYNTHETIC_PROVIDER") && !strcmp(getenv("SYNTHETIC_PROVIDER"),"fixture-value") && !getenv("OP_SERVICE_ACCOUNT_TOKEN") && !getenv("OPENROUTER_API_KEY") && !getenv("TYPESAFE_API_KEY"));
}
