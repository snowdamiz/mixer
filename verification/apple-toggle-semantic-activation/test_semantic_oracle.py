"""Host parser controls only; fabricated rows never qualify UIKit behavior."""
import copy,unittest
from semantic_oracle import verify,host_fixture
class OracleControls(unittest.TestCase):
 def test_closed36_fixture(self):self.assertEqual(verify(host_fixture())['cases'],36)
 def test_negative_controls(self):
  mutations=[]
  mutations.append(lambda x:x.pop())
  mutations.append(lambda x:x.append(copy.deepcopy(x[0])))
  mutations.append(lambda x:x.__setitem__(1,copy.deepcopy(x[0])))
  for k,v in [('selected',False),('retained',False),('events',7),('events',9),('accepted',5),('primary',13),('lastValue',False),('identity','other'),('nativeAutomaticSelection',True),('buttonTrait',False),('toggleTrait',False),('selectedTrait',False),('enabled',False),('allowed',False),('label','other')]:
   mutations.append(lambda x,k=k,v=v:x[0]['after'].__setitem__(k,v))
  for k,v in [('returned',False),('hookFired',True),('nestedReturn',False),('index',True)]:mutations.append(lambda x,k=k,v=v:x[0].__setitem__(k,v))
  mutations.append(lambda x:x[1]['after'].__setitem__('events',8))
  mutations.append(lambda x:x[1]['after'].__setitem__('selected',True))
  mutations.append(lambda x:x[4].__setitem__('returned',False))
  mutations.append(lambda x:x[16]['after'].__setitem__('events',9))
  mutations.append(lambda x:x[17].__setitem__('nestedReturn',True))
  for i,mutate in enumerate(mutations):
   with self.subTest(mutation=i):
    x=host_fixture();mutate(x)
    with self.assertRaises(AssertionError):verify(x)
if __name__=='__main__':unittest.main(verbosity=2)
