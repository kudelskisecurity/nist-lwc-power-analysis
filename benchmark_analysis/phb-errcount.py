import pickle
import matplotlib.pyplot as plt
import benchmark # weird pickle shenanigans

eliminate_bad_indexes = True

class RunObject:
    def __init__(self, parameters, status, runtime, measurables):
        self.measurables = measurables
        self.runtime = runtime
        self.status = status
        self.parameters = parameters


suffix = '-sanitized' if eliminate_bad_indexes else ''
o = pickle.load(open(f"./benchmarks/photon-beetle-desktop-40k{suffix}.benchmark.proj", "rb"))

by_param_value = {}

for round in o['rounds']:
    for ro in round:
        param = ro.parameters[0]
        if not param in by_param_value: by_param_value[param] = []
        by_param_value[param].append(ro)

# success_rates = {}
success_rate_by_errnum = [{} for i in range(9)]
num_rounds_per_succ_state = {}
time = {}
time_filtered = {}

print("success rate")
for k in by_param_value:
    ser = by_param_value[k]
    total = len(ser)
    succ = len([x for _ind, x in enumerate(ser) if x.status == 'found'])
    wrong = len([x for _ind, x in enumerate(ser) if x.status == 'wrong_key'])
    print(k, ":", (succ * 100 // total), "%\t", succ, "successes,", wrong, "wrong keys,", (total - wrong - succ), "not found")
    # success_rates[k] = succ / total

    for n_errors in range(9):
        recoverable = len([x for x in ser if x.measurables['unrecoverable_bytes'] <= 0 and x.measurables['incorrect_bytes'] <= n_errors])
        unrecoverable = len([x for x in ser if x.measurables['unrecoverable_bytes'] > 0 ])
        print(unrecoverable, "are unrecoverable")
        success_rate_by_errnum[n_errors][k] = recoverable / total

    num_rounds_per_succ_state[k] = {'successful': [max(x.measurables['iterations_per_column']) for x in ser if x.measurables['incorrect_bytes'] <= 0], 'recovered': [max(x.measurables['iterations_per_column']) for x in ser if x.measurables['unrecoverable_bytes'] <= 0 and x.measurables['incorrect_bytes'] > 0], 'unsuccessful': [max(x.measurables['iterations_per_column']) for x in ser if x.measurables['unrecoverable_bytes'] > 0]}
    
    time[k] = [x.runtime for x in ser]
    time_filtered[k] = [x.runtime for x in ser if x.runtime < 60]

    print(k, ":", (len(time[k]) - len(time_filtered[k])), "runtimes filtered out")

# fig, (ax1, ax3, ax4) = sp = plt.subplots(1, 3)
# fig.set_figwidth(fig.get_figheight() * 4)

# fig.suptitle("Benchmark results of the CPA attack on Dumbo")

# ax1.plot(success_rates.keys(), success_rates.values()) # , label='success rate')

markers = ['+', '|', 'x', '.', 'o']


plt.plot(success_rate_by_errnum[0].keys(), success_rate_by_errnum[0].values(), label=f"without exhaustive search")
plt.plot(success_rate_by_errnum[8].keys(), success_rate_by_errnum[8].values(), label=f"with exhaustive search")

# plt.axis([25, 35, 0, 1])
plt.xlabel('number of powertraces')
plt.ylabel('success rate')
# plt.title('Attack success rate by maximal number of errors in exhaustive search')
plt.grid(visible=True, axis='y', linestyle='dotted')
plt.legend()
plt.savefig(f"phb-success-rate.png", bbox_inches='tight')

plt.show()
plt.close()


plt.ylabel('max number of iterations')
plt.xlabel('status')
# plt.title('Attack runtime')
plt.boxplot(num_rounds_per_succ_state[(150)].values(), labels=num_rounds_per_succ_state[(150)].keys())

plt.savefig(f"phb-iterations.png", bbox_inches='tight')
plt.show()
