/*
    This file is part of the ChipWhisperer Example Targets
    Copyright (C) 2012-2017 NewAE Technology Inc.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

#include "hal.h"

#include "simpleserial.h"
#include "crypto_aead.h"

#define SUCCESS 0
#define E_NO_KEY 1
#define E_MISSING_PARAMS 2
#define E_TOO_LONG 3

uint16_t pt_len = 0;
uint8_t pt_bytes[256] = {0}; // 16 bytes per block * 16 blocks max
uint16_t ad_len = 0;
uint8_t ad_bytes[256] = {0}; // 16 bytes per block * 16 blocks max
uint8_t key[16] = {0};

uint8_t reset(uint8_t* buf, uint8_t len) {
	pt_len = 0;
	ad_len = 0;

	return SUCCESS;
}

uint8_t set_key(uint8_t* buf, uint8_t len)
{
	for (uint8_t i = 0; i < 16; ++i) {
		key[i] = buf[i];
	}

	return SUCCESS;
}

uint8_t set_plaintext_block(uint8_t* buf, uint8_t len) 
{
	uint8_t block_len = buf[0];
	uint16_t start = pt_len;

	for (uint8_t i = 0; i < block_len; ++i) {
		pt_bytes[i + start] = buf[i + 1];
	}

	pt_len += block_len;

	return 0;
}

uint8_t set_ad_block(uint8_t* buf, uint8_t len) 
{
	uint8_t block_len = buf[0];
	uint16_t start = ad_len;

	for (uint8_t i = 0; i < block_len; ++i) {
		ad_bytes[i + start] = buf[i + 1];
	}

	ad_len += block_len;

	return 0;
}


uint8_t encrypt_with_nonce(uint8_t* nonce, uint8_t len)
{
	/**********************************
	* Start user-specific code here. */
	uint8_t out[528] = {0}; // 512 + potential 16 bytes tag
	long long unsigned int ct_size = 0;
	
	trigger_high();
	crypto_aead_encrypt(out, &ct_size, pt_bytes, pt_len, ad_bytes, ad_len, 0, nonce, key);
	trigger_low();

	uint8_t len_out[2] = {0};
	len_out[0] = (ct_size >> 8) & 0xff;
	len_out[1] = (ct_size) & 0xff;

	simpleserial_put('r', 2, len_out);
	simpleserial_put('r', ct_size, out);

	/* End user-specific code here. *
	********************************/
	return 0x00;
}


uint8_t decrypt_with_nonce(uint8_t* nonce, uint8_t len)
{
	/**********************************
	* Start user-specific code here. */
	uint8_t out[512] = {0}; // 512 + potential 16 bytes tag
	long long unsigned int pt_size = 0;
	
	trigger_high();
	crypto_aead_decrypt(out, &pt_size, 0, pt_bytes, pt_len, ad_bytes, ad_len, nonce, key);
	trigger_low();

	uint8_t len_out[2] = {0};
	len_out[0] = (pt_size >> 8) & 0xff;
	len_out[1] = (pt_size) & 0xff;

	simpleserial_put('r', 2, len_out);
	simpleserial_put('r', pt_size, out);

	/* End user-specific code here. *
	********************************/
	return 0x00;
}


uint8_t encrypt_empty_pt(uint8_t* buf, uint8_t len)
{
	reset(buf, len);
	set_key(buf, 16);
	return encrypt_with_nonce(buf + 16, 0);
}

int main(void)
{
    platform_init();
	init_uart();
	trigger_setup();
    
    putch('h');
    putch('e');
    putch('l');
    putch('l');
    putch('o');
    putch('\n');

	simpleserial_init();
	simpleserial_addcmd('r', 0, reset);
	simpleserial_addcmd('e', 32, encrypt_empty_pt);

	simpleserial_addcmd('k', 16, set_key);
	simpleserial_addcmd('p', 17, set_plaintext_block);
	simpleserial_addcmd('a', 17, set_ad_block);

	simpleserial_addcmd('n', 16, encrypt_with_nonce);
	simpleserial_addcmd('d', 16, decrypt_with_nonce);
	while(1)
		simpleserial_get();
}
