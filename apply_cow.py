#!/usr/bin/env python3
# Copy-on-write fork for xv6. Idempotent.
import os, sys, re

def read(p):
    with open(p) as f: return f.read()
def write(p, c):
    with open(p, 'w') as f: f.write(c)
def need(p):
    if not os.path.exists(p):
        print(f"[ERROR] {p} not found. Run from your xv6 repo root."); sys.exit(1)

for f in ['kernel/riscv.h','kernel/kalloc.c','kernel/vm.c','kernel/trap.c',
          'kernel/defs.h','Makefile']:
    need(f)

def patch(path, anchor, replacement, tag, skip_if=None):
    c = read(path)
    if skip_if and skip_if in c:
        print(f"[SKIP] {path}: {tag} already applied"); return
    if anchor not in c:
        print(f"[WARN] {path}: anchor for '{tag}' NOT found -- tell Claude"); return
    if c.count(anchor) != 1:
        print(f"[WARN] {path}: anchor for '{tag}' x{c.count(anchor)} (need 1) -- tell Claude"); return
    write(path, c.replace(anchor, replacement, 1))
    print(f"[ OK ] {path}: {tag}")

patch('kernel/riscv.h',
      "#define PTE_U (1L << 4) // user can access",
      "#define PTE_U (1L << 4) // user can access\n#define PTE_COW (1L << 8) // copy-on-write page",
      "add PTE_COW", skip_if="PTE_COW")

patch('kernel/kalloc.c',
      "struct {\n  struct spinlock lock;\n  struct run *freelist;\n} kmem;",
      "struct {\n  struct spinlock lock;\n  struct run *freelist;\n} kmem;\n"
      "\n#define PA2IDX(pa) (((uint64)(pa) - KERNBASE) / PGSIZE)\n"
      "#define NPAGES     ((PHYSTOP - KERNBASE) / PGSIZE)\n"
      "\nstruct {\n  struct spinlock lock;\n  int count[NPAGES];\n} kref;\n"
      "\nvoid\nkincref(void *pa)\n{\n"
      "  acquire(&kref.lock);\n  kref.count[PA2IDX(pa)]++;\n  release(&kref.lock);\n}",
      "add refcount table + kincref", skip_if="kref")

patch('kernel/kalloc.c',
      '  initlock(&kmem.lock, "kmem");\n  freerange(end, (void *)PHYSTOP);',
      '  initlock(&kmem.lock, "kmem");\n  initlock(&kref.lock, "kref");\n  freerange(end, (void *)PHYSTOP);',
      "init kref lock", skip_if='initlock(&kref.lock')

patch('kernel/kalloc.c',
      "  p = (char *)PGROUNDUP((uint64)pa_start);\n"
      "  for (; p + PGSIZE <= (char *)pa_end; p += PGSIZE)\n    kfree(p);",
      "  p = (char *)PGROUNDUP((uint64)pa_start);\n"
      "  for (; p + PGSIZE <= (char *)pa_end; p += PGSIZE) {\n"
      "    kref.count[PA2IDX(p)] = 1;\n    kfree(p);\n  }",
      "freerange sets refcount", skip_if="kref.count[PA2IDX(p)] = 1")

patch('kernel/kalloc.c',
      '    panic("kfree");\n\n  // Fill with junk to catch dangling refs.',
      '    panic("kfree");\n\n'
      '  acquire(&kref.lock);\n'
      '  if (--kref.count[PA2IDX(pa)] > 0) {\n'
      '    release(&kref.lock);\n    return;\n  }\n'
      '  release(&kref.lock);\n\n'
      '  // Fill with junk to catch dangling refs.',
      "kfree decrements refcount", skip_if="--kref.count[PA2IDX(pa)]")

patch('kernel/kalloc.c',
      "  if (r)\n    memset((char *)r, 5, PGSIZE); // fill with junk\n  return (void *)r;",
      "  if (r) {\n    acquire(&kref.lock);\n    kref.count[PA2IDX(r)] = 1;\n"
      "    release(&kref.lock);\n    memset((char *)r, 5, PGSIZE); // fill with junk\n  }\n"
      "  return (void *)r;",
      "kalloc sets refcount=1", skip_if="kref.count[PA2IDX(r)] = 1")

