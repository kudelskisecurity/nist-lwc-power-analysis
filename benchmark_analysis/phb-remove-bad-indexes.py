import pickle
import matplotlib.pyplot as plt
import benchmark # weird pickle shenanigans

class RunObject:
    def __init__(self, parameters, status, runtime, measurables):
        self.measurables = measurables
        self.runtime = runtime
        self.status = status
        self.parameters = parameters

o = pickle.load(open("./benchmarks/photon-beetle-desktop-40k.benchmark.proj", "rb"))

# these samples were taken on a different power source and the templates were no longer good
bad_index_first = 76
bad_index_last = 101
o['rounds'] = o['rounds'][:bad_index_first] + o['rounds'][bad_index_last + 1:]

with open("./benchmarks/photon-beetle-desktop-40k-sanitized.benchmark.proj", "wb") as f:
    pickle.dump(o, f)

