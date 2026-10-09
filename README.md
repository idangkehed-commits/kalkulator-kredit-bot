# Bot Kalkulator Kredit (KUR & KUM)

Aplikasi bot kalkulator kredit untuk menghitung angsuran bulanan serta rincian biaya yang harus disiapkan oleh calon debitur untuk produk **Kredit Usaha Rakyat (KUR)** dan **Kredit Usaha Mikro (KUM)**.

---

## 📁 Lokasi Project
```
E:\kalkulator-kredit-bot\
│
├── kalkulator.py          # Modul logika perhitungan (Angsuran, Admin/Provisi, Asuransi Sijitu, Notaris)
├── bot.py                 # Bot interaktif versi Terminal / Command Prompt (CLI)
├── telegram_bot.py        # Bot interaktif versi TELEGRAM
├── config.json            # File konfigurasi Token Telegram Bot
├── run_bot.bat            # Shortcut klik 2x untuk membuka bot di Terminal
├── run_telegram_bot.bat   # Shortcut klik 2x untuk menjalankan Bot TELEGRAM
├── test_kalkulator.py     # Unit test pengujian akurasi perhitungan
└── excel_data\            # Folder untuk meletakkan file Excel kalkulator Asuransi Jiwa & Kerugian
```

---

## 🤖 Cara Menjalankan Bot Telegram

### 1. Dapatkan Token dari BotFather
1. Buka aplikasi Telegram di HP atau Laptop Anda.
2. Cari akun **@BotFather** (akun resmi Telegram bertanda centang biru).
3. Ketik `/newbot` lalu ikuti petunjuknya (masukkan nama bot dan username berakhiran `_bot`).
4. BotFather akan memberikan **HTTP API Token** (contoh: `123456789:ABCdefGhIJKlmNoPQRstuVWXyz`).

### 2. Pasang Token ke Bot
Ada 2 cara mudah:
* **Cara A:** Buka file `E:\kalkulator-kredit-bot\config.json`, lalu paste token Anda:
  ```json
  {
    "telegram_bot_token": "PASTE_TOKEN_ANDA_DISINI"
  }
  ```
* **Cara B:** Cukup klik 2x file **`run_telegram_bot.bat`**. Jika token masih kosong, jendela konsol akan otomatis meminta Anda untuk mem-paste token tersebut dan langsung menyimpannya.

### 3. Jalankan Bot
* Klik 2x file **`run_telegram_bot.bat`**.
* Buka bot Anda di Telegram dan ketik **/start** atau **/hitung**!

---

## 💻 Alternatif: Menjalankan Bot di Terminal (CLI)
1. Buka folder `E:\kalkulator-kredit-bot\` di Windows File Explorer.
2. Klik 2x file `run_bot.bat`.

---

## 📋 Alur Pertanyaan Bot (Start)
1. **Haloo, mau pengajuan apa nih?**
   - Pilihan: `[1] KUR` atau `[2] KUM`
2. **Limit pengajuan berapa?**
   - Format fleksibel: bisa tulis `110jt`, `110.000.000`, `50000000`, dsb.
3. **Mau Flat perbulan apa Efektif per tahun?**
   - Untuk **KUR**: otomatis dikunci ke **Efektif per tahun** (Anuitas).
   - Untuk **KUM**: user memilih tombol **Flat per bulan** atau **Efektif per tahun**.
4. **Mau pakai bunga berapa?**
   - Jika memilih **Flat per bulan**: ditanyakan persentase bunga flat per bulan (contoh: 0.9 atau 1).
   - Jika memilih **Efektif per tahun**: ditanyakan persentase bunga efektif per tahun (contoh: 11 atau 12, untuk KUR: 6% atau 7%).
5. **Tenor mau berapa?**
   - Diinput dalam satuan bulan (misal: `12`, `24`, `36`, `60`).
6. **Nama calon debitur?**
   - Nama lengkap calon debitur.
7. **Tanggal Lahir?**
   - Format `DD-MM-YYYY` (contoh: `17-08-1985`). Umur otomatis dihitung untuk dasar penentuan Asuransi Sijitu dan Asuransi Jiwa.
8. **Biaya Notaris?**
   - Diinput manual (ketik `0` jika tidak ada, atau masukkan nominal seperti `1500000`).

---

## 🧮 Logika & Rumus Perhitungan

### 1. Angsuran Bulanan
- **Efektif per tahun (Anuitas)**:
  $$r = \frac{\text{Bunga Pertahun}}{12 \times 100}$$
  $$\text{Angsuran} = \text{Limit} \times \frac{r \times (1 + r)^n}{(1 + r)^n - 1}$$
- **Flat per bulan**:
  $$\text{Pokok per bulan} = \frac{\text{Limit}}{n}$$
  $$\text{Bunga per bulan} = \text{Limit} \times \frac{\text{Bunga Flat Bulanan}}{100}$$
  $$\text{Total Angsuran} = \text{Pokok} + \text{Bunga}$$

### 2. Biaya Admin & Provisi
- **KUR**:
  - Limit 10 juta s/d 100 juta: **2%** dari limit pengajuan.
- **KUM**:
  - Limit s/d 100 juta: **1%** dari limit pengajuan.
  - Limit > 100 juta: **1.5%** dari limit pengajuan.

### 3. Asuransi Jiwa Kredit
- Dipengaruhi oleh: **Umur, Tenor, dan Limit Pengajuan**.
- Siap membaca tabel rumus dari file Excel yang diunggah ke folder `E:\kalkulator-kredit-bot\excel_data\`.

### 4. Asuransi Kerugian
- Syarat pembebanan:
  - **KUR**: Dibebankan jika pengajuan **di atas 100 juta**.
  - **KUM**: Dibebankan jika pengajuan **50 juta atau lebih**.
- Rumus akan membaca file Excel yang diunggah.

### 5. Biaya Notaris
- Diinput secara manual sesuai kesepakatan notaris.

### 6. Asuransi Sijitu
- Umur < 50 tahun: **Rp 600.000**
- Umur $\ge$ 50 tahun: **Rp 50.000**

---

## 📤 Upload File Excel Asuransi
Letakkan file Excel kalkulator Asuransi Jiwa dan Asuransi Kerugian ke dalam folder:
`E:\kalkulator-kredit-bot\excel_data\`

Setelah Anda mengunggah file tersebut, modul pembaca rumus di `kalkulator.py` akan segera dipetakan sesuai formula/tabel matriks yang ada di dalam Excel tersebut.
