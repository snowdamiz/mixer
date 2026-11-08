import pathlib,runpy,sys,tempfile
root=pathlib.Path(__file__).resolve().parent/"scratch"
original=tempfile.TemporaryDirectory
def owned(*a,**kw):
 kw["dir"]=str(root); return original(*a,**kw)
tempfile.TemporaryDirectory=owned
sys.argv=[sys.argv[1]]
runpy.run_path(sys.argv[0],run_name="__main__")
