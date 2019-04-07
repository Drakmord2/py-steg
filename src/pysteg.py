
import zlib


def get_length(datab, pos):
    length = datab[pos - 4:pos]
    intlen = 0
    power = 6
    for i in range(len(length)):
        intlen += (16 ** power) * length[i]
        power -= 2

    return intlen


def insert_data(rawdecomp, ihdr_data):
    scansize = int(len(rawdecomp) / ihdr_data[1])  # Bytes per scanline
    filtertype = 0  # No filter

    byte = 0
    while byte < len(rawdecomp):
        if byte % scansize == 0:
            rawdecomp[byte] = filtertype
            byte += 1
            continue

        r = byte
        g = byte+1
        b = byte+2
        alpha = byte+3

        rawdecomp[r] = 255 - rawdecomp[r]
        rawdecomp[g] = 255 - rawdecomp[g]
        rawdecomp[b] = 255 - rawdecomp[b]
        rawdecomp[alpha] = 255

        byte += 4

    return rawdecomp


def get_ihdr_data(datab):
    ihdrpos = datab.find(b'IHDR')
    ihdr = datab[ihdrpos+4:ihdrpos+4+13]

    widthi = int(ihdr[:4].hex(), 16)
    heighti = int(ihdr[4:8].hex(), 16)
    colortypei = int(ihdr[9:10].hex(), 16)
    filtermethodi = int(ihdr[11:12].hex(), 16)
    bitdepthi = int(ihdr[8:9].hex(), 16)
    compressioni = int(ihdr[10:11].hex(), 16)
    interlacei = int(ihdr[12:13].hex(), 16)

    width = "\t\t\t" + str(widthi) + " pixels"
    height = "\t\t" + str(heighti) + " pixels"

    pixelsize = 1
    bitdepth = "\t\t" + str(bitdepthi)
    if bitdepthi == 1:
        bitdepth += " (1 bit per pixel)"
    elif bitdepthi == 2:
        bitdepth += " (2 bits per pixel)"
        pixelsize = 2
    elif bitdepthi == 4:
        bitdepth += " (4 bits per pixel)"
        pixelsize = 4
    elif bitdepthi == 8:
        if colortypei in [0, 3]:
            bitdepth += " (8 bits per pixel)"
            pixelsize = 8
        elif colortypei == 4:
            bitdepth += " (16 bits per pixel)"
            pixelsize = 16
        elif colortypei == 2:
            bitdepth += " (24 bits per pixel)"
            pixelsize = 24
        elif colortypei == 6:
            bitdepth += " (32 bits per pixel)"
            pixelsize = 32
    elif bitdepthi == 16:
        if colortypei in [0, 3]:
            bitdepth += " (16 bits per pixel)"
            pixelsize = 16
        elif colortypei == 4:
            bitdepth += " (32 bits per pixel)"
            pixelsize = 32
        elif colortypei == 2:
            bitdepth += " (48 bits per pixel)"
            pixelsize = 48
        elif colortypei == 6:
            bitdepth += " (64 bits per pixel)"
            pixelsize = 64

    colortype = "\t\t" + str(colortypei)
    if colortypei == 0:
        colortype += " (Grayscale) [ 1 channel ]"
    elif colortypei == 2:
        colortype += " (Truecolor) [ 3 channels ]"
    elif colortypei == 3:
        colortype += " (Indexed) [ 1 channel ]"
    elif colortypei == 4:
        colortype += " (Grayscale and Alpha) [ 2 channels ]"
    elif colortypei == 6:
        colortype += " (Truecolor and Alpha) [ 4 channels ]"

    compression = "\t" + str(compressioni)
    if compressioni == 0:
        compression += " (DEFLATE)"
    else:
        compression += " (Unknown)"

    filtermethod = "\t\t" + str(filtermethodi)
    if filtermethodi == 0:
        filtermethod += " (None)"
    elif filtermethodi == 1:
        filtermethod += " (Sub)"
    elif filtermethodi == 2:
        filtermethod += " (Up)"
    elif filtermethodi == 3:
        filtermethod += " (Average)"
    elif filtermethodi == 4:
        filtermethod += " (Paeth)"

    interlace = "\t" + str(interlacei)
    if interlacei == 0:
        interlace += " (None)"
    elif interlacei == 1:
        interlace += " (Adam7)"

    print("    -IHDR data: \n        Width: {}\n        Height: {}\n        Bit Depth: {}\n        Color Type: {}\n    "
          "    Compression Method: {}\n        Filter Method: {}\n        Interlace Method: {}".format(
                                                                                width, height, bitdepth, colortype,
                                                                                compression, filtermethod,
                                                                                interlace))
    return widthi, heighti, filtermethodi, bytes(colortypei), pixelsize


