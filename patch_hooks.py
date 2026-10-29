#!/usr/bin/env python3
"""Pasang hook manual BakaSU ke source kernel 6.6 (Galaxy A05 / a05m).
Dipakai: python3 patch_hooks.py <path-source-kernel>
Skrip berhenti dengan error jika ada titik patch yang tidak ketemu,
dan aman dijalankan ulang (tidak menambah hook dua kali)."""
import sys, re, pathlib

root = pathlib.Path(sys.argv[1])
MARK = "CONFIG_KSU_MANUAL_HOOK"
ONLY_CERT = len(sys.argv) > 2 and sys.argv[2] == "--only-cert"  # mode SUSFS: hook dipasang patch SUSFS

def rd(p): return (root / p).read_text()
def wr(p, s): (root / p).write_text(s)

def patch(path, steps):
    if ONLY_CERT:
        return
    s = rd(path)
    if MARK in s:
        print(f"[skip] {path} sudah dipatch")
        return
    for name, old, new, count in steps:
        n = s.count(old)
        if n != count:
            sys.exit(f"[GAGAL] {path}: '{name}' ditemukan {n}x (harusnya {count}x)")
        s = s.replace(old, new)
    wr(path, s)
    print(f"[ok]   {path}")

# ---------- fs/stat.c ----------
stat_decl = '''#ifdef CONFIG_KSU_MANUAL_HOOK
__attribute__((hot))
extern int ksu_handle_stat(int *dfd, const char __user **filename_user,
				int *flags);
extern void ksu_handle_newfstat_ret(unsigned int *fd, struct stat __user **statbuf_ptr);
#endif

'''
patch("fs/stat.c", [
    ("decl newfstatat",
     "#if !defined(__ARCH_WANT_STAT64) || defined(__ARCH_WANT_SYS_NEWFSTATAT)\nSYSCALL_DEFINE4(newfstatat,",
     stat_decl + "#if !defined(__ARCH_WANT_STAT64) || defined(__ARCH_WANT_SYS_NEWFSTATAT)\nSYSCALL_DEFINE4(newfstatat,", 1),
    ("hook newfstatat",
     "\tstruct kstat stat;\n\tint error;\n\n\terror = vfs_fstatat(dfd, filename, &stat, flag);\n\tif (error)\n\t\treturn error;\n\treturn cp_new_stat(&stat, statbuf);",
     "\tstruct kstat stat;\n\tint error;\n\n#ifdef CONFIG_KSU_MANUAL_HOOK\n\tksu_handle_stat(&dfd, &filename, &flag);\n#endif\n\terror = vfs_fstatat(dfd, filename, &stat, flag);\n\tif (error)\n\t\treturn error;\n\treturn cp_new_stat(&stat, statbuf);", 1),
    ("hook newfstat ret",
     "\tint error = vfs_fstat(fd, &stat);\n\n\tif (!error)\n\t\terror = cp_new_stat(&stat, statbuf);\n\n\treturn error;",
     "\tint error = vfs_fstat(fd, &stat);\n\n\tif (!error)\n\t\terror = cp_new_stat(&stat, statbuf);\n\n#ifdef CONFIG_KSU_MANUAL_HOOK\n\tksu_handle_newfstat_ret(&fd, &statbuf);\n#endif\n\treturn error;", 1),
    # fstat64: WAJIB ada (pemeriksa BakaSU grep teks 'ksu_handle_fstat64_ret' di fs/stat.c).
    # Di arm64 blok ini ikut terkompilasi karena __ARCH_WANT_COMPAT_STAT64 (CONFIG_COMPAT=y).
    ("hook fstat64 ret",
     "SYSCALL_DEFINE2(fstat64, unsigned long, fd, struct stat64 __user *, statbuf)\n{\n\tstruct kstat stat;\n\tint error = vfs_fstat(fd, &stat);\n\n\tif (!error)\n\t\terror = cp_new_stat64(&stat, statbuf);\n\n\treturn error;\n}",
     "#ifdef CONFIG_KSU_MANUAL_HOOK\nextern void ksu_handle_fstat64_ret(unsigned long *fd, struct stat64 __user **statbuf_ptr);\n#endif\n\nSYSCALL_DEFINE2(fstat64, unsigned long, fd, struct stat64 __user *, statbuf)\n{\n\tstruct kstat stat;\n\tint error = vfs_fstat(fd, &stat);\n\n\tif (!error)\n\t\terror = cp_new_stat64(&stat, statbuf);\n\n#ifdef CONFIG_KSU_MANUAL_HOOK\n\tksu_handle_fstat64_ret(&fd, &statbuf);\n#endif\n\treturn error;\n}", 1),
    # fstatat64: untuk su 32-bit (sesuai dokumentasi BakaSU)
    ("hook fstatat64",
     "SYSCALL_DEFINE4(fstatat64, int, dfd, const char __user *, filename,\n\t\tstruct stat64 __user *, statbuf, int, flag)\n{\n\tstruct kstat stat;\n\tint error;\n\n\terror = vfs_fstatat(dfd, filename, &stat, flag);",
     "SYSCALL_DEFINE4(fstatat64, int, dfd, const char __user *, filename,\n\t\tstruct stat64 __user *, statbuf, int, flag)\n{\n\tstruct kstat stat;\n\tint error;\n\n#ifdef CONFIG_KSU_MANUAL_HOOK\n\tksu_handle_stat(&dfd, &filename, &flag);\n#endif\n\terror = vfs_fstatat(dfd, filename, &stat, flag);", 1),
])

