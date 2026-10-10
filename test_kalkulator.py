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

        # > 100jt -> 1.9%
        biaya_120, _ = hitung_admin_provisi("KUM", 120_000_000)
        self.assertEqual(biaya_120, 2_280_000)

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

        # Age 54 (diskon 18%), Tenor 24 bulan (2 tahun), Limit 75jt -> Rate 20.24 -> 1.518.000 * 0.82 = 1.244.760
        premi_54, ket_54 = self.reader.hitung_asuransi_jiwa(54, 24, 75_000_000)
        self.assertEqual(premi_54, 1_244_760)

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

if __name__ == "__main__":
    unittest.main()
