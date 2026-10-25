from run import run,OWN
import os,sys
for name in sys.argv[1:]:
 d=OWN/'original-compat'/name
 if run('original-'+name,[str(d/(name+'.mjs'))],{'MIXER_V2_RUN_DIR':str(d)}):sys.exit(1)
