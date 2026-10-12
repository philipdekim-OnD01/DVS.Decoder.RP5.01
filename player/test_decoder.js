const assert=require('node:assert/strict');
const {decode}=require('./decoder.js');
function sample(start){
 const data=new Uint8Array(175680);
 for(let j=0;j<16;j++)data.fill(0xcc,((start+j)%976)*180+176,((start+j)%976)*180+180);
 return data;
}
for(const start of [0,100,970]){
 const data=sample(start),first=(start+16)%976;
 const offset=(first*180+176)%data.length;
 data[offset]=0x6c; // 01, 10, 11, 00 at column 15, rows 719..716.
 const result=decode(data);
 assert.equal(result.valid,true);assert.equal(result.start,start);
 assert.deepEqual([719,718,717,716].map(y=>result.codes[y*960+15]),[1,2,3,0]);
 assert.equal(result.counts.reduce((a,b)=>a+b),960*720);
 data[offset]=0;
 assert.equal(decode(data).codes[719*960+15],0,'No persistence across records');
}
assert.equal(decode(new Uint8Array(175680)).valid,false,'Malformed frames remain explicit');
assert.throws(()=>decode(new Uint8Array(1)));
console.log('Decoder tests passed: wrap, polarity, unassigned code, no aggregation, invalid alignment');
