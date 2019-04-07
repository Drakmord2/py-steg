
import sys
import zlib


def get_length(datab, pos):
    """IDAT chunk data lenght in readable form"""

    length = datab[pos - 4:pos]
    intlen = 0
    power = 6
    for i in range(len(length)):
        intlen += (16 ** power) * length[i]
        power -= 2

    return intlen


def insert_data(data, rawdecomp, ihdr_data):
    """LSB Steganography"""

    max_size = len(rawdecomp)
    scansize = int(len(rawdecomp) / ihdr_data[1])  # Bytes per scanline
    colotype = ihdr_data[3]
    filtertype = 0  # No filter
    offset = 0  # Where to start inserting data

    if colotype in [4, 6]:
        raise Exception("Color Type not supported.")

    if type(data) == str:
        data = bytearray(data, "utf-8")
    else:
        data = bytearray(data)

    if len(data) * 8 > max_size:
        raise Exception("Too much data to add. (Data larger than image)")

    print("        Length of added data: {} Bytes".format(len(data)))

    byte = 0
    databyte = 0
    while databyte < len(data):
        if check_filter(byte + offset, scansize, rawdecomp, filtertype):
            byte += 1
            continue

        currbyte = byte + offset
        for i in range(1, 9):
            if check_filter(currbyte, scansize, rawdecomp, filtertype):
                currbyte += 1

            bitmask = 2**(9 - i)                                # 10000000 -> 01000000 -> 00100000 -> ...
            bit = (data[databyte] & bitmask) >> (8 - i)         # Get only desired bit

            try:
                rawdecomp[currbyte] = rawdecomp[currbyte] | bit     # OR the message bit with the current pixel/channel
            except IndexError:
                raise Exception("Too much data to add. (Offset Overflow)")

            currbyte += 1

        byte += 8
        databyte += 1

    return rawdecomp


def check_filter(position, scansize, rawdecomp, filtertype):
    """If start of scanline append Filter Type byte"""

    if position % scansize == 0:
        try:
            rawdecomp[position] = filtertype
        except IndexError:
            raise Exception("Too much data to add. (Offset Overflow)")

        return True

    return False


def get_ihdr_data(datab):
    """Get image's metadata from the IHDR chunk in readable form"""

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
    return widthi, heighti, filtermethodi, colortypei, pixelsize


def insert(inputpath, outputpath, message):
    """Inserts user data into a PNG image"""

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

        try:
            print("    -Adding information to image:")
            rawdecomp = insert_data(message, rawdecomp, ihdr_data)
        except Exception as err:
            print("\nERROR: {}\n".format(err))
            return

        print("    -Compressing new IDAT")

        compressor = zlib.compressobj()
        comp = compressor.compress(rawdecomp)
        comp += compressor.flush()

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


def extract(inputpath, outputpath):
    """Extracts hidden data from a PNG image"""

    print("\n- Mode not implemented -\n")


def show_help():
    """Display Help"""

    print("\n Error: [ Missing Required Arguments! ]\n")

    print("Name\n\tPySteg - insert data into PNG images\n")
    print("Synopsis\n\tpysteg.py mode inpath outpath [ datapath ]\n")
    print("Description\n\t"
          "mode\t\t- '-i' create image\n\t\t\t- '-e' extract data\n\t"
          "inpath\t\t- Path to input image\n\toutpath\t\t- Path to output image\n\tdatapath\t- Path to data")
    print("\nExamples\n\tpython pysteg.py -i smile.png hidden.png secret.txt\n\t"
          "python pysteg.py -e hidden.png secret.txt\n")


def init(args):
    """Start Application"""

    if len(args) < 4:
        show_help()
        return

    mode = args[1]

    print("\n - PySteg V0.3 -")

    if mode == "-i":
        if len(args) < 5:
            show_help()
            return

        inputpath = args[2]   # Path to input image
        outputpath = args[3]  # Path to output image
        datapath = args[4]    # Path to data

        with open(datapath, "rb") as file:
            message = file.read()

        message = bytearray(message)

        insert(inputpath, outputpath, message)
    elif mode == "-e":
        if len(args) < 4:
            show_help()
            return

        inputpath = args[2]   # Path to input image
        outputpath = args[3]  # Path to extracted data

        extract(inputpath, outputpath)
    else:
        print("\n- Invalid Mode -")


if __name__ == "__main__":
    init(sys.argv)
