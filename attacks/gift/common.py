import numpy as np

from attacks.gift.classifier import make_state, sbox_bitslice


def change_bits_in_bytes(nonce, diff, nibble):
    new_nonce = bytes()
    for i in range(4):
        nonce_part = nonce[i * 4: (i + 1) * 4]
        index = 3 - (nibble // 8)
        bit_position = nibble % 8

        new_nonce += bytes(nonce_part[:index])
        new_nonce += bytes([nonce_part[index] ^ ((diff >> i & 0x1) << bit_position)])
        if index < 3: new_nonce += bytes(nonce_part[index + 1:])

    return new_nonce


def nibble_at_position(bytes, positions):
    result = 0
    for i in range(4):
        index = 3 - (positions[i] // 8)
        bit_position = positions[i] % 8

        # positions are lsb first but result is not, so we need to access the correct bit
        bit = bytes[index + i * 4] >> bit_position & 0x1

        result = result | (bit << i)

    return result


def determine_diff(diff_abs, round=1, threshold=5.5):
    # position of the 4 bits in the trace
    ranges = [[(5050, 6050), (6100, 7100), (7150, 8150), (8200, 9200)],
              [(5050, 6050), (6100, 7100), (7150, 8150), (8200, 9200)]]
              # [(9500, 10400), (10500, 11400), (11500, 12400), (12500, 13400)]]

    # from lascar.plotting import plot
    # plot(diff_abs)

    # detect peaks in ranges
    peaks = [diff_abs[l:r].max() for l,r in ranges[round - 1]]
    avg_glob = diff_abs.mean()

    #print(avg_glob)
    for pos in range(4):
        print(2 ** pos, "peak", peaks[pos], "over avg", peaks[pos] / avg_glob, sep='\t')
    print()
    peaks = [i / avg_glob for i in peaks]

    est_changes = [i for i, k in enumerate(peaks) if k > threshold]

    out_diff = 0
    for pos in est_changes:
        out_diff |= (1 << pos)

    return out_diff


def determine_peaks(diff_abs):
    # position of the 4 bits in the trace
    ranges = [(5050, 6050), (6100, 7100), (7150, 8150), (8200, 9200)]

    peaks = [diff_abs[l:r].max() for l,r in ranges]
    avg_glob = diff_abs.mean()
    peaks = [i / avg_glob for i in peaks]

    return peaks



def determine_diff_with_key(nonce_1, nonce_2, real_key_schedule, round=1):
    sim_r1 = simulate_real_output_state(nonce_1, real_key_schedule, round)
    sim_r2 = simulate_real_output_state(nonce_2, real_key_schedule, round)

    diff = 0
    for i in range(4):
        if (sim_r1[i] ^ sim_r2[i]) != 0:
            diff |= (1 << i)

    return diff


def simulate_real_output_state(nonce, real_key_schedule, rounds):
    from .classifier import simulate_round
    sim = make_state(nonce)
    sched = real_key_schedule.copy()
    simulate_round(0, sim, sched)
    if rounds == 2:
        simulate_round(1, sim, sched)
    sbox_bitslice(sim)
    return sim
