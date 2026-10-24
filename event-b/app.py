#!/usr/bin/env python3
"""Event-only runtime: runs belong to this private package; loopback viewer only."""
import argparse,pathlib,json,sys,subprocess,os,re,stat,signal,http.server,functools
ROOT=pathlib.Path(__file__).resolve().parent.parent

def checked_name(s):
 if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',s) is None:raise ValueError('invalid run name')
 return s

def read_config(path):
 # Pin without opening a data/device file, then read the verified regular inode.
 directory=ROOT/'config'
 if directory.is_symlink() or path.parent.resolve()!=directory.resolve():raise ValueError('config must be inside package/config')
 pin=os.open(path,os.O_PATH|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  st=os.fstat(pin)
  if not stat.S_ISREG(st.st_mode) or not 0<st.st_size<=16384:raise ValueError('config must be a small non-symlink regular file')
  fd=os.open('/proc/self/fd/'+str(pin),os.O_RDONLY|os.O_CLOEXEC|os.O_NONBLOCK)
  try:
   raw=os.read(fd,16385);after=os.fstat(fd)
   if len(raw)!=st.st_size or (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):raise ValueError('config changed')
  finally:os.close(fd)
 finally:os.close(pin)
 def pairs(items):
  result={}
  for k,v in items:
   if k in result:raise ValueError('duplicate config key')
   result[k]=v
  return result
 return json.loads(raw,object_pairs_hook=pairs)

def main():
 # Reject every device spelling before file/config/output operations.
 if any(x=='--device' or x.startswith('--device=') for x in sys.argv[1:]):print('PHASE_C_BLOCKED: file-only package',file=sys.stderr);return 2
 p=argparse.ArgumentParser(description='Event B — independent offline file replay');sub=p.add_subparsers(dest='command',required=True)
 r=sub.add_parser('replay');r.add_argument('--file',type=pathlib.Path,required=True);r.add_argument('--name',required=True);r.add_argument('--config',type=pathlib.Path,default=ROOT/'config/default.json')
 s=sub.add_parser('serve');s.add_argument('--name',required=True);s.add_argument('--port',type=int,default=8767)
 sub.add_parser('info');a=p.parse_args()
 if a.command=='info':print((ROOT/'manifest.json').read_text());return 0
 name=checked_name(a.name);runs=ROOT/'runs';out=runs/name
 if runs.is_symlink() or out.is_symlink():raise ValueError('run path symlink refused')
 if a.command=='replay':
  config=read_config(a.config)
  if not isinstance(config,dict) or set(config)!={'queue_capacity','decode_delay_us'} or type(config['queue_capacity']) is not int or not 1<=config['queue_capacity']<=32 or type(config['decode_delay_us']) is not int or not 0<=config['decode_delay_us']<=1000000:raise ValueError('invalid config')
  if a.file.is_symlink() or not stat.S_ISREG(a.file.lstat().st_mode) or a.file.lstat().st_size<=0:raise ValueError('input must be non-symlink regular file')
  if out.exists():raise ValueError('run already exists')
  proc=subprocess.Popen([str(ROOT/'bin/event-b-engine'),'--file',str(a.file),str(out),str(config['queue_capacity']),str(config['decode_delay_us'])],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  def forward(signum,_frame):
   if proc.poll() is None:proc.send_signal(signum)
  signal.signal(signal.SIGINT,forward);signal.signal(signal.SIGTERM,forward)
  stdout,stderr=proc.communicate()
  if out.is_dir():
   (out/'stdout.log').write_text(stdout);(out/'stderr.log').write_text(stderr)
   (out/'status.json').write_text(json.dumps({'mode':'file','exit_code':proc.returncode,'complete':proc.returncode==0,'phase_c':'HARD BLOCKED','production_changed':False})+'\n')
   for f in ('index.html','viewer.js'):(out/f).write_bytes((ROOT/'share'/f).read_bytes())
  print(json.dumps({'run':str(out),'exit_code':proc.returncode,'viewer':'serve --name '+name}));return proc.returncode if proc.returncode>=0 else 128-proc.returncode
 if not out.is_dir() or not (out/'status.json').exists():raise ValueError('unknown/incomplete run')
 if not 1024<=a.port<=65535:raise ValueError('invalid port')
 class Handler(http.server.SimpleHTTPRequestHandler):
  def do_GET(self):
   target=pathlib.Path(self.translate_path(self.path))
   if not target.resolve().is_relative_to(out.resolve()):self.send_error(403);return
   return super().do_GET()
 handler=functools.partial(Handler,directory=str(out));server=http.server.ThreadingHTTPServer(('127.0.0.1',a.port),handler)
 print('Event B viewer: http://127.0.0.1:'+str(a.port),flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
 return 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except (ValueError,OSError,json.JSONDecodeError) as e:print('Event B: '+str(e),file=sys.stderr);raise SystemExit(2)
