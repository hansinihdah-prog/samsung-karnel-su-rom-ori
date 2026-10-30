#!/usr/bin/env python3
"""Pasang driver ZeroMount VFS (patch 60_zeromount dari Enginex0/Super-Builders) ke source kernel A05 6.6.89
yang SUDAH dipasangi SUSFS v2.3.0 lewat patch_susfs.py.
Pakai: python3 patch_zeromount.py <source-kernel> <60_zeromount-android15-6.6.patch>

Patch aslinya ditulis untuk SUSFS versi lain, jadi:
  - fs/stat.c dan fs/proc/task_mmu.c dipasang manual di sini (patch biasa salah tempat atau ditolak),
    memakai patokan yang harus ditemukan tepat 1x;
  - bagian lain dipasang dengan patch biasa dan harus tanpa reject.
Berhenti dengan error kalau ada yang tidak cocok."""
import sys, re, pathlib, subprocess

k = pathlib.Path(sys.argv[1]); pf = pathlib.Path(sys.argv[2])
if (k / "fs/zeromount.c").exists():
    sys.exit("[GAGAL] ZeroMount sudah terpasang di source ini")

MANUAL = {"fs/stat.c", "fs/proc/task_mmu.c"}
text = pf.read_text()
# pecah patch per file; buang bagian yang dipasang manual
parts = re.split(r'(?m)^(?=--- )', text)
keep, dropped = [], []
for p in parts:
    m = re.search(r'(?m)^\+\+\+ b/(\S+)', p)
    if m and m.group(1) in MANUAL: dropped.append(m.group(1)); continue
    keep.append(p)
if sorted(dropped) != sorted(MANUAL):
    sys.exit(f"[GAGAL] bagian patch yang dibuang tidak sesuai: {dropped}")
tmp = k / ".zeromount_rest.patch"; tmp.write_text("".join(keep))
res = subprocess.run(["patch", "-p1", "--no-backup-if-mismatch", "-i", str(tmp)], cwd=k, capture_output=True, text=True)
tmp.unlink()
print(res.stdout[-1200:])
rej = sorted(str(p.relative_to(k)) for p in k.rglob("*.rej"))
if rej or res.returncode != 0:
    sys.exit(f"[GAGAL] patch ZeroMount ditolak. Reject: {rej}\n{res.stderr[-800:]}")

def edit(path, pairs):
    p = k / path; s = p.read_text()
    for name, old, new in pairs:
        n = s.count(old)
        if n != 1: sys.exit(f"[GAGAL] {path}: patokan '{name}' ditemukan {n}x (harusnya 1x)")
        s = s.replace(old, new)
    p.write_text(s); print(f"[ok]   {path} (manual)")

# ---- fs/stat.c ----
hook = '''#ifdef CONFIG_ZEROMOUNT
static inline int zeromount_stat_hook(int dfd, struct filename *filename,
                                      struct kstat *stat, unsigned int request_mask,
                                      int flags) {
    const char *kname;
    if (zm_is_recursive() || IS_ERR_OR_NULL(filename)) return -ENOENT;
    if (!filename || IS_ERR(filename)) return -ENOENT;
    kname = filename->name;
    if (kname && kname[0] != '/') {
        char *abs_path = zeromount_build_absolute_path(dfd, kname);
        if (abs_path) {
            char *resolved = zeromount_resolve_path(abs_path);
            if (resolved) {
                struct path zm_path;
                int zm_ret;
                zm_enter();
                zm_ret = kern_path(resolved, (flags & AT_SYMLINK_NOFOLLOW) ? 0 : LOOKUP_FOLLOW, &zm_path);
                zm_exit();
                kfree(resolved);
                kfree(abs_path);
                if (zm_ret == 0) {
                    zm_ret = vfs_getattr(&zm_path, stat, request_mask,
                                         (flags & AT_SYMLINK_NOFOLLOW) ? AT_SYMLINK_NOFOLLOW : 0);
                    path_put(&zm_path);
                    return zm_ret;
                }
            } else {
                kfree(abs_path);
            }
        }
    }
    return -ENOENT;
}
#endif

'''
call = '''#ifdef CONFIG_ZEROMOUNT
	/* Try ZeroMount hook for relative paths */
	if (filename) {
		int zm_ret = zeromount_stat_hook(dfd, filename, stat, request_mask, flags);
		if (zm_ret != -ENOENT)
			return zm_ret;
	}
#endif

'''
inc_old = "#include <linux/uaccess.h>\n#include <asm/unistd.h>\n"
fn_old = "/**\n * vfs_fstat - Get the basic attributes by file descriptor\n"
call_old = "orig_flow:\n#endif\n\n\tif (flags & ~(AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT | AT_EMPTY_PATH |"
edit("fs/stat.c", [
    ("include", inc_old, "#include <linux/uaccess.h>\n#ifdef CONFIG_ZEROMOUNT\n#include <linux/zeromount.h>\n#endif\n#include <asm/unistd.h>\n"),
    ("fungsi hook", fn_old, hook + fn_old),
    ("panggilan hook", call_old, "orig_flow:\n#endif\n\n" + call + call_old.split("#endif\n\n", 1)[1]),
])

# ---- fs/proc/task_mmu.c ----
spoof_old = ("\t\tino = inode->i_ino;\n\t\tpgoff = ((loff_t)vma->vm_pgoff) << PAGE_SHIFT;\n"
             "#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n\t\tsusfs_sus_kstat_spoof_show_map_vma(inode, &dev, &ino);")
edit("fs/proc/task_mmu.c", [
    ("include", "#include <linux/page_size_compat.h>\n#include <linux/shmem_fs.h>\n",
                "#include <linux/page_size_compat.h>\n#ifdef CONFIG_ZEROMOUNT\n#include <linux/zeromount.h>\n#endif\n#include <linux/shmem_fs.h>\n"),
    ("spoof mmap", spoof_old,
     "\t\tino = inode->i_ino;\n#ifdef CONFIG_ZEROMOUNT\n\t\tzeromount_spoof_mmap_metadata(inode, &dev, &ino);\n#endif\n"
     + spoof_old.split("\t\tino = inode->i_ino;\n", 1)[1]),
])

# ---- pemeriksaan: semua definisi/hook harus berada di kode, bukan di dalam komentar ----
def strip_comments(s):
    return re.sub(r'/\*.*?\*/', '', s, flags=re.S)
checks = {
    "fs/stat.c": ["zeromount_stat_hook(int dfd", "zeromount_stat_hook(dfd, filename"],
    "fs/proc/task_mmu.c": ["zeromount_spoof_mmap_metadata(inode"],
    "fs/namei.c": ["zeromount_getname_hook(result)"],
    "fs/readdir.c": ["zeromount_inject_dents(", "zeromount_inject_dents64("],
    "fs/d_path.c": ["zeromount_get_static_vpath("],
    "fs/statfs.c": ["zeromount_spoof_statfs("],
    "fs/xattr.c": ["zeromount_spoof_xattr("],
    "fs/proc/base.c": ["zeromount_get_static_vpath("],
}
for f, needles in checks.items():
    s = strip_comments((k / f).read_text())
    for n in needles:
        if n not in s: sys.exit(f"[GAGAL] {f}: '{n}' tidak ada di kode (hilang atau jatuh di dalam komentar)")
print("[ok] ZeroMount terpasang dan semua hook berada di kode")
