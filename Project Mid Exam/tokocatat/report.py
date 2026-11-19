"""Pemformatan tampilan teks (single responsibility: presentasi)."""

GARIS = "=" * 60


def rupiah(angka):
    """Format bilangan bulat ke Rupiah: 1250000 -> 'Rp 1.250.000'."""
    teks = f"{abs(angka):,}".replace(",", ".")
    return f"-Rp {teks}" if angka < 0 else f"Rp {teks}"


def tabel_stok(baris):
    """Format list baris stok menjadi tabel teks. Pesan khusus bila kosong."""
    if not baris:
        return "(tidak ada barang yang cocok)"
    kepala = f"{'KODE':<6}{'NAMA':<20}{'KATEGORI':<12}{'STOK':>5}{'MIN':>5}  {'HARGA JUAL':>12}  STATUS"
    isi = [f"{r['kode']:<6}{r['nama']:<20}{r['kategori']:<12}{r['stok']:>5}"
           f"{r['stok_minimum']:>5}  {rupiah(r['harga_jual']):>12}  {r.get('status', '-')}"
           for r in baris]
    return "\n".join([kepala, "-" * len(kepala), *isi])


def tabel_transaksi(sah, limit=20):
    """Format transaksi sah menjadi tabel teks."""
    if not sah:
        return "(tidak ada transaksi yang cocok)"
    kepala = f"{'ID':<6}{'TANGGAL':<12}{'KODE':<6}{'JENIS':<6}{'JML':>5}  {'NILAI':>14}"
    isi = [f"{t['id']:<6}{t['tanggal']:<12}{t['kode_barang']:<6}{t['jenis']:<6}"
           f"{t['jumlah']:>5}  {rupiah(t['nilai']):>14}" for t in sah[:limit]]
    sisa = [f"... dan {len(sah) - limit} transaksi lainnya"] if len(sah) > limit else []
    return "\n".join([kepala, "-" * len(kepala), *isi, *sisa])


def format_laporan(ringkas, barang, stok_akhir, menipis, top, duplikat, ditolak):
    """Susun laporan keuangan & stok lengkap menjadi satu string.

    Args:
        ringkas (dict): hasil processor.hitung_keuangan.
        barang (dict): master barang.
        stok_akhir (dict): hasil processor.proses_transaksi.
        menipis (list[dict]): hasil processor.stok_menipis.
        top (list[tuple]): hasil processor.terlaris.
        duplikat (int): jumlah transaksi duplikat dibuang.
        ditolak (list[str]): semua pesan penolakan data/transaksi.
    """
    nilai = sum(stok_akhir[k] * b["harga_beli"] for k, b in barang.items())
    baris = [GARIS, "LAPORAN KEUANGAN & STOK TOKO", GARIS,
             f"Omzet penjualan          : {rupiah(ringkas['omzet'])}",
             f"Modal barang terjual     : {rupiah(ringkas['hpp'])}",
             f"Laba kotor               : {rupiah(ringkas['laba_kotor'])}  (margin {ringkas['margin']}%)",
             f"Belanja stok (periode)   : {rupiah(ringkas['belanja'])}",
             f"Nilai persediaan akhir   : {rupiah(nilai)}",
             f"Transaksi duplikat dibuang: {duplikat}",
             f"Data/transaksi ditolak   : {len(ditolak)}"]

    if not ringkas["per_hari"]:
        baris += ["", "Belum ada transaksi sah untuk dilaporkan."]
    else:
        baris += ["", "[Rekap Harian]",
                  f"  {'TANGGAL':<12}{'OMZET':>14}{'LABA':>14}{'BELANJA':>14}"]
        baris += [f"  {tgl:<12}{rupiah(h['omzet']):>14}{rupiah(h['laba']):>14}{rupiah(h['belanja']):>14}"
                  for tgl, h in ringkas["per_hari"].items()]
        baris += ["", "[Omzet per Kategori]"]
        baris += [f"  {k:<14}{rupiah(v):>14}"
                  for k, v in sorted(ringkas["per_kategori"].items(), key=lambda kv: -kv[1])]
        baris += ["", "[Barang Terlaris]"]
        baris += [f"  {i}. {barang[k]['nama']:<20}{n} unit" for i, (k, n) in enumerate(top, 1)]

    baris += ["", "[Peringatan Stok - perlu belanja ulang]"]
    if menipis:
        baris += [f"  {r['kode']} {r['nama']:<18} sisa {r['stok']:>3} (min {r['stok_minimum']})  -> {r['status']}"
                  for r in menipis]
    else:
        baris.append("  Semua stok aman.")

    if ditolak:
        baris += ["", "[Data / Transaksi Ditolak]"] + [f"  - {m}" for m in ditolak]
    return "\n".join(baris)
