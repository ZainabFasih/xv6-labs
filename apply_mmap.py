#!/usr/bin/env python3
# Implements Exercise 9: mmap / munmap. Idempotent.
import os, sys, re

def read(p):
    with open(p) as f: return f.read()
def write(p, c):
    with open(p, 'w') as f: f.write(c)
def need(p):
    if not os.path.exists(p):
        print(f"[ERROR] {p} not found. Run from your xv6 repo root."); sys.exit(1)

for f in ['kernel/fcntl.h','kernel/param.h','kernel/proc.h','kernel/proc.c',
          'kernel/trap.c','kernel/defs.h','kernel/sysfile.c','kernel/syscall.h',
          'kernel/syscall.c','user/user.h','user/usys.pl']:
    need(f)

def patch(path, anchor, repl, tag, skip_if=None):
    c = read(path)
    if skip_if and skip_if in c:
        print(f"[SKIP] {path}: {tag} already applied"); return
    if anchor not in c:
        print(f"[WARN] {path}: anchor for '{tag}' NOT found -- tell Claude"); return
    if c.count(anchor) != 1:
        print(f"[WARN] {path}: anchor for '{tag}' x{c.count(anchor)} (need 1) -- tell Claude"); return
    write(path, c.replace(anchor, repl, 1)); print(f"[ OK ] {path}: {tag}")

fc = read('kernel/fcntl.h')
if 'PROT_READ' in fc:
    print("[SKIP] fcntl.h already has PROT/MAP")
else:
    write('kernel/fcntl.h', fc.rstrip('\n') + '\n\n'
          '#define PROT_NONE  0x0\n'
          '#define PROT_READ  0x1\n'
          '#define PROT_WRITE 0x2\n'
          '#define PROT_EXEC  0x4\n\n'
          '#define MAP_SHARED  0x01\n'
          '#define MAP_PRIVATE 0x02\n')
    print("[ OK ] fcntl.h: added PROT_/MAP_")

pm = read('kernel/param.h')
if 'NVMA' in pm:
    print("[SKIP] param.h already has NVMA")
else:
    write('kernel/param.h', pm.rstrip('\n') + '\n#define NVMA        16                // max mmap regions per process\n')
    print("[ OK ] param.h: added NVMA")

patch('kernel/sysfile.c', '#include "fcntl.h"',
      '#include "fcntl.h"\n#include "memlayout.h"',
      "include memlayout.h", skip_if='memlayout.h')

patch('kernel/proc.h',
      "struct proc {\n  struct spinlock lock;",
      "struct vma {\n"
      "  int used;             // is this slot in use?\n"
      "  uint64 addr;          // start virtual address\n"
      "  uint64 length;        // length in bytes (as requested)\n"
      "  int prot;             // PROT_READ / PROT_WRITE / ...\n"
      "  int flags;            // MAP_SHARED / MAP_PRIVATE\n"
      "  int offset;           // file offset\n"
      "  struct file *file;    // the mapped file\n"
      "};\n\n"
      "struct proc {\n  struct spinlock lock;",
      "add struct vma", skip_if="struct vma {")

patch('kernel/proc.h',
      "  struct trapframe alarm_tf;   // saved regs for sigreturn\n};",
      "  struct trapframe alarm_tf;   // saved regs for sigreturn\n"
      "  struct vma vmas[NVMA];       // mmap regions\n};",
      "add vmas[] to struct proc", skip_if="struct vma vmas[NVMA]")

patch('kernel/proc.c',
      "  p->alarm_ticks = 0;\n  p->alarm_on = 0;\n\n  return p;",
      "  p->alarm_ticks = 0;\n  p->alarm_on = 0;\n\n"
      "  for (int vi = 0; vi < NVMA; vi++)\n    p->vmas[vi].used = 0;\n\n  return p;",
      "allocproc inits vmas", skip_if="p->vmas[vi].used = 0")

patch('kernel/proc.c',
      "      np->ofile[i] = filedup(p->ofile[i]);\n  np->cwd = idup(p->cwd);",
      "      np->ofile[i] = filedup(p->ofile[i]);\n\n"
      "  for (i = 0; i < NVMA; i++) {\n"
      "    if (p->vmas[i].used) {\n"
      "      np->vmas[i] = p->vmas[i];\n"
      "      filedup(p->vmas[i].file);\n"
      "    }\n"
      "  }\n\n"
      "  np->cwd = idup(p->cwd);",
      "kfork copies vmas", skip_if="np->vmas[i] = p->vmas[i]")

