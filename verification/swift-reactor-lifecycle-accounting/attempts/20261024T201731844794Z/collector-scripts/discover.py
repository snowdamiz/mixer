"""Fresh eight-context metadata-only discovery; no unit test executes."""
import query_layouts as q
for features in ['swift','all']:
 for profile in ['debug','release']:
  for unit in [False,True]:
   print(features,profile,'unit'if unit else'production',flush=True)
   assert q.run(features,profile,unit)==0
