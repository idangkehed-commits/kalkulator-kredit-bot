# -*- coding: utf-8 -*-
import unittest
from datetime import date
from kalkulator import (
    hitung_umur,
    hitung_angsuran_efektif,
    hitung_angsuran_flat,
    hitung_admin_provisi,
    hitung_asuransi_sijitu,
    is_asuransi_kerugian_dibebankan,
    kalkulasi_lengkap,
    generate_hasil_teks,
    ExcelInsuranceReader
)

class TestKalkulatorKredit(unittest.TestCase):
    def setUp(self):
        self.reader = ExcelInsuranceReader()

    def test_hitung_umur(self):
        tgl_lahir = date(1990, 5, 10)
        ref_date = date(2026, 10, 9)
        self.assertEqual(hitung_umur(tgl_lahir, ref_date), 36)

        tgl_lahir_50 = date(1975, 1, 1)
        self.assertEqual(hitung_umur(tgl_lahir_50, ref_date), 51)

    def test_angsuran_efektif(self):
        angsuran = hitung_angsuran_efektif(110_000_000, 6.0, 36)
        self.assertTrue(3_340_000 < angsuran < 3_355_000)

    def test_angsuran_flat(self):
        angsuran = hitung_angsuran_flat(60_000_000, 1.0, 12)
        self.assertEqual(angsuran, 5_600_000)

    def test_admin_provisi_kur(self):
        biaya, _ = hitung_admin_provisi("KUR", 50_000_000)
        self.assertEqual(biaya, 1_000_000)

        biaya_100, _ = hitung_admin_provisi("KUR", 100_000_000)
        self.assertEqual(biaya_100, 2_000_000)

        # > 100jt -> 1.9%
        biaya_110, _ = hitung_admin_provisi("KUR", 110_000_000)
        self.assertEqual(biaya_110, 2_090_000)

    def test_admin_provisi_kum(self):
        biaya, _ = hitung_admin_provisi("KUM", 80_000_000)
        self.assertEqual(biaya, 800_000)

        # > 100jt -> tetap 1.5%
        biaya_120, _ = hitung_admin_provisi("KUM", 120_000_000)
        self.assertEqual(biaya_120, 1_800_000)

    def test_asuransi_sijitu(self):
        biaya_35, _ = hitung_asuransi_sijitu(35)
        self.assertEqual(biaya_35, 600_000)

        biaya_50, _ = hitung_asuransi_sijitu(50)
        self.assertEqual(biaya_50, 50_000)

        biaya_60, _ = hitung_asuransi_sijitu(60)
        self.assertEqual(biaya_60, 50_000)

    def test_asuransi_kerugian_syarat(self):
        dibebankan, _ = is_asuransi_kerugian_dibebankan("KUR", 100_000_000)
        self.assertFalse(dibebankan)

        dibebankan, _ = is_asuransi_kerugian_dibebankan("KUR", 100_000_001)
        self.assertTrue(dibebankan)

        dibebankan, _ = is_asuransi_kerugian_dibebankan("KUM", 49_000_000)
        self.assertFalse(dibebankan)

        dibebankan, _ = is_asuransi_kerugian_dibebankan("KUM", 50_000_000)
        self.assertTrue(dibebankan)

    def test_excel_asuransi_jiwa(self):
        # Age 38, Tenor 36 bulan (3 tahun), Limit 110jt -> Rate 5.90 -> 649.000
        premi, ket = self.reader.hitung_asuransi_jiwa(38, 36, 110_000_000)
        self.assertEqual(premi, 649_000)

        # Age 54 (premi dasar, tanpa diskon 18%), Tenor 24 bulan (2 tahun), Limit 75jt -> Rate 20.24 -> 1.518.000
        premi_54, ket_54 = self.reader.hitung_asuransi_jiwa(54, 24, 75_000_000)
        self.assertEqual(premi_54, 1_518_000)

    def test_excel_asuransi_kerugian(self):
        # KUR 110jt (dibebankan): Tenor 3 tahun: 3 * (110jt * 0.294/1000) = 97.020 + 25.000 + 10.000 = 132.020
        total, ket = self.reader.hitung_asuransi_kerugian("KUR", 110_000_000, 36)
        self.assertEqual(total, 132_020)

        # KUR 80jt (tidak dibebankan): Rp 0
        total_80, _ = self.reader.hitung_asuransi_kerugian("KUR", 80_000_000, 36)
        self.assertEqual(total_80, 0)

    def test_full_simulasi_teks(self):
        data = {
            "jenis_kredit": "KUR",
            "limit": 110_000_000,
            "tenor": 36,
            "bunga": 6.0,
            "tipe_bunga": "efektif",
            "tanggal_lahir": date(1988, 3, 15),
            "nama": "Budi Santoso",
            "biaya_notaris": 1_250_000
        }
        hasil = kalkulasi_lengkap(data, self.reader)
        teks = generate_hasil_teks(hasil)
        print("\n--- OUTPUT TEST SIMULASI LENGKAP ---")
        print(teks)
        self.assertIn("**Pengajuan KUR limit 110.000.000 tenor 36 bulan**", teks)
        self.assertIn("Angsuran:", teks)
        self.assertIn("1. Admin & Provisi", teks)
        self.assertIn("Rp 2.090.000", teks)
        self.assertIn("Rp 649.000", teks)
        self.assertIn("Rp 132.020", teks)
        self.assertIn("5. Asuransi Sijitu", teks)
        self.assertIn("Rp 4.721.020", teks)

    def test_topup_kum(self):
        data = {
            "jenis_kredit": "Top Up KUM",
            "is_topup": True,
            "sisa_bade": 20_000_000,
            "limit": 80_000_000,
            "tenor": 24,
            "bunga": 1.0,
            "tipe_bunga": "flat",
            "tanggal_lahir": date(1988, 3, 15),
            "nama": "Ahmad Topup",
            "biaya_notaris": 0
        }
        hasil = kalkulasi_lengkap(data, self.reader)
        self.assertTrue(hasil["is_topup"])
        self.assertEqual(hasil["sisa_bade"], 20_000_000)
        self.assertEqual(hasil["biaya_admin"], 800_000)  # 1% untuk KUM <= 100jt
        self.assertEqual(hasil["biaya_jiwa"], 337_600)
        self.assertEqual(hasil["biaya_kerugian"], 82_040)  # KUM >= 50jt dibebankan
        self.assertEqual(hasil["biaya_sijitu"], 600_000)
        self.assertEqual(hasil["total_biaya"], 1_819_640)
        # Dana cair = 80jt - 20jt - 1.819.640 = 58.180.360
        self.assertEqual(hasil["dana_cair_bersih"], 58_180_360)

        teks = generate_hasil_teks(hasil)
        print("\n--- OUTPUT TEST TOP UP KUM ---")
        print(teks)
        self.assertIn("**Pengajuan Top Up KUM limit 80.000.000 tenor 24 bulan**", teks)
        self.assertIn("Perhitungan Penerimaan Bersih (Top Up):", teks)
        self.assertIn("- Sisa Pokok / Bade Hutang  : Rp 20.000.000", teks)
        self.assertIn("- Total Biaya Disiapkan     : Rp 1.819.640", teks)
        self.assertIn("Estimasi Dana Diterima Bersih : Rp 58.180.360", teks)

    def test_kur_bpjstk(self):
        # KUR 110jt, tidak punya BPJSTK -> + Rp 168.000
        data_tidak = {
            "jenis_kredit": "KUR",
            "limit": 110_000_000,
            "tenor": 36,
            "bunga": 6.0,
            "tipe_bunga": "efektif",
            "tanggal_lahir": date(1988, 3, 15),
            "nama": "Budi Santoso",
            "biaya_notaris": 1_250_000,
            "punya_bpjstk": False
        }
        hasil_tidak = kalkulasi_lengkap(data_tidak, self.reader)
        self.assertEqual(hasil_tidak["biaya_bpjstk"], 168_000)
        self.assertEqual(hasil_tidak["total_biaya"], 4_889_020)
        teks_tidak = generate_hasil_teks(hasil_tidak)
        print("\n--- OUTPUT TEST KUR BPJSTK TIDAK PUNYA ---")
        print(teks_tidak)
        self.assertIn("6. BPJSTK                : Rp 168.000", teks_tidak)
        self.assertIn("Rp 4.889.020", teks_tidak)

        # KUR 110jt, punya BPJSTK -> Rp 0
        data_punya = {
            "jenis_kredit": "KUR",
            "limit": 110_000_000,
            "tenor": 36,
            "bunga": 6.0,
            "tipe_bunga": "efektif",
            "tanggal_lahir": date(1988, 3, 15),
            "nama": "Budi Santoso",
            "biaya_notaris": 1_250_000,
            "punya_bpjstk": True
        }
        hasil_punya = kalkulasi_lengkap(data_punya, self.reader)
        self.assertEqual(hasil_punya["biaya_bpjstk"], 0)
        self.assertEqual(hasil_punya["total_biaya"], 4_721_020)
        teks_punya = generate_hasil_teks(hasil_punya)
        print("\n--- OUTPUT TEST KUR BPJSTK PUNYA ---")
        print(teks_punya)
        self.assertIn("6. BPJSTK                : Rp 0 (Sudah punya kartu)", teks_punya)

if __name__ == "__main__":
    unittest.main()
