# Kernel Galaxy A05 (SM-A055F) untuk ROM original + BakaSU + SUSFS

Kernel 6.6 untuk **Samsung Galaxy A05 (SM-A055F / a05m)** yang memakai **ROM original (stock) Samsung**, dengan root **BakaSU** (sebelumnya bernama ReSukiSU) dan **SUSFS**.

> ⚠️ **Hanya untuk SM-A055F dengan firmware `A055FXXSHDZF1` (Android 15).**
> Flash di model atau firmware lain bisa membuat HP bootloop. Ini bukan kernel untuk ROM custom.

## Status

| Hal | Status |
|---|---|
| Build lewat GitHub Actions | ✅ Berhasil |
| Kecocokan dengan kernel stok (CRC simbol) | ✅ 16.237 simbol cocok, 0 beda, 0 hilang |
| Boot di HP | ⏳ Belum dikonfirmasi (isi bagian ini setelah diuji) |
| Root, modul, SUSFS | ⏳ Belum diuji |

Pernah ada versi awal yang berhenti di logo Samsung. Penyebabnya sudah ditemukan dan diperbaiki, lihat bagian **Kenapa repo ini ada**.

## Spesifikasi

| Komponen | Versi |
|---|---|
| Kernel | `6.6.89-android15-8-abA055FXXSHDZF1-4k` (sama dengan kernel ROM ori) |
| Source kernel | [rsuntk/android_kernel_samsung_a05m-6.6](https://github.com/rsuntk/android_kernel_samsung_a05m-6.6), commit `f599cd4b93a4` |
| Root | BakaSU `v4.2.0-rc3`, commit `d5e9e025`, mode SUSFS inline hook |
| SUSFS | v2.3.0 (commit `ebf876e`, branch `gki-android15-6.6`) |
| Config | Config asli kernel ROM ori, diambil dari `boot.img` stok |
| DEFEX | Dibiarkan menyala seperti stok |

## Cek dulu sebelum flash

1. Buka **Pengaturan → Tentang ponsel → Informasi perangkat lunak**.
2. **Versi pita dasar** harus `A055FXXSHDZF1`.
3. **Versi kernel** harus diawali `6.6.89-android15-8-abA055FXXSHDZF1-4k`.
4. Model harus **SM-A055F**.

Kalau ada yang berbeda, jangan flash.

## Syarat

- Bootloader sudah **unlocked**.
- **vbmeta** sebaiknya sudah dinonaktifkan. Kernel buatan sendiri bisa ditolak bootloader kalau verifikasi vbmeta masih aktif.
- Cadangan `boot.img` (dan `init_boot.img`) dari firmware ROM ori kamu.

## Cara pasang

1. **Backup** partisi `boot` dan `init_boot`. Simpan juga `boot.img` dan `init_boot.img` dari file firmware.
2. Unduh zip `A05-6.6.89-BakaSU-....zip` dari **Actions → run terbaru → Artifacts**.
3. Flash zip itu lewat OrangeFox/TWRP, lalu reboot.
4. Pasang **BakaSU Manager v4.2.0-rc3**: https://github.com/Baka-SU/BakaSU/releases/tag/v4.2.0-rc3
5. Buka manager dan cek apakah driver kernel terbaca dan SUSFS menampilkan v2.3.0.

## Kalau bootloop

Flash ulang `boot.img` dan `init_boot.img` ori lewat OrangeFox, atau lewat Odin kalau OrangeFox tidak bisa dimasuki. HP kembali normal.

## Kenapa repo ini ada

Kernel ROM custom dan kernel ROM ori punya konfigurasi yang berbeda. Build yang memakai `gki_defconfig` (dan mematikan `io_uring`, `ublk`, `DEFEX`) tidak cocok dengan ROM ori: **10.310 dari 16.231 simbol punya CRC berbeda**, jadi modul vendor ROM ditolak saat boot dan HP berhenti di logo Samsung.

Repo ini memperbaikinya dengan:

- memakai **config asli kernel ROM ori** (`stock_a05m.config`) sebagai basis;
- menanam **sertifikat penanda tangan modul** stok (`stock_trusted_cert.pem`) supaya modul vendor lolos cek tanda tangan;
- memeriksa **CRC simbol** hasil build terhadap kernel stok (`stock_modver.json`). Kalau ada yang beda, zip tidak dibuat.

## Cara build sendiri

1. Fork repo ini atau salin file-nya ke repo baru.
2. Buka **Actions → Build Kernel A05 6.6.89 → Run workflow**.
3. Biarkan nilai default, lalu tunggu sekitar satu jam. Hasilnya ada di **Artifacts**.

Pilihan di workflow:

| Pilihan | Fungsi |
|---|---|
| `config_only` | Hanya cek source, hook, dan config (beberapa menit), tanpa compile |
| `defex` | `keep` = DEFEX menyala seperti stok (default, aman untuk boot). `off` = matikan DEFEX kalau root diblokir |
| `crc_strict` | `true` = zip tidak dibuat kalau CRC beda dari kernel stok (default) |
| `config_mode` | `ori` = config ROM ori (default). `gki` = `gki_defconfig`, hanya untuk ROM custom |
| `localversion` | Akhiran versi kernel. Default sama dengan uname ROM ori |

Isi artifact: zip untuk flash, `Image` mentah, `final.config`, `build.log`, dan `crc.log`.

## Isi repo

```
.github/workflows/build.yml   workflow build
patch_hooks.py                perbaikan sertifikat di source kernel
patch_susfs.py                pasang SUSFS ke source (sudah disesuaikan untuk 6.6.89)
stock_a05m.config             config asli kernel ROM ori
stock_modver.json             tabel CRC simbol kernel ROM ori
stock_trusted_cert.pem        sertifikat penanda tangan modul stok
tools/kcrc.py                 pembaca tabel simbol dari Image
tools/cekcrc.py               pembanding CRC build vs kernel stok
tools/cmpconfig.py            pembanding config build vs config stok
```

## Kredit

- [BakaSU](https://github.com/Baka-SU/BakaSU) dan KernelSU
- [SUSFS](https://gitlab.com/simonpunk/susfs4ksu) oleh simonpunk, branch `gki-android15-6.6` dari [ShirkNeko](https://github.com/ShirkNeko/susfs4ksu)
- [rsuntk](https://github.com/rsuntk) untuk source kernel A05
- [AnyKernel3](https://github.com/osm0sis/AnyKernel3) oleh osm0sis

Kernel berlisensi GPL-2.0, sesuai source aslinya.

## Tanggung jawab

Flash dengan risiko sendiri. Selalu simpan backup sebelum mencoba, karena kernel yang salah bisa membuat HP tidak bisa boot. Garansi dan Knox bisa terpengaruh oleh unlock bootloader dan flash kernel kustom.