# ---------- fs/exec.c ----------
exec_decl = '''#ifdef CONFIG_KSU_MANUAL_HOOK
__attribute__((hot))
extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr,
				void *argv, void *envp, int *flags);
__attribute__((hot))
extern int ksu_handle_post_execveat(int *fd, struct filename **filename_ptr,
				void *argv, void *envp, int *flags, int *retval);
#endif

'''
patch("fs/exec.c", [
    ("decl execveat",
     "static int do_execveat_common(int fd, struct filename *filename,",
     exec_decl + "static int do_execveat_common(int fd, struct filename *filename,", 1),
    ("pre execveat",
     "\tstruct linux_binprm *bprm;\n\tint retval;\n\n\tif (IS_ERR(filename))\n\t\treturn PTR_ERR(filename);\n",
     "\tstruct linux_binprm *bprm;\n\tint retval;\n\n#ifdef CONFIG_KSU_MANUAL_HOOK\n\tksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);\n#endif\n\n\tif (IS_ERR(filename))\n\t\treturn PTR_ERR(filename);\n", 1),
    ("post execveat",
     "\tretval = bprm_execve(bprm, fd, filename, flags);\nout_free:\n\tfree_bprm(bprm);\n\nout_ret:\n\tputname(filename);\n\treturn retval;",
     "\tretval = bprm_execve(bprm, fd, filename, flags);\nout_free:\n\tfree_bprm(bprm);\n\nout_ret:\n#ifdef CONFIG_KSU_MANUAL_HOOK\n\tksu_handle_post_execveat(&fd, &filename, &argv, &envp, &flags, &retval);\n#endif\n\tputname(filename);\n\treturn retval;", 1),
])

# ---------- fs/open.c ----------
patch("fs/open.c", [
    ("faccessat",
     "SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)\n{\n\treturn do_faccessat(dfd, filename, mode, 0);\n}",
     '''#ifdef CONFIG_KSU_MANUAL_HOOK
__attribute__((hot))
extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user,
				int *mode, int *flags);
#endif

SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)
{
#ifdef CONFIG_KSU_MANUAL_HOOK
	ksu_handle_faccessat(&dfd, &filename, &mode, NULL);
#endif
	return do_faccessat(dfd, filename, mode, 0);
}''', 1),
])

# ---------- kernel/reboot.c ----------
patch("kernel/reboot.c", [
    ("reboot",
     "SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,\n\t\tvoid __user *, arg)\n{\n\tstruct pid_namespace *pid_ns = task_active_pid_ns(current);\n\tchar buffer[256];\n\tint ret = 0;\n\n",
     '''#ifdef CONFIG_KSU_MANUAL_HOOK
extern int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd, void __user **arg);
#endif

SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,
		void __user *, arg)
{
	struct pid_namespace *pid_ns = task_active_pid_ns(current);
	char buffer[256];
	int ret = 0;

#ifdef CONFIG_KSU_MANUAL_HOOK
	ksu_handle_sys_reboot(magic1, magic2, cmd, &arg);
#endif

''', 1),
])

# ---------- certs/extract-cert.c (bug di source rsuntk) ----------
# 'key_pass' dideklarasikan di dalam #ifdef USE_PKCS11_ENGINE tapi dipakai tanpa
# #ifdef, sehingga host tool extract-cert gagal dikompilasi. Hapus #ifdef-nya.
def fix_extract_cert():
    path = "certs/extract-cert.c"
    s = rd(path)
    a_old = "#ifdef USE_PKCS11_ENGINE\nstatic const char *key_pass;\n#endif\n"
    b_old = "#ifdef USE_PKCS11_ENGINE\n\tkey_pass = getenv(\"KBUILD_SIGN_PIN\");\n#endif\n"
    if a_old not in s and b_old not in s:
        print(f"[skip] {path} tidak perlu diperbaiki")
        return
    for old, new in ((a_old, "static const char *key_pass;\n"),
                     (b_old, "\tkey_pass = getenv(\"KBUILD_SIGN_PIN\");\n")):
        if old in s:
            s = s.replace(old, new)
    wr(path, s)
    print(f"[ok]   {path} (perbaikan key_pass)")

fix_extract_cert()

print("Semua hook terpasang.")
