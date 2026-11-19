# TokoCatat — Pencatatan Stok & Keuangan Toko Sederhana

## 1. Masalah, Pengguna, dan Fitur
Pemilik toko kecil biasanya mencatat penjualan dan belanja di buku tulis. Akibatnya stok sulit
dipantau (barang tiba-tiba habis), laba tidak diketahui pasti, dan catatan sering ganda atau salah tulis.
TokoCatat menyimpan data di file CSV, menghitung stok akhir dan laba otomatis, serta memberi peringatan stok menipis.

**Target pengguna:** pemilik/penjaga toko kelontong atau warung dan mahasiswa yang belajar membuat sistem pencatatan.

**Fitur utama:**
1. Pencatatan transaksi JUAL/BELI dengan validasi (`catat`, atau menu interaktif)
2. Perhitungan stok akhir otomatis dan status AMAN / MENIPIS / HABIS
3. Laporan keuangan: omzet, modal barang terjual, laba kotor, margin, belanja stok, nilai persediaan, rekap harian dan per kategori
4. Peringatan stok menipis dan barang terlaris
5. Pencarian barang dan filter riwayat transaksi (jenis, rentang tanggal, kode)
6. Pembersihan data: hapus transaksi duplikat (ID sama), tolak data tidak valid beserta alasannya
7. Ekspor hasil ke CSV, JSON, dan TXT

## 2. Format Input & Output
**`barang.csv`** (master barang + stok awal): `kode,nama,kategori,harga_beli,harga_jual,stok,stok_minimum`

**`transaksi.csv`**: `id,tanggal,kode_barang,jenis,jumlah`

| Kolom | Aturan |
|---|---|
| tanggal | `YYYY-MM-DD`, harus tanggal yang benar-benar ada |
| jenis | `JUAL` (stok berkurang, menjadi omzet) atau `BELI` (stok bertambah, menjadi belanja) |
| jumlah, harga, stok | bilangan bulat; jumlah >= 1; harga jual >= harga beli |

Semua uang memakai bilangan bulat Rupiah (bukan float) agar perhitungan tidak bergeser.

**Output** (`data/output/`): `laporan.txt`, `ringkasan.json`, `stok_akhir.csv`, `data_ditolak.txt`.

## 3. Struktur Program
```
uts_toko/
├── main.py                  # entry point
├── tokocatat/               # package buatan sendiri
│   ├── __init__.py
│   ├── errors.py            # exception khusus
│   ├── validator.py         # validasi 1 baris barang/transaksi
│   ├── fileio.py            # baca/tulis CSV & JSON, append transaksi
│   ├── processor.py         # stok, laba-rugi, cari, filter (tanpa I/O)
│   ├── report.py            # format Rupiah, tabel, laporan
│   └── cli.py               # argparse + menu interaktif
├── tests/test_tokocatat.py  # 19 unit test
├── data/input/              # barang.csv, transaksi.csv, file edge case
├── data/output/             # contoh hasil run
└── docs/                    # demo debugging
```
Alur dependensi: `main → cli → (fileio, processor, report)`; `fileio → validator → errors`;
`processor → validator, errors`. Tidak ada dependensi melingkar.

## 4. Cara Menjalankan
**Cara termudah: jalankan tanpa argumen, menu interaktif langsung muncul.**
```bash
python main.py
```
```
=== TOKOCATAT - MENU UTAMA ===
1. Laporan keuangan & stok
2. Lihat stok akhir
3. Peringatan stok menipis
4. Cari barang
5. Catat penjualan
6. Catat pembelian (stok masuk)
7. Riwayat transaksi (filter)
8. Simpan hasil ke file
0. Keluar
```
Mode perintah (opsional, untuk otomatisasi/skrip):
```bash
python main.py laporan                 # laporan lengkap + simpan file
python main.py stok --menipis          # barang yang perlu dibeli ulang
python main.py riwayat --jenis beli --dari 2026-10-07
python main.py cari sembako
python main.py catat --kode B002 --jenis JUAL --jumlah 3     # tanggal default: hari ini
python main.py menu -b barang.csv -t transaksi.csv           # menu dengan file sendiri
python -m unittest -v                  # jalankan semua test
```
Menu (pilihan 5 dan 6) dan perintah `catat` **menambah baris** ke file transaksi; salin dulu data contoh bila
hanya ingin mencoba. File default: `data/input/barang.csv` dan `data/input/transaksi.csv`.
Kode exit: `0` sukses, `1` error file/data, `2` input tidak valid, `130` dibatalkan (Ctrl+C).

## 5. Penanganan Error
File tidak ada / izin / encoding salah / kolom wajib hilang → pesan jelas. Baris tidak valid
(angka salah, tanggal tidak ada, jenis salah, harga jual < beli, kode barang ganda) dicatat lalu dilewati.
Transaksi tidak masuk akal (kode tidak terdaftar, jual melebihi stok) ditolak tanpa menghentikan program.
Input menu (pilihan, jumlah, tanggal) yang salah diminta ulang. Ctrl+C dan EOF keluar dengan rapi.

## 6. Dependency
Hanya standard library: `argparse, csv, json, os, re, sys, datetime, unittest, tempfile, shutil`.

## 7. Referensi & Bantuan AI
Dokumentasi resmi Python (docs.python.org). Kode ini dibuat dengan bantuan AI (Claude, Anthropic) hanya ketika diperlukan. Kemudian dijalankan secara mandiri untuk QA testing.
