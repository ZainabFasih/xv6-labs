// Exercise 7: grow the address space by one byte and inspect the page table
// before and after, for BOTH eager (sbrk) and lazy (sbrklazy) allocation.
#include "kernel/types.h"
#include "kernel/riscv.h"
#include "user/user.h"

static void
show_flags(uint64 pte)
{
  printf("    flags: V=%d R=%d W=%d X=%d U=%d\n",
         (pte & PTE_V) ? 1 : 0, (pte & PTE_R) ? 1 : 0,
         (pte & PTE_W) ? 1 : 0, (pte & PTE_X) ? 1 : 0,
         (pte & PTE_U) ? 1 : 0);
}

int
main(void)
{
  printf("PGSIZE = %d bytes\n\n", PGSIZE);

  printf("=== EAGER: sbrk(1) ===\n");
  char *a = sbrk(0);
  printf("break before      : %p\n", a);
  printf("PTE before sbrk   : 0x%lx\n", pgpte(a));
  char *p = sbrk(1);
  printf("sbrk(1) returned  : %p  (old break)\n", p);
  printf("break after       : %p\n", sbrk(0));
  uint64 pte = pgpte(p);
  printf("PTE after sbrk    : 0x%lx  (eager => already mapped)\n", pte);
  show_flags(pte);

  printf("\n=== LAZY: sbrklazy(1) ===\n");
  char *q = sbrklazy(1);
  printf("sbrklazy(1) ret   : %p  (old break)\n", q);
  printf("break after       : %p\n", sbrk(0));
  pte = pgpte(q);
  printf("PTE before touch  : 0x%lx  (lazy => expect 0, no page yet)\n", pte);
  *q = 'z';
  printf("wrote '%c' to new byte\n", *q);
  pte = pgpte(q);
  printf("PTE after touch   : 0x%lx  (now mapped by vmfault)\n", pte);
  show_flags(pte);

  exit(0);
}
