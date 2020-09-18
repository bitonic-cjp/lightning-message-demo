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

import hashlib
import os
import struct
import sys
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lightningd import lightning, plugin

sha256 = lambda preimage: hashlib.sha256(preimage).digest()


MESSAGE_TLV_TYPE = 254



def serializeBigsize(n):
	if n < 0xfd:
		return struct.pack('B', n)
	elif n < 0x10000:
		return b'\xfd' + struct.pack('>H', n)
	elif n < 0x100000000:
		return b'\xfe' + struct.pack('>I', n)
	else:
		return b'\xff' + struct.pack('>Q', n)


def deserializeBigsize(data):
	first = data[0]
	data = data[1:]
	if first == 0xff:
		return struct.unpack('>Q', data[:8])[0], data[8:]
	elif first == 0xfe:
		return struct.unpack('>I', data[:4])[0], data[4:]
	elif first == 0xfd:
		return struct.unpack('>H', data[:2])[0], data[2:]
	else:
		return first, data


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


def deserializeTLVPayload(TLVData):
	hop_payload_length, data = deserializeBigsize(TLVData)
	assert hop_payload_length != 0
	assert hop_payload_length == len(data)
	ret = {}
	while data:
		T, data = deserializeBigsize(data)
		L, data = deserializeBigsize(data)
		assert L <= len(data)
		V = data[:L]
		data = data[L:]
		ret[T] = V
	return ret


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


def serializeCustomPayload(message):
	return serializeTLVPayload({MESSAGE_TLV_TYPE: message.encode('utf-8')})


p = plugin.Plugin()


@p.method('sendmessage')
def sendMessage(destination, payment_hash, msatoshi, message, plugin=None):
	route = plugin.rpc.getroute(destination, msatoshi, 10)['route']

	payloads = [serializeStandardPayload(hop) for hop in route[1:]]
	customPayload = serializeCustomPayload(message)
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



transactions = {}


@p.hook("htlc_accepted")
def on_htlc_accepted(onion, htlc, plugin, **kwargs):
	plugin.log('> on_htlc_accepted')
	try:
		payload = bytes.fromhex(onion['payload'])
		TLVData = deserializeTLVPayload(payload)
		assert list(TLVData.keys()) == [MESSAGE_TLV_TYPE]
		message = TLVData[MESSAGE_TLV_TYPE].decode('utf-8')
		payment_hash = bytes.fromhex(htlc['payment_hash'])
		tx = transactions[payment_hash]
		preimage = tx['preimage']

		del tx['preimage']
		tx['amount'] = htlc['amount']
		tx['message'] = message

		plugin.log('< on_htlc_accepted: resolve')
		return {'result': 'resolve', 'payment_key': preimage}
	except:
		plugin.log('  exception in on_htlc_accepted:')
		plugin.log(traceback.format_exc())

	plugin.log('< on_htlc_accepted: continue')
	return {'result': 'continue'}


@p.method('receivemessage_new')
def receivemessage_new():
	paymentPreimage = os.urandom(32)
	paymentHash = sha256(paymentPreimage)
	transactions[paymentHash] = {'preimage': paymentPreimage.hex()}
	return paymentHash.hex()


@p.method('receivemessage_poll')
def receivemessage_poll(payment_hash):
	payment_hash = bytes.fromhex(payment_hash)
	tx = transactions[payment_hash]
	if 'message' in tx:
		return tx
	return None


p.run()