patch('kernel/vm.c', "  uint flags;\n  char *mem;\n", "  uint flags;\n",
      "uvmcopy: drop unused mem var", skip_if="// copy-on-write: share")

patch('kernel/vm.c',
      "    pa = PTE2PA(*pte);\n    flags = PTE_FLAGS(*pte);\n"
      "    if ((mem = kalloc()) == 0)\n      goto err;\n"
      "    memmove(mem, (char *)pa, PGSIZE);\n"
      "    if (mappages(new, i, PGSIZE, (uint64)mem, flags) != 0) {\n"
      "      kfree(mem);\n      goto err;\n    }",
      "    pa = PTE2PA(*pte);\n    // copy-on-write: share the page read-only instead of copying.\n"
      "    if (*pte & PTE_W)\n      *pte = (*pte & ~PTE_W) | PTE_COW;\n"
      "    flags = PTE_FLAGS(*pte);\n"
      "    if (mappages(new, i, PGSIZE, pa, flags) != 0) {\n      goto err;\n    }\n"
      "    kincref((void *)pa);",
      "uvmcopy shares pages COW", skip_if="// copy-on-write: share")

patch('kernel/vm.c',
      "    pte = walk(pagetable, va0, 0);\n"
      "    // forbid copyout over read-only user text pages.\n"
      "    if ((*pte & PTE_W) == 0)\n      return -1;",
      "    pte = walk(pagetable, va0, 0);\n"
      "    // forbid copyout over read-only text; copy-on-write otherwise.\n"
      "    if ((*pte & PTE_W) == 0) {\n      if (*pte & PTE_COW) {\n"
      "        if (cowfault(pagetable, va0) != 0)\n          return -1;\n"
      "        pa0 = walkaddr(pagetable, va0);\n      } else {\n        return -1;\n      }\n    }",
      "copyout handles COW", skip_if="if (*pte & PTE_COW) {")

vmc = read('kernel/vm.c')
if 'cowfault(pagetable_t' in vmc:
    print("[SKIP] vm.c: cowfault already present")
else:
    vmc = vmc.rstrip('\n') + '''

// Handle a store page fault that may be on a copy-on-write page.
int
cowfault(pagetable_t pagetable, uint64 va)
{
  pte_t *pte;
  uint64 pa, new;
  uint flags;

  if (va >= MAXVA)
    return -1;
  va = PGROUNDDOWN(va);
  pte = walk(pagetable, va, 0);
  if (pte == 0 || (*pte & PTE_V) == 0 || (*pte & PTE_U) == 0)
    return -1;
  if ((*pte & PTE_COW) == 0)
    return -1;

  pa = PTE2PA(*pte);
  flags = (PTE_FLAGS(*pte) & ~PTE_COW) | PTE_W;

  if ((new = (uint64)kalloc()) == 0)
    return -1;
  memmove((void *)new, (void *)pa, PGSIZE);
  *pte = PA2PTE(new) | flags;
  kfree((void *)pa);
  sfence_vma();
  return 0;
}
'''
    write('kernel/vm.c', vmc)
    print("[ OK ] vm.c: added cowfault")

patch('kernel/trap.c',
      "  } else if ((r_scause() == 15 || r_scause() == 13) &&\n"
      "             vmfault(p->pagetable, p->sz, r_stval(),\n"
      "                     (r_scause() == 13) ? 1 : 0) != 0) {",
      "  } else if (r_scause() == 15 &&\n"
      "             cowfault(p->pagetable, r_stval()) == 0) {\n"
      "    // copy-on-write page fault handled\n"
      "  } else if ((r_scause() == 15 || r_scause() == 13) &&\n"
      "             vmfault(p->pagetable, p->sz, r_stval(),\n"
      "                     (r_scause() == 13) ? 1 : 0) != 0) {",
      "usertrap tries cowfault", skip_if="cowfault(p->pagetable, r_stval())")

patch('kernel/defs.h',
      "void            kfree(void *);",
      "void            kfree(void *);\nvoid            kincref(void *);",
      "declare kincref", skip_if="kincref")

patch('kernel/defs.h',
      "int             uvmcopy(pagetable_t, pagetable_t, uint64);",
      "int             uvmcopy(pagetable_t, pagetable_t, uint64);\nint             cowfault(pagetable_t, uint64);",
      "declare cowfault", skip_if="cowfault")

print("\nCOW patches done.")
