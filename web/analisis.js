/* Inputs stay in memory. Generated scenarios fill the form; the original inputs can be restored. */
(()=>{
  'use strict';
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money=n=>'Rp '+Math.round(n).toLocaleString('id-ID');
  const number=n=>n.toLocaleString('id-ID',{maximumFractionDigits:3});
  const percent=n=>(n*100).toLocaleString('id-ID',{maximumFractionDigits:2})+'%';
  const numeric=(v,moneyField=false)=>v===''?null:Number(moneyField?v.replace(/\./g,''):v);
  const num=id=>numeric($(id).value,$(id).hasAttribute('data-money'));
  let originalState=null,simulationMode=false;
  let items=[],expenses=[],debts=[],actualState=null,actualResult=null,scenarios=[];
  const newItem=()=>({name:'',unit:'unit',sell:null,buy:null,qty:null,maxQty:null});
  items=[newItem()];
  expenses=['Listrik','Transportasi','Telepon','Sampah','Pegawai','Lainnya'].map(name=>({name,amount:0}));
  function fieldValue(v,m=false){return v===null?'':m?number(v):v;}
  function input(group,i,key,label,value,opts={}) {
    const id=`${group}-${i}-${key}`;
    return `<label${opts.wide?' class="wide"':''} for="${id}">${label}<input id="${id}" data-group="${group}" data-index="${i}" data-key="${key}" ${opts.money?'data-money type="text" inputmode="numeric"':opts.text?'type="text"':'type="number" min="0" step="any"'} value="${esc(fieldValue(value,opts.money))}"${opts.placeholder?` placeholder="${esc(opts.placeholder)}"`:''}${opts.text?' maxlength="120"':''}></label>`;
  }
  function renderRows(){
    $('items').innerHTML=items.map((it,i)=>`<div class="item"><div class="item-head"><strong>BARANG / JASA ${i+1}</strong><button type="button" class="remove" data-remove="items" data-index="${i}" aria-label="Hapus barang ${i+1}">Hapus</button></div><div class="item-grid">${input('items',i,'name','Nama barang / jasa',it.name,{text:true,wide:true,placeholder:'Contoh: Ayam bakar'})}${input('items',i,'sell','Harga jual satuan (Rp)',it.sell,{money:true})}${input('items',i,'buy','Harga beli satuan (Rp)',it.buy,{money:true})}${input('items',i,'qty','Banyaknya terjual / hari',it.qty,{placeholder:'Contoh: 18'})}${input('items',i,'unit','Satuan',it.unit,{text:true,placeholder:'Porsi / kg / unit'})}${input('items',i,'maxQty','Batas unit / hari untuk simulasi',it.maxQty,{wide:true,placeholder:'Opsional; kosong = tanpa batas input'})}</div></div>`).join('');
    for(const [group,rows] of [['expenses',expenses],['debts',debts]])$(group).innerHTML=rows.map((row,i)=>`<div class="compact-row">${input(group,i,'name',group==='debts'?'Bank / pemberi pinjaman':'Pengeluaran',row.name,{text:true})}${input(group,i,'amount','Angsuran / bulan (Rp)'.replace('Angsuran',group==='debts'?'Angsuran':'Biaya'),row.amount,{money:true})}<button type="button" class="remove" data-remove="${group}" data-index="${i}" aria-label="Hapus ${group==='debts'?'angsuran':'pengeluaran'} ${i+1}">×</button></div>`).join('');
  }
  function state(){return {product:$('product').value,principal:num('principal'),months:num('months'),scheme:$('scheme').value,rate:num('rate'),sector:$('sector').value,days:num('days'),otherIncome:num('otherIncome'),items:structuredClone(items),expenses:structuredClone(expenses),debts:structuredClone(debts)};}
  const statusName={kurang:'TIDAK REKOM',rekom:'REKOM OK',lebih:'TERLALU BESAR'};
  function clearSimulation(){scenarios=[];$('simulation').hidden=true;$('scenarioNotes').textContent='';}
  function update(preserve=false){
    if(!preserve)clearSimulation();
    document.querySelectorAll("[data-state-label]").forEach(el=>el.textContent=simulationMode?"HASIL SIMULASI":"DATA AKTUAL");
    $("restore").hidden=!originalState;
    const sec=Usaha.sectors[$('sector').value];
    $('sectorNote').textContent=sec?`${sec.name}: laba harga ${percent(sec.min)}–${percent(sec.max)} dari harga beli. Rentang ini dipakai untuk alternatif harga.`:'Pilih jenis usaha untuk melihat rentang laba acuannya.';
    actualState=state();actualResult=Usaha.analyze(actualState);
    const a=actualResult;
    $('emptyState').hidden=a.valid;$('actual').hidden=!a.valid;
    $('generate').disabled=!a.valid;$('copy').disabled=!a.valid;$('print').disabled=!a.valid;
    if(!a.valid){$('validation').innerHTML=a.errors.map(e=>`<li>${esc(e)}</li>`).join('');return;}
    $('status').textContent=statusName[a.status];$('status').className='status '+a.status;
    $('resultTitle').textContent={kurang:'Kapasitas belum mencukupi.',rekom:'Masuk rentang rekomendasi.',lebih:'Kapasitas di atas rentang.'}[a.status];
    $('resultReason').textContent={kurang:`Kapasitas kurang ${money(a.minCapacity-a.capacity)} dari batas bawah template. Bandingkan alternatif usaha atau plafon.`,rekom:'Kapasitas angsuran berada di antara 125% dan 140% dari cicilan pengajuan.',lebih:'Excel memberi status TERLALU BESAR jika kapasitas melebihi 140% cicilan. Ini berarti kapasitas berada di atas rentang, bukan kekurangan kemampuan bayar.'}[a.status];
    $('capacity').textContent=money(a.capacity);$('installment').textContent=money(a.installment)+' / bln';$('coverage').textContent='Kapasitas / cicilan: '+percent(a.coverage);
    const ledger=[['Penjualan',a.revenue],['Pembelian barang / biaya langsung',-a.cost],['Laba kotor',a.gross,'subtotal'],['Pengeluaran',-a.expense],['Laba usaha bersih',a.profit,'subtotal'],['Pendapatan tambahan diakui (50%)',a.recognizedOther],['Total pendapatan',a.income,'subtotal'],['Batas angsuran 35% pendapatan',a.dsrBudget],['Angsuran di luar Mandiri',-a.debt],['Kapasitas angsuran Mandiri',a.capacity,'subtotal']];
    $('ledger').innerHTML=ledger.map(([label,v,cl])=>`<div${cl?` class="${cl}"`:''}><dt>${label}</dt><dd>${v<0?'− ':''}${money(Math.abs(v))}</dd></div>`).join('');
    $('targetRange').textContent=money(a.minCapacity)+' – '+money(a.maxCapacity);
    const bad=a.rows.filter(r=>!r.marginOK);
    $('marginNote').className='notice'+(bad.length?' warning':'');
    $('marginNote').textContent=bad.length?`Periksa laba harga: ${bad.map(r=>r.name+' ('+percent(r.markup)+')').join(', ')} di luar acuan ${sec.name}. Status rasio di atas tidak otomatis mengesahkan asumsi harga.`:'Laba harga seluruh barang sesuai rentang '+sec.name+'.';
    $('itemResults').innerHTML=a.rows.map(r=>`<tr><td>${esc(r.name)}</td><td>${number(r.dailyUnits)} ${esc(r.unit)}</td><td>${money(r.revenue)}</td><td class="${r.marginOK?'good':'bad'}">${percent(r.markup)}</td></tr>`).join('');
    $('method').innerHTML=`<p>Kapasitas = (laba usaha + 50% pendapatan tambahan) × 35% − angsuran lain.</p><p>Rentang plafon matematis untuk REKOM OK: <strong>${money(a.minPrincipal)} – ${money(a.maxPrincipal)}</strong>. Bunga ${esc($('rate').value)}% ${actualState.scheme==='flat'?'flat/bulan':'efektif/tahun'}, tenor ${actualState.months} bulan.</p><p>Limit dihitung balik dari rumus cicilan yang sama, termasuk pengakuan pendapatan tambahan dan angsuran lain. Ini menyamakan parameter yang berbeda pada rumus LIMIT MAX asli.</p>`;
  }
  function loanHref(s){return '/?'+new URLSearchParams({analisis:'1',produk:s.product,plafon:String(Math.round(s.principal)),tenor:String(s.months),bunga:String(s.rate),skema:s.scheme});}
  function fillState(s){
    for(const key of ['product','principal','months','scheme','rate','sector','days','otherIncome'])$(key).value=fieldValue(s[key],$(key).hasAttribute('data-money'));
    items=structuredClone(s.items);expenses=structuredClone(s.expenses);debts=structuredClone(s.debts);
    $('scheme').disabled=s.product==='KUR';$('rateUnit').textContent=s.scheme==='flat'?'% per bulan':'% per tahun';
    renderRows();
  }
  function renderScenario(){
    const c=scenarios[Number($('candidate').value)];if(!c)return;
    if(!originalState)originalState=structuredClone(actualState);
    simulationMode=true;fillState(c.scenario);update(true);
    $('scenarioDetail').innerHTML='<div class="notice">Alternatif diterapkan ke input: <strong>'+esc(c.title)+'</strong>. Hasil di atas sudah dihitung ulang.</div><a class="button secondary full" href="'+esc(loanHref(actualState))+'">Lihat biaya pencairan</a>';
    $('feedback').textContent='Input telah diganti dengan hasil simulasi. Status: '+statusName[actualResult.status]+'.';
  }
  $('restore').onclick=()=>{
    if(!originalState)return;const saved=originalState;originalState=null;simulationMode=false;
    fillState(saved);update();$('feedback').textContent='Data awal dikembalikan.';
  };
  function formatMoneyInput(el){
    if(!el.hasAttribute('data-money'))return;
    const raw=el.value.replace(/[^0-9]/g,'');el.value=raw?Number(raw).toLocaleString('id-ID'):'';
  }
  $('inputs').addEventListener('input',e=>{
    const el=e.target;formatMoneyInput(el);
    if(el.dataset.group){const rows={items,expenses,debts}[el.dataset.group];rows[Number(el.dataset.index)][el.dataset.key]=['name','unit'].includes(el.dataset.key)?el.value:numeric(el.value,el.hasAttribute('data-money'));}
    if(el.id==='product'){
      if(el.value==='KUR'){$('scheme').value='efektif';$('scheme').disabled=true;}else $('scheme').disabled=false;
    }
    if(['product','scheme'].includes(el.id))$('rateUnit').textContent=$('scheme').value==='flat'?'% per bulan':'% per tahun';
    update();
  });
  $('inputs').addEventListener('click',e=>{
    const btn=e.target.closest('[data-remove]');if(!btn)return;
    const rows={items,expenses,debts}[btn.dataset.remove];rows.splice(Number(btn.dataset.index),1);renderRows();update();
  });
  $('inputs').addEventListener('submit',e=>e.preventDefault());
  $('addItem').onclick=()=>{items.push(newItem());renderRows();update();};
  $('addExpense').onclick=()=>{expenses.push({name:'',amount:0});renderRows();update();};
  $('addDebt').onclick=()=>{debts.push({name:'',amount:0});renderRows();update();};
  $('generate').onclick=()=>{
    const out=Usaha.simulate(actualState);
    scenarios=out.candidates.map(c=>{
      const s=structuredClone(c.scenario);
      s.principal=Math.round(s.principal);s.otherIncome=Math.round(s.otherIncome);
      s.items.forEach(it=>{it.sell=Math.round(it.sell);it.buy=Math.round(it.buy);});
      [...s.expenses,...s.debts].forEach(it=>it.amount=Math.round(it.amount));
      return {...c,scenario:s,result:Usaha.analyze(s)};
    }).filter(c=>c.result.valid&&c.result.status==='rekom'&&c.result.marginOK);
    $('simulation').hidden=!scenarios.length;
    $('candidate').innerHTML=scenarios.map((c,i)=>`<option value="${i}">${esc(c.title)}</option>`).join('');
    $('scenarioNotes').innerHTML=(scenarios.length?'':`<div class="notice warning">Belum ada alternatif yang memenuhi kedua rentang dengan parameter dan batas penjualan ini. Tinjau data usaha atau pengajuan.</div>`)+(out.notes.length?`<details><summary>Alternatif yang tidak dapat dipenuhi (${out.notes.length})</summary><ul>${out.notes.map(n=>`<li>${esc(n)}</li>`).join('')}</ul></details>`:'');
    renderScenario();
  };
  $('candidate').onchange=renderScenario;
  $('example').onclick=()=>{
    originalState=null;simulationMode=false;
    const values={product:'KUR',principal:'100.000.000',months:'36',scheme:'efektif',rate:'6',sector:'makan',days:'25',otherIncome:'0'};
    Object.entries(values).forEach(([k,v])=>$(k).value=v);$('scheme').disabled=true;$('rateUnit').textContent='% per tahun';
    items=[['Ayam Bakar',20000,16000,18],['Ayam Goreng',18000,14000,17],['Nasi Uduk',8000,6000,17],['Nasi',6000,4500,25],['Ati Ampela',10000,7500,21]].map(([name,sell,buy,qty])=>({name,sell,buy,qty,unit:'porsi',maxQty:null}));
    expenses=[['Listrik',150000],['Transportasi',200000],['Telepon',100000],['Sampah',50000],['Pegawai',0],['Lainnya',100000]].map(([name,amount])=>({name,amount}));debts=[];
    renderRows();update();$('feedback').textContent='Contoh angka dari Excel dimuat. Satuan porsi dapat Anda sesuaikan.';
  };
  $('copy').onclick=async()=>{
    if(!actualResult.valid)return;const a=actualResult;
    const lines=[`ANALISIS ${simulationMode?'SIMULASI':'AKTUAL'} ${actualState.product}`,`Plafon ${money(actualState.principal)}, tenor ${actualState.months} bulan`,`Bunga ${actualState.rate}% ${actualState.scheme==='flat'?'flat/bulan':'efektif/tahun'}`,`Jenis usaha: ${Usaha.sectors[actualState.sector].name}`,`Hari usaha: ${actualState.days}/bulan`,...a.rows.map(r=>`${r.name}: beli ${money(r.buy)}, jual ${money(r.sell)}, ${number(r.qty)} ${r.unit}/hari, laba harga ${percent(r.markup)}`),`Penjualan: ${money(a.revenue)}`,`Pembelian: ${money(a.cost)}`,`Biaya: ${money(a.expense)}`,`Laba usaha: ${money(a.profit)}`,`Pendapatan tambahan diakui 50%: ${money(a.recognizedOther)}`,`Angsuran luar Mandiri: ${money(a.debt)}`,`Kapasitas: ${money(a.capacity)}`,`Cicilan: ${money(a.installment)}`,`Rentang kapasitas 125–140% cicilan: ${money(a.minCapacity)} – ${money(a.maxCapacity)}`,`Status template: ${statusName[a.status]}`,`Laba harga: ${a.marginOK?'sesuai rentang usaha':'perlu ditinjau'}`];
    try{await navigator.clipboard.writeText(lines.join('\n'));$('feedback').textContent='Analisis berhasil disalin.';}catch{$('feedback').textContent='Browser tidak mengizinkan penyalinan. Gunakan Cetak / simpan PDF.';}
  };
  $('print').onclick=()=>window.print();
  const q=new URLSearchParams(location.search);
  if(['KUR','KUM'].includes(q.get('produk'))){
    $('product').value=q.get('produk');
    for(const [key,id] of [['plafon','principal'],['tenor','months'],['bunga','rate']])if(q.has(key)&&Number.isFinite(Number(q.get(key)))&&Number(q.get(key))>=0)$(id).value=id==='principal'?number(Number(q.get(key))):q.get(key);
    $('scheme').value=q.get('produk')==='KUR'?'efektif':q.get('skema')==='flat'?'flat':'efektif';$('scheme').disabled=q.get('produk')==='KUR';$('rateUnit').textContent=$('scheme').value==='flat'?'% per bulan':'% per tahun';
  }
  renderRows();update();
  if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
})();
