"""Temporary Codex app-server adapter behind the provider-independent Core boundary."""
from __future__ import annotations
import json,queue,subprocess,threading,time
from dataclasses import dataclass
from pathlib import Path
from typing import Any,Sequence
class CodexAppServerError(RuntimeError):pass
@dataclass(frozen=True)
class CodexTurnResult:
 status:str;thread_id:str;elapsed_seconds:float;event_methods:tuple[str,...];item_summaries:tuple[str,...]
def execute_turn(executable:str,workspace:Path,instruction:str,*,model:str='gpt-6.1-sol',effort:str='low',timeout_seconds:float=180.0,command:Sequence[str]|None=None)->CodexTurnResult:
 """Run one bounded turn; correlate responses and asynchronous notifications."""
 if not workspace.is_dir():raise ValueError('workspace must preexist')
 argv=list(command) if command is not None else [executable,'app-server','--stdio'];started=time.monotonic()
 p=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',errors='strict',bufsize=1)
 inbox:queue.Queue[dict[str,Any]|BaseException]=queue.Queue();pending:list[dict[str,Any]]=[];events:list[str]=[];items:list[str]=[];next_id=1
 def reader()->None:
  try:
   assert p.stdout is not None
   for line in p.stdout:inbox.put(json.loads(line))
   inbox.put(CodexAppServerError('app-server closed unexpectedly'))
  except BaseException as exc:inbox.put(exc)
 threading.Thread(target=reader,daemon=True).start()
 def receive()->dict[str,Any]:
  remaining=timeout_seconds-(time.monotonic()-started)
  if remaining<=0:raise TimeoutError(f'Codex turn exceeded {timeout_seconds}s')
  try:item=inbox.get(timeout=remaining)
  except queue.Empty:raise TimeoutError(f'Codex turn exceeded {timeout_seconds}s') from None
  if isinstance(item,BaseException):raise item
  return item
 def send(method:str,rid:int|None,params:dict[str,Any])->None:
  assert p.stdin is not None
  message={'method':method,'params':params}
  if rid is not None:message['id']=rid
  p.stdin.write(json.dumps(message,separators=(',',':'))+'\n');p.stdin.flush()
 def request(method:str,params:dict[str,Any])->dict[str,Any]:
  nonlocal next_id
  rid=next_id;next_id+=1;send(method,rid,params)
  while True:
   m=receive();name=m.get('method')
   if isinstance(name,str):events.append(name);pending.append(m)
   if m.get('id')==rid:
    if 'error' in m:raise CodexAppServerError(str(m['error']))
    return m['result']
 try:
  request('initialize',{'clientInfo':{'name':'ia-director-core','title':'IA Director Core','version':'0'},'capabilities':{'experimentalApi':True,'requestAttestation':False}})
  send('initialized',None,{})
  th=request('thread/start',{'model':model,'cwd':str(workspace.resolve()),'approvalPolicy':'never','sandbox':'workspace-write','ephemeral':True,'developerInstructions':'Operate only inside the workspace. Complete the requested work and verification without asking the user.'});tid=th['thread']['id']
  request('turn/start',{'threadId':tid,'input':[{'type':'text','text':instruction,'text_elements':[]}],'effort':effort})
  while True:
   m=pending.pop(0) if pending else receive();name=m.get('method')
   if isinstance(name,str) and m not in pending and name not in events:events.append(name)
   if name in {'item/started','item/completed'}:
    item=(m.get('params') or {}).get('item') or {}
    kind=item.get('type','unknown');label=item.get('label') or item.get('command') or item.get('text') or ''
    items.append(f'{name}:{kind}:{str(label)[:240]}')
   if name=='turn/completed':
    status=(m.get('params') or {}).get('turn',{}).get('status')
    if status!='completed':raise CodexAppServerError(f'Codex turn completed notification carried non-success status: {status!r}')
    return CodexTurnResult(status,tid,time.monotonic()-started,tuple(events),tuple(items))
   if name=='turn/failed':raise CodexAppServerError('Codex turn failed')
 finally:
  p.terminate()
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
  for stream in (p.stdin,p.stdout):
   if stream is not None:stream.close()
