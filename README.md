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
   - Format fleksibel & super ringkas: Cukup ketik angka jutanya saja, misal ketik **`10`** (untuk 10 Juta), **`50`** (50 Juta), **`110`** (110 Juta) s/d **`500`** (500 Juta).
   - Juga mendukung desimal seperti **`10.5`** atau **`12,5`** (12,5 Juta), serta format lengkap seperti `110jt`, `110.000.000`, `110000000`.
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
9. **Promo Biaya Admin & Provisi?**
   - Ditanyakan apakah ingin memakai promo Admin & Provisi:
     - Jika **Ya**: Biaya Admin & Provisi otomatis menjadi **Rp 1** (berlaku untuk semua jenis kredit: KUR, KUM, Top Up).
     - Jika **Tidak**: Dihitung menggunakan tarif reguler.
10. **Asuransi Kerugian (Jika dibebankan: KUR > 100jt atau KUM > 25jt)**
   - Pilihan Agunan: Kebakaran (FLEXAS), Mobil Pribadi (TLO), Motor (TLO), Truk/Pick Up (TLO).
   - **Nominal yang dicover (Nilai Pertanggungan Agunan)**: Ditanyakan berapa nominal objek yang ingin dicover (bebas diisi sesuai nilai agunan, atau tekan tombol/enter untuk sama dengan limit).
11. **Kartu BPJSTK (Khusus KUR > 100jt)**
   - Ditanyakan apakah calon debitur sudah memiliki kartu BPJSTK (Punya: Rp 0, Belum Punya: Rp 170.000).

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
- **🎉 Promo Admin & Provisi (Rp 1)**:
  - Berlaku untuk **seluruh jenis kredit** (KUR, KUM, Top Up KUM).
  - Jika promo aktif, Biaya Admin & Provisi otomatis menjadi **Rp 1** (Keterangan: `Promo Admin & Provisi`).
- **Tarif Normal (Tanpa Promo)**:
  - **KUR**:
    - Limit 10 juta s/d 100 juta: **2%** dari limit pengajuan.
    - Limit di atas 100 juta: **1.9%** dari limit pengajuan.
    - Limit di bawah 10 juta: **0%** (bebas biaya admin/provisi).
  - **KUM & Top Up KUM**:
    - Limit s/d 100 juta: **1%** dari limit pengajuan.
    - Limit 101 juta s/d 250 juta: **1.25%** dari limit pengajuan.
    - Limit 251 juta s/d 500 juta: **1.5%** dari limit pengajuan.

### 3. Asuransi Jiwa Kredit
- Dipengaruhi oleh: **Umur, Tenor, dan Limit Pengajuan**.
- Menggunakan perhitungan **Premi Dasar** murni (tanpa diskon 18%).
- Siap membaca tabel rumus dari file Excel yang diunggah ke folder `E:\kalkulator-kredit-bot\excel_data\`.

### 4. Asuransi Kerugian (Model AXA MyBiz Mikro)
- Syarat pembebanan:
  - **KUR**: Dibebankan jika pengajuan **di atas 100 juta**.
  - **KUM**: Dibebankan jika pengajuan **di atas 25 juta** (> 25jt).
- **Nominal Coverage / Nilai Pertanggungan (Sum Insured)**:
  - Tidak harus sama dengan limit pengajuan. Pengguna dapat menentukan nominal nilai pertanggungan agunan sendiri.
- Pilihan Jenis Agunan Kerugian:
  1. **Bangunan / Rumah Tinggal (Kebakaran FLEXAS)**: Rate dasar `0.294‰` per tahun dikali tenor terhadap nilai pertanggungan.
  2. **Kendaraan Mobil Pribadi (TLO)**: Rate OJK Zone 2 (`0.65%` s/d `0.20%` per tahun berdasarkan bracket nilai pertanggungan mobil) dikali tenor.
  3. **Kendaraan Sepeda Motor (TLO)**: Rate OJK `1.80%` per tahun dikali tenor terhadap nilai pertanggungan motor.
  4. **Kendaraan Truk / Pick Up (TLO)**: Rate OJK `1.68%` per tahun dikali tenor terhadap nilai pertanggungan truk.
- **Biaya Polis & Materai**: Dihilangkan (Rp 0), murni menghitung premi risiko.

### 5. Biaya Notaris
- Diinput secara manual sesuai kesepakatan notaris.

### 6. Asuransi Sijitu
- Umur < 50 tahun: **Rp 600.000**
- Umur $\ge$ 50 tahun: **Rp 50.000**

### 7. Biaya BPJSTK (Khusus KUR > 100 Juta)
- Ditanyakan pada saat pengajuan KUR > 100 juta: apakah calon debitur memiliki kartu BPJSTK (BPJS Ketenagakerjaan).
- Jika **Tidak Punya**: ditambahkan biaya sebesar **Rp 170.000** pada poin 6 rincian biaya.
- Jika **Punya**: **Rp 0** (bebas biaya).

### 8. Perhitungan Penerimaan Bersih & Blokir 2x Angsuran
- **Total Biaya Disiapkan**: Admin + Asuransi Jiwa + Asuransi Kerugian + Notaris + Sijitu + BPJSTK.
- **Blokir 2x Angsuran**: Disimpan pada Perhitungan Penerimaan Bersih sebesar $2 \times \text{Angsuran Bulanan}$.
- **Rumus Penerimaan Bersih Reguler**:
  $$\text{Dana Diterima Bersih} = \text{Limit Pengajuan} - \text{Total Biaya Disiapkan} - \text{Blokir 2x Angsuran}$$
- **Rumus Penerimaan Bersih Top Up (KUM)**:
  $$\text{Dana Diterima Bersih} = \text{Limit Baru} - \text{Sisa Pokok Hutang} - \text{Total Biaya Disiapkan} - \text{Blokir 2x Angsuran}$$

---

## 📱 Aplikasi Android (PWA & APK)

Tersedia aplikasi Android praktis yang dapat dipakai langsung oleh marketing/analis kredit di lapangan:

### 1. Langsung Pasang di HP Android (PWA - 100% Offline Ready)
1. Buka browser **Google Chrome** di HP Android Anda.
2. Akses alamat web bot: `https://kalkulator-kredit-bot.onrender.com/`
3. Ketuk tombol **"📲 Pasang App"** di bagian atas (atau ketuk menu titik tiga Chrome $\rightarrow$ pilih **"Tambahkan ke Layar Utama" / "Install Aplikasi"**).
4. Aplikasi akan terpasang di layar utama HP Anda dengan ikon resmi, layar penuh (fullscreen), dan **dapat digunakan offline tanpa kuota internet**!
5. Dilengkapi tombol **"Kirim WhatsApp"** untuk langsung mengirim rincian simulasi rapi ke calon debitur.

### 2. Source Code Aplikasi Flutter Android
- Source code lengkap aplikasi Flutter native berada di folder `flutter_app/`.
- Dapat dibuka menggunakan Android Studio / VS Code untuk di-build menjadi file installer `.apk` (`flutter build apk --release`).

---

## 📤 Upload File Excel Asuransi
Letakkan file Excel kalkulator Asuransi Jiwa dan Asuransi Kerugian ke dalam folder:
`E:\kalkulator-kredit-bot\excel_data\`

Setelah Anda mengunggah file tersebut, modul pembaca rumus di `kalkulator.py` akan segera dipetakan sesuai formula/tabel matriks yang ada di dalam Excel tersebut.
