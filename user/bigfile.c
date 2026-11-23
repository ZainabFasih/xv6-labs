#include "kernel/types.h"
#include "kernel/fs.h"
#include "kernel/stat.h"
#include "kernel/fcntl.h"
#include "user/user.h"
int main(){
  char buf[BSIZE]; int fd, blocks;
  fd = open("big.file", O_CREATE | O_WRONLY);
  if(fd < 0){ printf("bigfile: cannot open big.file for writing\n"); exit(1); }
  blocks = 0;
  while(1){
    *(int*)buf = blocks;
    int cc = write(fd, buf, sizeof(buf));
    if(cc <= 0) break;
    blocks++;
    if(blocks % 100 == 0) printf(".");
  }
  printf("\n"); printf("wrote %d blocks\n", blocks);
  if(blocks != 65803){ printf("bigfile: file is too small\n"); exit(1); }
  close(fd);
  fd = open("big.file", O_RDONLY);
  if(fd < 0){ printf("bigfile: cannot re-open big.file for reading\n"); exit(1); }
  blocks = 0;
  while(1){
    int cc = read(fd, buf, sizeof(buf));
    if(cc <= 0) break;
    if(*(int*)buf != blocks){ printf("bigfile: wrong data (%d) block %d\n", *(int*)buf, blocks); exit(1); }
    blocks++;
  }
  close(fd); printf("done; ok\n"); exit(0);
}
