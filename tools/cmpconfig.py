#!/usr/bin/env python3
"""Bandingkan config final hasil build dengan config kernel stok ROM ori.
Pakai: cmpconfig.py stock.config final.config [regex_abaikan]
Gagal (exit 1) kalau opsi penting berubah. Selain itu hanya melaporkan selisihnya."""
import sys, re

def load(p):
    d = {}
    for l in open(p):
        l = l.strip()
        m = re.match(r'^(CONFIG_\w+)=(.*)$', l)
        if m: d[m.group(1)] = m.group(2); continue
        m = re.match(r'^# (CONFIG_\w+) is not set$', l)
        if m: d[m.group(1)] = 'n'
    return d

stock, final = load(sys.argv[1]), load(sys.argv[2])
ign = re.compile(r'^CONFIG_(KSU|LOCALVERSION|MODULE_SIG_KEY|SYSTEM_TRUSTED_KEYS|CC_|LD_|CLANG_VERSION|LLD_VERSION|GCC_VERSION|AS_|PAHOLE|TOOLS_SUPPORT|RUSTC|CAN_LINK|CXX_|HAVE_.*CLANG|EXT_MODULES)'
                 + (r'|' + sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else ''))
dropped = [k for k in stock if k not in final and stock[k] != 'n']
changed = [(k, stock[k], final[k]) for k in stock if k in final and stock[k] != final[k] and not ign.match(k)]
print(f"opsi stok: {len(stock)} | opsi final: {len(final)}")
print(f"opsi aktif di stok yang tidak ada di source ini (dibuang, biasanya driver vendor di luar source): {len(dropped)}")
print(f"opsi yang NILAINYA BERUBAH (di luar KSU/toolchain): {len(changed)}")
for k, a, b in changed[:80]: print(f"  {k:48s} stok={a:10s} final={b}")
crit = {'CONFIG_IO_URING': 'y', 'CONFIG_MODVERSIONS': 'y', 'CONFIG_MODULE_SIG': 'y', 'CONFIG_MODULE_SIG_PROTECT': 'y',
        'CONFIG_ARCH_MEDIATEK': 'y', 'CONFIG_BLK_DEV_UBLK': 'y', 'CONFIG_PROC_STLOG': 'y'}
bad = [(k, v, final.get(k, '(hilang)')) for k, v in crit.items() if final.get(k) != v and stock.get(k) == v]
for k, v, f in bad: print(f"[PENTING] {k}: stok={v} final={f}")
sys.exit(1 if bad else 0)