patch('kernel/proc.c',
      "  // Close all open files.\n  for (int fd = 0; fd < NOFILE; fd++) {",
      "  // Unmap and write back any mmap regions.\n"
      "  for (int vi = 0; vi < NVMA; vi++) {\n"
      "    struct vma *v = &p->vmas[vi];\n"
      "    if (v->used) {\n"
      "      vmaunmap(p->pagetable, v, v->addr, v->length);\n"
      "      fileclose(v->file);\n"
      "      v->used = 0;\n"
      "    }\n"
      "  }\n\n"
      "  // Close all open files.\n  for (int fd = 0; fd < NOFILE; fd++) {",
      "kexit unmaps vmas", skip_if="vmaunmap(p->pagetable, v, v->addr")

patch('kernel/defs.h', "struct superblock;",
      "struct superblock;\nstruct vma;",
      "forward-declare struct vma", skip_if="struct vma;")
patch('kernel/defs.h',
      "int             uvmcopy(pagetable_t, pagetable_t, uint64);",
      "int             uvmcopy(pagetable_t, pagetable_t, uint64);\n"
      "int             mmapfault(struct proc*, uint64);\n"
      "void            vmaunmap(pagetable_t, struct vma*, uint64, uint64);",
      "declare mmapfault/vmaunmap", skip_if="mmapfault")

patch('kernel/trap.c',
      "                     (r_scause() == 13) ? 1 : 0) != 0) {\n"
      "    // page fault on lazily-allocated page\n"
      "  } else {",
      "                     (r_scause() == 13) ? 1 : 0) != 0) {\n"
      "    // page fault on lazily-allocated page\n"
      "  } else if ((r_scause() == 15 || r_scause() == 13) &&\n"
      "             mmapfault(p, r_stval()) == 0) {\n"
      "    // mmap page fault handled\n"
      "  } else {",
      "usertrap tries mmapfault", skip_if="mmapfault(p, r_stval())")

sf = read('kernel/sysfile.c')
if 'sys_mmap' in sf:
    print("[SKIP] sysfile.c already has sys_mmap")
else:
    sf = sf.rstrip('\n') + r'''

// ---------------- mmap / munmap ----------------

int
mmapfault(struct proc *p, uint64 va)
{
  struct vma *v = 0;
  for (int i = 0; i < NVMA; i++) {
    struct vma *t = &p->vmas[i];
    if (t->used && va >= t->addr && va < t->addr + PGROUNDUP(t->length)) {
      v = t;
      break;
    }
  }
  if (v == 0)
    return -1;

  va = PGROUNDDOWN(va);
  char *mem = kalloc();
  if (mem == 0)
    return -1;
  memset(mem, 0, PGSIZE);

  uint64 off = v->offset + (va - v->addr);
  ilock(v->file->ip);
  readi(v->file->ip, 0, (uint64)mem, off, PGSIZE);
  iunlock(v->file->ip);

  int perm = PTE_U;
  if (v->prot & PROT_READ)
    perm |= PTE_R;
  if (v->prot & PROT_WRITE)
    perm |= PTE_W;
  if (v->prot & PROT_EXEC)
    perm |= PTE_X;

  if (mappages(p->pagetable, va, PGSIZE, (uint64)mem, perm) != 0) {
    kfree(mem);
    return -1;
  }
  return 0;
}

void
vmaunmap(pagetable_t pagetable, struct vma *v, uint64 addr, uint64 length)
{
  uint64 a;
  for (a = PGROUNDDOWN(addr); a < addr + length; a += PGSIZE) {
    pte_t *pte = walk(pagetable, a, 0);
    if (pte == 0 || (*pte & PTE_V) == 0)
      continue;
    if ((v->flags & MAP_SHARED) && (v->prot & PROT_WRITE)) {
      uint64 pa = PTE2PA(*pte);
      uint64 foff = v->offset + (a - v->addr);
      int n = PGSIZE;
      if ((a - v->addr) + PGSIZE > v->length)
        n = v->length - (a - v->addr);
      if (n > 0) {
        begin_op();
        ilock(v->file->ip);
        writei(v->file->ip, 0, pa, foff, n);
        iunlock(v->file->ip);
        end_op();
      }
    }
    kfree((void *)PTE2PA(*pte));
    *pte = 0;
  }
}

uint64
sys_mmap(void)
{
  uint64 addr, offset;
  int length, prot, flags, fd;
  struct file *f;
  struct proc *p = myproc();

  argaddr(0, &addr);
  argint(1, &length);
  argint(2, &prot);
  argint(3, &flags);
  argint(4, &fd);
  argaddr(5, &offset);

  if (length <= 0)
    return -1;
  if (fd < 0 || fd >= NOFILE || (f = p->ofile[fd]) == 0)
    return -1;
  if ((prot & PROT_READ) && !f->readable)
    return -1;
  if ((prot & PROT_WRITE) && (flags & MAP_SHARED) && !f->writable)
    return -1;

  uint64 len = PGROUNDUP(length);

  struct vma *v = 0;
  uint64 top = TRAPFRAME;
  for (int i = 0; i < NVMA; i++) {
    if (p->vmas[i].used) {
      if (p->vmas[i].addr < top)
        top = p->vmas[i].addr;
    } else if (v == 0) {
      v = &p->vmas[i];
    }
  }
  if (v == 0)
    return -1;

  uint64 a = PGROUNDDOWN(top - len);

  v->used = 1;
  v->addr = a;
  v->length = length;
  v->prot = prot;
  v->flags = flags;
  v->offset = offset;
  v->file = f;
  filedup(f);

  return a;
}

uint64
sys_munmap(void)
{
  uint64 addr, length;
  struct proc *p = myproc();

  argaddr(0, &addr);
  argaddr(1, &length);

  struct vma *v = 0;
  for (int i = 0; i < NVMA; i++) {
    struct vma *t = &p->vmas[i];
    if (t->used && addr >= t->addr && addr < t->addr + PGROUNDUP(t->length)) {
      v = t;
      break;
    }
  }
  if (v == 0)
    return -1;

  vmaunmap(p->pagetable, v, addr, length);

  if (addr == v->addr && length >= v->length) {
    fileclose(v->file);
    v->used = 0;
  } else if (addr == v->addr) {
    v->addr += length;
    v->offset += length;
    v->length -= length;
  } else {
    v->length = addr - v->addr;
  }
  return 0;
}
'''
    write('kernel/sysfile.c', sf)
    print("[ OK ] sysfile.c: added mmap/munmap/mmapfault/vmaunmap")

