#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"
#include "kernel/fs.h"
#include "kernel/fcntl.h"
#include "kernel/param.h"

char *
fmtname(char *path)
{
  char *p;

  for (p = path + strlen(path); p >= path && *p != '/'; p--)
    ;
  p++;
  return p;
}

void
run_exec(char **exec_argv, int exec_argc, char *matched_path)
{
  int pid;

  if ((pid = fork()) == 0) {
    char *argv2[MAXARG];
    int i;
    for (i = 0; i < exec_argc; i++) {
      argv2[i] = exec_argv[i];
    }
    argv2[i++] = matched_path;
    argv2[i] = 0;

    exec(argv2[0], argv2);
    fprintf(2, "find: exec %s failed\n", argv2[0]);
    exit(1);
  } else {
    wait(0);
  }
}

void
find(char *path, char *target, char **exec_argv, int exec_argc)
{
  char buf[512], *p;
  int fd;
  struct dirent de;
  struct stat st;

  if ((fd = open(path, O_RDONLY)) < 0) {
    fprintf(2, "find: cannot open %s\n", path);
    return;
  }

  if (fstat(fd, &st) < 0) {
    fprintf(2, "find: cannot stat %s\n", path);
    close(fd);
    return;
  }

  switch (st.type) {
  case T_FILE:
    if (strcmp(fmtname(path), target) == 0) {
      if (exec_argc > 0) {
        run_exec(exec_argv, exec_argc, path);
      } else {
        printf("%s\n", path);
      }
    }
    break;

  case T_DIR:
    if (strlen(path) + 1 + DIRSIZ + 1 > sizeof buf) {
      printf("find: path too long\n");
      break;
    }
    strcpy(buf, path);
    p = buf + strlen(buf);
    *p++ = '/';
    while (read(fd, &de, sizeof(de)) == sizeof(de)) {
      if (de.inum == 0)
        continue;
      if (strcmp(de.name, ".") == 0 || strcmp(de.name, "..") == 0)
        continue;

      memmove(p, de.name, DIRSIZ);
      p[DIRSIZ] = 0;

      if (stat(buf, &st) < 0) {
        printf("find: cannot stat %s\n", buf);
        continue;
      }

      if (strcmp(de.name, target) == 0) {
        if (exec_argc > 0) {
          run_exec(exec_argv, exec_argc, buf);
        } else {
          printf("%s\n", buf);
        }
      }

      if (st.type == T_DIR) {
        find(buf, target, exec_argv, exec_argc);
      }
    }
    break;
  }
  close(fd);
}

int
main(int argc, char *argv[])
{
  char **exec_argv = 0;
  int exec_argc = 0;

  if (argc < 3) {
    fprintf(2, "Usage: find <path> <name> [-exec cmd ...]\n");
    exit(1);
  }

  // check for -exec starting at argv[3]
  if (argc > 3) {
    if (strcmp(argv[3], "-exec") == 0) {
      exec_argv = &argv[4];
      exec_argc = argc - 4;
      if (exec_argc <= 0) {
        fprintf(2, "Usage: find <path> <name> -exec cmd ...\n");
        exit(1);
      }
    }
  }

  find(argv[1], argv[2], exec_argv, exec_argc);

  exit(0);
}
