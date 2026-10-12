'use strict';
const $=id=>document.getElementById(id), ctx=$('image').getContext('2d',{alpha:false});
let info,current=-1,busy=false,playing=false,bytes,header,shown=0,visited,generation=0;
const palette=[[0,0,0],[255,255,255],[0,191,255],[255,0,255]];
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function buttons(){
  $('play').textContent=playing?'❚❚ 일시정지':'▶ 재생';
  for(const id of ['prev','next','go','seek','position']) $(id).disabled=busy||playing;
  for(const id of ['raw','png'])$(id).disabled=busy||playing||!bytes;
  $('prev').disabled=busy||playing||current<=0;
  $('next').disabled=busy||playing||current>=info.count-1;
}
function pause(){playing=false;generation++;buttons();}
function hex(){
 if(!bytes)return;
 const start=Math.max(0,Math.min(bytes.length-1,Number($('offset').value)||0));let rows=[];
 for(let i=start;i<Math.min(start+256,bytes.length);i+=16)
  rows.push(i.toString(16).padStart(6,'0')+'  '+Array.from(bytes.subarray(i,i+16),v=>v.toString(16).padStart(2,'0')).join(' '));
 $('hex').textContent=rows.join('\n');
}
async function show(index){
 if(busy)throw Error('Concurrent frame request');
 busy=true;buttons();
 try{
  const response=await fetch('/frame?i='+index);if(!response.ok)throw Error(await response.text());
  const record=await response.arrayBuffer();if(record.byteLength!==175712)throw Error('Record size mismatch');
  header=new DataView(record);bytes=new Uint8Array(record,32);
  const result=DVSDecoder.decode(bytes);
  const canvas=$('image');canvas.width=result.valid?960:976;canvas.height=result.valid?720:180;
  const picture=ctx.createImageData(canvas.width,canvas.height);
  for(let i=0;i<canvas.width*canvas.height;i++){
   const color=result.valid?palette[result.codes[i]]:[bytes[i],bytes[i],bytes[i]];
   picture.data.set([color[0],color[1],color[2],255],i*4);
  }
  ctx.putImageData(picture,0,0);
  current=index;shown++;visited[index]=1;
  $('position').value=$('seek').value=index+1;
  const relative=Number(header.getBigUint64(8,true)-BigInt(info.first_ns))/1e9;
  $('timing').textContent=`프레임 ${(index+1).toLocaleString()} / ${info.count.toLocaleString()} · 수신 시각 +${relative.toFixed(6)}초 · 표시 횟수 ${shown.toLocaleString()} · 고유 프레임 ${visited.reduce((a,b)=>a+b,0).toLocaleString()}`;
  $('warning').textContent=result.valid?'기존 RAW2 디코더의 좌표 배치로 표시합니다. 저장 전 수신 손실 여부를 보증하지 않습니다.':`정렬 불일치: 내장 영역 ${result.length}개 (예상 16개). 이 레코드를 버리지 않고 원시 바이트 회색조로 표시합니다.`;
  $('stats').textContent=`V4L2 순번: ${header.getUint32(16,true)}\nSOF (ns): ${header.getBigUint64(0,true)}\n수신 (ns): ${header.getBigUint64(8,true)}\nflags: 0x${header.getUint32(20,true).toString(16)}\nbytesused: ${header.getUint32(24,true)}\n보존 payload: ${bytes.length} bytes\n정렬 후보: ${result.start}, 길이 ${result.length}\n코드 [00,01,10,11]: ${result.valid?result.counts.join(', '):'해석 보류'}\n\n전체 호스트 순번 gap: ${info.host_sequence_gaps}\n역행: ${info.host_sequence_regressions} / 중복: ${info.host_sequence_duplicates}\nV4L2 오류 플래그: ${info.host_error_frames}\n※ 센서 자체 누락 통계가 아닙니다.`;
  $('embedded').textContent=result.words.map((row,i)=>`chunk +${i}\n`+row.map(v=>v.toString(16).padStart(8,'0')).join(' ')).join('\n\n')||'내장 영역 후보가 없습니다. RAW 바이트를 확인하세요.';
  hex();
  // Yield through two animation callbacks before requesting the next record.
  // This never catches up to wall clock by skipping source frames.
  if(!document.hidden)await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
 }finally{busy=false;buttons();}
}
async function play(){
 if(playing){pause();return;}if(busy)return;
 if(current===info.count-1)await show(0);
 playing=true;const token=++generation;buttons();$('error').textContent='';
 try{
  while(playing&&token===generation&&current<info.count-1){
   await delay(1000/Number($('rate').value));
   if(!playing||token!==generation)break;
   await show(current+1);
  }
 }catch(error){$('error').textContent='재생 중지: '+error.message;}
 finally{if(token===generation)pause();}
}
async function move(index){
 if(busy||playing)return;
 try{await show(Math.max(0,Math.min(info.count-1,index)));}
 catch(error){$('error').textContent=error.message;}
}
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('play').onclick=play;$('prev').onclick=()=>move(current-1);$('next').onclick=()=>move(current+1);
$('go').onclick=()=>move((Number($('position').value)||1)-1);$('seek').onchange=()=>move(Number($('seek').value)-1);
$('offset').oninput=hex;$('raw').onclick=()=>download(new Blob([bytes]),`frame-${String(current+1).padStart(6,'0')}.raw2`);
$('png').onclick=()=>$('image').toBlob(blob=>download(blob,`frame-${current+1}.png`));
document.addEventListener('visibilitychange',()=>{if(document.hidden&&info)pause();});
document.addEventListener('keydown',e=>{if(e.target.matches('input,select')||!info)return;if(e.code==='Space'){e.preventDefault();play();}else if(e.code==='ArrowRight')move(current+1);else if(e.code==='ArrowLeft')move(current-1);});
(async()=>{
 try{
  const response=await fetch('/info');if(!response.ok)throw Error(await response.text());info=await response.json();visited=new Uint8Array(info.count);
  $('file').textContent=`${info.name} · ${info.count.toLocaleString()}개 · 호스트 수신 ${info.received_fps.toFixed(2)}/초 · SHA-256 ${info.sha256_verified?'일치 확인':'기준 JSON 없음 (미검증)'} · 60개/초 표시도 약 ${(info.received_fps/60).toFixed(1)}배 슬로모션`;
  $('seek').max=$('position').max=info.count;
  await show(0);for(const id of ['play','raw','png'])$(id).disabled=false;
 }catch(error){$('error').textContent=error.message;}
})();
