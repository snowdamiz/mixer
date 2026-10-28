"""Reserve exactly one manual diagnostic at the delivered exact head."""
import base64,json,re
from owned import Commands,OUT,ROOT,now,row,save
assert not (OUT/"dispatch-once.json").exists(),"dispatch reservation consumed; never retry"
r=json.loads((OUT/"receipt.json").read_bytes());s=json.loads((OUT/"selection.json").read_bytes());assert r["pushed"] and not r["force"] and r["allNewCommandsReapedGroupsAbsentAndEOF"]
head,tree=r["commit"],r["tree"];path=s["workflow"]["destination"];name=path.rsplit("/",1)[1];c=Commands(150,8,"dispatch-")
assert c.run("head",["git","rev-parse","HEAD","HEAD^{tree}"]).decode().splitlines()==[head,tree]
assert c.run("remote",["git","ls-remote","origin","refs/heads/main"]).decode().split()[0]==head
assert row(ROOT/path)==r["workflow"]
content=json.loads(c.run("workflow-content",["gh","api","repos/snowdamiz/mixer/contents/"+path+"?ref="+head]))
assert content["encoding"]=="base64" and base64.b64decode(content["content"])==(ROOT/path).read_bytes()
w=json.loads(c.run("workflow-state",["gh","api","repos/snowdamiz/mixer/actions/workflows/"+name]));assert w["state"]=="active" and w["path"]==path
save("dispatch-once.json",{"schema":1,"at":now(),"head":head,"tree":tree,"workflow":name,"workflowSHA256":s["workflow"]["sha256"],"dispatchLimit":1,"reservationConsumed":True,"retryFallbackOrDefaultPromotionSelected":False,"inputs":{},"bounds":s["bounds"]})
output=c.run("submit",["gh","workflow","run",name,"--ref","main","--repo","snowdamiz/mixer"],seconds=40)
match=re.search(rb"https://github\.com/snowdamiz/mixer/actions/runs/(\d+)",output);run=None
if match:
    run=json.loads(c.run("run-binding",["gh","api","repos/snowdamiz/mixer/actions/runs/"+match[1].decode(),"--jq","{id,head_sha,event,run_attempt,status,conclusion,workflow_id,path,html_url}"]))
    assert run["head_sha"]==head and run["event"]=="workflow_dispatch" and run["run_attempt"]==1 and run["workflow_id"]==w["id"] and run["path"]==path
save("dispatch-receipt.json",{"schema":1,"at":now(),"head":head,"tree":tree,"workflow":name,"workflowSHA256":s["workflow"]["sha256"],"dispatchCallsMade":1,"dispatchCommandSucceeded":True,"ref":"main","expectedHead":head,"inputs":{},"runId":run["id"] if run else None,"runURL":run["html_url"] if run else None,"resultingRunHeadBound":run is not None,"run":run,"allNewCommands":c.records,"allNewCommandsReapedGroupsAbsentAndEOF":True,"runtimeResult":"pending exact-source result review","runtimeReleaseOrGAAccepted":False})
print(json.dumps({"dispatchCallsMade":1,"head":head,"tree":tree,"run":run,"exactHeadBound":run is not None,"cleanupVerified":True}))
