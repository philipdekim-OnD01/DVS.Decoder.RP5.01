#!/usr/bin/env python3
"""One bounded directory inventory; no RAW data, device, debugfs or I2C reads."""
import argparse,datetime,hashlib,json,pathlib,re,subprocess
p=argparse.ArgumentParser();p.add_argument('directory',type=pathlib.Path);p.add_argument('--pi-state',action='store_true');a=p.parse_args()
root=a.directory;rows=[];terms=re.compile(r'CSI|wire|packet|frame.counter|embedded|Fig.?46|DT/WC|FS/FE',re.I)
entries=sorted(root.iterdir());assert len(entries)<=256,'scope exceeds bound'
for f in entries:
 if f.is_symlink():rows.append({'name':f.name,'skipped':'symlink'});continue
 s=f.stat();r={'name':f.name,'bytes':s.st_size,'type':'directory' if f.is_dir() else 'file'}
 if f.is_file() and f.suffix.lower() in ('.md','.json','.txt','.log','.csv') and s.st_size<=262144:
  b=f.read_bytes();r['sha256']=hashlib.sha256(b).hexdigest();text=b.decode(errors='replace');r['matching_line_numbers']=[i for i,line in enumerate(text.splitlines(),1) if terms.search(line)];r['inspected_text']=True
 else:r['content_read']=False
 rows.append(r)
report={'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':str(root),'depth':1,'max_entries':256,'max_text_bytes':262144,'raw_content_read':False,'entries':rows,'same_session_wire_identity':'NOT_AUTHENTICATED','production_changes':0}
if a.pi_state:
 report['service']=subprocess.run(['systemctl','show','dvs-raw2-production.service','-p','ActiveState','-p','UnitFileState','-p','MainPID','-p','NRestarts'],capture_output=True,text=True,check=True,timeout=10).stdout
print(json.dumps(report,indent=2))
