'use strict';
(() => {
  let checks=0, transitions=0, histories=0, corruptions=0;
  const require=(v,m)=>{checks++;if(!v)throw Error(m);};
  const equal=(a,b,m)=>require(JSON.stringify(a,(_,v)=>typeof v==='bigint'?v.toString():v)===JSON.stringify(b,(_,v)=>typeof v==='bigint'?v.toString():v),m);
  const snapshot=m=>({bits:m.bits,records:m.records.slice(),next:m.next,live:m.live});
  const full=n=>Array.from({length:n},(_,i)=>1n<<BigInt(i)).reduce((a,b)=>a|b,0n);
  const make=n=>({n,owner:71,bits:full(n),records:Array(n).fill(0),next:1,live:0,terminal:false});
  // Independent oracle: occupied slots are derived from a successful event log.
  const oracle=(n,events)=>{const live=new Map();for(const e of events){if(e.kind==='issue')live.set(e.token.slot,e.token);else live.delete(e.token.slot);}return {live,free:Array.from({length:n},(_,i)=>i).filter(i=>!live.has(i))};};
  const invariant=(m,events)=>{let o=oracle(m.n,events);equal(m.live,o.live.size,'ledger/event disagreement');equal(m.records.map((v,i)=>v?i:-1).filter(i=>i>=0),[...o.live.keys()].sort((a,b)=>a-b),'record/event disagreement');equal(m.bits, o.free.reduce((s,i)=>s|(1n<<BigInt(i)),0n),'bitmap/event disagreement');};
  const take=(m,fail=0,mutation='')=>{
    const before=snapshot(m);let failat=stage=>fail===stage;
    if(m.terminal||m.next===Number.MAX_SAFE_INTEGER||failat(1))return null;
    if(m.n>64||(m.bits&~full(m.n))!==0n||m.bits.toString(2).replace(/0/g,'').length+m.live!==m.n)return null;
    if(m.bits===0n)return null;
    let selected=0;while((m.bits&(1n<<BigInt(selected)))===0n)selected++;
    if(m.records[selected]!==0||failat(2))return null;
    if(mutation==='early_publish')m.bits &= ~(1n<<BigInt(selected));
    if(failat(3)||failat(4)||failat(5))return null;
    let token={owner:m.owner,slot:selected,nonce:m.next};
    m.live++;m.records[selected]=m.next++;m.bits &= ~(1n<<BigInt(selected));
    transitions++;return token;
  };
  const drop=(m,t,fail=false,mutation='')=>{
    if((mutation!=='owner'&&t.owner!==m.owner)||t.slot<0||t.slot>=m.n||m.records[t.slot]===0||(mutation!=='nonce'&&m.records[t.slot]!==t.nonce))return false;
    if(m.n>64||(m.bits&~full(m.n))!==0n||(m.bits&(1n<<BigInt(t.slot)))!==0n)return false;
    if(mutation==='early_release')m.bits |= 1n<<BigInt(t.slot);
    if(fail)return false;
    m.live--;m.records[t.slot]=0;m.bits |= 1n<<BigInt(t.slot);transitions++;return true;
  };
  for(let n=0;n<=64;n++){
    let m=make(n),events=[],tokens=[];invariant(m,events);
    for(let i=0;i<n;i++){
      for(let f=1;f<=5;f++){let before=snapshot(m);require(take(m,f)===null,'failed acquisition published');equal(snapshot(m),before,'failure changed pin authority');}
      const expected=oracle(n,events).free[0], t=take(m);require(t.slot===expected,'first free slot');tokens.push(t);events.push({kind:'issue',token:t});invariant(m,events);
    }
    let before=snapshot(m);require(take(m)===null,'exhaustion');equal(snapshot(m),before,'full mutated');
    const order=tokens.map((_,i)=>i).sort((a,b)=>((a*37)%65)-((b*37)%65));
    for(const i of order){let t=tokens[i];before=snapshot(m);require(!drop(m,{...t,owner:72}),'foreign token');require(!drop(m,{...t,nonce:t.nonce+900}),'stale token');require(!drop(m,t,true),'failed release');equal(snapshot(m),before,'invalid release mutation');require(drop(m,t),'valid release');events.push({kind:'release',token:t});invariant(m,events);before=snapshot(m);require(!drop(m,t),'repeated token');equal(snapshot(m),before,'repeat changed state');}
    for(let round=0;round<8;round++){
      for(let i=0;i<n;i++){let t=take(m);tokens[i]=t;events.push({kind:'issue',token:t});invariant(m,events);}
      m.terminal=true;before=snapshot(m);require(take(m)===null,'terminal acquisition');equal(snapshot(m),before,'terminal changed authority');
      for(let i=n-1;i>=0;i--){require(drop(m,tokens[i]),'terminal drain blocked');events.push({kind:'release',token:tokens[i]});invariant(m,events);}m.terminal=false;
    }
    histories++;require(m.live===0&&m.bits===full(n),'final cleanup');
  }
  // Exhaustively visit every valid inventory up to 8 slots, with nonce identities
  // assigned from event history rather than inferred from bitmap shape.
  for(let n=1;n<=8;n++)for(let mask=0;mask<(1<<n);mask++){
    let m=make(n),events=[],issued=[];for(let i=0;i<n;i++){let t=take(m);events.push({kind:'issue',token:t});issued.push(t);}
    for(let i=0;i<n;i++)if(mask&(1<<i)){require(drop(m,issued[i]),'subset release');events.push({kind:'release',token:issued[i]});}
    invariant(m,events);let expected=oracle(n,events).free[0],t=take(m);equal(t?.slot,expected,'subset first free');histories++;
  }
  for(let n=1;n<=64;n++){
    let m=make(n),t=take(m);m.bits|=1n;let before=snapshot(m);require(!drop(m,t),'release marked free');equal(snapshot(m),before,'corrupt release changed');corruptions++;
    m=make(n);m.bits^=1n;before=snapshot(m);require(take(m)===null,'mask/count disagreement');equal(snapshot(m),before,'corrupt count changed');corruptions++;
    if(n<64){m=make(n);m.bits|=1n<<63n;before=snapshot(m);require(take(m)===null,'out-of-range bit');equal(snapshot(m),before,'corrupt range changed');corruptions++;}
  }
  // A balanced corruption outside the selected slot is not a full audit. This is
  // an explicit boundary, not a test failure or a promise of arbitrary corruption
  // recovery: later selection of the occupied marked-free slot fails closed.
  {let m=make(4),t=take(m),u=take(m);require(drop(m,t),'setup');m.bits^=2n|8n;require(take(m)?.slot===0,'unaffected selected slot can proceed');require(take(m)===null,'subsequent occupied selection rejected');}
  const killed=[];
  for(const mutation of ['owner','nonce','early_publish','early_release']){
    let caught=false;try{let m=make(2),t=take(m),before=snapshot(m);if(mutation==='owner')require(!drop(m,{...t,owner:99},false,mutation),'foreign mutation accepted');if(mutation==='nonce')require(!drop(m,{...t,nonce:99},false,mutation),'stale mutation accepted');if(mutation==='early_publish'){take(m,3,mutation);equal(snapshot(m),before,'early bit mutation');}if(mutation==='early_release'){drop(m,t,true,mutation);equal(snapshot(m),before,'early release mutation');}}catch{caught=true;}require(caught,'mutation survived '+mutation);killed.push(mutation);
  }
  require(typeof process==='undefined'&&typeof requireNode==='undefined'&&typeof fetch==='undefined'&&typeof WebSocket==='undefined'&&typeof setTimeout==='undefined','sandbox APIs');
  return {checks,transitions,histories,corruptions,killed,scope:'independent event-log oracle and pure transaction model; not Rust execution',balancedCorruptionAudit:'selected-slot and cardinality checks, not full record audit'};
})()