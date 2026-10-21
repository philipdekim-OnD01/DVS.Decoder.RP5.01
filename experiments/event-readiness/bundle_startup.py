"""Tamper-evident synthetic bundle and isolated startup; NO hardware backend."""
import fcntl,hashlib,json,os,pathlib,re,stat,tempfile,time
ROLES=('rp1_override','sensor_module','dt_overlay','boot_config','sensor_options','cfe_options','unit','unit_dropins','setfile','saved_registers','initializer','producer','hand_profile','server')
ADDRESSES=('3000','3260','3901','3902','3903','3906','3907','3908','3910','3915','391A','391B')
TARGET={'kernel':'6.12.47+rpt-rpi-2712','receiver_dt':42,'width':8192,'height':128,'fourcc':'GREY','link_frequency':625000000,'lanes':4}
STAGES=('receiver','sensor-profile','media-profile','processes')
def digest(data):return hashlib.sha256(data).hexdigest()
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
def no_duplicates(pairs):
 result={}
 for k,v in pairs:
  if k in result:raise ValueError('duplicate JSON key')
  result[k]=v
 return result
def bounded_read(root,relative):
 parts=pathlib.PurePosixPath(relative).parts
 if not parts or relative.startswith('/') or any(p in ('.','..') for p in parts) or str(pathlib.PurePosixPath(relative))!=relative:raise ValueError('unsafe bundle path')
 fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  for part in parts[:-1]:
   nxt=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nxt
  file=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
  try:
   before=os.fstat(file)
   if not stat.S_ISREG(before.st_mode) or before.st_size>16*1024*1024:raise ValueError('bundle object is not a bounded regular file')
   data=b''
   while True:
    chunk=os.read(file,65536)
    if not chunk:break
    data+=chunk
    if len(data)>16*1024*1024:raise ValueError('bundle file grew beyond limit')
   after=os.fstat(file)
   if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):raise ValueError('bundle changed during read')
   return data
  finally:os.close(file)
 finally:os.close(fd)
def validate_bundle(root,trusted_manifest_hash):
 raw=bounded_read(root,'manifest.json')
 if not re.fullmatch('[0-9a-f]{64}',trusted_manifest_hash) or digest(raw)!=trusted_manifest_hash:raise ValueError('external manifest pin mismatch')
 m=json.loads(raw,object_pairs_hook=no_duplicates)
 if set(m)!={'schema','target','files','register_evidence'} or m['schema']!=1 or m['target']!=TARGET:raise ValueError('target/schema mismatch or unsupported commands')
 if m['register_evidence']!='STORED_NOT_LIVE':raise ValueError('unsupported or falsely asserted live evidence')
 if set(m['files'])!=set(ROLES):raise ValueError('required role missing or extra role')
 seen=set();total=0
 for role,entry in m['files'].items():
  if set(entry)!={'path','sha256'} or entry['path'] in seen:raise ValueError('duplicate or malformed file role')
  seen.add(entry['path']);data=bounded_read(root,entry['path']);total+=len(data)
  if total>64*1024*1024 or digest(data)!=entry['sha256']:raise ValueError('file drift/hash mismatch')
  if role=='saved_registers':
   rows=data.decode('ascii').splitlines();parsed=[re.fullmatch(r'([0-9A-F]{4}) 0x[0-9A-F]{2}',s) for s in rows]
   if len(rows)!=12 or not all(parsed) or sorted(p[1] for p in parsed)!=sorted(ADDRESSES):raise ValueError('malformed or incomplete saved register list')
 return {'validated':True,'manifest_sha256':trusted_manifest_hash,'roles':len(ROLES),'register_rows':12,'live_registers_verified':False,'production_ready':False}
def make_fixture(root):
 root=pathlib.Path(root)
 if not root.resolve().is_relative_to(pathlib.Path(tempfile.gettempdir()).resolve()):raise ValueError('fixtures are temp-only')
 root.mkdir();entries={}
 for role in ROLES:
  # Synthetic zero values only. NOT a usable sensor setfile/register dump.
  data=(''.join(a+' 0x00\n' for a in ADDRESSES) if role=='saved_registers' else 'SYNTHETIC-NONPRODUCTION:'+role+'\n').encode()
  path=root/(role+'.fixture');path.write_bytes(data);entries[role]={'path':path.name,'sha256':digest(data)}
 m={'schema':1,'target':TARGET.copy(),'files':entries,'register_evidence':'STORED_NOT_LIVE'}
 raw=canonical(m);(root/'manifest.json').write_bytes(raw)
 for p in root.iterdir():p.chmod(0o444)
 return digest(raw)
def temp_workspace(root):
 root=pathlib.Path(root)
 if root.is_symlink() or not root.resolve().is_relative_to(pathlib.Path(tempfile.gettempdir()).resolve()):raise ValueError('sandbox outside temp')
 root.mkdir(exist_ok=False);(root/'SANDBOX_ONLY').write_text('STARTUP-NO-HARDWARE')
 return root
def startup(root,bundle,pin,hook=lambda stage:None):
 root=pathlib.Path(root)
 if root.is_symlink() or not root.resolve().is_relative_to(pathlib.Path(tempfile.gettempdir()).resolve()) or (root/'SANDBOX_ONLY').read_text()!='STARTUP-NO-HARDWARE':raise ValueError('invalid startup sandbox')
 for name in ('startup.lock','journal.json'):
  if (root/name).is_symlink():raise ValueError('sandbox symlink')
 result={'mode':'SANDBOX_ONLY','status':'REFUSED','effects':[],'legacy_invocations':0,'real_production_actions':0,'production_ready':False}
 with (root/'startup.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:result['reason']='concurrent sandbox startup';return result
  def guard():
   if (root/'pending_first_boot_validation').exists() or (root/'firstboot-timer-active').exists():raise ValueError('firstboot marker/timer conflict')
   validate_bundle(bundle,pin)
  try:
   guard();hook('after-initial-check');guard()
   for stage in STAGES:
    guard();hook('before-'+stage);guard()
    # Only the test journal changes. No process, sensor or media is started.
    result['effects'].append(stage)
    hook('after-'+stage);guard()
   result['status']='VERIFIED_SANDBOX';result['reason']='no live backend'
  except (ValueError,OSError) as e:result['reason']=str(e)
  (root/'journal.json').write_text(json.dumps(result,indent=2)+'\n')
  return result
