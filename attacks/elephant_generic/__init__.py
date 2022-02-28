from argparse import ArgumentParser

from runners.cw_basic import WrappedChipWhisperer
import chipwhisperer as cw

def init_subcommand(subparser: ArgumentParser):
    subparser.add_argument('--save', dest='save', metavar='project name', default=None,
                           help='save the generated data, traces, oracle response')
    subparser.add_argument('--load', dest='load', metavar='project name', default=None,
                           help='the name of a saved project to load (ignores source)')
    subparser.add_argument('-n', '--num-traces', dest='num_traces', type=int, default=50,
                           help='override the number of traces to capture')
    subparser.add_argument('--verify-key', dest='verify_key', action='store_const', const=True, default=False,
                           help='capture a known plaintext-ciphertext pair on the device to verify the key')
    subparser.add_argument('-b', '--block-size', dest='block_size', type=int, choices=[160,176], default=160,
                           help='targetted variant of the cipher')

def init_wrap(size):
    input("Please connect the board and press enter.")
    return WrappedChipWhisperer(
        alg='elephant176v2' if size == 176 else 'elephant160v2-o3',
        platform='CWLITEARM',
        target_type=cw.targets.SimpleSerial,
        prog=cw.programmers.STM32FProgrammer)

def run(args):
    from .attack import attack
    from .classifiers import JumboModel, DumboModel
    classifier = JumboModel() if args.block_size == 176 else DumboModel()
    attack(args.num_traces, args.load, args.save, args.verbosity, classifier, args.verify_key, init_wrap(args.block_size))

