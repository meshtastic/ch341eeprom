import os
import subprocess
import argparse
import time
import binascii
import hashlib

def hexDump(buf):
  buf=bytearray(buf)
  alphabet=b'0123456789abcdef'
  ln = len(buf)
  #print("Len of buf: "+str(ln))
  print("   +------------------------------------------------+ +----------------+")
  print("   |.0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .a .b .c .d .e .f | |      ASCII     |")
  i = 0
  while i < ln:
    if i % 128 == 0:
      print("   +------------------------------------------------+ +----------------+")
    s=b'|                                                | |................|'
    s0=list(s)
    ix = 1
    iy = 52
    j=0
    while j < 16:
      if (i + j) < ln:
        c=buf[i+j]
        s0[ix] = alphabet[(c >> 4) & 0x0F]
        ix += 1
        s0[ix] = alphabet[c & 0x0F]
        ix += 2
        if (c > 31 and c < 127):
          s0[iy] = c
        iy += 1
      j += 1
    index = int(i / 16)
    hd=("00"+hex(index)[2:])[-2:]+"."
    s=bytearray(s0)
    s = hd+s.decode()
    print(s)
    i += 16
  print("   +------------------------------------------------+ +----------------+")


class eepCH341(object):
    """
    :param size_str: EEPROM size string      - default "24c02"
    :param size_bytes: EEPROM size in bytes  - default 256
    :param majorVersion: Major version number
    :param minorVersion: Minor version number
    :param serial: Serial number (8 bytes)
    :param product: Product string (up to 95 bytes)
    :param MODE: Mode byte            - default 0x12
    :param CFG: Configuration byte    - default 0xCC
    :param VID: Vendor ID (2 bytes)   - default (0x1A, 0x86)
    :param PID: Product ID (2 bytes)  - default (0x55, 0x12)
    """

    def __init__(
            self, majorVersion: bytes, minorVersion: bytes, serial: str, product: str,
            size_str: str = "24c02", size_bytes: int = 256,
            MODE: bytes = 0x12, CFG: bytes = 0xCC, VID: bytearray = (0x1A, 0x86), PID: bytearray = (0x55, 0x12)
    ):
        self.size = size_str
        self.size_bytes = size_bytes
        self.majorVersion = majorVersion
        self.minorVersion = minorVersion
        if len(serial) == 8:
            self.serial = serial
        else:
            raise ValueError("Serial number must be 8 digits")
        if len(product) < 79:
            self.product = product
        else:
            raise ValueError("Product string too long, max 79 characters")
        self.MODE = MODE
        self.CFG = CFG
        self.VID = VID
        self.PID = PID
        self.device_id = os.urandom(16)

    def __str__(self):
        return f"EEPROM: {self.majorVersion}.{self.minorVersion} {self.serial} {self.product}"

    def bytes(self):
        """
        Generate the EEPROM bytes
        :return: bytearray of EEPROM
        """
        rom = bytearray(self.size_bytes-1)
        rom[0] = 0x53
        rom[1] = self.MODE
        rom[2] = self.CFG
        rom[3] = 0x00
        rom[4] = self.VID[1]
        rom[5] = self.VID[0]
        rom[6] = self.PID[1]
        rom[7] = self.PID[0]
        rom[8] = self.minorVersion
        rom[9] = self.majorVersion
        # Bytes 10-15 are padding
        # Serial number (bytes 16-23)
        serial_bytes = bytearray(self.serial.encode('ascii'))
        rom[16:23] = serial_bytes
        # Bytes 24-31 are padding
        # Product String bytes (32-127)
        product_bytes = bytearray(self.product.encode('ascii'))
        rom[32:32 + len(product_bytes)] = product_bytes
        rom[32 + len(product_bytes) + 1:32 + len(product_bytes) + 16 + 1] = self.device_id
        return rom

    def hex(self):
        return self.bytes().hex()

    def erase(self, bin_ch341eeprom: str):
        r = subprocess.run([
            bin_ch341eeprom,
            # "--verbose",
            "--erase",
            "--size", self.size
        ], check=True)
        return r

    def read(self, bin_ch341eeprom: str):
        # Delete existing read_eeprom.bin file if it exists
        if os.path.exists("read_eeprom.bin"):
            os.remove("read_eeprom.bin")
        # Use `ch341eeprom` to read the EEPROM
        r = subprocess.run([
            bin_ch341eeprom,
            # "--verbose",
            "--read", "read_eeprom.bin",
            "--size", self.size
        ], capture_output=True, check=True)

        # Read the EEPROM file and return it as a byte array
        with open("read_eeprom.bin", "rb") as f:
            data = f.read()
        os.remove("read_eeprom.bin")

        return data

    def flash(self, bin_ch341eeprom: str):
        # Delete existing write_eeprom.bin file if it exists
        if os.path.exists("write_eeprom.bin"):
            os.remove("write_eeprom.bin")
        # Write the byte array to a temp file
        with open("write_eeprom.bin", "wb") as f:
            f.write(self.bytes())
        # Use `ch341eeprom` to flash the EEPROM
        r = subprocess.run([
            bin_ch341eeprom,
            # "--verbose",
            "--write", "write_eeprom.bin",
            "--size", self.size
        ], check=True)
        os.remove("write_eeprom.bin")

        return r

    def verify(self, bin_ch341eeprom: str):
        # Delete existing verify_eeprom.bin file if it exists
        if os.path.exists("verify_eeprom.bin"):
            os.remove("verify_eeprom.bin")
        # Write the byte array to a temp file
        with open("verify_eeprom.bin", "wb") as f:
            f.write(self.bytes())
        # Use `ch341eeprom` to verify the EEPROM
        r = subprocess.run([
            bin_ch341eeprom,
            # "--verbose",
            "--verify", "verify_eeprom.bin",
            "--size", self.size
        ], check=True)
        os.remove("verify_eeprom.bin")

        return r

