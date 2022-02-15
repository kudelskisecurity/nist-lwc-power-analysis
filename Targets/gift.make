ALG_NAME = gift-cofb
ALG_VARIANT = giftcofb128v1

ALG_PATH = $(CANDIDATES_BASEPATH)/$(ALG_NAME)/Implementations/crypto_aead/$(ALG_VARIANT)/ref

# List C source files here.
# Header files (.h) are automatically pulled in.
SRC += $(ALG_PATH)/gift128.c $(ALG_PATH)/encrypt.c
# OPT = 3
