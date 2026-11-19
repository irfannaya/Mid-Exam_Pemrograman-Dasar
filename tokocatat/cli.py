"""Antarmuka command line: argparse + menu interaktif."""

import argparse
import os
import sys
from datetime import date

from . import fileio, processor, report
from .errors import TokoError
from .validator import KOLOM_BARANG, validasi_tanggal

BARANG_DEFAULT = os.path.join("data", "input", "barang.csv")
TRANSAKSI_DEFAULT = os.path.join("data", "input", "transaksi.csv")
OUTPUT_DEFAULT = os.path.join("data", "output")


def buat_parser():
    """Bangun parser dengan sub-perintah: laporan, stok, riwayat, cari, catat, menu."""
    parser = argparse.ArgumentParser(
        prog="main.py", description="TokoCatat - pencatatan stok & keuangan toko sederhana. "
                    "Jalankan tanpa perintah untuk membuka menu interaktif.")
    sub = parser.add_subparsers(dest="perintah",
                                help="kosongkan untuk membuka menu interaktif")

    def umum(p):
        p.add_argument("-b", "--barang", default=BARANG_DEFAULT, help="file master barang (CSV)")
        p.add_argument("-t", "--transaksi", default=TRANSAKSI_DEFAULT, help="file transaksi (CSV)")

    p = sub.add_parser("laporan", help="hitung laporan lengkap dan simpan ke file")
    umum(p)
    p.add_argument("-o", "--output-dir", default=OUTPUT_DEFAULT)

    p = sub.add_parser("stok", help="tampilkan stok akhir")
    umum(p)
    p.add_argument("--menipis", action="store_true", help="hanya yang menipis/habis")

    p = sub.add_parser("riwayat", help="filter riwayat transaksi")
    umum(p)
    p.add_argument("--jenis")
    p.add_argument("--dari", help="tanggal awal YYYY-MM-DD")
    p.add_argument("--sampai", help="tanggal akhir YYYY-MM-DD")
    p.add_argument("--kode")

    p = sub.add_parser("cari", help="cari barang (kode/nama/kategori)")
    umum(p)
    p.add_argument("kata")

    p = sub.add_parser("catat", help="catat transaksi baru ke file transaksi")
    umum(p)
    p.add_argument("--kode", required=True)
    p.add_argument("--jenis", required=True, help="JUAL atau BELI")
    p.add_argument("--jumlah", required=True, type=int)
    p.add_argument("--tanggal", default=None, help="default: hari ini")

    p = sub.add_parser("menu", help="mode interaktif")
    umum(p)
    return parser


def muat_data(path_barang, path_transaksi):
    """Baca, bersihkan, dan hitung stok. Returns dict berisi seluruh state aplikasi."""
    barang, err_barang = fileio.baca_barang(path_barang)
    transaksi, err_trx = fileio.baca_transaksi(path_transaksi)
    transaksi, duplikat = processor.hapus_duplikat_id(transaksi)
    stok, sah, err_proses = processor.proses_transaksi(barang, transaksi)
    return {"barang": barang, "transaksi": transaksi, "stok": stok, "sah": sah,
            "duplikat": duplikat, "ditolak": err_barang + err_trx + err_proses}


def buat_laporan(d):
    """Susun teks laporan dari state hasil muat_data."""
    ringkas = processor.hitung_keuangan(d["sah"], d["barang"])
    return report.format_laporan(
        ringkas, d["barang"], d["stok"], processor.stok_menipis(d["barang"], d["stok"]),
        processor.terlaris(d["sah"], 3), d["duplikat"], d["ditolak"]), ringkas


def simpan_hasil(d, folder):
    """Simpan 4 file keluaran ke `folder`. Returns teks laporan."""
    teks, ringkas = buat_laporan(d)
    baris = processor.daftar_stok(d["barang"], d["stok"])
    fileio.tulis_teks(os.path.join(folder, "laporan.txt"), teks + "\n")
    fileio.tulis_csv(os.path.join(folder, "stok_akhir.csv"), baris, KOLOM_BARANG + ("status",))
    fileio.tulis_json(os.path.join(folder, "ringkasan.json"), {
        "keuangan": ringkas,
        "nilai_persediaan": processor.nilai_stok(d["barang"], d["stok"]),
        "terlaris": processor.terlaris(d["sah"], 3),
        "stok_menipis": [r["kode"] for r in processor.stok_menipis(d["barang"], d["stok"])],
        "duplikat_dibuang": d["duplikat"],
        "ditolak": d["ditolak"]})
    fileio.tulis_teks(os.path.join(folder, "data_ditolak.txt"),
                      "\n".join(d["ditolak"]) + ("\n" if d["ditolak"] else ""))
    return teks


