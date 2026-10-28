(function(root) {
  'use strict';
  const sectors = {
    jasa: {name:'Jasa', min:.40, max:.80},
    makan: {name:'Warung makan', min:.25, max:.35},
    pakaian: {name:'Pakaian jadi', min:.15, max:.25},
    grosir: {name:'Grosir', min:.03, max:.08},
    sembako: {name:'Kelontong / sembako', min:.05, max:.15},
    produksi: {name:'Produksi', min:.20, max:.35}
  };
  const DS=.35, LO=1.25, HI=1.40;
  function payment(principal, rate, months, scheme) {
    if (scheme==='flat') return principal/months+principal*rate/100;
    const r=rate/1200;
    return r===0 ? principal/months : principal*r/(-Math.expm1(-months*Math.log1p(r)));
  }
  function errors(s) {
    const out=[];
    const num=(v,min=0)=>typeof v==='number' && Number.isFinite(v) && v>=min;
    if (!['KUR','KUM'].includes(s.product)) out.push('Pilih produk KUR atau KUM.');
    if (!sectors[s.sector]) out.push('Pilih jenis usaha untuk acuan laba.');
    if (!num(s.principal,1)) out.push('Isi plafon pengajuan lebih dari nol.');
    if (!num(s.months,1)||!Number.isInteger(s.months)||s.months>600) out.push('Isi tenor bulat antara 1–600 bulan.');
    if (!num(s.rate)) out.push('Isi bunga nol atau lebih.');
    if (!['flat','efektif'].includes(s.scheme)||s.product==='KUR'&&s.scheme!=='efektif') out.push('KUR memakai bunga efektif per tahun.');
    if (!num(s.days,1)||s.days>31||!Number.isInteger(s.days)) out.push('Isi hari usaha bulat antara 1–31 hari per bulan.');
    if (!num(s.otherIncome)) out.push('Pendapatan tambahan harus nol atau lebih.');
    if (!s.items.length) out.push('Tambahkan minimal satu barang atau jasa.');
    s.items.forEach((it,i)=>{
      if (!it.name.trim()) out.push(`Isi nama barang/jasa ${i+1}.`);
      if (!num(it.buy,0.01)||!num(it.sell,0.01)) out.push(`Isi harga beli dan jual barang ${i+1} lebih dari nol.`);
      if (!num(it.qty)) out.push(`Isi banyaknya terjual per hari barang ${i+1}.`);
      if (it.maxQty!==null && (!num(it.maxQty)||it.qty>it.maxQty)) out.push(`Batas penjualan barang ${i+1} harus setidaknya sebesar penjualan aktual.`);
    });
    for(const [name,rows] of [['Biaya',s.expenses],['Angsuran',s.debts]]) rows.forEach((it,i)=>{
      if(!num(it.amount)) out.push(`${name} baris ${i+1} harus nol atau lebih.`);
      if(it.amount>0&&!it.name.trim()) out.push(`Isi keterangan ${name.toLowerCase()} baris ${i+1}.`);
    });
    return out;
  }
  function analyze(s) {
    const invalid=errors(s); if(invalid.length) return {valid:false,errors:invalid};
    const sec=sectors[s.sector];
    const rows=s.items.map(it=>{
      const dailyUnits=it.qty;
      const markup=(it.sell-it.buy)/it.buy;
      return {...it,dailyUnits,markup,marginOK:markup>=sec.min-1e-9&&markup<=sec.max+1e-9,
        revenue:it.sell*dailyUnits*s.days,cost:it.buy*dailyUnits*s.days};
    });
    const sum=(a,k)=>a.reduce((n,r)=>n+r[k],0);
    const revenue=sum(rows,'revenue'),cost=sum(rows,'cost'),expense=sum(s.expenses,'amount'),debt=sum(s.debts,'amount');
    const gross=revenue-cost, profit=gross-expense, recognizedOther=s.otherIncome*.5;
    const income=profit+recognizedOther, dsrBudget=income*DS, capacity=dsrBudget-debt;
    const installment=payment(s.principal,s.rate,s.months,s.scheme);
    const minCapacity=LO*installment,maxCapacity=HI*installment;
    const status=capacity<minCapacity-1e-6?'kurang':capacity>maxCapacity+1e-6?'lebih':'rekom';
    const unitPayment=payment(1,s.rate,s.months,s.scheme);
    const maxPrincipal=Math.max(0,capacity/LO/unitPayment),minPrincipal=Math.max(0,capacity/HI/unitPayment);
    return {valid:true,rows,revenue,cost,gross,expense,profit,recognizedOther,income,debt,dsrBudget,capacity,installment,minCapacity,maxCapacity,
      status,coverage:capacity/installment,marginOK:rows.every(r=>r.marginOK),maxPrincipal,minPrincipal,
      targetIncome:((LO+HI)/2*installment+debt)/DS,
      actualDSR:income>0?(debt+installment)/income:null};
  }
  const copy=s=>JSON.parse(JSON.stringify(s));
  function simulate(s) {
    const a=analyze(s);if(!a.valid)return {candidates:[],notes:a.errors};
    const sec=sectors[s.sector], targetProfit=a.targetIncome-a.recognizedOther;
    const candidates=[],notes=[];
    function add(title,detail,scenario) {
      scenario.items.forEach((it,i)=>{
        it.qty=Math.ceil(it.qty);
        if(it.sell!==s.items[i].sell||it.buy!==s.items[i].buy){
          const roundedSell=Math.ceil(it.sell/1000)*1000;
          // Adjust for selling-price rounding, then round purchase costs up to Rp100 and revalidate.
          it.buy=Math.ceil((it.buy+roundedSell-it.sell)/100)*100;
          it.sell=roundedSell;
        }
      });
      const result=analyze(scenario);
      if(result.valid&&result.status==='rekom'&&result.marginOK) candidates.push({title,detail,scenario,result});
      else notes.push(title+': belum memenuhi rentang kapasitas dan laba usaha.');
    }
    // Round selling prices first, adjust purchase prices to sector markup, then solve daily quantities.
    let both=copy(s),markup=(sec.min+sec.max)/2;
    both.items.forEach(it=>{it.sell=Math.ceil(it.buy*(1+markup)/1000)*1000;it.buy=Math.ceil(it.sell/(1+markup)/100)*100;});
    const neededGross=targetProfit+a.expense;
    const grossAt=scale=>both.items.reduce((t,it)=>t+(it.sell-it.buy)*Math.min((it.qty||1)*scale,it.maxQty??Infinity)*s.days,0);
    if(neededGross>0) {
      let high=1;
      while(grossAt(high)<neededGross&&high<1e9)high*=2;
      if(grossAt(high)>=neededGross) {
        let low=0;for(let i=0;i<70;i++){const mid=(low+high)/2;if(grossAt(mid)<neededGross)low=mid;else high=mid;}
        both.items.forEach(it=>{it.qty=Math.ceil((it.qty||1)*high);});
        add('Harga jual & penjualan harian','Harga jual dibulatkan ke atas ke ribuan rupiah; harga beli menyesuaikan rentang laba usaha dan dibulatkan ke atas ke ratusan rupiah. Jumlah terjual per hari dibulatkan ke atas.',both);
      } else notes.push('Harga jual & penjualan: kapasitas penjualan maksimum yang diisi belum cukup untuk target pengajuan.');
    } else notes.push('Harga jual & penjualan: target laba tidak membutuhkan penjualan positif pada asumsi pendapatan tambahan saat ini.');
    // Required selling prices for unchanged quantities and purchase prices.
    if(a.cost>0) {
      const m=(targetProfit+a.expense)/a.cost;
      if(m>=sec.min&&m<=sec.max) {
        const c=copy(s);c.items.forEach(it=>it.sell=Math.round(it.buy*(1+m)*100)/100);
        add('Harga jual, jumlah tetap','Harga jual dibulatkan ke atas ke ribuan rupiah dan harga beli menyesuaikan; jumlah terjual tetap.',c);
      } else notes.push('Harga jual saja: laba yang dibutuhkan berada di luar rentang jenis usaha.');
    }
    const targetCost=a.revenue-a.expense-targetProfit;
    if(targetCost>0&&a.revenue>0) {
      const m=a.revenue/targetCost-1;
      if(m>=sec.min&&m<=sec.max) {
        const c=copy(s);c.items.forEach(it=>it.buy=Math.round(it.sell/(1+m)*100)/100);
        add('Harga beli, jumlah tetap','Harga jual dibulatkan ke atas ke ribuan rupiah; harga beli menyesuaikan target laba, jumlah terjual tetap.',c);
      } else notes.push('Harga beli saja: target berada di luar rentang laba jenis usaha.');
    }
    const targetExpense=a.gross-targetProfit;
    if(a.expense>0&&targetExpense>=0&&targetExpense<a.expense) {
      const c=copy(s);c.expenses.forEach(it=>it.amount=it.amount*targetExpense/a.expense);
      add('Efisiensi pengeluaran','Biaya usaha diturunkan secara proporsional; periksa apakah penghematan dapat dilakukan.',c);
    } else notes.push('Pengeluaran saja: penghematan biaya tidak menghasilkan target dalam rentang rekomendasi.');
    const targetDebt=a.dsrBudget-(LO+HI)/2*a.installment;
    if(a.debt>0&&targetDebt>=0&&targetDebt<a.debt) {
      const c=copy(s);c.debts.forEach(it=>it.amount=it.amount*targetDebt/a.debt);
      add('Pengurangan angsuran lain','Menunjukkan kebutuhan penurunan kewajiban bulanan, bukan penghapusan utang aktual.',c);
    }
    if(a.capacity>0) {
      const c=copy(s);c.principal=(a.minPrincipal+a.maxPrincipal)/2;
      add('Plafon sesuai kemampuan','Pendapatan, harga, jumlah terjual, biaya, dan angsuran lain mengikuti data aktual.',c);
    }
    return {candidates,notes};
  }
  const api={sectors,analyze,simulate,payment,DS,LO,HI};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.Usaha=api;
})(typeof window!=='undefined'?window:globalThis);

