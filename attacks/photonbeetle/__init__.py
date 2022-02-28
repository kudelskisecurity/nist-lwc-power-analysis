import string
from argparse import ArgumentParser

from runners.cw_basic import WrappedChipWhisperer
import chipwhisperer as cw
TPL_PATH = "./attacks/photonbeetle/models/"

def init_subcommand(subparser: ArgumentParser):
    subparser.add_argument('template', help='the name of the template to use')

    sp2 = subparser.add_subparsers(title='action', dest='action', help='what to do with this attack')

    # train
    train = sp2.add_parser('template', help='create a template for a device')
    train.add_argument('platform', choices=['xmega', 'stm32'], help='the platform on which to make the template')
    train.add_argument('binary_file', help='the name of the binary file to run (in ./bin/, of the form '
                                                           './bin/{binaryfile}-{CWLITEARM|CWLITEXMEGA}.hex)')
    train.add_argument('-n', '--num-traces', dest='num_traces', type=int, default=20000,
                       help='how many traces to capture to make the template')
    train.add_argument('-s', '--array-start', dest='array_start', type=int, default=0,
                       help='index of the first position in the traces to keep')
    train.add_argument('-e', '--array-end', dest='array_end', type=int, default=None,
                       help='index of the first position in the traces to exclude')
    train.add_argument('-w', '--windows', dest='windows', type=int, default=1, help='number of windows to capture')

    # attack
    attack = sp2.add_parser('attack', help='launch an attack on a device using the template')
    attack.add_argument('-n', '--num-traces', dest='num_traces', type=int, default=100,
                       help='how many traces to capture to perform the attack')
    attack.add_argument('-i', '--num-identical', dest='num_identical', type=int, default=25,
                       help='for how many rounds a given key must remain top ranked for it to be returned')
    attack.add_argument('-k', '--keep', dest='keep_n', type=int, default=4,
                        help='how many top rank predictions should be returned for each column (higher improves chances of recovery at the expense of a longer exhaustive search)')
    attack.add_argument('-t', '--num-threads', dest='threads', type=int, default=None,
                       help='how many threads to use in the final step (by default: number of cores)')


def init_wrap():
    # This works for benchmarks but not anything else
    return WrappedChipWhisperer(alg='photonbeetleaead128rate128v1-bitslice_sb32',
                                platform='CWLITEARM', target_type=cw.targets.SimpleSerial,
                                prog=cw.programmers.STM32FProgrammer)


def run(args):
    if args.action == 'template':
        from .create_model import create_template

        create_template(args)
    elif args.action == 'attack':
        from .attack import attack

        attack(args)
    else:
        print("Error: nothing to do.")
        exit(1)


class dotdict(dict):
    __getattr__ = dict.get


def run_benchmark(parameters: dict[string, any], wrap) -> tuple[string, dict[string, any]]:
    obj = {
        "template": parameters["template"],
        "num_traces": parameters["num_traces"],
        "threads": parameters["threads"],
        "keep_n": 4,
        "num_identical": 25
    }

    from .attack import attack
    status, col_num_iter, num_it, initially_incorrect_bytes, unrecoverable_bytes = attack(dotdict(obj), wrap)

    return status, {"exhaustive_search_iterations": num_it, "iterations_per_column": col_num_iter, "incorrect_bytes": initially_incorrect_bytes, "unrecoverable_bytes": unrecoverable_bytes}


benchmark_parameters = {
    "num_traces": [100, 125, 150], # 175, 200], # 25, 50, 75, 100, 125, 150, 
    "threads": [8], # [1, 2, 4, 8],
    # "template": ["arm-sb32-10k", "arm-sb32-15k", "arm-sb32-20k", "arm-sb32-25k", "arm-sb32-30k"]
    "template": ["stm32-30k"],

}

