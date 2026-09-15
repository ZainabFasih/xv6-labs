#include "kernel/types.h"
#include "user/user.h"
#include "kernel/fcntl.h"

void memdump(char *fmt, char *data, int len);

int
main(int argc, char *argv[])
{
  if (argc == 1) {
    printf("Example 1:\n");
    int a[2] = {61810, 2026};
    memdump("ii", (char *)a, sizeof(a));

    printf("Example 2:\n");
    memdump("S", "a string", sizeof("a string"));

    printf("Example 3:\n");
    char *s = "another";
    memdump("s", (char *)&s, sizeof(s));

    struct sss {
      char *ptr;
      int num1;
      short num2;
      char byte;
      char bytes[8];
    } example;

    example.ptr = "hello";
    example.num1 = 1819438967;
    example.num2 = 100;
    example.byte = 'z';
    strcpy(example.bytes, "xyzzy");

    printf("Example 4:\n");
    memdump("pihcS", (char *)&example, sizeof(example));

    printf("Example 5:\n");
    memdump("sccccc", (char *)&example, sizeof(example));
  } else if (argc == 2) {
    // format in argv[1], up to 512 bytes of data from standard input.
    char data[512];
    int n = 0;
    memset(data, '\0', sizeof(data));
    while (n < sizeof(data)) {
      int nn = read(0, data + n, sizeof(data) - n);
      if (nn <= 0)
        break;
      n += nn;
    }
    memdump(argv[1], data, n);
  } else {
    printf("Usage: memdump [format]\n");
    exit(1);
  }
  exit(0);
}

void
memdump(char *fmt, char *data, int len)
{
  int off = 0;

  for (int fi = 0; fmt[fi]; fi++) {
    char f = fmt[fi];
    int remaining = len - off;

    if (f == 'i') {
      if (remaining < 4) {
        printf("memdump: not enough data for 'i'\n");
        return;
      }
      int val;
      memmove(&val, data + off, 4);
      printf("%d\n", val);
      off += 4;

    } else if (f == 'p') {
      if (remaining < 8) {
        printf("memdump: not enough data for 'p'\n");
        return;
      }
      uint64 val;
      memmove(&val, data + off, 8);
      printf("%lx\n", val);
      off += 8;

    } else if (f == 'h') {
      if (remaining < 2) {
        printf("memdump: not enough data for 'h'\n");
        return;
      }
      short val;
      memmove(&val, data + off, 2);
      printf("%d\n", val);
      off += 2;

    } else if (f == 'c') {
      if (remaining < 1) {
        printf("memdump: not enough data for 'c'\n");
        return;
      }
      char val = data[off];
      printf("%c\n", val);
      off += 1;

    } else if (f == 's') {
      if (remaining < 8) {
        printf("memdump: not enough data for 's'\n");
        return;
      }
      char *ptr;
      memmove(&ptr, data + off, 8);
      printf("%s\n", ptr);
      off += 8;

    } else if (f == 'S') {
      int seg_len = 0;
      while (off + seg_len < len && data[off + seg_len] != 0) {
        seg_len++;
      }
      write(1, data + off, seg_len);
      write(1, "\n", 1);
      off = len;
    }
  }
}
