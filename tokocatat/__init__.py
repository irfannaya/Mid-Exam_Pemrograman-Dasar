"""tokocatat - paket pencatatan stok dan keuangan sederhana untuk toko kecil.

Modul:
    errors     : exception khusus aplikasi
    validator  : validasi & normalisasi satu baris data (barang / transaksi)
    fileio     : baca/tulis file CSV dan JSON
    processor  : logika bisnis (stok, laba-rugi, pencarian, filter)
    report     : pemformatan tampilan teks (termasuk format Rupiah)
    cli        : antarmuka command line (argparse + menu interaktif)
"""

__version__ = "1.0.0"
