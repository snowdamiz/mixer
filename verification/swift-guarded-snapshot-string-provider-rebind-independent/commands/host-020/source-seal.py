"""Complete membership seal and read-only recheck for the independent packet."""
from support import *
def inventory():
    out=[]
    for p in sorted(D.rglob('*')):
        require(not p.is_symlink(),'review packet symlink')
        if p.is_file() and p!=D/'seal.json':out.append(row(p.relative_to(D),p.read_bytes()))
    return out
def seal():
    members=inventory();save('seal.json',{'schema':1,'source_tree_sha256':TREES[3],'candidate_seal_sha256':SEAL,'members':members,'member_count':len(members),'member_bytes':sum(x['bytes'] for x in members),'member_table_sha256':sha(canon(members)),'scope':'Independent offline conditional source/MIR review; root decides bounded acceptance. No current L_str/root funding/actual caller/runtime/native/OTA/GA selection.'})
    for p in D.rglob('*'):
        if p.is_file():p.chmod(0o444)
    for p in sorted((p for p in D.rglob('*') if p.is_dir()),reverse=True):p.chmod(0o555)
    D.chmod(0o555)
def check():
    s=read(D/'seal.json');actual=inventory();require(actual==s['members'] and sha(canon(actual))==s['member_table_sha256'],'complete independent review seal')
    for p in [D,*D.rglob('*')]:require(stat.S_IMODE(p.stat().st_mode)==(0o555 if p.is_dir() else 0o444),'review file/directory modes')
    require(custody()==read(D/'input-custody.json'),'fresh complete original/current frozen input closure')
    print(json.dumps({'seal_sha256':sha((D/'seal.json').read_bytes()),'members':len(actual),'bytes':sum(x['bytes'] for x in actual),'complete_membership_and_inputs':True,'read_only_modes':True}))
if __name__=='__main__':
    require(sys.argv[1:]==['--check'],'read-only check entry only');check()
