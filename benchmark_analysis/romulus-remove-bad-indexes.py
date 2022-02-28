import pickle
import matplotlib.pyplot as plt
import benchmark # weird pickle shenanigans

class RunObject:
    def __init__(self, parameters, status, runtime, measurables):
        self.measurables = measurables
        self.runtime = runtime
        self.status = status
        self.parameters = parameters

o = pickle.load(open("./benchmarks/romulusn-multi-2.benchmark.proj", "rb"))

bad_index_first = 0
bad_index_last = 5
o['rounds'] = o['rounds'][:bad_index_first] + o['rounds'][bad_index_last + 1:]

with open("./benchmarks/romulusn-multi-sanitized.benchmark.proj", "wb") as f:
    pickle.dump(o, f)

