# from . import romulus
#
# attacks = [
#     ('Romulus', 'An attack on RomulusN', romulus.attack)
# ]
from . import romulus, photonbeetle, elephant160, elephant176, elephant_generic, gift

ATTACKS = {
    'romulusn': ('A CPA attack on RomulusN', romulus),
    'gift-cofb': ('A SC assisted DPA attack on GIFT', gift),
    'photon-beetle': ('A template attack on Photon-Beetle', photonbeetle),
    'elephant160': ('A template attack on Elephant-160 (Dumbo)', elephant160),
    'elephant176': ('A template attack on Elephant-160 (Elephant Spongent)', elephant176),
    'elephant': ('A template attack on Elephant-160 and Elephant-176 (Elephant Spongent) - Generic variant, '
                 'no benchmark available', elephant_generic)
}
