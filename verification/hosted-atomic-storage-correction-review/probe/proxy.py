#!/usr/bin/env python3
"""Owned UNIX-socket PostgreSQL fixture: drop exactly one armed COMMIT reply."""
import json,pathlib,selectors,socket,struct,sys,threading
source,target,arm,log=map(pathlib.Path,sys.argv[1:])
def record(value):
 with log.open('a') as f:f.write(json.dumps(value)+'\n')
def handle(client):
 backend=socket.socket(socket.AF_UNIX);backend.connect(str(source/'.s.PGSQL.5432'))
 selector=selectors.DefaultSelector();selector.register(client,selectors.EVENT_READ,backend);selector.register(backend,selectors.EVENT_READ,client)
 pending=b''
 try:
  while True:
   for key,_ in selector.select():
    chunk=key.fileobj.recv(65536)
    if not chunk:return
    if key.fileobj is client:key.data.sendall(chunk);continue
    pending+=chunk
    while len(pending)>=5:
     length=struct.unpack('!I',pending[1:5])[0]
     if length<4 or length>16777216:raise RuntimeError('fixture framing')
     if len(pending)<length+1:break
     frame,pending=pending[:length+1],pending[length+1:]
     if frame[:1]==b'C' and frame[5:]==b'COMMIT\0' and arm.exists():
      arm.unlink();record({'dropped':'COMMIT CommandComplete','server_commit_completed':True,'client_ack_sent':False});return
     client.sendall(frame)
 finally:
  selector.close();client.close();backend.close()
listener=socket.socket(socket.AF_UNIX);listener.bind(str(target/'.s.PGSQL.5432'));listener.listen(8)
record({'ready':True,'transport':'owned unix socket only'})
while True:
 client,_=listener.accept();threading.Thread(target=handle,args=(client,),daemon=True).start()
