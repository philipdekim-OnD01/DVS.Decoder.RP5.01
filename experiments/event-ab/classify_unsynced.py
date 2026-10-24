#!/usr/bin/env python3
"""Relate observed SDK increments to independent 4B classes and trace offsets."""
import argparse,pathlib,json,collections,struct,hashlib,itertools,platform
p=argparse.ArgumentParser();p.add_argument('--sample',type=pathlib.Path,required=True);p.add_argument('--work',type=pathlib.Path,required=True);p.add_argument('--results',type=pathlib.Path,required=True);a=p.parse_args()
b=a.sample.read_bytes();assert hashlib.sha256(b).hexdigest()=='962925dfaf87fcd1a16d04cd6e122d32558527b543f39acc2803926f2fc897b3'
rows=[list(map(int,x.split(','))) for x in (a.work/'sdk.unsynced.csv').read_text().splitlines()];offsets={r[0] for r in rows};assert len(rows)==len(offsets)==830
counts=collections.Counter();first={};mo=False;group_mo=collections.Counter();prefix_groups=0;changes=0;prevx=None;col_frame=-1;last_end=-1;orphan_words=0;frame_mismatches=0;first_epoch=None
for o in range(0,len(b),4):
 c0,c1,c2,c3=b[o:o+4];tag=c0&124
 cls='PAD' if not(c0|c1|c2|c3) else 'GROUP' if c0&128 else ('SUB_TS' if c1&128 else 'REF_TS') if tag==8 else 'COLUMN' if tag==4 else 'FRAME_END' if tag==12 else 'UNKNOWN'
 counts[cls]+=1;first.setdefault(cls,o)
 if cls=='COLUMN':
  mo=bool(c1&128);x=((c2&7)<<8)|c3;col_frame=((c1&7)<<5)|(c2>>3)
  if first_epoch is None and c1&32 and o>first.get('SUB_TS',len(b)):first_epoch=o
  if o<=max(offsets) and x!=prevx:changes+=1
  prevx=x
 if cls=='FRAME_END':
  end=((c1&7)<<5)|(c2>>3)
  frame_mismatches+=int(col_frame>=0 and end!=col_frame)+int(last_end>=0 and end!=((last_end+1)&255));last_end=end;col_frame=-1
 if cls=='GROUP':
  orphan_words+=int(col_frame<0)
  group_mo[str(int(mo))]+=1
  if o<=max(offsets):prefix_groups+=1;assert o in offsets
 if o in offsets:assert cls=='GROUP'
assert all(r[1]==0 and r[2]>=0 and r[3:]==[0,0,0] for r in rows)

def events(name):
 data=(a.work/(name+'.events')).read_bytes();return {o:list(g) for o,g in itertools.groupby(struct.iter_unpack('<QHHBBxx',data),key=lambda r:r[0])}
old=events('dual');new=events('sdk');different={o for o in old.keys()|new.keys() if old.get(o,[])!=new.get(o,[])};assert different==offsets
prefixevents=[e for o in offsets for e in old[o]];assert len(prefixevents)==1073
pol=collections.Counter(e[3] for e in prefixevents)
report={'host':platform.platform(),'sample_sha256':hashlib.sha256(b).hexdigest(),'sdk_unsynced_count':len(rows),'offset_min':min(offsets),'offset_max':max(offsets),'before_first_column':sum(o<first['COLUMN'] for o in offsets),'before_first_frame_end':sum(o<first['FRAME_END'] for o in offsets),'before_first_ref_ts':sum(o<first['REF_TS'] for o in offsets),'before_first_sub_ts':sum(o<first['SUB_TS'] for o in offsets),'missing_state':{'x_invalid':sum(r[2]<0 for r in rows),'ref_missing':830,'sub_missing':830,'epoch_missing':830,'CID1':0},'method_reference':{'name':'Jetson dvs_gaps.py','git_blob_sha':'08bb04300fc876e11b4966832e4fc24ebb132636','scope':'reviewed 4B classification, carried COLUMN/FE state and fixed-offset method only; no private code copied'},'column_orphan_group_words':orphan_words,'frame_number_check_failures':frame_mismatches,'first_epoch_column_after_timestamp':first_epoch,'fixed_boundary_causality':'NOT INFERABLE: original buffer/packet metadata absent; offset0 is file start, not proven DMA boundary','prefix_group_words':prefix_groups,'prefix_column_changes':changes,'first_offsets':first,'word_class_counts':dict(counts),'group_words_by_column_mo':dict(group_mo),'different_dual_words_equal_unsynced_offsets':True,'dual_prefix_extra_events':len(prefixevents),'extra_on':pol[0],'extra_off':pol[1],'events_after_prefix_equal':True,'unsynced_after_offset5732':0,'original_v4l2_boundaries':'UNKNOWN / not preserved in raw word sample','CSI_packet_boundaries':'UNKNOWN / not preserved','actual_sensor_loss':'UNKNOWN / not derivable from this counter','software_interpretation':'all observed increments are file-prefix groups with valid X but no ref/sub/epoch; no evidence of interior split-induced increments','physical_prefix_origin':'UNKNOWN: truncation/recording-start position not authenticated','hardware_actions':0}
a.results.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
