#!/usr/bin/env python3
"""Read-only Pi inventory. Never invokes I2C, scripts or mutating subcommands."""
import datetime,hashlib,json,os,pathlib,platform,re,shutil,subprocess,time
ROOT=pathlib.Path('/home/philip/dvs_raw2_production')
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=15)
 return {'returncode':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
def describe(path):
 p=pathlib.Path(path)
 try:
  b=p.read_bytes();s=p.stat()
  return {'exists':True,'resolved':str(p.resolve()),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'mtime_ns':s.st_mtime_ns}
 except OSError as e:return {'exists':p.exists(),'unobserved':type(e).__name__}
def main():
 files=[str(ROOT/n) for n in ('raw2_production_start.sh','raw2_production_rollback.sh','raw2_production_validate.sh','raw2_production_install.sh','raw2_producer','sensor_hand_profile.py','server_production.py','backup/sensor_registers_before_key.txt','sensor_registers_raw2_programmed.txt')]
 files+=['/home/philip/bin/Delta_10_2000FPS.txt','/home/philip/bin/s5krc1s_probe_init.py','/boot/firmware/config.txt','/boot/firmware/overlays/s5krc1s-cam0.dtbo','/etc/modprobe.d/s5krc1s_min.conf','/etc/modprobe.d/dvs-raw2-production-rp1.conf','/etc/systemd/system/dvs-raw2-production.service','/usr/local/sbin/camera-root-watchdog.sh']
 files += [str(p) for p in pathlib.Path('/etc/systemd/system/dvs-raw2-production.service.d').glob('*.conf')]
 modules={}
 for name in ('rp1_cfe','s5krc1s_min'):
  modules[name]=run(['/usr/sbin/modinfo','-n',name]);path=modules[name]['stdout']
  modules[name]['file_srcversion']=run(['/usr/sbin/modinfo','-F','srcversion',name])
  for field in ('srcversion','version','initstate','refcnt'):
   f=pathlib.Path('/sys/module')/name/field
   try:modules[name]['loaded_'+field]=f.read_text().strip()
   except OSError:modules[name]['loaded_'+field]='UNOBSERVED'
  if path.startswith('/lib/modules/'+platform.release()+'/'):files.append(path)
 params={}
 for name in ('rp1_cfe','s5krc1s_min'):
  directory=pathlib.Path('/sys/module')/name/'parameters'
  params[name]={p.name:p.read_text().strip() for p in directory.glob('*') if p.is_file()}
 tools={}
 for candidate in dict.fromkeys(filter(None,[shutil.which('i2ctransfer'),'/usr/bin/i2ctransfer','/usr/sbin/i2ctransfer','/sbin/i2ctransfer'])):
  tools[candidate]=describe(candidate)
 reg=ROOT/'sensor_registers_raw2_programmed.txt';rows=reg.read_text().splitlines()
 parsed=[re.fullmatch(r'([0-9A-Fa-f]{4})\s+0x([0-9A-Fa-f]{2})',line) for line in rows]
 valid=bool(rows) and all(parsed)
 if valid:valid=len({m[1].upper() for m in parsed})==len(rows)
 properties=['-p', 'Id','-p','LoadState','-p','ActiveState','-p','UnitFileState','-p','FragmentPath','-p','DropInPaths','-p','ExecStart','-p','Restart','-p','RestartUSec','-p','MainPID','-p','NRestarts']
 service=run(['systemctl','show','dvs-raw2-production.service',*properties])
 firstboot=run(['systemctl','show','raw2-production-firstboot-expiry.timer','raw2-production-firstboot-expiry.service','camera-root-watchdog.timer',*properties])
 graph=run(['media-ctl','-d','/dev/media0','-p'])
 graph_summary={'returncode':graph['returncode'],'sha256':hashlib.sha256(graph['stdout'].encode()).hexdigest(),'y8_8192_128':graph['stdout'].count('Y8_1X8/8192x128'),'ch0_present':'rp1-cfe-csi2_ch0' in graph['stdout']}
 keys=('v4l2_sequence','capture_buffers_sec','raw_bytes_sec','web_fps','hdmi_fps','v4l2_dequeue_errors','v4l2_buffer_errors','v4l2_sequence_gaps')
 a=json.loads(pathlib.Path('/tmp/dvs_web_metrics.json').read_text());time.sleep(2);b=json.loads(pathlib.Path('/tmp/dvs_web_metrics.json').read_text())
 return {'observed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'kernel':platform.release(),'files':{p:describe(p) for p in files},'live_fdt':describe('/sys/firmware/fdt'),'modules':modules,'module_parameters':params,'tools':tools,'tool_invoked':False,'register_record':{'rows':len(rows),'well_formed':valid,'live_readback':False},'pending_marker':(ROOT/'pending_first_boot_validation').exists(),'service':service,'watchdogs':firstboot,'media':graph_summary,'system_timers':run(['systemctl','list-timers','--all','--no-pager']),'before':{k:a.get(k) for k in keys},'after':{k:b.get(k) for k in keys},'production_changed':False,'live_register_access':False}
if __name__=='__main__':print(json.dumps(main(),indent=2))
