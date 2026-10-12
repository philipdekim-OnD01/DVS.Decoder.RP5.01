/* Every 2-bit code remains visible: 00 black, 01 white, 10 blue, 11 magenta.
   Coordinate mapping follows the existing PACK_BYTES receiver decoder.
   Metadata interpretation is provisional; raw words are always inspectable. */
(function(root) {
'use strict';
const N=976, B=180, P=N*B;
function decode(raw) {
  if(raw.length!==P) throw Error('Unexpected payload length');
  const view=new DataView(raw.buffer,raw.byteOffset,raw.byteLength);
  const flags=new Uint8Array(N);
  for(let i=0;i<N;i++) {
    if(view.getUint32(i*B+176,true)!==0xcccccccc) continue;
    const unique=new Set();
    for(let j=0;j<45;j++) unique.add(view.getUint32(i*B+j*4,true));
    if(unique.size<=20) flags[i]=1;
  }
  let start=-1,length=0;
  for(let i=0;i<N;i++) {
    if(!flags[i]||flags[(i+N-1)%N]) continue;
    let n=0;while(n<N&&flags[(i+n)%N]) n++;
    if(n>length) {start=i;length=n;}
  }
  const codes=new Uint8Array(960*720), counts=[0,0,0,0], words=[];
  if(start>=0) for(let j=0;j<18;j++) {
    const base=((start+j)%N)*B;
    words.push(Array.from({length:45},(_,k)=>view.getUint32(base+k*4,false)));
  }
  if(length!==16) return {valid:false,start,length,codes,counts,words};
  const first=(start+16)%N;
  for(let serial=0;serial<960;serial++) {
    const offset=(((first+serial)%N)*B+176)%P;
    const x=Math.floor(serial/16)*16+15-serial%16;
    for(let b=0;b<B;b++) {
      const value=raw[(offset+b)%P];
      for(let k=0;k<4;k++) {
        const code=(value>>(6-2*k))&3;
        codes[(719-b*4-k)*960+x]=code;counts[code]++;
      }
    }
  }
  return {valid:true,start,length,codes,counts,words};
}
root.DVSDecoder={decode};
if(typeof module!=='undefined') module.exports=root.DVSDecoder;
})(globalThis);