def insert(inputpath, outputpath, message=""):

    try:
        filename = inputpath.split("/")[-1]
        print("\n-Reading image: [ {} ]".format(filename))
        with open(inputpath, "rb") as image:
            data = image.read()
    except Exception as err:
        print("\n- ERROR: Could not load image.\n{}".format(err))
        return

    datab = bytearray(data)
    magic_number = datab[:8].hex()

    if magic_number != "89504e470d0a1a0a":
        print("\n- ERROR: Invalid Image. Must be PNG.\n")
        return

    ihdr_data = get_ihdr_data(datab)

    print("-Adding user data to image:")

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

    # Size:             4 Bytes     | 4 Bytes    | Length * 1 byte | 4 Bytes
    # PNG Chunk Format: Data Length | Chunk Type | Compressed Data | CRC-32

    if len(idat_chunks) != 0:
        pos = idat_chunks[0]
        print("    -Accessing IDAT chunk at position: {}".format(pos))
        datalen = get_length(datab, pos)

        oldcrc = datab[pos + 4 + datalen:pos + 8 + datalen].hex()

        print("    -Decompressing IDAT")
        decomp = zlib.decompress(datab[pos + 4:pos + 4 + datalen])
        rawdecomp = bytearray(decomp)

        print("    -Adding information to image:")
        rawdecomp = insert_data(rawdecomp, ihdr_data)

        print("    -Compressing new IDAT")
        comp = zlib.compress(rawdecomp, level=6)
        comp = bytearray(comp)

        print("    -Computing new IDAT data length:")
        newlen = len(comp)
        print("        Old: {} -> New: {}".format(datalen, newlen))

        hexlen = hex(newlen).replace("0x", "")
        while len(hexlen) < 8:
            hexlen = "0" + hexlen
        hexlen = bytearray.fromhex(hexlen)

        newdata = datab[:pos-4]
        newdata += hexlen
        newdata += bytearray(b'IDAT')

        end = datab[pos + 4 + datalen:]
        newdata += comp
        newdata += end

        print("    -Computing new CRC-32:")
        newcrc = hex(zlib.crc32(newdata[pos: pos+4+newlen])).replace("0x", '')
        while len(newcrc) < 8:
            newcrc = '0' + newcrc

        newdata[pos + 4 + newlen:pos + 8 + newlen] = bytearray.fromhex(newcrc)
        print("        Old: {} -> New: {}".format(oldcrc, bytearray.fromhex(newcrc).hex()))

    filename = outputpath.split("/")[-1]
    print("-Writting new image: [ {} ]".format(filename))
    with open(outputpath, "wb") as image:
        if 'newdata' not in locals():
            newdata = datab

        image.write(newdata)

    print("\n- Done -\n")


def extract():
    print("\n- Mode not implemented -\n")


if __name__ == "__main__":
    print("\n - PySteg V0.2 -\n")

    # mode = input("Select Mode (i = Insert | e = Extract): ")
    mode = "i"

    if mode == "i":
        # inputpath = input("Path to input image: ")
        # outputpath = input("Path to output image: ")
        inputpath = "../bin/original.png"
        outputpath = "../bin/hidden.png"
        message = "Hidden stuff"

        insert(inputpath, outputpath, message)
    elif mode == "e":
        extract()
    else:
        print("\n- Invalid Mode -")
