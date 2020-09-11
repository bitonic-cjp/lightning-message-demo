#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lightningd import lightning

rpc = lightning.LightningRpc('/home/corne/lightning-network/node0/testnet/node0.rpc')

payment_hash = input('Payment hash? ')
message = input('Message? ')

ret = rpc.call('sendmessage',
	{
	'destination': '033b83e1f29b0b73633258f27e9c4d97f37cc8a5b84e2a2d8fdd1b5bb43b5db3e0',
	'payment_hash': payment_hash,
	'msatoshi': 1000,
	'message': message,
	})

print(ret)

