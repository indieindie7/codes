# load ResPlan.pkl allowing only the classes it was seen to need
import pickle, sys, importlib
OK = {('numpy', 'dtype'), ('numpy._core.multiarray', 'scalar'), ('numpy.core.multiarray', 'scalar'), ('shapely.io', 'from_wkb')}
class Safe(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) not in OK:
            raise pickle.UnpicklingError(f"not allowed: {module}.{name}")
        return getattr(importlib.import_module(module), name)
def load(path):
    with open(path, 'rb') as f:
        return Safe(f).load()
