import pickle
import matplotlib.pyplot as plt
import benchmark # weird pickle shenanigans


class RunObject:
    def __init__(self, parameters, status, runtime, measurables):
        self.measurables = measurables
        self.runtime = runtime
        self.status = status
        self.parameters = parameters


o = pickle.load(open("./benchmarks/romulusn-multi-sanitized.benchmark.proj", "rb"))

by_param_value = {}

for round in o['rounds']:
    for ro in round:
        param = ro.parameters[0]
        if not param in by_param_value: by_param_value[param] = []
        by_param_value[param].append(ro)

# success_rates = {}
time = {}
time_successful = {}
num_iterations = {}
num_iterations_successful = {}
success_rates = {}

print("success rate")
for k in by_param_value:
    ser = by_param_value[k]
    total = len(ser)
    succ = len([x for _ind, x in enumerate(ser) if x.status == 'found'])
    wrong = len([x for _ind, x in enumerate(ser) if x.status == 'wrong_key'])
    print(k, ":", (succ * 100 // total), "%\t", succ, "successes,", wrong, "wrong keys,", (total - wrong - succ), "not found")
    success_rates[k] = succ / total
    num_iterations[k] = [x.measurables['round_2_iterations'] for x in ser]
    time[k] = [x.runtime for x in ser]
    num_iterations_successful[k] = [x.measurables['round_2_iterations'] for x in ser if x.status == 'found']
    time_successful[k] = [x.runtime for x in ser if x.status == 'found']


# fig, (ax1, ax3, ax4) = sp = plt.subplots(1, 3)
# fig.set_figwidth(fig.get_figheight() * 4)

# fig.suptitle("Benchmark results of the CPA attack on Dumbo")

# ax1.plot(success_rates.keys(), success_rates.values()) # , label='success rate')


plt.plot(success_rates.keys(), success_rates.values(), label='attack success rate')
plt.xlabel('number of powertraces')
plt.ylabel('success rate')
plt.grid(visible=True, axis='y', linestyle='dotted')
plt.legend()
plt.savefig(f"romulus-success-rate.png", bbox_inches='tight')
plt.close()


plt.xlabel('number of powertraces')
plt.ylabel('attack runtime (s)')
plt.grid(visible=True, axis='y', linestyle='dotted')
plt.boxplot(time.values(), labels=time.keys())
plt.savefig(f"romulus-runtimes.png", bbox_inches='tight')
plt.close()

plt.xlabel('number of powertraces')
plt.ylabel('attack runtime (s)')
plt.grid(visible=True, axis='y', linestyle='dotted')
plt.boxplot(time_successful.values(), labels=time_successful.keys())
plt.savefig(f"romulus-runtimes-successful.png", bbox_inches='tight')
plt.close()


plt.xlabel('number of powertraces')
plt.ylabel('number of round 2 CPA attempts')
plt.grid(visible=True, axis='y', linestyle='dotted')
plt.boxplot(num_iterations.values(), labels=num_iterations.keys())
plt.savefig(f"romulus-num-iterations.png", bbox_inches='tight')
plt.close()

plt.xlabel('number of powertraces')
plt.ylabel('number of round 2 CPA attempts')
plt.grid(visible=True, axis='y', linestyle='dotted')
plt.boxplot(num_iterations_successful.values(), labels=num_iterations_successful.keys())
plt.savefig(f"romulus-num-iterations-successful.png", bbox_inches='tight')
plt.close()
