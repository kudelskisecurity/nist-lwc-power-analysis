import pickle
import matplotlib.pyplot as plt
import benchmark # weird pickle shenanigans

class RunObject:
    def __init__(self, parameters, status, runtime, measurables):
        self.measurables = measurables
        self.runtime = runtime
        self.status = status
        self.parameters = parameters

o = pickle.load(open("./benchmarks/elephant160-final-bench.benchmark.proj", "rb"))

by_param_value = {}

for round in o['rounds']:
    for ro in round:
        param = ro.parameters[0]
        if not param in by_param_value: by_param_value[param] = []
        by_param_value[param].append(ro)

# success_rates = {}
success_rate_by_errnum = [{} for i in range(4)]
time = {}
time_filtered = {}

print("success rate")
for k in by_param_value:
    ser = by_param_value[k]
    total = len(ser)
    succ = len([x for x in ser if x.status == 'found'])
    wrong = len([x for x in ser if x.status == 'wrong_key'])
    print(k, ":", (succ * 100 // total), "%\t", succ, "successes,", wrong, "wrong keys,", (total - wrong - succ), "not found")
    # success_rates[k] = succ / total

    for n_errors in range(4):
        recoverable = len([x for x in ser if x.measurables['unrecoverable_bytes'] == 0 and x.measurables['incorrect_bytes'] <= n_errors])
        success_rate_by_errnum[n_errors][k] = recoverable / total

    time[k] = [x.runtime for x in ser]
    time_filtered[k] = [x.runtime for x in ser if x.runtime < 60]

    print(k, ":", (len(time[k]) - len(time_filtered[k])), "runtimes filtered out")

# fig, (ax1, ax3, ax4) = sp = plt.subplots(1, 3)
# fig.set_figwidth(fig.get_figheight() * 4)

# fig.suptitle("Benchmark results of the CPA attack on Dumbo")

# ax1.plot(success_rates.keys(), success_rates.values()) # , label='success rate')

markers = ['+', '|', 'x', '.']

for n_errors, success_rates_dict in enumerate(success_rate_by_errnum):
    plt.plot(success_rates_dict.keys(), success_rates_dict.values(), label=f"{n_errors} errors", marker=markers[n_errors])

# plt.axis([25, 35, 0, 1])
plt.xlabel('number of powertraces')
plt.ylabel('success rate')
# plt.title('Attack success rate by maximal number of errors in exhaustive search')
plt.grid(visible=True, axis='y', linestyle='dotted')
plt.legend()
plt.savefig("elephant-success-rate.png", bbox_inches='tight')

# plt.show()
plt.close()

print("unrecoverable error rate")
for k in by_param_value:
    ser = by_param_value[k]
    unrecoverable = len([x for x in ser if x.measurables['unrecoverable_bytes'] > 0])

    print(k, ":", (unrecoverable * 100 // len(ser)), "%\t", unrecoverable, "errors")

plt.xlabel('number of powertraces')
plt.ylabel('attack runtime (s)')
# plt.title('Attack runtime')
plt.boxplot(time.values(), labels=time.keys())
plt.savefig("elephant-runtimes.png", bbox_inches='tight')
