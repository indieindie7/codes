"""Run the harness milestone tests with tuned knobs: python tests/tune_check.py alpha=0.85 edge_damp=1.0"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import harness as H
over = {k: float(v) for k, v in (a.split("=") for a in sys.argv[1:])}
_Opts = H.Opts
def Opts():
    o = _Opts()
    for k, v in over.items(): setattr(o, k, v)
    return o
H.Opts = Opts
for n in H.TESTS: H.TESTS[n]()
