#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# hexdump.py: display contents of a file in hex
from xtlib import console

def get_nice_text(byte_buff, start, end):
    text = byte_buff[start:end+1].decode()
    # filter out CR/LF
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    return text

def hex_dump(fn):
    console.print("hex dump of: {}\n".format(fn))

    # read file raw
    with open(fn, "rb") as infile:
        byte_buff = infile.read()

    start_index = 0
    addr = 0
    console.print("{:04x}    ".format(addr), end="") 

    for i in range(len(byte_buff)):
        value = byte_buff[i]
        console.print("{:02x} ".format(value), end="")

        if (i+1) % 16 == 0:
            text = get_nice_text(byte_buff, start_index, i)
            console.print("   " + text)
            addr += 16
            console.print("{:04x}    ".format(addr), end="") 
            start_index = i+1

    # console.print last text
    i -= 1
    if start_index <= i:
        text = get_nice_text(byte_buff, start_index, i+1)
        missing = 15-((i+1) % 16)
        spaces =  "   "*missing
        text = spaces + " " + text
        console.print(text)

