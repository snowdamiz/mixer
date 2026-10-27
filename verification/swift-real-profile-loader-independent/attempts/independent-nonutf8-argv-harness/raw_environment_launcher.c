#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
/* Reviewer-owned trusted launcher. execve replaces this same direct child. */
int main(int argc, char **argv) {
  if (argc < 4) return 2;
  FILE *file=fopen(argv[1],"rb"); if (!file) return 3;
  static char raw[65537]; size_t n=fread(raw,1,65536,file);
  int failed=ferror(file); int extra=fgetc(file); fclose(file);
  if (failed || extra!=EOF || n==0 || raw[n-1]!=0) return 4;
  char *items[129];size_t count=0,at=0;
  while (at<n) {
    if(count>=128) return 5;
    items[count++]=raw+at;
    char *end=memchr(raw+at,0,n-at);if(!end)return 6;
    at=(size_t)(end-raw)+1;
  }
  items[count]=0;
  execve(argv[2],argv+2,items);
  return 7;
}
