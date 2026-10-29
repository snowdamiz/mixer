"use strict";
(() => {
  let checks = 0;
  const check = (ok, message) => { checks++; if (!ok) throw Error(message); };
  const allowed = n => n < 0 || n > 64 ? 0n : (1n << BigInt(n)) - 1n;
  const popcount = mask => { let n = 0; while (mask) { mask &= mask - 1n; n++; } return n; };
  const reference = records => records.indexOf(0);
  const bitmap = (records, mask, active, budget = 5, cancelled = false) => {
    let charged = 0;
    const charge = n => { if (cancelled || charged + n > budget) throw Error('stop'); charged += n; };
    charge(3);
    if (records.length > 64 || (mask & ~allowed(records.length)) || popcount(mask) + active !== records.length) throw Error('mask');
    if (mask === 0n) {
      for (const record of records) { charge(1); if (record === 0) throw Error('orphan'); }
      throw Error('full');
    }
    let slot = 0; while (((mask >> BigInt(slot)) & 1n) === 0n) slot++;
    charge(2);
    if (records[slot] !== 0) throw Error('occupied');
    return { slot, charged };
  };
  const make = (n, mask) => Array.from({length:n}, (_,i) => (mask & (1n << BigInt(i))) ? 0 : i + 1);
  let states = 0;
  for (let n=0;n<=64;n++) {
    const samples = n <= 10 ? Array.from({length:2**n},(_,i)=>BigInt(i)) :
      [0n, allowed(n), ...Array.from({length:n},(_,i)=>1n<<BigInt(i)), ...Array.from({length:n},(_,i)=>allowed(n)^(1n<<BigInt(i)))];
    for (const mask of samples) {
      const records=make(n,mask), active=n-popcount(mask), before=records.slice();
      const expected=reference(records);
      try { const actual=bitmap(records,mask,active,n+5); check(actual.slot===expected,'first free'); check(actual.charged===5,'constant selection charge'); }
      catch(e) { check(expected===-1 && e.message==='full','only genuinely full exhausts'); }
      check(records.every((v,i)=>v===before[i]),'selection has no record effect');
      if (expected>=0) {
        for (let limit=0;limit<5;limit++) { let failed=false;try{bitmap(records,mask,active,limit);}catch(e){failed=e.message==='stop';}check(failed,'short budget before publication'); }
        let failed=false;try{bitmap(records,mask,active,5,true);}catch(e){failed=e.message==='stop';}check(failed,'cancellation before publication');
        const published=mask & ~(1n<<BigInt(expected)); records[expected]=99;
        check(popcount(published)+active+1===n,'publish count agrees');
        records[expected]=0;const released=published|(1n<<BigInt(expected));
        check(released===mask,'release restores original mask');
      }
      states++;
    }
  }
  let seed=0x75a24019;
  const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed;};
  let operations=0;
  for(const n of [1,2,8,31,32,63,64]) {
    let mask=allowed(n), active=0, records=Array(n).fill(0), nonce=1;
    for(let t=0;t<2048;t++) {
      const occupied=records.map((v,i)=>v?i:-1).filter(i=>i>=0);
      if(occupied.length && (random()&1)) { const slot=occupied[random()%occupied.length];records[slot]=0;mask|=1n<<BigInt(slot);active--; }
      else if(active<n) { const expected=reference(records), actual=bitmap(records,mask,active);check(actual.slot===expected,'random first-free'); records[actual.slot]=nonce++;mask&=~(1n<<BigInt(actual.slot));active++; }
      check(popcount(mask)+active===n,'random invariant');check(records.filter(v=>v!==0).length===active,'actual record count');operations++;
    }
  }
  let corruptionCases=0;
  for(let n=1;n<=64;n++) {
    const records=make(n,allowed(n)^1n),mask=allowed(n)^1n,active=1;
    for(const corrupt of [mask|(1n<<64n),mask|1n]) { let failed=false;try{bitmap(records,corrupt,active);}catch(e){failed=e.message==='mask';}check(failed,'mask corruption rejected');corruptionCases++; }
    if(n>=2){const swap=mask^1n^2n;let failed=false;try{bitmap(records,swap,active);}catch(e){failed=e.message==='occupied';}check(failed,'equal-popcount occupied selection rejected');corruptionCases++;}
  }
  // Terminal release deliberately has no work/cancellation argument.
  const release=(records,mask,slot,owner,nonce,token)=>{
    if(token.owner!==owner||token.slot!==slot||records[slot]!==token.nonce||token.nonce!==nonce)throw Error('token');
    if(slot>=records.length||(mask&~allowed(records.length))||(mask&(1n<<BigInt(slot))))throw Error('release-mask');
    const out=records.slice();out[slot]=0;return {records:out,mask:mask|(1n<<BigInt(slot))};
  };
  for(const bad of [{owner:8,slot:0,nonce:3},{owner:7,slot:0,nonce:2},{owner:7,slot:1,nonce:3}]){
    let failed=false;try{release([3],0n,0,7,3,bad);}catch(e){failed=true;}check(failed,'foreign or stale token rejected');
  }
  check(release([3],0n,0,7,3,{owner:7,slot:0,nonce:3}).mask===1n,'terminal release');
  for(const name of ['process','require','module','fetch','WebSocket','setTimeout','setInterval'])check(typeof globalThis[name]==='undefined','sandbox excludes '+name);
  return {checks,states,operations,corruptionCases,scope:'independent finite BigInt/array model; no Rust execution'};
})();
