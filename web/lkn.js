/* LKN Phase 4: grouped purchase and sale dates. */
(()=>{
  'use strict';
  const $=id=>document.getElementById(id), money=n=>'Rp '+Math.round(n).toLocaleString('id-ID');
  let context=null, source='Input manual';
  const rows=Array.from({length:7},()=>({buyDate:'',sellDate:'',buy:null,sell:null}));
  const root=$('lknRows');
  function group(kind,title,count,offset){
    return '<section class="lkn-group"><h3>'+title+'</h3><div class="lkn-list">'+rows.slice(0,count).map((r,i)=>{
      const date=i*2+offset;r[kind+'Date']=String(date);
      return '<div class="grid two lkn-entry"><label>Tanggal<input type="number" min="1" max="31" step="1" value="'+date+'" data-lkn-row="'+i+'" data-lkn-key="'+kind+'Date"></label><label>'+title+' (Rp)<input type="text" inputmode="numeric" data-lkn-row="'+i+'" data-lkn-key="'+kind+'"></label></div>';
    }).join('')+'</div></section>';
  }
  root.innerHTML=group('buy','Pembelian',7,1)+group('sell','Penjualan',7,2);
  const summary=$('lknSummary'),message=$('lknMessage');
  const validDate=v=>Number.isInteger(Number(v))&&Number(v)>=1&&Number(v)<=31;
  function render(){
    summary.hidden=true;
    const complete=rows.every(r=>validDate(r.buyDate)&&r.buy!==null)&&rows.slice(0,7).every(r=>validDate(r.sellDate)&&r.sell!==null);
    if(!complete){message.textContent='Lengkapi 7 tanggal pembelian dan 7 tanggal penjualan beserta nominalnya. Nominal 0 boleh diisi jika tidak ada transaksi.';return;}
    if(new Set(rows.map(r=>Number(r.buyDate))).size!==7||new Set(rows.slice(0,7).map(r=>Number(r.sellDate))).size!==7){message.textContent='Tanggal pada masing-masing daftar harus berbeda: 8 tanggal pembelian dan 7 tanggal penjualan.';return;}
    const s=context;
    const validAmount=n=>Number.isFinite(n)&&n>=0;
    if(!s||!Number.isInteger(s.days)||s.days<1||s.days>31||!['KUR','KUM'].includes(s.product)||!Number.isInteger(s.months)||s.months<1||s.months>600||!validAmount(s.rate)||!Number.isFinite(s.principal)||s.principal<=0||![...s.expenses,...s.debts].every(r=>validAmount(r.amount))){message.textContent='Lengkapi produk, plafon, tenor, bunga, hari usaha, biaya, dan angsuran lain pada formulir utama.';return;}
    const totalBuy=rows.reduce((t,r)=>t+r.buy,0),totalSell=rows.slice(0,7).reduce((t,r)=>t+r.sell,0);
    const avgBuy=totalBuy/7,avgSell=totalSell/7,monthlyBuy=avgBuy*s.days,monthlySell=avgSell*s.days;
    const expenses=s.expenses.reduce((t,r)=>t+r.amount,0),debt=s.debts.reduce((t,r)=>t+r.amount,0);
    const gross=monthlySell-monthlyBuy,net=gross-expenses,budget=net*.35,capacity=budget-debt;
    const installment=Usaha.payment(s.principal,s.rate,s.months,s.product==='KUR'?'efektif':s.scheme);
    const recommended=capacity>installment;
    message.textContent=source+'. Menggunakan '+s.days+' hari usaha/bulan dan parameter pengajuan pada formulir utama.';
    $('lknStatus').textContent=recommended?'REKOM LIMIT':'TIDAK REKOM';$('lknStatus').className='status '+(recommended?'rekom':'kurang');
    $('lknLedger').innerHTML=[['Total pembelian 7 tanggal',totalBuy],['Total penjualan 7 tanggal',totalSell],['Rata-rata pembelian / hari',avgBuy],['Rata-rata penjualan / hari',avgSell],['Pembelian / bulan',monthlyBuy],['Penjualan / bulan',monthlySell],['Laba kotor / bulan',gross],['Biaya usaha / bulan',expenses],['Laba bersih / bulan',net],['DSR 35%',budget],['Angsuran di luar Mandiri',debt],['Maksimum angsuran Mandiri',capacity],['Cicilan pengajuan',installment]].map(([label,value])=>'<div><dt>'+label+'</dt><dd>'+money(value)+'</dd></div>').join('');
    summary.hidden=false;
  }
  root.addEventListener('input',e=>{
    const el=e.target;if(!el.dataset.lknKey)return;
    const key=el.dataset.lknKey;
    if(key==='buy'||key==='sell'){
      const raw=el.value.replace(/[^0-9]/g,'');rows[Number(el.dataset.lknRow)][key]=raw===''?null:Number(raw);
      el.value=raw===''?'':Number(raw).toLocaleString('id-ID');
    }else rows[Number(el.dataset.lknRow)][key]=el.value;
    source='Input manual';render();
  });
  document.addEventListener('usaha:change',e=>{context=e.detail;render();});
  function spread(total,weights){
    // Largest-remainder allocation keeps whole-rupiah entries and an exact total for each group.
    const sum=weights.reduce((a,b)=>a+b,0);
    const raw=weights.map(w=>total*w/sum),values=raw.map(Math.floor);
    const order=raw.map((n,i)=>({i,fraction:n-values[i]})).sort((a,b)=>b.fraction-a.fraction);
    const remainder=total-values.reduce((a,b)=>a+b,0);
    for(let j=0;j<remainder;j++)values[order[j].i]++;
    return values;
  }
  $('lknFill').onclick=()=>{
    if(!context){return;}
    const a=Usaha.analyze(context);
    if(!a.valid){message.textContent='Lengkapi hitungan barang pada formulir utama terlebih dahulu untuk mengisi tabel otomatis.';return;}
    const purchases=spread(Math.round(a.cost/context.days*7),[88,104,95,112,91,107,103]);
    const sales=spread(Math.round(a.revenue/context.days*7),[94,109,87,103,114,96,97]);
    rows.forEach((r,i)=>{
      // Dates follow the template's 1,3,...13 purchase / 2,4,...14 sale example.
      r.buyDate=r.buyDate||String(i*2+1);if(i<7)r.sellDate=r.sellDate||String(i*2+2);
      r.buy=purchases[i];if(i<7)r.sell=sales[i];
    });
    root.querySelectorAll('input').forEach(el=>{const v=rows[Number(el.dataset.lknRow)][el.dataset.lknKey];el.value=typeof v==='number'?v.toLocaleString('id-ID'):v;});
    source='Simulasi variasi harian dari hitungan barang; rata-rata masing-masing daftar mengikuti hitungan sumber';render();
  };
  document.dispatchEvent(new Event('lkn:request'));
})();
