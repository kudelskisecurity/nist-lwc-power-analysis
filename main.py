import argparse as argparse
import random
import numpy as np

from util import select
from attacks import ATTACKS

if __name__ == "__main__":
    parse = argparse.ArgumentParser()

    attacks = list(ATTACKS.keys())

    parse.add_argument('-i', '--interactive', dest='interactive', action='store_const', const=True, default=False)
    parse.add_argument('--seed', dest='seed', default=None, type=int,
                       help='set random generators seed (for reproducible attacks)')
    parse.add_argument('-v', dest='verbosity', action='store_const', const=1, default=0)
    parse.add_argument('-vv', dest='verbosity', action='store_const', const=2, default=0)

    subparsers = parse.add_subparsers(title='attack', dest='attack', help='select the attack to run')

    for attack, content in ATTACKS.items():
        desc, pkg = content
        parser = subparsers.add_parser(attack, help=desc)
        pkg.init_subcommand(parser)

    args = parse.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    attack = select('Which attack do you want to run?', attacks) if args.interactive or args.attack is None else args.attack

    if attack in ATTACKS:
        _, pkg = ATTACKS[attack]
        pkg.run(args)
    else:
        print("FATAL: invalid attack selected")

