ALG_NAME = elephant

ifndef ($(ALG_VARIANT))
	ALG_VARIANT = elephant160v2
endif

ALG_PATH = $(CANDIDATES_BASEPATH)/$(ALG_NAME)/Implementations/crypto_aead/$(ALG_VARIANT)/ref
OPT = 3

# List C source files here.
# Header files (.h) are automatically pulled in.
SRC += $(ALG_PATH)/encrypt.c

ifeq ($(ALG_VARIANT),elephant200v2)
	SRC += $(ALG_PATH)/keccak.c
else
	SRC += $(ALG_PATH)/spongent.c
endif
