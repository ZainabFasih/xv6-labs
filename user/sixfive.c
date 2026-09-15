#include "kernel/types.h"
#include "user/user.h"

char buf[512];
char *seps = " -\r\t\n./,";

int
is_sep(char c)
{
  return strchr(seps, c) != 0;
}

void
sixfive(int fd)
{
  int n;
  long num = 0;
  int in_number = 0;
  int start_ok = 1;      // was this number's start bounded by a real separator?
  int prev_was_sep = 1;  // start of input counts as a separator

  while ((n = read(fd, buf, sizeof(buf))) > 0) {
    for (int i = 0; i < n; i++) {
      char c = buf[i];

      if (c >= '0' && c <= '9') {
        if (!in_number) {
          start_ok = prev_was_sep;
        }
        num = num * 10 + (c - '0');
        in_number = 1;
        prev_was_sep = 0;
      } else if (is_sep(c)) {
        if (in_number && start_ok) {
          if (num % 5 == 0 || num % 6 == 0) {
            printf("%ld\n", num);
          }
        }
        num = 0;
        in_number = 0;
        prev_was_sep = 1;
      } else {
        // some other character (like a letter) — breaks any number's validity
        num = 0;
        in_number = 0;
        prev_was_sep = 0;
      }
    }
  }

  // handle a number that ends right at end-of-file (EOF counts as a separator)
  if (in_number && start_ok) {
    if (num % 5 == 0 || num % 6 == 0) {
      printf("%ld\n", num);
    }
  }
}

int
main(int argc, char *argv[])
{
  int fd;

  if (argc <= 1) {
    sixfive(0);
  } else {
    for (int i = 1; i < argc; i++) {
      fd = open(argv[i], 0);
      if (fd < 0) {
        fprintf(2, "sixfive: cannot open %s\n", argv[i]);
        continue;
      }
      sixfive(fd);
      close(fd);
    }
  }

  exit(0);
}