sh = read('kernel/syscall.h')
if 'SYS_mmap' in sh:
    print("[SKIP] syscall.h already has SYS_mmap")
else:
    nums = [int(n) for n in re.findall(r'#define\s+SYS_\w+\s+(\d+)', sh)]
    m = max(nums)
    write('kernel/syscall.h', sh.rstrip('\n') +
          f'\n#define SYS_mmap   {m+1}\n#define SYS_munmap {m+2}\n')
    print(f"[ OK ] syscall.h: SYS_mmap={m+1}, SYS_munmap={m+2}")

sc = read('kernel/syscall.c')
if 'sys_mmap' not in sc:
    ext = list(re.finditer(r'extern uint64 sys_\w+\(void\);\n', sc))
    i = ext[-1].end()
    sc = sc[:i] + 'extern uint64 sys_mmap(void);\nextern uint64 sys_munmap(void);\n' + sc[i:]
    arr = list(re.finditer(r'\[SYS_\w+\]\s*=\s*sys_\w+,\n', sc))
    j = arr[-1].end()
    sc = sc[:j] + '  [SYS_mmap]    = sys_mmap,\n  [SYS_munmap]  = sys_munmap,\n' + sc[j:]
    write('kernel/syscall.c', sc)
    print("[ OK ] syscall.c: externs + table")
else:
    print("[SKIP] syscall.c already has sys_mmap")

uh = read('user/user.h')
if 'mmap' in uh:
    print("[SKIP] user.h already declares mmap")
else:
    uh = uh.replace('char *sbrk(int);',
                    'char *sbrk(int);\n'
                    'void *mmap(void *addr, int length, int prot, int flags, int fd, int offset);\n'
                    'int munmap(void *addr, int length);', 1)
    write('user/user.h', uh)
    print("[ OK ] user.h: declared mmap/munmap")

pl = read('user/usys.pl')
if 'mmap' in pl:
    print("[SKIP] usys.pl already has mmap")
else:
    write('user/usys.pl', pl.rstrip('\n') + '\nentry("mmap");\nentry("munmap");\n')
    print("[ OK ] usys.pl: added entries")

print("\nmmap patches done. Build with LAB=mmap.")
