#!/usr/bin/env python3
"""Pasang SUSFS (gki-android15-6.6) ke source kernel A05 (6.6.89 maupun 6.6.142).
Pakai: python3 patch_susfs.py <source-kernel> <repo-susfs4ksu>
Patch resmi gagal di 2 tempat karena kode Samsung berbeda dari kernel Google:
  - fs/namespace.c  (blok PROC_STLOG di antara include)
  - fs/proc/base.c  (di 6.6.89 belum ada #include <linux/dma-buf.h> yang jadi patokan patch)
Dua bagian itu dipasang manual di sini. Berhenti dengan error kalau ada yang tidak cocok."""
import sys, pathlib, shutil, subprocess

k = pathlib.Path(sys.argv[1]); r = pathlib.Path(sys.argv[2]) / "kernel_patches"
shutil.copy(r / "fs/susfs.c", k / "fs/susfs.c")
for h in (r / "include/linux").iterdir():
    shutil.copy(h, k / "include/linux" / h.name)

res = subprocess.run(["patch", "-p1", "--no-backup-if-mismatch", "-i", str(r / "50_add_susfs_in_gki-android15-6.6.patch")],
                     cwd=k, capture_output=True, text=True)
print(res.stdout[-1500:])
rej = sorted(str(p.relative_to(k)) for p in k.rglob("*.rej"))
allowed = {"fs/namespace.c.rej", "fs/proc/base.c.rej"}
if not set(rej) <= allowed or "fs/namespace.c.rej" not in rej:
    sys.exit(f"[GAGAL] hasil patch tidak sesuai harapan. Reject: {rej}\n{res.stderr}")

def edit(path, pairs):
    p = k / path; s = p.read_text()
    for name, old, new in pairs:
        if s.count(old) != 1:
            sys.exit(f"[GAGAL] {path}: anchor {name} ditemukan {s.count(old)}x (harusnya 1x)")
        s = s.replace(old, new)
    p.write_text(s)

# ---- fs/namespace.c ----
b_old = "#ifdef CONFIG_PROC_STLOG\n#include <linux/fslog.h>\n#endif\n\n"
edit("fs/namespace.c", [
    ("a", "#include <linux/mnt_idmapping.h>\n\n#include \"pnode.h\"",
          "#include <linux/mnt_idmapping.h>\n#ifdef CONFIG_KSU_SUSFS\n#include <linux/susfs_def.h>\n"
          "#endif // #ifdef CONFIG_KSU_SUSFS\n\n#include \"pnode.h\""),
    ("b", b_old, b_old + "#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\nextern bool susfs_is_current_ksu_domain(void);\n"
          "extern struct static_key_true susfs_is_sdcard_android_data_not_decrypted;\n\n"
          "#define CL_COPY_MNT_NS BIT(25) /* used by copy_mnt_ns() */\n#endif // #ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\n\n"),
])
(k / "fs/namespace.c.rej").unlink()

# ---- fs/proc/base.c (hanya kalau hunk include-nya ditolak) ----
if "fs/proc/base.c.rej" in rej:
    inc = ("#if defined(CONFIG_KSU_SUSFS_SUS_MAP) || defined(CONFIG_KSU_SUSFS_OPEN_REDIRECT)\n"
           "#include <linux/susfs_def.h>\n"
           "#endif // #if defined(CONFIG_KSU_SUSFS_SUS_MAP) || defined(CONFIG_KSU_SUSFS_OPEN_REDIRECT)\n\n")
    anchor = "#include <linux/cpufreq_times.h>\n"
    edit("fs/proc/base.c", [("include", anchor, anchor + inc)])
    (k / "fs/proc/base.c.rej").unlink()
    print("[ok] fs/proc/base.c disesuaikan manual")
print("[ok] SUSFS terpasang (fs/namespace.c disesuaikan manual)")
