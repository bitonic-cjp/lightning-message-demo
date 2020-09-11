#!/usr/bin/env python3

import os
import struct
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lightningd import lightning, plugin


def serializeBigsize(n):
	if n < 0xfd:
		return struct.pack('B', n)
	elif n < 0x10000:
		return b'\xfd' + struct.pack('>H', n)
	elif n < 0x100000000:
		return b'\xfe' + struct.pack('>I', n)
	else:
		return b'\xff' + struct.pack('>Q', n)


def serializeTLVPayload(TLVData):
	keys = list(TLVData.keys())
	keys.sort()
	hop_payload = b''
	for k in keys:
		T = serializeBigsize(k)
		V = TLVData[k]
		L = serializeBigsize(len(V))
		hop_payload += T + L + V
	hop_payload_length = serializeBigsize(len(hop_payload))
	return hop_payload_length + hop_payload


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


def serializeCustomPayload(T, message):
	return serializeTLVPayload({T: message.encode('utf-8')})


p = plugin.Plugin()


@p.method('sendmessage')
def sendMessage(destination, payment_hash, msatoshi, message, plugin=None):
	route = plugin.rpc.getroute(destination, msatoshi, 10)['route']

	payloads = [serializeStandardPayload(hop) for hop in route[1:]]
	customPayload = serializeCustomPayload(254, message)
	payloads.append(customPayload)

	hops = \
	[
	{'pubkey': r['id'], 'payload': pl.hex()}
	for r, pl in zip(route, payloads)
	]

	ret = plugin.rpc.createonion(hops, payment_hash)
	onion = ret['onion']
	shared_secrets = ret['shared_secrets']

	sendOutput = plugin.rpc.sendonion(
		onion=onion,
		first_hop=route[0],
		payment_hash=payment_hash,
		label='sendmessage payment',
		shared_secrets=shared_secrets,
		msatoshi=msatoshi,
		)

	waitOutput = plugin.rpc.waitsendpay(payment_hash)

	return {'send': sendOutput, 'wait': waitOutput}



p.run()

