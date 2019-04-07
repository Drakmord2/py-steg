#!/usr/local/Cellar/python/3.7.2_2/libexec/bin/python

import zlib

def get_length(datab, pos):
	length = datab[pos-4:pos]
	intlen = 0
	power = 6
	for i in range(len(length)):
		intlen += (16**power)*length[i]
		power -= 2

	return intlen

print("\n - PySteg V0.1 -\n")

info = "Hidden stuff"
data = None

print("-Reading image...")
with open("original.png", "rb") as image:
	data = image.read()

print("-Hidding stuff...")
datab = bytearray(data)
pos = datab.find(b'IDAT')
if pos != -1:
	print("    -Found an IDAT chunk at position: {}".format(pos))
	datalen = get_length(datab, pos)

	oldcrc = datab[pos+4+datalen:pos+8+datalen].hex()

	print("    -Decompressing IDAT...")
	decomp = zlib.decompress(datab[pos+4:pos+4+datalen])
	rawdecomp = bytearray(decomp)

	print("    -Adding information to image...")
	for r in range(len(rawdecomp)):
		if rawdecomp[r] == 2:
			rawdecomp[r] = 255
	
	print("    -Compressing new IDAT...")
	comp = zlib.compress(rawdecomp)
	comp = bytearray(comp)

	print("    -Computing new data length...")
	newlen = len(comp)
	print("      Old length: {} - New length: {}".format(datalen, newlen))

	hexlen = hex(newlen).replace("0x","")
	while len(hexlen) < 8:
		hexlen = "0"+hexlen
	hexlen = bytearray.fromhex(hexlen)

	datab[pos-4:pos] = hexlen
	datab[pos+4:pos+4+newlen] = comp
	datab[pos+4+newlen:] = datab[pos+4+datalen:]

	print("    -Updating CRC...")
	newcrc = hex(zlib.crc32(datab[pos:pos+4+newlen])).replace("0x", '')
	datab[pos+4+newlen:pos+8+newlen] = bytearray.fromhex(newcrc)
	print("      Old CRC: {} - New CRC: {}".format(oldcrc, bytearray.fromhex(newcrc).hex()))

print("-Writting new image...")
with open("hidden.png", "wb") as image:
	image.write(datab)

print("\n- Done -\n")
