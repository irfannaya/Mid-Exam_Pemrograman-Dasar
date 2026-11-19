"""Unit test (unittest, standard library). Jalankan: python -m unittest -v"""

import contextlib
import io
import os
import shutil
import tempfile
import unittest
from unittest import mock

from tokocatat import cli, fileio, processor, report
from tokocatat.errors import DataFileError, DataFormatError
from tokocatat.validator import parse_barang, parse_transaksi

BARANG = {
    "B1": {"kode": "B1", "nama": "Beras", "kategori": "Sembako",
           "harga_beli": 10000, "harga_jual": 12000, "stok": 10, "stok_minimum": 3},
    "B2": {"kode": "B2", "nama": "Kopi", "kategori": "Minuman",
           "harga_beli": 1000, "harga_jual": 1500, "stok": 5, "stok_minimum": 2},
}


def trx(id, tgl, kode, jenis, jml):
    return {"id": id, "tanggal": tgl, "kode_barang": kode, "jenis": jenis, "jumlah": jml}


class TestValidator(unittest.TestCase):
    def test_barang_valid(self):
        b = parse_barang({"kode": "b1", "nama": "Beras", "kategori": "S", "harga_beli": "100",
                          "harga_jual": "120", "stok": "5", "stok_minimum": "1"}, 2)
        self.assertEqual((b["kode"], b["harga_jual"]), ("B1", 120))

    def test_harga_jual_lebih_kecil(self):
        with self.assertRaises(DataFormatError):
            parse_barang({"kode": "B", "nama": "x", "kategori": "k", "harga_beli": "100",
                          "harga_jual": "50", "stok": "1", "stok_minimum": "0"}, 2)

    def test_transaksi_tidak_valid(self):
        dasar = {"id": "T1", "tanggal": "2026-10-01", "kode_barang": "B1", "jenis": "JUAL", "jumlah": "2"}
        self.assertEqual(parse_transaksi(dasar, 2)["jumlah"], 2)
        for ubah in ({"jumlah": "0"}, {"jumlah": "dua"}, {"tanggal": "2026-13-01"}, {"jenis": "RETUR"}):
            with self.assertRaises(DataFormatError):
                parse_transaksi({**dasar, **ubah}, 2)


class TestProcessor(unittest.TestCase):
    def test_duplikat_id(self):
        data = [trx("T1", "2026-10-01", "B1", "JUAL", 1)] * 2 + [trx("T2", "2026-10-01", "B1", "JUAL", 1)]
        unik, dibuang = processor.hapus_duplikat_id(data)
        self.assertEqual((len(unik), dibuang), (2, 1))

    def test_stok_dan_keuangan_hitung_manual(self):
        data = [trx("T1", "2026-10-01", "B1", "JUAL", 4),    # omzet 48.000, modal 40.000
                trx("T2", "2026-10-02", "B1", "BELI", 5)]    # belanja 50.000
        stok, sah, ditolak = processor.proses_transaksi(BARANG, data)
        self.assertEqual((stok["B1"], ditolak), (11, []))
        k = processor.hitung_keuangan(sah, BARANG)
        self.assertEqual((k["omzet"], k["hpp"], k["laba_kotor"], k["belanja"]),
                         (48000, 40000, 8000, 50000))
        self.assertEqual(k["margin"], 16.7)

    def test_edge_jual_pas_habis_dan_kelebihan(self):
        stok, sah, ditolak = processor.proses_transaksi(BARANG, [trx("T1", "2026-10-01", "B1", "JUAL", 10)])
        self.assertEqual(stok["B1"], 0)                       # tepat habis: diizinkan
        stok, sah, ditolak = processor.proses_transaksi(BARANG, [trx("T1", "2026-10-01", "B1", "JUAL", 11)])
        self.assertEqual((stok["B1"], len(sah), len(ditolak)), (10, 0, 1))   # kelebihan: ditolak

    def test_kode_tidak_terdaftar(self):
        _, sah, ditolak = processor.proses_transaksi(BARANG, [trx("T1", "2026-10-01", "ZZZ", "JUAL", 1)])
        self.assertEqual((sah, len(ditolak)), ([], 1))

    def test_tanpa_transaksi_edge_case(self):
        stok, sah, _ = processor.proses_transaksi(BARANG, [])
        k = processor.hitung_keuangan(sah, BARANG)
        self.assertEqual((k["omzet"], k["margin"], k["per_hari"]), (0, 0.0, {}))
        self.assertIn("Belum ada transaksi", report.format_laporan(k, BARANG, stok, [], [], 0, []))

    def test_status_dan_menipis(self):
        self.assertEqual([processor.status_stok(*a) for a in ((0, 3), (3, 3), (4, 3))],
                         ["HABIS", "MENIPIS", "AMAN"])
        self.assertEqual([r["kode"] for r in processor.stok_menipis(BARANG, {"B1": 3, "B2": 9})], ["B1"])

    def test_cari_filter_id(self):
        self.assertEqual(len(processor.cari_barang(BARANG, "KOPI")), 1)
        self.assertEqual(processor.cari_barang(BARANG, "  "), [])
        data = [trx("T1", "2026-10-01", "B1", "JUAL", 1), trx("T2", "2026-10-05", "B1", "BELI", 1)]
        self.assertEqual(len(processor.filter_transaksi(data, jenis="beli")), 1)
        self.assertEqual(len(processor.filter_transaksi(data, tanggal_awal="2026-10-02")), 1)
        with self.assertRaises(ValueError):
            processor.filter_transaksi(data, jenis="RETUR")
        with self.assertRaises(ValueError):
            processor.filter_transaksi(data, tanggal_awal="besok")
        self.assertEqual(processor.id_baru(data), "T003")
        self.assertEqual(processor.id_baru([]), "T001")

    def test_periksa_transaksi_baru(self):
        stok = {"B1": 10, "B2": 5}
        self.assertEqual(processor.periksa_transaksi_baru(BARANG, stok, " b1 ", "jual", 3), ("B1", "JUAL"))
        for args in (("X", "JUAL", 1), ("B1", "RETUR", 1), ("B1", "JUAL", 0), ("B1", "JUAL", 11)):
            with self.assertRaises(ValueError):
                processor.periksa_transaksi_baru(BARANG, stok, *args)


