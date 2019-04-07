
import zlib


def get_length(datab, pos):
    length = datab[pos - 4:pos]
    intlen = 0
    power = 6
    for i in range(len(length)):
        intlen += (16 ** power) * length[i]
        power -= 2

    return intlen


def insert(imagepath, message=""):

    try:
        print("\n-Reading image...")
        with open(imagepath, "rb") as image:
            data = image.read()
    except Exception as err:
        print("\n- ERROR: Could not load image.\n{}".format(err))
        return

    datab = bytearray(data)
    magic_number = datab[:8].hex()

    if magic_number != "89504e470d0a1a0a":
        print("\n- ERROR: Invalid Image. Must be PNG.\n")
        return

    print("-Hidding stuff...")

    data2 = datab
    idat_chunks = []
    while True:
        pos = data2.find(b'IDAT')
        if pos != -1:
            idat_chunks.append(pos)
            data2 = data2[pos+4:]
            continue
        break

    print("    -[ {} ] IDAT chunk(s) found.".format(len(idat_chunks)))

    # Size:             4 bytes     | 4 bytes    | Length * 1 byte | 4 bytes
    # PNG Chunk Format: Data Length | Chunk Type | Compressed Data | CRC-32

    if len(idat_chunks) != 0:
        pos = idat_chunks[0]
        print("    -Acessing IDAT chunk at position: {}".format(pos))
        datalen = get_length(datab, pos)

        oldcrc = datab[pos + 4 + datalen:pos + 8 + datalen].hex()

        print("    -Decompressing IDAT...")
        decomp = zlib.decompress(datab[pos + 4:pos + 4 + datalen])
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

        hexlen = hex(newlen).replace("0x", "")
        while len(hexlen) < 8:
            hexlen = "0" + hexlen
        hexlen = bytearray.fromhex(hexlen)

        datab[pos - 4:pos] = hexlen
        datab[pos + 4:pos + 4 + newlen] = comp
        datab[pos + 4 + newlen:] = datab[pos + 4 + datalen:]

        print("    -Updating CRC...")
        newcrc = hex(zlib.crc32(datab[pos:pos + 4 + newlen])).replace("0x", '')
        datab[pos + 4 + newlen:pos + 8 + newlen] = bytearray.fromhex(newcrc)
        print("      Old CRC: {} - New CRC: {}".format(oldcrc, bytearray.fromhex(newcrc).hex()))

    print("-Writting new image...")
    with open("../bin/hidden.png", "wb") as image:
        image.write(datab)

    print("\n- Done -\n")


def extract():
    print("\n- Mode not implemented -\n")


if __name__ == "__main__":
    print("\n - PySteg V0.2 -\n")

    mode = input("Select Mode (i = Insert | e = Extract): ")
    # mode = "i"

    if mode == "i":
        imagepath = input("Path to image: ")
        # imagepath = "../bin/original.png"
        message = "Hidden stuff"

        insert(imagepath, message)
    elif mode == "e":
        extract()
    else:
        print("\n- Invalid Mode -")
