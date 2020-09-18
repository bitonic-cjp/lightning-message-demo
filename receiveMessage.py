#!/usr/bin/env python3
#    Copyright (C) 2020 by Bitonic B.V.
#
#    This file is part of the Lightning Message Demo.
#
#    The Lightning Message Demo is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    The Lightning Message Demo is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with the Lightning Message Demo. If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from lightningd import lightning

rpc = lightning.LightningRpc(config.receiveNodeRPCFile)

payment_hash = rpc.call('receivemessage_new')

print('Payment hash: ' + payment_hash)

while True:
	message = rpc.call('receivemessage_poll', {'payment_hash': payment_hash})
	if message is not None:
		break
	time.sleep(0.1)

print(message)

