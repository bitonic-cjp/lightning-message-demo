#!/usr/bin/env python3

import os
import struct
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lightningd import lightning, plugin


def serializeStandardPayload(route_data, plugin):
	style = route_data['style']
	if style == 'legacy':
		blockHeight = plugin.rpc.getinfo()['blockheight']

		realm = b'\x00'
		#This may be Bitcoin-specific:
		# Short Channel ID is composed of 3 bytes for the block height, 3
		# bytes of tx index in block and 2 bytes of output index
		chnBlockHeight, chnTxIndex, chnOutputIndex = route_data['channel'].split('x')
		chnBlockHeight = struct.pack('>I', int(chnBlockHeight))[-3:]
		chnTxIndex = struct.pack('>I', int(chnTxIndex))[-3:]
		chnOutputIndex = struct.pack('>H', int(chnOutputIndex))
		short_channel_id = realm + chnBlockHeight + chnTxIndex + chnOutputIndex

		amt_to_forward = route_data['msatoshi']
		outgoing_cltv_value = blockHeight + route_data['delay']
		return \
			struct.pack('>9sQI',
				short_channel_id,
				amt_to_forward,
				outgoing_cltv_value
				) + 24*b'\0'

	raise Exception('Style not supported: ' + style)


p = plugin.Plugin()


@p.method('sendmessage')
def sendMessage(destination, msatoshi, message, plugin=None):
	route = plugin.rpc.getroute(destination, msatoshi, 10)
	#return route
	return serializeStandardPayload({
		'channel': '103x1x1',
		'msatoshi': 1001,
		'delay': 15,
		'style': 'legacy',
		}, plugin).hex()


p.run()

