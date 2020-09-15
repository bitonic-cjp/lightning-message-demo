#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from lightningd import lightning

rpc = lightning.LightningRpc(config.sendNodeRPCFile)

payment_hash = input('Payment hash? ')
msatoshi = int(input ('Amount (msatoshi)? '))
message = input('Message? ')

ret = rpc.call('sendmessage',
	{
	'destination': config.receiveNodeID,
	'payment_hash': payment_hash,
	'msatoshi': msatoshi,
	'message': message,
	})

print(ret)

