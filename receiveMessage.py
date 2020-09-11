#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lightningd import lightning

rpc = lightning.LightningRpc('/home/corne/lightning-network/node2/testnet/node2.rpc')

payment_hash = rpc.call('receivemessage_new')

print('Payment hash: ' + payment_hash)

