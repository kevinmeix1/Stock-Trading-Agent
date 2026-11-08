'use strict';
const report = JSON.parse(document.getElementById('report-data').textContent);
const $ = id => document.getElementById(id);
const fmt = value => value === null || value === undefined ? '—' : new Intl.NumberFormat('de-DE',{maximumFractionDigits:2}).format(value);
const el = (tag,text='',cls='') => { const node=document.createElement(tag);node.textContent=text;node.className=cls;return node; };
const svg = (tag,attrs={},text='') => {const node=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))node.setAttribute(k,v);node.textContent=text;return node;};
const labels={BULLISH:'Bullish',BEARISH:'Bearish',NEUTRAL:'Neutral',UNAVAILABLE:'Nicht verfügbar',support:'Support',resistance:'Resistance'};
const recent = events => events.filter(e=>e.index>=report.bars-252);
$('title').textContent=report.symbol;
$('meta').textContent=`${report.as_of} · ${report.currency} · ${report.bars} Tagesabschlüsse · ${report.source}`;
$('state').append(el('small','TECHNICAL STATE'),el('div',report.assessment.state,`badge ${report.assessment.state}`));
const last=report.series.at(-1), rsi=report.momentum.rsi14;
const metric=(label,value,note,cls='')=>{const item=el('article','','metric');item.append(el('span',label),el('strong',value,cls),el('small',note));$('metrics').append(item);};
metric('Schlusskurs',`${fmt(last.close)} ${report.currency}`,last.date);
for(const t of report.trends)metric(`Trend · ${t.window} Sessions`,labels[t.direction],t.efficiency===null?'Historie zu kurz':`Effizienz ${fmt(t.efficiency*100)} %`,t.direction);
metric('RSI 14',fmt(rsi),rsi>70?'Überkauft':rsi<30?'Überverkauft':'Neutral',rsi>70?'BEARISH':rsi<30?'BULLISH':'NEUTRAL');
metric('ATR 14',fmt(report.atr14),`${report.currency} · Wilder`);
const reasonText={trend:'Trend',structure:'Marktstruktur',momentum:'MACD-Momentum'};
for(const [key,value]of Object.entries(report.assessment.votes))$('assessment').append(el('p',`${reasonText[key]}: ${labels[value]}`,value));
const near=report.zones.find(z=>z.role==='support'&&z.status==='confirmed'&&z.distance_atr<=1);
if(near)$('assessment').append(el('p','Bestätigter Support liegt innerhalb von 1 ATR. Die Kurslage bestätigt noch keine Trendwende.'));
for(const conflict of report.assessment.conflicts){const translated=conflict.startsWith('Technical state remains')?'Bearish trotz naher Unterstützung: Ein Kontakt allein bestätigt keine Trendwende.':conflict.startsWith('Oversold RSI')?'Überverkaufter RSI bei schwachem Trend: Die Gegenbewegung ist noch nicht bestätigt.':conflict.startsWith('200-session')?'Die Historie reicht für den 200-Tage-Trend mit Steigung noch nicht aus.':'Trend, Marktstruktur und MACD-Momentum widersprechen sich.';$('conflicts').append(el('li',translated,'conflict'));}
if(!report.assessment.conflicts.length)$('conflicts').append(el('li','Kein Richtungswiderspruch zwischen den verfügbaren Hauptbereichen.'));
const activeZones=report.zones.filter(z=>z.status==='confirmed').slice(0,6);
for(const z of activeZones){const node=el('div','','zone');node.append(el('strong',`${labels[z.role]} · ${fmt(z.lower)}–${fmt(z.upper)} ${report.currency}`,z.role==='support'?'BULLISH':'BEARISH'),el('small',`${z.touches} bestätigte Berührungen · ${fmt(z.distance_atr)} ATR Abstand · bestätigt ${z.confirmed_at}`));$('zones').append(node);}
if(!activeZones.length)$('zones').append(el('p','Keine mehrfach bestätigte intakte Zone.'));
const list=(id,events,describe,empty)=>{const target=$(id);if(!events.length)target.append(el('p',empty));for(const e of events.slice(-8).reverse()){const row=el('div','','event');row.append(el('b',describe(e),e.direction||''),el('span',e.confirmed_at?`${e.date} · bestätigt ${e.confirmed_at}`:e.date));target.append(row);}};
list('swings',recent(report.swings),e=>`${e.label} · ${fmt(e.price)} ${report.currency}`,'Noch keine bestätigten Swings.');
list('breaks',recent(report.breaks),e=>`${e.event} ${e.direction} · ${fmt(e.level)}${e.initial?' · initial':''}`,'Keine bestätigten Schlusskursbrüche.');
list('patterns',recent(report.patterns),e=>`${e.pattern} · Neckline ${fmt(e.neckline)}`,'Keine bestätigte Double-Bottom-/Top-Formation.');
list('divergences',recent(report.divergences),e=>`${e.direction} · RSI ${fmt(e.first_rsi)} → ${fmt(e.second_rsi)}`,'Keine bestätigte reguläre RSI-Divergenz.');
$('trends').append(el('p',`MACD ${fmt(report.momentum.macd)} · Signal ${fmt(report.momentum.signal)} · Histogramm ${fmt(report.momentum.histogram)}`));
$('trends').append(el('p','Divergenzen und Formationen sind historische Bestätigungen. Entscheidend für den aktuellen Zustand bleiben die oben ausgewiesenen Richtungen.'));
const width=1200,left=14,right=90,plot=width-left-right;
const x=i=>left+(report.series.length===1?0:i/(report.series.length-1)*plot);
const priceValues=report.series.flatMap(p=>[p.close,p.sma20,p.sma50,p.sma200].filter(Number.isFinite));
const min=Math.min(...priceValues),max=Math.max(...priceValues),pad=Math.max((max-min)*.08,max*.01),low=min-pad,high=max+pad;
const line=(root,values,y,color,extra={})=>{let segment=[];const flush=()=>{if(segment.length>1)root.append(svg('polyline',{points:segment.join(' '),fill:'none',stroke:color,'stroke-width':1.7,...extra}));segment=[];};values.forEach((v,i)=>{if(Number.isFinite(v))segment.push(`${x(i)},${y(v)}`);else flush();});flush();};
function rsiFillPoints(values,threshold,x,y){const known=values.map((v,i)=>Number.isFinite(v)?i:null).filter(i=>i!==null);if(!known.length)return '';return [`${x(known[0])},${y(threshold)}`,...known.map(i=>`${x(i)},${y(values[i])}`),`${x(known.at(-1))},${y(threshold)}`].join(' ');}
function priceChart(){const height=330,y=v=>20+(high-v)/(high-low)*(height-55),root=svg('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':'252 Schlusskurse, SMA-Linien und bestätigte Preiszonen'});
 for(let i=0;i<5;i++){const value=low+(high-low)*i/4,py=y(value);root.append(svg('line',{x1:left,x2:width-right,y1:py,y2:py,stroke:'#34424a'}),svg('text',{x:width-right+10,y:py+4,fill:'#a4b7c0','font-size':11},fmt(value)));}
 for(const z of activeZones){const lo=Math.max(low,z.lower),hi=Math.min(high,z.upper),from=x(Math.max(0,z.established_index-(report.bars-report.series.length)));if(hi>lo&&from<width-right){root.append(svg('rect',{x:from,y:y(hi),width:width-right-from,height:Math.max(2,y(lo)-y(hi)),fill:z.role==='support'?'#70d5a8':'#e47d83',opacity:.16,'data-established-at':z.established_at}));root.append(svg('text',{x:from+8,y:y(hi)-4,fill:z.role==='support'?'#70d5a8':'#e47d83','font-size':10},`${labels[z.role]} ${fmt(z.lower)}–${fmt(z.upper)}`));}}
 for(const [key,color] of [['sma200','#d98eb2'],['sma50','#b4a5ee'],['sma20','#e4bb70'],['close','#71d5d1']])line(root,report.series.map(p=>p[key]),y,color,{'data-series':key});
 const offset=report.bars-report.series.length;for(const s of recent(report.swings).slice(-16)){const index=s.index-offset;if(index<0||index>=report.series.length)continue;root.append(svg('circle',{cx:x(index),cy:y(s.price),r:2.5,fill:'#e7c390'}),svg('text',{x:x(index),y:y(s.price)+(s.kind==='H'?-9:16),fill:'#e7c390','font-size':10,'text-anchor':'middle'},s.label));}
 for(const i of [0,Math.floor(report.series.length/2),report.series.length-1])root.append(svg('text',{x:x(i),y:height-3,fill:'#9aafb9','font-size':10,'text-anchor':i===0?'start':i===report.series.length-1?'end':'middle'},report.series[i].date));
 root.addEventListener('pointermove',event=>{const r=root.getBoundingClientRect(),i=Math.max(0,Math.min(report.series.length-1,Math.round(((event.clientX-r.left)*width/r.width-left)/plot*(report.series.length-1))));const p=report.series[i];$('price-readout').textContent=`${p.date} · Schlusskurs ${fmt(p.close)} ${report.currency}`;});
 $('price-chart').append(root);$('price-readout').textContent=`${last.date} · Schlusskurs ${fmt(last.close)} ${report.currency}`;
}
function rsiChart(){const height=150,y=v=>10+(100-v)*1.15,root=svg('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':'RSI: transparente rote Überschreitung über70, grüne Unterschreitung unter30'}),defs=svg('defs');
 for(const [name,value,color]of [['overbought',70,'#e47d83'],['oversold',30,'#70d5a8']]){const clip=svg('clipPath',{id:`rsi-${name}`});clip.append(svg('rect',{x:left,y:name==='overbought'?y(100):y(30),width:plot,height:name==='overbought'?y(70)-y(100):y(0)-y(30)}));defs.append(clip);const points=rsiFillPoints(report.series.map(p=>p.rsi14),value,x,y);if(points){root.append(svg('polygon',{points,fill:color,opacity:.23,'clip-path':`url(#rsi-${name})`,'data-rsi-zone':name}));}}
 root.append(defs);for(const value of [0,30,50,70,100])root.append(svg('line',{x1:left,x2:width-right,y1:y(value),y2:y(value),stroke:value===30?'#39775b':value===70?'#8c5055':'#34424a','stroke-dasharray':value===30||value===70?'4 4':'none'}),svg('text',{x:width-right+10,y:y(value)+4,fill:'#a4b7c0','font-size':10},value));
 line(root,report.series.map(p=>p.rsi14),y,'#bea9ef',{'data-series':'rsi14'});root.addEventListener('pointermove',event=>{const r=root.getBoundingClientRect(),i=Math.max(0,Math.min(report.series.length-1,Math.round(((event.clientX-r.left)*width/r.width-left)/plot*(report.series.length-1))));const p=report.series[i];$('rsi-readout').textContent=`${p.date} · RSI ${fmt(p.rsi14)}`;});
 $('rsi-chart').append(root);$('rsi-state').textContent=`${fmt(rsi)} · ${rsi>70?'Überkauft':rsi<30?'Überverkauft':'Neutral'}`;$('rsi-readout').textContent='Über 70: überkauft · Unter 30: überverkauft';
}
priceChart();rsiChart();
for(const line of [`Quelle: ${report.source}`,`Preisbehandlung: ${report.adjustment}`,`CSV SHA-256: ${report.dataset?.sha256||'nicht angegeben'}`,`Prüfsumme gegen Vorgabe: ${report.dataset?.checksum_verified?'bestätigt':'nur Fingerabdruck, keine externe Verifikation'}`,`3/3-Pivots · Zonen: mindestens2 Berührungen · ATR14 Wilder · RSI14 Wilder · MACD12/26/9 · Trend-SMA20/50/200`,...report.limits])$('evidence').append(el('p',line));
