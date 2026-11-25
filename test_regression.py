import unittest
from audit import month_bounds
from replay import reference_exit
class Regression(unittest.TestCase):
    def test_sealed(self):
        for m in ['2019-12','2026-01','2025-13','2025-1','../2020-01']:
            with self.assertRaises(ValueError): month_bounds(m)
    def test_leap(self): self.assertEqual(month_bounds('2020-02')[1],41760)
    def test_long_same_bar(self): self.assertEqual(reference_exit([(100,110,90,100)],1,95,105),(0,95,1))
    def test_short_same_bar(self): self.assertEqual(reference_exit([(100,110,90,100)],-1,105,95),(0,105,1))
    def test_long_gap(self): self.assertEqual(reference_exit([(94,100,90,98)],1,95,105),(0,94,1))
    def test_short_gap(self): self.assertEqual(reference_exit([(106,110,100,102)],-1,105,95),(0,106,1))
    def test_target_conservative(self): self.assertEqual(reference_exit([(100,108,99,105)],1,95,105),(0,105,2))
    def test_time_exit(self): self.assertEqual(reference_exit([(100,101,99,100),(100,101,98,99)],1,95,105),(1,99,0))
if __name__=='__main__': unittest.main()
