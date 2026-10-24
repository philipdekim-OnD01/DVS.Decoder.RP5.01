// Same EventGroup rendering rule as PR5, extended to indexed file playback.
export function indexFrames(buffer) {
 if(buffer.byteLength>128*1024*1024)throw Error('재생 파일이 128MiB 제한을 초과했습니다');
 const v=new DataView(buffer),frames=[];let at=0;
 while(at<v.byteLength){
  if(v.byteLength-at<16)throw Error('잘린 프레임 헤더');
  const timestamp=v.getBigUint64(at,true),period=v.getUint32(at+8,true),groups=v.getUint32(at+12,true),end=at+16+groups*6;
  if(end>v.byteLength)throw Error('잘린 이벤트 그룹');
  for(let p=at+16;p<end;p+=6)if(v.getUint16(p,true)>=960||v.getUint16(p+2,true)>712||v.getUint16(p+2,true)%8||v.getUint8(p+5)>1)throw Error('잘못된 이벤트 좌표');
  frames.push({offset:at,timestamp,period,groups});at=end;
 }
 return {view:v,frames};
}
export function renderFrame(data,index,filter='all') {
 if(!['all','on','off'].includes(filter)||index<0||index>=data.frames.length)throw Error('잘못된 프레임 선택');
 const pixels=new Uint8ClampedArray(960*720*4),f=data.frames[index],v=data.view;let on=0,off=0;
 for(let i=3;i<pixels.length;i+=4)pixels[i]=255;
 for(let n=0;n<f.groups;n++){
  const p=f.offset+16+n*6,x=v.getUint16(p,true),y=v.getUint16(p+2,true),mask=v.getUint8(p+4),pol=v.getUint8(p+5);
  for(let bit=0;bit<8;bit++)if(mask&(1<<bit)){if(pol)off++;else on++;if(filter==='on'&&pol||filter==='off'&&!pol)continue;pixels[((y+bit)*960+x)*4+(pol?0:1)]=255;}
 }
 return {pixels,on,off};
}
if(typeof document!=='undefined'){
 const $=id=>document.getElementById(id);let data,current=0,timer=null;
 function stop(){clearTimeout(timer);timer=null;$('play').textContent='재생';}
 function draw(){const f=data.frames[current],r=renderFrame(data,current,$('polarity').value);$('view').getContext('2d').putImageData(new ImageData(r.pixels,960,720),0,0);$('seek').value=current;$('frameinfo').textContent=`프레임 ${current+1} / ${data.frames.length} · 센서 시각 ${f.timestamp} µs · 주기 ${f.period} µs · ON ${r.on} / OFF ${r.off}`;}
 function tick(){if(current+1>=data.frames.length){stop();return;}current++;draw();timer=setTimeout(tick,1000/Number($('fps').value));}
 $('play').onclick=()=>{if(timer!==null){stop();return;}if(current+1>=data.frames.length)current=0;draw();$('play').textContent='일시정지';timer=setTimeout(tick,1000/Number($('fps').value));};
 $('seek').oninput=()=>{stop();current=Number($('seek').value);draw();};$('polarity').onchange=()=>{if(data?.frames.length)draw();};
 (async()=>{try{
  const [res,m,s]=await Promise.all(['frames.bin','metrics.json','status.json'].map(x=>fetch(x,{cache:'no-store'})));if(!res.ok||!m.ok||!s.ok)throw Error('결과 파일을 읽을 수 없습니다');
  const status=await s.json(),metrics=await m.json();if(!status.complete)throw Error(`미완료 실행: exit ${status.exit_code}`);
  data=indexFrames(await res.arrayBuffer());if(!data.frames.length)throw Error('완성된 이벤트 프레임이 없습니다');
  $('seek').max=data.frames.length-1;$('seek').disabled=false;$('play').disabled=false;
  $('stats').textContent=JSON.stringify({mode:metrics.mode,completed_frames:metrics.frames,SDK_events:metrics.events,ON:metrics.on_events,OFF:metrics.off_events,unsynced_groups:metrics.unsynced_groups,queue_high_water:metrics.queue_high_water,queue_capacity:metrics.queue_capacity,queue_drops:metrics.queue_drops,queue_final:metrics.queue_final,cpu_percent:metrics.cpu_percent,file_MB_per_second:metrics.MB_per_second,EOF_incomplete_frames:metrics.eof_incomplete_frames,EOF_partial_bytes:metrics.eof_partial_bytes},null,2);draw();
 }catch(e){stop();$('frameinfo').textContent=e.message;$('stats').textContent='재생 실패';}})();
}
