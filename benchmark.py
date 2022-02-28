import argparse as argparse
import itertools
import json
import os
import pickle
import time

from attacks import ATTACKS


class RunObject:
    def __init__(self, parameters, status, runtime, measurables):
        self.measurables = measurables
        self.runtime = runtime
        self.status = status
        self.parameters = parameters


if __name__ == "__main__":
    parse = argparse.ArgumentParser()

    attacks = list(ATTACKS.keys())
    parse.add_argument('-n', dest='num_run', default=100, type=int, help='number of data to collect for each parameters combination')

    parse.add_argument('attack', help='the name of the attack to benchmark', choices=attacks)
    parse.add_argument('project', help='the name of the project to load/save')

    args = parse.parse_args()
    if args.attack not in ATTACKS:
        print("FATAL: invalid attack selected")
        exit()

    _, pkg = ATTACKS[args.attack]
    project_path = f"benchmarks/{args.attack}-{args.project}.benchmark.proj"

    # TODO: load existing parameter set

    params = pkg.benchmark_parameters
    project_data = {
        "param_names": list(params.keys()),
        "current_round": [],
        "rounds": []
    }

    if os.path.exists(project_path):
        with open(project_path, "rb") as f:
            new_data = pickle.load(f)

            if new_data["param_names"] != project_data["param_names"]:
                print("Invalid project", project_path, "- the parameter names have been updated since you last saved the project")
                print(new_data["param_names"], "is different from", project_data["param_names"])
                exit(1)

            project_data = new_data
            print("Loaded saved project.")


    def get_params_object(param_values):
        params_object = {}
        for i, key in enumerate(params.keys()):
            params_object[key] = param_values[i]
        return params_object


    def save_state(state):
        if not os.path.exists("./benchmarks"):
            os.mkdir("./benchmarks")

        with open(project_path, "wb") as f:
            pickle.dump(state, f)

    start_round = len(project_data["rounds"])
    input("Please connect the board and press enter.")
    wrap = pkg.init_wrap()
    print("")
    print("")

    for round in range(start_round, args.num_run):
        print(f"[-] Round {round} starting")
        comb = list(itertools.product(*params.values()))
        cur = project_data["current_round"]
        if len(cur) > 0:
            print("[-] Skipping", len(cur), "first combinations (already done)")
            comb = comb[len(cur):]

        for values in comb:
            print(f"[{round}] Parameters:", values)

            params_object = get_params_object(values)
            returned = False

            while not returned:
                try:
                    start = time.perf_counter() # TODO: use other time measurement method
                    status, measurable = pkg.run_benchmark(params_object, wrap)
                    end = time.perf_counter()
                    returned = True
                except IOError:
                    print(f"[{round}][{values}] IOError encountered, restarting in one second")
                    time.sleep(1)

            print(f"[{round}][{values}] Done in {(end - start)} seconds. measured:", measurable, "status:", status)
            run_object = RunObject(values, status, end-start, measurable)
            project_data["current_round"].append(run_object)
            save_state(project_data)

        project_data["rounds"].append(project_data["current_round"])
        project_data["current_round"] = []
        save_state(project_data)

