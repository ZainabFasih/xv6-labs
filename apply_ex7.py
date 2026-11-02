#!/usr/bin/env python3
# Applies Exercise 7: pgpte() syscall + sbrktest user program. Idempotent.
import re, os, sys

def read(p):
    with open(p) as f: return f.read()
def write(p, c):
    with open(p, 'w') as f: f.write(c)

for need in ['kernel/syscall.h','kernel/syscall.c','kernel/sysproc.c',
             'user/user.h','user/usys.pl','Makefile']:
    if not os.path.exists(need):
        print(f"[ERROR] {need} not found. Run this from your xv6 repo root."); sys.exit(1)

h = read('kernel/syscall.h')
if 'SYS_pgpte' in h:
    print("[SKIP] syscall.h already has SYS_pgpte")
else:
    nums = [int(n) for n in re.findall(r'#define\s+SYS_\w+\s+(\d+)', h)]
    nxt = max(nums) + 1
    h = h.rstrip('\n') + f'\n#define SYS_pgpte  {nxt}\n'
    write('kernel/syscall.h', h)
    print(f"[ OK ] syscall.h: SYS_pgpte = {nxt}")

c = read('kernel/syscall.c')
changed = False
if 'sys_pgpte' not in c:
    ext = list(re.finditer(r'extern uint64 sys_\w+\(void\);\n', c))
    i = ext[-1].end()
    c = c[:i] + 'extern uint64 sys_pgpte(void);\n' + c[i:]
    arr = list(re.finditer(r'\[SYS_\w+\]\s*=\s*sys_\w+,\n', c))
    j = arr[-1].end()
    c = c[:j] + '  [SYS_pgpte]   = sys_pgpte,\n' + c[j:]
    write('kernel/syscall.c', c); changed = True
print("[ OK ] syscall.c: extern + table entry" if changed else "[SKIP] syscall.c already has sys_pgpte")

sp = read('kernel/sysproc.c')
if 'sys_pgpte' in sp:
    print("[SKIP] sysproc.c already has sys_pgpte")
else:
    sp = sp.rstrip('\n') + '''

uint64
sys_pgpte(void)
{
  uint64 va;
  argaddr(0, &va);

  struct proc *p = myproc();
  pte_t *pte = walk(p->pagetable, va, 0);
  if(pte == 0)
    return 0;
  return (uint64) *pte;
}
'''
    write('kernel/sysproc.c', sp)
    print("[ OK ] sysproc.c: added sys_pgpte")

u = read('user/user.h')
if 'pgpte' in u:
    print("[SKIP] user.h already declares pgpte")
else:
    if 'char *sbrklazy(int);' in u:
        u = u.replace('char *sbrklazy(int);',
                      'char *sbrklazy(int);\nuint64 pgpte(void *va);', 1)
    else:
        u = u.replace('char *sbrk(int);',
                      'char *sbrk(int);\nuint64 pgpte(void *va);', 1)
    write('user/user.h', u)
    print("[ OK ] user.h: declared pgpte")

pl = read('user/usys.pl')
if 'pgpte' in pl:
    print("[SKIP] usys.pl already has pgpte")
else:
    pl = pl.rstrip('\n') + '\nentry("pgpte");\n'
    write('user/usys.pl', pl)
    print("[ OK ] usys.pl: added entry")

mk = read('Makefile')
if '_sbrktest' in mk:
    print("[SKIP] Makefile already has _sbrktest")
else:
    m = re.search(r'\n(\t\$U/_cat\\\n)', mk)
    if m:
        mk = mk[:m.end()] + '\t$U/_sbrktest\\\n' + mk[m.end():]
    else:
        mk = re.sub(r'(UPROGS=\\\n)', r'\1\t$U/_sbrktest\\\n', mk, count=1)
    write('Makefile', mk)
    print("[ OK ] Makefile: added $U/_sbrktest")

SBRKTEST = r'''// Exercise 7: grow the address space by one byte and inspect the page table
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
'''
write('user/sbrktest.c', SBRKTEST)
print("[ OK ] wrote user/sbrktest.c")
print("\nDone. Now run:  make clean && make qemu   then at the prompt:  sbrktest")
