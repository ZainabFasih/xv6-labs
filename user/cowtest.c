// Tests for copy-on-write fork (Exercise 8).
#include "kernel/types.h"
#include "kernel/memlayout.h"
#include "user/user.h"

#define FAILED ((char*)0xffffffffffffffffL)

void
simpletest()
{
  uint64 phys = PHYSTOP - KERNBASE;
  int sz = (phys / 3) * 2;

  printf("simple:    ");
  char *p = sbrk(sz);
  if (p == FAILED) { printf("sbrk failed\n"); exit(-1); }
  for (char *q = p; q < p + sz; q += 4096)
    *(int*)q = getpid();

  int pid = fork();
  if (pid < 0) { printf("fork failed (COW not sharing?)\n"); exit(-1); }
  if (pid == 0)
    exit(0);

  int st; wait(&st);
  for (char *q = p; q < p + sz; q += 4096)
    if (*(int*)q != getpid()) { printf("parent data changed!\n"); exit(-1); }

  if (sbrk(-sz) == FAILED) { printf("sbrk(-) failed\n"); exit(-1); }
  printf("ok\n");
}

void
isolationtest()
{
  int sz = 4 * 1024 * 1024;

  printf("isolation: ");
  char *p = sbrk(sz);
  if (p == FAILED) { printf("sbrk failed\n"); exit(-1); }
  for (char *q = p; q < p + sz; q += 4096)
    *(int*)q = 1;

  int pid = fork();
  if (pid < 0) { printf("fork failed\n"); exit(-1); }
  if (pid == 0) {
    for (char *q = p; q < p + sz; q += 4096)
      *(int*)q = 2;
    for (char *q = p; q < p + sz; q += 4096)
      if (*(int*)q != 2) { printf("child sees wrong value\n"); exit(-1); }
    exit(0);
  }

  int st; wait(&st);
  if (st != 0) { printf("child failed\n"); exit(-1); }
  for (char *q = p; q < p + sz; q += 4096)
    if (*(int*)q != 1) { printf("parent corrupted by child!\n"); exit(-1); }

  if (sbrk(-sz) == FAILED) { printf("sbrk(-) failed\n"); exit(-1); }
  printf("ok\n");
}

void
freetest()
{
  int sz = 4 * 1024 * 1024;

  printf("free:      ");
  for (int i = 0; i < 20; i++) {
    char *p = sbrk(sz);
    if (p == FAILED) { printf("iter %d: sbrk failed (leak?)\n", i); exit(-1); }
    for (char *q = p; q < p + sz; q += 4096)
      *(int*)q = i;

    int pid = fork();
    if (pid < 0) { printf("fork failed\n"); exit(-1); }
    if (pid == 0) {
      for (char *q = p; q < p + sz; q += 4096)
        *(int*)q = 0xbeef;
      exit(0);
    }
    wait(0);
    if (sbrk(-sz) == FAILED) { printf("sbrk(-) failed\n"); exit(-1); }
  }
  printf("ok\n");
}

int
main(void)
{
  simpletest();
  isolationtest();
  freetest();
  printf("ALL COW TESTS PASSED\n");
  exit(0);
}
