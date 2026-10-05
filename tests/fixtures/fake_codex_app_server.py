import json,sys
sys.stdout.reconfigure(encoding='utf-8')
thread='fixture-thread'
for line in sys.stdin:
 m=json.loads(line);method=m['method'];i=m['id']
 if method=='initialize':
  print(json.dumps({'id':i,'result':{'codexHome':'/fixture'}}),flush=True)
 elif method=='thread/start':
  print(json.dumps({'method':'thread/started','params':{'thread':{'id':thread}}}),flush=True)
  print(json.dumps({'id':i,'result':{'thread':{'id':thread}}}),flush=True)
 elif method=='turn/start':
  print(json.dumps({'id':i,'result':{'turn':{'status':'inProgress'}}}),flush=True)
  print(json.dumps({'method':'item/started','params':{'item':{'type':'commandExecution','label':'utf8-✝'}}},ensure_ascii=False),flush=True)
  print(json.dumps({'method':'turn/completed','params':{'turn':{'status':'completed'}}}),flush=True)