if __name__ == "__main__":
    timestr = time.strftime("%Y%m%d-%H%M%S")

    parser = argparse.ArgumentParser(description="CH341 EEPROM programmer utility")
    parser.add_argument("--serial", type=int, default=0,
                        help="8-digit serial number (default: 0)")
    parser.add_argument("--product", default="MESHSTICK 1262",
                        help="Product name (default: MESHSTICK 1262)")
    parser.add_argument("--major-version", type=int, default=1, dest="majorVersion",
                        help="Major version number (default: 1)")
    parser.add_argument("--minor-version", type=int, default=0, dest="minorVersion",
                        help="Minor version number (default: 0)")
    parser.add_argument("--bin", default="./ch341eeprom",
                        help="Path to ch341eeprom binary (default: ch341eeprom in local folder)")
    args = parser.parse_args()

    cur_serial = int(args.serial)
    logfile = open(timestr + ".log", 'w')

    while True:
        input(f"Attach serial number: {cur_serial}")
        eeprom = eepCH341(args.majorVersion, args.minorVersion, str(cur_serial), args.product)
        # print(eeprom.hex())

        # Read the EEPROM before flashing
        read_init = eeprom.read(args.bin)
        if len(read_init) != eeprom.size_bytes:
            raise ValueError(f"EEPROM read error: expected {eeprom.size_bytes} bytes, got {len(read_init)} bytes")

        # Erase the EEPROM
        eeprom.erase(args.bin)

        # Flash/verify the EEPROM
        eeprom.flash(args.bin)
        eeprom.verify(args.bin)
        print(f"Flashed EEPROM for {args.product} {cur_serial}")

        # Read the EEPROM again
        read_again = eeprom.read(args.bin)
        print("New EEPROM Contents:")
        # Print the first 128 bytes of the EEPROM
        # print(read_again[0:127])
        hexDump(read_again[0:127])

        print("")

        hash_object = hashlib.sha256((eeprom.serial + eeprom.product).encode())
        hexdigest = hash_object.hexdigest()
        firstbyte = hexdigest[:2]
        intfirstbyte = int(firstbyte, 16)
        intfirstbyte = hex(((intfirstbyte << 4) | 2) % 256)[2:4]
        macstr = f"{intfirstbyte}:" + hexdigest[2:4] + ":" + hexdigest[4:6] + ":" + hexdigest[6:8] + ":" + hexdigest[8:10] + ":" + hexdigest[10:12]
        #print(macstr)
        logfile.write(eeprom.serial + ", " + macstr + ", " + eeprom.product + ", " + binascii.hexlify(eeprom.device_id).decode("ascii") + "\n" )

        cur_serial += 1