def cmd_laporan(a):
    d = muat_data(a.barang, a.transaksi)
    print(simpan_hasil(d, a.output_dir))
    print(f"\nFile keluaran disimpan di: {a.output_dir}/")
    return 0


def cmd_stok(a):
    d = muat_data(a.barang, a.transaksi)
    baris = (processor.stok_menipis(d["barang"], d["stok"]) if a.menipis
             else processor.daftar_stok(d["barang"], d["stok"]))
    print(report.tabel_stok(baris))
    return 0


def cmd_riwayat(a):
    d = muat_data(a.barang, a.transaksi)
    hasil = processor.filter_transaksi(d["sah"], a.jenis, a.dari, a.sampai, a.kode)
    print(f"{len(hasil)} transaksi cocok:\n")
    print(report.tabel_transaksi(hasil))
    return 0


def cmd_cari(a):
    d = muat_data(a.barang, a.transaksi)
    hasil = processor.cari_barang(d["barang"], a.kata)
    daftar = [{**b, "stok": d["stok"][b["kode"]],
               "status": processor.status_stok(d["stok"][b["kode"]], b["stok_minimum"])}
              for b in hasil]
    print(f"{len(daftar)} barang ditemukan untuk '{a.kata}':\n")
    print(report.tabel_stok(daftar))
    return 0


def catat_transaksi(d, path_transaksi, kode, jenis, jumlah, tanggal=None):
    """Validasi lalu simpan transaksi baru. Returns dict transaksi yang disimpan.

    Raises:
        ValueError: data tidak valid (kode, jenis, jumlah, stok kurang, tanggal).
    """
    kode, jenis = processor.periksa_transaksi_baru(d["barang"], d["stok"], kode, jenis, jumlah)
    tanggal = tanggal or date.today().isoformat()
    try:
        validasi_tanggal(tanggal, "argumen", 0)
    except TokoError:
        raise ValueError(f"tanggal harus YYYY-MM-DD, bukan '{tanggal}'") from None
    trx = {"id": processor.id_baru(d["transaksi"]), "tanggal": tanggal,
           "kode_barang": kode, "jenis": jenis, "jumlah": jumlah}
    fileio.tambah_transaksi(path_transaksi, trx)
    return trx


def cmd_catat(a):
    d = muat_data(a.barang, a.transaksi)
    trx = catat_transaksi(d, a.transaksi, a.kode, a.jenis, a.jumlah, a.tanggal)
    d = muat_data(a.barang, a.transaksi)
    print(f"Tercatat {trx['id']}: {trx['jenis']} {trx['jumlah']} x {trx['kode_barang']} "
          f"({trx['tanggal']}). Stok sekarang: {d['stok'][trx['kode_barang']]}")
    return 0


def baca_int_positif(prompt):
    """Minta bilangan bulat >= 1; ulangi sampai valid (defensive input)."""
    while True:
        mentah = input(f"{prompt}: ").strip()
        try:
            nilai = int(mentah)
        except ValueError:
            print("  ! Harus berupa angka bulat.")
            continue
        if nilai < 1:
            print("  ! Angka harus >= 1.")
            continue
        return nilai


MENU = """
=== TOKOCATAT - MENU UTAMA ===
1. Laporan keuangan & stok
2. Lihat stok akhir
3. Peringatan stok menipis
4. Cari barang
5. Catat penjualan
6. Catat pembelian (stok masuk)
7. Riwayat transaksi (filter)
8. Simpan hasil ke file
0. Keluar"""


def baca_tanggal_opsional(prompt, keterangan):
    """Minta tanggal YYYY-MM-DD; Enter kosong -> None. Ulangi sampai valid.

    Args:
        prompt (str): label isian.
        keterangan (str): arti Enter kosong (mis. 'hari ini', 'semua').
    Returns:
        str | None: tanggal valid atau None.
    """
    while True:
        mentah = input(f"{prompt} (YYYY-MM-DD, Enter = {keterangan}): ").strip()
        if not mentah:
            return None
        try:
            return validasi_tanggal(mentah, "input", 0)
        except TokoError:
            print("  ! Format harus YYYY-MM-DD dan tanggalnya harus ada di kalender.")


