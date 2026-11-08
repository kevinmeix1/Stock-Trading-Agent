import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { test } from 'node:test';
import { calculateSMA, calculateEMA, calculateRSI, calculateATR } from './moeuu-analysis.ts';
import { createWalkForwardSplits } from './mcp2-walkForward.ts';
import { compareIndicatorObservations } from './mcp2-indicatorAudit.ts';
const fixture=JSON.parse(readFileSync(new URL('./fixture-comparison.json',import.meta.url),'utf8'));
const closes=fixture.bars.map(b=>b.close);
const calculated={
 sma20:calculateSMA(closes,20),
 ema20:calculateEMA(closes,20),
 rsi14:calculateRSI(closes,14),
 atr14:calculateATR(fixture.bars,14),
};
const differences={};
for(const [name,actual]of Object.entries(calculated)){
 let max=0,compared=0,nullMismatch=0;
 actual.forEach((v,i)=>{
  const ref=fixture[name][i];
  if((v===null)!==(ref===null)){nullMismatch++; return;}
  if(v!==null){compared++;max=Math.max(max,Math.abs(v-ref));}
 });
 differences[name]={compared,maxAbsDifference:max,nullMismatch};
}
writeFileSync(new URL('./comparison-results.json',import.meta.url),JSON.stringify({fixture:fixture.fixture,checks:differences},null,2)+'\n');
test('SMA known values',()=>assert.deepEqual(calculateSMA([1,2,3,4,5],3),[null,null,2,3,4]));
test('RSI monotone up',()=>assert.equal(calculateRSI(Array.from({length:40},(_,i)=>100+i),14).at(-1),100));
test('Four indicator series are prefix invariant',()=>{
 const count=200;
 const prefix=fixture.bars.slice(0,count),c=prefix.map(b=>b.close);
 const funcs={sma20:calculateSMA(c,20),ema20:calculateEMA(c,20),rsi14:calculateRSI(c,14),atr14:calculateATR(prefix,14)};
 for(const [k,v]of Object.entries(funcs)) assert.deepEqual(v,calculated[k].slice(0,count));
});
test('SMA EMA RSI agree across two independent implementations within 1e-8',()=>{
 for(const name of ['sma20','ema20','rsi14']){
  assert.equal(differences[name].nullMismatch,0,name);
  assert.ok(differences[name].maxAbsDifference<1e-8,name);
 }
});
test('Walk-forward embargo and disjoint test periods',()=>{
 const splits=createWalkForwardSplits({length:320,train_size:100,test_size:40,embargo:20});
 assert.equal(splits.length,5);
 splits.forEach((s,i)=>{
  assert.equal(s.test[0]-s.train[1]-1,20);
  if(i)assert.ok(splits[i-1].test[1]<s.test[0]);
 });
});
test('ATR initialization difference is detected, not silently treated as equivalent',()=>{
 assert.equal(differences.atr14.nullMismatch,1);
 assert.ok(differences.atr14.maxAbsDifference>1e-8);
});
test('Restart audit detects changed historical indicator value',()=>{
 const base={study_id:'a',symbol:'SYNTH',resolution:'D',bars:[{time:1,values:{rsi:50}}]};
 const after={...base,bars:[{time:1,values:{rsi:60}}]};
 assert.equal(compareIndicatorObservations(base,after).status,'changed');
});
console.log(JSON.stringify(differences));
