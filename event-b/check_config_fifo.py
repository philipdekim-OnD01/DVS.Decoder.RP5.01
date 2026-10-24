#!/usr/bin/env python3
"""One owned named-pipe config fixture; no device or production access."""
import pathlib,subprocess,os,json,sys
root=pathlib.Path(sys.argv[1]);fifo=root/'config/fifo-test.json';os.mkfifo(fifo)
try:
 p=subprocess.Popen([str(root/'bin/event-b'),'replay','--file',str(root/'config/default.json'),'--name','fifo-refusal','--config',str(fifo)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:stdout,stderr=p.communicate(timeout=.5);result={'blocked':False,'exit':p.returncode,'stderr':stderr}
 except subprocess.TimeoutExpired:p.terminate();p.communicate(timeout=2);result={'blocked':True,'owned_process_terminated':True,'reason':'config.read_text attempts FIFO open before type validation'}
 print(json.dumps(result))
finally:fifo.unlink()
