import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

void main() {
  runApp(const KalkulatorKreditApp());
}

class KalkulatorKreditApp extends StatelessWidget {
  const KalkulatorKreditApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Kalkulator Kredit Mikro',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0F4C81),
          primary: const Color(0xFF0F4C81),
        ),
      ),
      home: const KalkulatorScreen(),
    );
  }
}

class KalkulatorScreen extends StatefulWidget {
  const KalkulatorScreen({super.key});

  @override
  State<KalkulatorScreen> createState() => _KalkulatorScreenState();
}

class _KalkulatorScreenState extends State<KalkulatorScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // Form Controllers
  final TextEditingController _limitController = TextEditingController(text: '110.000.000');
  final TextEditingController _sisaBadeController = TextEditingController(text: '20.000.000');
  final TextEditingController _bungaController = TextEditingController(text: '6.0');
  final TextEditingController _tenorController = TextEditingController(text: '36');
  final TextEditingController _namaController = TextEditingController(text: 'Budi Santoso');
  final TextEditingController _notarisController = TextEditingController(text: '1.250.000');

  String _jenisKredit = 'KUR'; // KUR, KUM, Top Up KUM
  String _tipeBunga = 'efektif'; // flat, efektif
  DateTime _tanggalLahir = DateTime(1988, 3, 15);
  bool _punyaBpjstk = false;

  final NumberFormat _currencyFormat = NumberFormat.currency(
    locale: 'id_ID',
    symbol: 'Rp ',
    decimalDigits: 0,
  );

  static const Map<int, List<double>> _jiwaRates = {
    18: [1.78, 2.70, 3.42, 3.71, 4.25], 19: [1.78, 2.70, 3.42, 3.71, 4.25],
    20: [1.78, 2.70, 3.42, 3.71, 4.25], 21: [1.78, 2.70, 3.42, 3.71, 4.25],
    22: [1.78, 2.70, 3.42, 3.71, 4.25], 23: [1.78, 2.70, 3.42, 3.71, 4.25],
    24: [1.78, 2.70, 3.42, 3.71, 4.25], 25: [1.78, 2.70, 3.42, 3.71, 4.25],
    26: [1.78, 2.70, 3.42, 3.71, 4.25], 27: [1.78, 2.70, 3.42, 3.71, 4.25],
    28: [1.78, 2.70, 3.42, 3.71, 4.25], 29: [1.78, 2.70, 3.42, 3.71, 4.25],
    30: [1.78, 2.70, 3.42, 3.71, 4.25], 31: [1.83, 2.83, 3.96, 4.47, 5.24],
    32: [1.83, 2.83, 3.96, 4.47, 5.24], 33: [1.83, 2.83, 3.96, 4.47, 5.24],
    34: [1.83, 2.83, 3.96, 4.47, 5.24], 35: [1.83, 2.83, 3.96, 4.47, 5.24],
    36: [2.73, 4.22, 5.90, 6.68, 7.83], 37: [2.73, 4.22, 5.90, 6.68, 7.83],
    38: [2.73, 4.22, 5.90, 6.68, 7.83], 39: [2.73, 4.22, 5.90, 6.68, 7.83],
    40: [2.73, 4.22, 5.90, 6.68, 7.83], 41: [4.66, 7.32, 10.26, 11.58, 13.56],
    42: [4.66, 7.32, 10.26, 11.58, 13.56], 43: [4.66, 7.32, 10.26, 11.58, 13.56],
    44: [4.66, 7.32, 10.26, 11.58, 13.56], 45: [4.66, 7.32, 10.26, 11.58, 13.56],
    46: [7.11, 12.69, 17.79, 20.08, 23.52], 47: [7.11, 12.69, 17.79, 20.08, 23.52],
    48: [7.11, 12.69, 17.79, 20.08, 23.52], 49: [7.11, 12.69, 17.79, 20.08, 23.52],
    50: [7.11, 12.69, 17.79, 20.08, 23.52], 51: [11.21, 20.24, 28.38, 32.04, 37.53],
    52: [11.21, 20.24, 28.38, 32.04, 37.53], 53: [11.21, 20.24, 28.38, 32.04, 37.53],
    54: [11.21, 20.24, 28.38, 32.04, 37.53], 55: [11.21, 20.24, 28.38, 32.04, 37.53],
    56: [15.98, 28.49, 39.95, 45.10, 52.84], 57: [15.98, 28.49, 39.95, 45.10, 52.84],
    58: [15.98, 28.49, 39.95, 45.10, 52.84], 59: [15.98, 28.49, 39.95, 45.10, 52.84],
    60: [15.98, 28.49, 39.95, 45.10, 52.84], 61: [20.76, 33.46, 47.84, 54.01, 63.27],
    62: [20.76, 33.46, 47.84, 54.01, 63.27], 63: [20.76, 33.46, 47.84, 54.01, 63.27],
    64: [20.76, 33.46, 47.84, 54.01, 63.27], 65: [20.76, 33.46, 47.84, 54.01, 63.27]
  };

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(() {
      if (_tabController.indexIsChanging) return;
      setState(() {
        if (_tabController.index == 0) {
          _jenisKredit = 'KUR';
          _tipeBunga = 'efektif';
          _bungaController.text = '6.0';
        } else if (_tabController.index == 1) {
          _jenisKredit = 'KUM';
          _bungaController.text = '1.0';
        } else {
          _jenisKredit = 'Top Up KUM';
          _bungaController.text = '1.0';
        }
      });
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _limitController.dispose();
    _sisaBadeController.dispose();
    _bungaController.dispose();
    _tenorController.dispose();
    _namaController.dispose();
    _notarisController.dispose();
    super.dispose();
  }

  double _parseNominal(String text) {
    final clean = text.replaceAll(RegExp(r'[^\d]'), '');
    return double.tryParse(clean) ?? 0.0;
  }

  int _hitungUmur(DateTime birth) {
    final today = DateTime.now();
    int age = today.year - birth.year;
    if (today.month < birth.month || (today.month == birth.month && today.day < birth.day)) {
      age--;
    }
    return age;
  }

  double _hitungJiwaRate(int umur, int tenorBulan) {
    final effAge = umur.clamp(18, 65);
    final rowRates = _jiwaRates[effAge] ?? _jiwaRates[30]!;
    final termYear = tenorBulan ~/ 12;
    final termMonth = tenorBulan % 12;

    if (termYear < 1) {
      return double.parse((rowRates[0] * (tenorBulan / 12.0)).toStringAsFixed(2));
    } else if (termYear >= 5) {
      return rowRates[4];
    } else {
      final rateCurr = rowRates[termYear - 1];
      final rateNext = termYear < rowRates.length ? rowRates[termYear] : rateCurr;
      return double.parse((rateCurr + (rateNext - rateCurr) * (termMonth / 12.0)).toStringAsFixed(2));
    }
  }

  @override
  Widget build(BuildContext context) {
    final limit = _parseNominal(_limitController.text);
    final sisaBade = _parseNominal(_sisaBadeController.text);
    final bungaVal = double.tryParse(_bungaController.text.replaceAll(',', '.')) ?? 0.0;
    final tenorBulan = int.tryParse(_tenorController.text) ?? 12;
    final notaris = _parseNominal(_notarisController.text);
    final umur = _hitungUmur(_tanggalLahir);

    final isKur = _jenisKredit.contains('KUR');
    final isTopUp = _jenisKredit.contains('Top Up');

    // Angsuran
    int angsuran = 0;
    String infoBunga = '';
    if (isKur || _tipeBunga == 'efektif') {
      if (bungaVal <= 0) {
        angsuran = (limit / tenorBulan).round();
      } else {
        final r = (bungaVal / 100) / 12;
        final pmt = limit * (r * pow(1 + r, tenorBulan)) / (pow(1 + r, tenorBulan) - 1);
        angsuran = pmt.round();
      }
      infoBunga = 'Bunga Efektif ${bungaVal.toStringAsFixed(2)}% per tahun';
    } else {
      final pokok = limit / tenorBulan;
      final bungaRp = limit * (bungaVal / 100);
      angsuran = (pokok + bungaRp).round();
      infoBunga = 'Bunga Flat ${bungaVal.toStringAsFixed(2)}% per bulan';
    }

    // 1. Admin & Provisi
    int biayaAdmin = 0;
    String ketAdmin = '';
    if (isKur) {
      if (limit < 10000000) {
        biayaAdmin = 0;
        ketAdmin = '0% (< 10jt)';
      } else if (limit <= 100000000) {
        biayaAdmin = (0.02 * limit).round();
        ketAdmin = '2% (10jt s/d 100jt)';
      } else {
        biayaAdmin = (0.019 * limit).round();
        ketAdmin = '1.9% (> 100jt)';
      }
    } else {
      if (limit <= 100000000) {
        biayaAdmin = (0.01 * limit).round();
        ketAdmin = '1% (s/d 100jt)';
      } else {
        biayaAdmin = (0.015 * limit).round();
        ketAdmin = '1.5% (> 100jt)';
      }
    }

    // 2. Asuransi Jiwa Kredit (Premi Dasar murni)
    final jiwaRate = _hitungJiwaRate(umur, tenorBulan);
    final biayaJiwa = (jiwaRate * limit / 1000.0).round();

    // 3. Asuransi Kerugian
    int biayaKerugian = 0;
    final dibebankanKerugian = isKur ? (limit > 100000000) : (limit >= 50000000);
    if (dibebankanKerugian) {
      final flexas = (tenorBulan / 12.0) * (limit * 0.294 / 1000.0);
      final materai = flexas >= 5000000 ? 20000 : 10000;
      biayaKerugian = (flexas + 25000 + materai).round();
    }

    // 4. Biaya Notaris
    final biayaNotaris = notaris.round();

    // 5. Asuransi Sijitu
    final biayaSijitu = umur >= 50 ? 50000 : 600000;

    // 6. BPJSTK (Khusus KUR > 100jt)
    final showBpjstk = isKur && (limit > 100000000);
    final biayaBpjstk = (showBpjstk && !_punyaBpjstk) ? 168000 : 0;

    // Total Biaya
    final totalBiaya = biayaAdmin + biayaJiwa + biayaKerugian + biayaNotaris + biayaSijitu + biayaBpjstk;
    final danaCairBersih = (limit - sisaBade - totalBiaya).round();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Kalkulator Kredit Mikro', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        backgroundColor: const Color(0xFF0F4C81),
        foregroundColor: Colors.white,
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.amber,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white70,
          tabs: const [
            Tab(text: 'KUR'),
            Tab(text: 'KUM'),
            Tab(text: 'Top Up KUM'),
          ],
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Banner Hasil Angsuran
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF092C4C), Color(0xFF0F4C81)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('PENGAJUAN $_jenisKredit', style: const TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 6),
                Text(
                  '${_currencyFormat.format(angsuran)} / bln',
                  style: const TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.18),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(infoBunga, style: const TextStyle(color: Colors.white, fontSize: 12)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Form Input
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Parameter Pinjaman', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                  const SizedBox(height: 12),

                  // Limit Pengajuan
                  TextField(
                    controller: _limitController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Limit Pengajuan (Plafond)',
                      prefixText: 'Rp ',
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (val) {
                      final n = _parseNominal(val);
                      _limitController.value = TextEditingValue(
                        text: NumberFormat('#,###', 'id_ID').format(n),
                        selection: TextSelection.collapsed(offset: NumberFormat('#,###', 'id_ID').format(n).length),
                      );
                      setState(() {});
                    },
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    children: [10, 25, 50, 100, 110, 200, 500].map((jt) {
                      return ActionChip(
                        label: Text('$jt Jt', style: const TextStyle(fontSize: 11)),
                        onPressed: () {
                          setState(() {
                            _limitController.text = NumberFormat('#,###', 'id_ID').format(jt * 1000000);
                          });
                        },
                      );
                    }).toList(),
                  ),

                  // Sisa Pokok Hutang (Khusus Top Up KUM)
                  if (isTopUp) ...[
                    const SizedBox(height: 16),
                    TextField(
                      controller: _sisaBadeController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Sisa Pokok Hutang / Baki Debet',
                        prefixText: 'Rp ',
                        border: OutlineInputBorder(),
                      ),
                      onChanged: (_) => setState(() {}),
                    ),
                  ],

                  // Pilihan Tipe Bunga (Khusus KUM)
                  if (!isKur) ...[
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            style: OutlinedButton.styleFrom(
                              backgroundColor: _tipeBunga == 'flat' ? const Color(0xFF0F4C81).withOpacity(0.1) : null,
                              side: BorderSide(color: _tipeBunga == 'flat' ? const Color(0xFF0F4C81) : Colors.grey),
                            ),
                            onPressed: () => setState(() => _tipeBunga = 'flat'),
                            child: const Text('Flat per bulan'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: OutlinedButton(
                            style: OutlinedButton.styleFrom(
                              backgroundColor: _tipeBunga == 'efektif' ? const Color(0xFF0F4C81).withOpacity(0.1) : null,
                              side: BorderSide(color: _tipeBunga == 'efektif' ? const Color(0xFF0F4C81) : Colors.grey),
                            ),
                            onPressed: () => setState(() => _tipeBunga = 'efektif'),
                            child: const Text('Efektif per tahun'),
                          ),
                        ),
                      ],
                    ),
                  ],

                  const SizedBox(height: 16),
                  TextField(
                    controller: _bungaController,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: 'Suku Bunga (${isKur || _tipeBunga == 'efektif' ? '% per tahun' : '% per bulan'})',
                      border: const OutlineInputBorder(),
                    ),
                    onChanged: (_) => setState(() {}),
                  ),

                  const SizedBox(height: 16),
                  TextField(
                    controller: _tenorController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Tenor (Bulan)',
                      border: const OutlineInputBorder(),
                    ),
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    children: [12, 24, 36, 48, 60].map((bln) {
                      return ActionChip(
                        label: Text('$bln Bln', style: const TextStyle(fontSize: 11)),
                        onPressed: () => setState(() => _tenorController.text = '$bln'),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Data Debitur
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Data Calon Debitur', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _namaController,
                    decoration: const InputDecoration(labelText: 'Nama Debitur', border: OutlineInputBorder()),
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 12),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('Tgl Lahir: ${DateFormat('dd-MM-yyyy').format(_tanggalLahir)} (Umur: $umur th)'),
                    trailing: const Icon(Icons.calendar_month, color: Color(0xFF0F4C81)),
                    onTap: () async {
                      final picked = await showDatePicker(
                        context: context,
                        initialDate: _tanggalLahir,
                        firstDate: DateTime(1950),
                        lastDate: DateTime.now(),
                      );
                      if (picked != null) setState(() => _tanggalLahir = picked);
                    },
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _notarisController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Biaya Notaris (Opsional)',
                      prefixText: 'Rp ',
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (_) => setState(() {}),
                  ),
                  if (showBpjstk) ...[
                    const SizedBox(height: 12),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Sudah Punya Kartu BPJSTK?'),
                      subtitle: Text(_punyaBpjstk ? 'Bebas Biaya (Rp 0)' : 'Dikenakan biaya Rp 168.000'),
                      value: _punyaBpjstk,
                      onChanged: (val) => setState(() => _punyaBpjstk = val),
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Rincian Biaya
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Rincian Biaya Calon Debitur', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                  const SizedBox(height: 8),
                  _buildCostRow('1. Admin & Provisi', biayaAdmin, subtitle: ketAdmin),
                  _buildCostRow('2. Asuransi Jiwa Kredit', biayaJiwa, subtitle: 'Premi Dasar (${jiwaRate.toStringAsFixed(2)}‰)'),
                  _buildCostRow('3. Asuransi Kerugian', biayaKerugian, subtitle: dibebankanKerugian ? 'FLEXAS + Polis + Materai' : 'Tidak dibebankan'),
                  _buildCostRow('4. Biaya Notaris', biayaNotaris),
                  _buildCostRow('5. Asuransi Sijitu', biayaSijitu, subtitle: umur >= 50 ? 'Umur >= 50 th' : 'Umur < 50 th'),
                  if (showBpjstk)
                    _buildCostRow('6. BPJSTK', biayaBpjstk, subtitle: _punyaBpjstk ? 'Sudah punya kartu' : 'Belum punya kartu'),
                  const Divider(),
                  _buildCostRow('Total Biaya Disiapkan', totalBiaya, isBold: true),

                  if (isTopUp) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.green.shade50,
                        border: Border.all(color: Colors.green.shade300),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Penerimaan Bersih (Top Up)', style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold, fontSize: 13)),
                          const SizedBox(height: 4),
                          Text(
                            _currencyFormat.format(danaCairBersih),
                            style: TextStyle(color: Colors.green.shade800, fontWeight: FontWeight.bold, fontSize: 20),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'Plafond (${_currencyFormat.format(limit)}) - Sisa Pokok (${_currencyFormat.format(sisaBade)}) - Biaya (${_currencyFormat.format(totalBiaya)})',
                            style: TextStyle(fontSize: 11, color: Colors.green.shade900),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Tombol Salin
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF0F4C81),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            icon: const Icon(Icons.copy),
            label: const Text('Salin Rincian Simulasi', style: TextStyle(fontWeight: FontWeight.bold)),
            onPressed: () {
              final summary = '''*Pengajuan $_jenisKredit limit ${_currencyFormat.format(limit)} tenor $tenorBulan bulan*
Angsuran: ${_currencyFormat.format(angsuran)} / bulan ($infoBunga)

Rincian Biaya yang Harus Disiapkan Calon Debitur:
1. Admin & Provisi       : ${_currencyFormat.format(biayaAdmin)} ($ketAdmin)
2. Asuransi Jiwa Kredit  : ${_currencyFormat.format(biayaJiwa)}
3. Asuransi Kerugian     : ${_currencyFormat.format(biayaKerugian)}
4. Biaya Notaris         : ${_currencyFormat.format(biayaNotaris)}
5. Asuransi Sijitu       : ${_currencyFormat.format(biayaSijitu)}
${showBpjstk ? "6. BPJSTK                : ${_currencyFormat.format(biayaBpjstk)}\n" : ""}----------------------------------------------------------------------
Total Biaya yang Disiapkan : ${_currencyFormat.format(totalBiaya)}*
*(Catatan: Calon Debitur: ${_namaController.text}, Umur: $umur tahun)
${isTopUp ? "\nPerhitungan Penerimaan Bersih (Top Up):\n- Limit Pengajuan Baru      : ${_currencyFormat.format(limit)}\n- Sisa Pokok / Bade Hutang  : ${_currencyFormat.format(sisaBade)}\n- Total Biaya Disiapkan     : ${_currencyFormat.format(totalBiaya)}\n----------------------------------------------------------------------\nEstimasi Dana Diterima Bersih : ${_currencyFormat.format(danaCairBersih)}" : ""}''';
              Clipboard.setData(ClipboardData(text: summary));
              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Rincian berhasil disalin ke clipboard!')));
            },
          ),
        ],
      ),
    );
  }

  Widget _buildCostRow(String title, int amount, {String? subtitle, bool isBold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(fontWeight: isBold ? FontWeight.bold : FontWeight.w500, fontSize: isBold ? 14 : 13)),
                if (subtitle != null) Text(subtitle, style: const TextStyle(fontSize: 11, color: Colors.grey)),
              ],
            ),
          ),
          Text(
            _currencyFormat.format(amount),
            style: TextStyle(fontWeight: isBold ? FontWeight.bold : FontWeight.w600, fontSize: isBold ? 15 : 13, color: isBold ? const Color(0xFF0F4C81) : null),
          ),
        ],
      ),
    );
  }
}