class TestFileIO(unittest.TestCase):
    def test_file_tidak_ada(self):
        with self.assertRaises(DataFileError):
            fileio.baca_barang("tidak_ada.csv")

    def test_kolom_kurang(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "b.csv")
            with open(p, "w") as fh:
                fh.write("kode,nama\nB1,Beras\n")
            with self.assertRaises(DataFileError):
                fileio.baca_barang(p)

    def test_rupiah(self):
        self.assertEqual(report.rupiah(1250000), "Rp 1.250.000")
        self.assertEqual(report.rupiah(0), "Rp 0")
        self.assertEqual(report.rupiah(-5000), "-Rp 5.000")

    def test_catat_transaksi_menambah_baris(self):
        with tempfile.TemporaryDirectory() as d:
            b, t = os.path.join(d, "barang.csv"), os.path.join(d, "transaksi.csv")
            shutil.copy("data/input/barang.csv", b)
            shutil.copy("data/input/transaksi.csv", t)
            data = cli.muat_data(b, t)
            baru = cli.catat_transaksi(data, t, "b002", "jual", 2, "2026-10-11")
            self.assertEqual(baru["id"], "T036")
            self.assertEqual(cli.muat_data(b, t)["stok"]["B002"], data["stok"]["B002"] - 2)
            with self.assertRaises(ValueError):
                cli.catat_transaksi(data, t, "B002", "JUAL", 2, "kemarin")


class TestMenu(unittest.TestCase):
    def jalankan(self, argv, masukan):
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=masukan), contextlib.redirect_stdout(out):
            kode = cli.main(argv)
        return kode, out.getvalue()

    def test_tanpa_argumen_langsung_menu(self):
        kode, out = self.jalankan([], ["0"])
        self.assertEqual(kode, 0)
        self.assertIn("MENU UTAMA", out)

    def test_menu_pilihan_salah_lalu_keluar(self):
        kode, out = self.jalankan([], ["x", "99", "0"])
        self.assertEqual(out.count("Pilihan tidak dikenal"), 2)

    def test_menu_catat_penjualan_dan_validasi_input(self):
        with tempfile.TemporaryDirectory() as d:
            b, t = os.path.join(d, "b.csv"), os.path.join(d, "t.csv")
            shutil.copy("data/input/barang.csv", b)
            shutil.copy("data/input/transaksi.csv", t)
            # jumlah 'abc' dan '0' diulang, tanggal salah diulang, lalu valid
            masukan = ["5", "b002", "abc", "0", "3", "kemarin", "2026-10-11", "0"]
            kode, out = self.jalankan(["menu", "-b", b, "-t", t], masukan)
            self.assertIn("Tercatat T036", out)
            self.assertIn("Harus berupa angka bulat", out)
            self.assertIn("Format harus YYYY-MM-DD", out)
            self.assertTrue(open(t).read().rstrip().endswith("T036,2026-10-11,B002,JUAL,3"))

    def test_menu_penjualan_melebihi_stok_ditolak(self):
        with tempfile.TemporaryDirectory() as d:
            b, t = os.path.join(d, "b.csv"), os.path.join(d, "t.csv")
            shutil.copy("data/input/barang.csv", b)
            shutil.copy("data/input/transaksi.csv", t)
            sebelum = open(t).read()
            kode, out = self.jalankan(["menu", "-b", b, "-t", t], ["5", "B008", "1", "", "0"])
            self.assertIn("Ditolak: stok B008 tidak cukup", out)
            self.assertEqual(open(t).read(), sebelum)


if __name__ == "__main__":
    unittest.main()
