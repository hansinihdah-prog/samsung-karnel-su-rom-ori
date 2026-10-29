#!/usr/bin/env python3
"""Ekstrak tabel ekspor simbol (nama -> CRC) dari Image arm64 (kernel 6.6, prel32 ksymtab)."""
import sys, struct, array, json

def extract(path):
    d = open(path, 'rb').read()
    N = len(d)
    a = array.array('i'); a.frombytes(d[:N - N % 4])
    n = len(a)
    # entri ksymtab: tiga int32 (value_off, name_off, ns_off); name target = byte(i+1)*4 + name_off
    def ok(i):
        if i + 2 >= n: return False
        t = (i + 1) * 4 + a[i + 1]
        if not (1 < t < N - 2): return False
        if d[t - 1] != 0: return False
        c = d[t]
        return 0x21 <= c < 0x7f
    # cari run panjang stride-3
    runs = []; i = 0
    while i < n - 3:
        if ok(i) and ok(i + 3) and ok(i + 6) and ok(i + 9):
            s = i
            while ok(i): i += 3
            if (i - s) // 3 > 500: runs.append((s, i))
        else:
            i += 1
    if not runs: raise SystemExit("ksymtab tidak ditemukan")
    # gabungkan run bersebelahan (ksymtab + ksymtab_gpl)
    runs.sort()
    merged = [list(runs[0])]
    for s, e in runs[1:]:
        if s - merged[-1][1] <= 8: merged[-1][1] = e
        else: merged.append([s, e])
    s, e = max(merged, key=lambda r: r[1] - r[0])
    cnt = (e - s) // 3
    names = []
    for k in range(cnt):
        i = s + 3 * k
        t = (i + 1) * 4 + a[i + 1]
        names.append(d[t:d.index(b'\0', t)].decode('ascii', 'replace'))
    crc0 = e * 4  # __kcrctab mulai tepat setelah akhir ksymtab_gpl
    crcs = struct.unpack_from('<%dI' % cnt, d, crc0)
    return dict(zip(names, crcs)), cnt

if __name__ == '__main__':
    tab, cnt = extract(sys.argv[1])
    print("entri ekspor:", cnt)
    json.dump({k: hex(v) for k, v in tab.items()}, open(sys.argv[2], 'w'))