def catat_interaktif(a, d, jenis):
    """Alur tanya-jawab untuk mencatat satu transaksi. Returns state data terbaru."""
    print(report.tabel_stok(processor.daftar_stok(d["barang"], d["stok"])))
    kode = input("Kode barang: ")
    jumlah = baca_int_positif("Jumlah")
    tanggal = baca_tanggal_opsional("Tanggal", "hari ini")
    try:
        trx = catat_transaksi(d, a.transaksi, kode, jenis, jumlah, tanggal)
    except ValueError as exc:
        print(f"  ! Ditolak: {exc}")
        return d
    d = muat_data(a.barang, a.transaksi)
    print(f"  Tercatat {trx['id']}: {trx['jenis']} {trx['jumlah']} x {trx['kode_barang']}. "
          f"Stok sekarang: {d['stok'][trx['kode_barang']]}")
    return d


def cmd_menu(a):
    """Loop menu interaktif. Menangani input salah, Ctrl+C, dan EOF."""
    d = muat_data(a.barang, a.transaksi)
    print(f"Data dimuat: {len(d['barang'])} barang, {len(d['sah'])} transaksi sah, "
          f"{len(d['ditolak'])} data ditolak.")
    while True:
        print(MENU)
        try:
            pilih = input("Pilih menu: ").strip()
            if pilih == "0":
                print("Sampai jumpa.")
                return 0
            elif pilih == "1":
                print(buat_laporan(d)[0])
            elif pilih == "2":
                print(report.tabel_stok(processor.daftar_stok(d["barang"], d["stok"])))
            elif pilih == "3":
                print(report.tabel_stok(processor.stok_menipis(d["barang"], d["stok"])))
            elif pilih == "4":
                hasil = processor.cari_barang(d["barang"], input("Kata kunci (kode/nama/kategori): "))
                print(report.tabel_stok([{**b, "stok": d["stok"][b["kode"]],
                                          "status": processor.status_stok(d["stok"][b["kode"]], b["stok_minimum"])}
                                         for b in hasil]))
            elif pilih == "5":
                d = catat_interaktif(a, d, "JUAL")
            elif pilih == "6":
                d = catat_interaktif(a, d, "BELI")
            elif pilih == "7":
                jenis = input("Jenis (JUAL/BELI, Enter = semua): ").strip() or None
                dari = baca_tanggal_opsional("Dari tanggal", "semua")
                sampai = baca_tanggal_opsional("Sampai tanggal", "semua")
                kode = input("Kode barang (Enter = semua): ").strip() or None
                try:
                    hasil = processor.filter_transaksi(d["sah"], jenis, dari, sampai, kode)
                except ValueError as exc:
                    print(f"  ! {exc}")
                else:
                    print(f"{len(hasil)} transaksi cocok:\n")
                    print(report.tabel_transaksi(hasil))
            elif pilih == "8":
                simpan_hasil(d, OUTPUT_DEFAULT)
                print(f"Tersimpan di {OUTPUT_DEFAULT}/")
            else:
                print("  ! Pilihan tidak dikenal. Masukkan angka 0-8.")
        except (EOFError, KeyboardInterrupt):
            print("\nKeluar.")
            return 0


PERINTAH = {"laporan": cmd_laporan, "stok": cmd_stok, "riwayat": cmd_riwayat,
            "cari": cmd_cari, "catat": cmd_catat, "menu": cmd_menu}


def main(argv=None):
    """Titik masuk. Kode exit: 0 sukses, 1 error file/data, 2 input tidak valid, 130 dibatalkan."""
    args = buat_parser().parse_args(argv)
    if args.perintah is None:      # `python main.py` saja -> langsung menu interaktif
        args = argparse.Namespace(perintah="menu", barang=BARANG_DEFAULT, transaksi=TRANSAKSI_DEFAULT)
    try:
        return PERINTAH[args.perintah](args)
    except TokoError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Input tidak valid: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR sistem berkas: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nDibatalkan pengguna.", file=sys.stderr)
        return 130
