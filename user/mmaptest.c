// Tests for mmap / munmap (Exercise 9).
#include "kernel/types.h"
#include "kernel/fcntl.h"
#include "kernel/stat.h"
#include "user/user.h"

#define MAP_FAILED ((char*)0xffffffffffffffffL)
#define FSIZE 8192
char buf[FSIZE];
char *fname = "mmaptestfile";

static char expected(int i) { return 'A' + (i % 26); }

void
makefile(void)
{
  int fd = open(fname, O_CREATE | O_RDWR);
  if (fd < 0) { printf("makefile: open failed\n"); exit(1); }
  for (int i = 0; i < FSIZE; i++) buf[i] = expected(i);
  if (write(fd, buf, FSIZE) != FSIZE) { printf("makefile: write failed\n"); exit(1); }
  close(fd);
}

void
privateread(void)
{
  printf("private read:      ");
  int fd = open(fname, O_RDONLY);
  char *p = mmap(0, FSIZE, PROT_READ, MAP_PRIVATE, fd, 0);
  if (p == MAP_FAILED) { printf("mmap failed\n"); exit(1); }
  for (int i = 0; i < FSIZE; i++)
    if (p[i] != expected(i)) { printf("wrong byte at %d\n", i); exit(1); }
  if (munmap(p, FSIZE) != 0) { printf("munmap failed\n"); exit(1); }
  close(fd);
  printf("ok\n");
}

void
privatewrite(void)
{
  printf("private isolation: ");
  int fd = open(fname, O_RDWR);
  char *p = mmap(0, FSIZE, PROT_READ | PROT_WRITE, MAP_PRIVATE, fd, 0);
  if (p == MAP_FAILED) { printf("mmap failed\n"); exit(1); }
  for (int i = 0; i < FSIZE; i++) p[i] = 'z';
  munmap(p, FSIZE);
  close(fd);

  fd = open(fname, O_RDONLY);
  read(fd, buf, FSIZE);
  for (int i = 0; i < FSIZE; i++)
    if (buf[i] != expected(i)) { printf("file changed by private map at %d\n", i); exit(1); }
  close(fd);
  printf("ok\n");
}

void
sharedwrite(void)
{
  printf("shared write-back: ");
  int fd = open(fname, O_RDWR);
  char *p = mmap(0, FSIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (p == MAP_FAILED) { printf("mmap failed\n"); exit(1); }
  for (int i = 0; i < FSIZE; i++) p[i] = p[i] + 1;
  munmap(p, FSIZE);
  close(fd);

  fd = open(fname, O_RDONLY);
  read(fd, buf, FSIZE);
  for (int i = 0; i < FSIZE; i++)
    if (buf[i] != (char)(expected(i) + 1)) { printf("shared write lost at %d\n", i); exit(1); }
  close(fd);
  printf("ok\n");
}

void
exitclean(void)
{
  printf("unmap on exit:     ");
  int pid = fork();
  if (pid == 0) {
    int fd = open(fname, O_RDONLY);
    char *p = mmap(0, FSIZE, PROT_READ, MAP_PRIVATE, fd, 0);
    if (p == MAP_FAILED) exit(1);
    volatile char c = p[0] + p[4096];
    (void)c;
    exit(0);
  }
  int st; wait(&st);
  if (st != 0) { printf("child failed\n"); exit(1); }
  printf("ok\n");
}

int
main(void)
{
  makefile();
  privateread();
  privatewrite();
  sharedwrite();
  exitclean();
  printf("ALL MMAP TESTS PASSED\n");
  exit(0);
}
