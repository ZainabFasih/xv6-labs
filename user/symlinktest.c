#include "kernel/types.h"
#include "kernel/stat.h"
#include "kernel/fs.h"
#include "kernel/fcntl.h"
#include "user/user.h"

#define fail(m) do { printf("FAILED: %s at %s:%d\n", m, __FILE__, __LINE__); exit(1); } while(0)

char buf[128];

static void
cleanup(void)
{
  unlink("/testsymlink/a");
  unlink("/testsymlink/b");
  unlink("/testsymlink/c");
  unlink("/testsymlink/1");
  unlink("/testsymlink/2");
  unlink("/testsymlink/3");
  unlink("/testsymlink");
}

static void
testsymlinks(void)
{
  int fd, r;
  printf("Start: test symlinks\n");
  cleanup();
  if(mkdir("/testsymlink") < 0)
    fail("mkdir failed");

  fd = open("/testsymlink/a", O_CREATE | O_RDWR);
  if(fd < 0)
    fail("open a");
  if(write(fd, "hello", 5) != 5)
    fail("write a");
  close(fd);

  if(symlink("/testsymlink/a", "/testsymlink/b") < 0)
    fail("symlink b");
  if(symlink("/testsymlink/b", "/testsymlink/c") < 0)
    fail("symlink c");

  fd = open("/testsymlink/c", O_RDONLY);
  if(fd < 0)
    fail("open c");
  memset(buf, 0, sizeof(buf));
  r = read(fd, buf, sizeof(buf));
  if(r != 5 || strcmp(buf, "hello") != 0)
    fail("chained symlink data");
  close(fd);

  fd = open("/testsymlink/b", O_RDONLY | O_NOFOLLOW);
  if(fd < 0)
    fail("open nofollow");
  memset(buf, 0, sizeof(buf));
  r = read(fd, buf, sizeof(buf));
  if(r != (int)strlen("/testsymlink/a") || strcmp(buf, "/testsymlink/a") != 0)
    fail("nofollow content");
  close(fd);

  if(symlink("/testsymlink/nosuch", "/testsymlink/1") < 0)
    fail("symlink 1");
  if(open("/testsymlink/1", O_RDONLY) >= 0)
    fail("dangling should fail");

  if(symlink("/testsymlink/3", "/testsymlink/2") < 0)
    fail("symlink 2");
  if(symlink("/testsymlink/2", "/testsymlink/3") < 0)
    fail("symlink 3");
  if(open("/testsymlink/2", O_RDONLY) >= 0)
    fail("cycle should fail");

  cleanup();
  printf("test symlinks: ok\n");
}

static void
testconcurrent(void)
{
  int i, pid, n;
  printf("Start: test concurrent symlinks\n");
  cleanup();
  if(mkdir("/testsymlink") < 0)
    fail("mkdir failed");
  int fd = open("/testsymlink/a", O_CREATE | O_RDWR);
  if(fd < 0)
    fail("open a");
  write(fd, "x", 1);
  close(fd);

  for(n = 0; n < 4; n++){
    pid = fork();
    if(pid < 0)
      fail("fork");
    if(pid == 0){
      for(i = 0; i < 50; i++){
        char lp[32];
        strcpy(lp, "/testsymlink/l0");
        lp[14] = '0' + n;
        symlink("/testsymlink/a", lp);
        int f = open(lp, O_RDONLY);
        if(f >= 0)
          close(f);
        unlink(lp);
      }
      exit(0);
    }
  }
  for(n = 0; n < 4; n++)
    wait(0);

  cleanup();
  printf("test concurrent symlinks: ok\n");
}

int
main(void)
{
  testsymlinks();
  testconcurrent();
  exit(0);
}
