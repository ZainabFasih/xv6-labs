#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"
#include "kernel/riscv.h"

int
main(int argc, char *argv[])
{
  char *marker = "Here it is: ";
  int mlen = strlen(marker);

  for(int i = 0; i < 256; i++){
    char *pg = sbrk(PGSIZE);
    if(pg == (char*)-1)
      break;
    for(char *p = pg; p + mlen < pg + PGSIZE; p++){
      if(memcmp(p, marker, mlen) == 0){
        char *secret = p + mlen;
        int len = strlen(secret);
        if(len > 0){
          write(1, secret, len);
          write(1, "\n", 1);
          exit(0);
        }
      }
    }
  }
  exit(1);
}
