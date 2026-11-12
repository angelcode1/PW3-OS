#!/usr/bin/env python3
"""Validate BMP captured directly from NetSurf's SDL framebuffer; make PW3 PGM.

A distinct producer from Xvfb screenshots, usable with SDL's dummy driver.
No Pillow and no physical framebuffer access.
"""
from pathlib import Path
import struct
import sys

PW3_W,PW3_H=1072,1448
PGM_HEADER=b"P5\n1072 1448\n255\n"

def read_bmp(path):
    b=Path(path).read_bytes()
    if len(b)<54 or b[:2]!=b"BM":
        raise ValueError("Expected Windows BMP")
    file_size=struct.unpack_from("<I",b,2)[0]
    off=struct.unpack_from("<I",b,10)[0]
    header_size=struct.unpack_from("<I",b,14)[0]
    if file_size!=len(b) or header_size<40 or header_size>124 or off<54:
        raise ValueError("BMP file/header size invalid")
    width,height=struct.unpack_from("<ii",b,18)
    planes,bpp=struct.unpack_from("<HH",b,26)
    compression=struct.unpack_from("<I",b,30)[0]
    if (width<100 or height==0 or abs(height)<100 or width>1072 or
            abs(height)>1448 or planes!=1 or bpp not in (24,32) or
            compression!=0):
        raise ValueError("Unsupported BMP geometry/format")
    H=abs(height)
    channels=bpp//8
    stride=(width*channels+3)&~3
    if off+H*stride!=len(b):
        raise ValueError("BMP has truncated or trailing pixels")
    return b,off,width,H,channels,stride,height>0

def validate_and_convert(source, destination):
    b,offset,w,h,ch,stride,bottom_up=read_bmp(source)
    black=white=magenta=0
    for y in range(h):
        line=offset+(h-1-y if bottom_up else y)*stride
        for x in range(w):
            i=line+x*ch
            blue,green,red=b[i],b[i+1],b[i+2]
            if max(red,green,blue)<50: black+=1
            if min(red,green,blue)>=220: white+=1
            if red>=145 and 20<=green<=105 and 80<=blue<=185:
                magenta+=1
    if black<1000 or white<10000 or magenta<5000:
        raise ValueError(f"Direct SDL framebuffer lacks CSS proof "
                         f"black={black} white={white} magenta={magenta}")
    if PW3_W*h<=PW3_H*w:
        dw=PW3_W
        dh=max(1,h*PW3_W//w)
    else:
        dh=PW3_H
        dw=max(1,w*PW3_H//h)
    left=(PW3_W-dw)//2
    top=(PW3_H-dh)//2
    gray=bytearray(b"\xff"*(PW3_W*PW3_H))
    for y in range(dh):
        sy=y*h//dh
        line=offset+(h-1-sy if bottom_up else sy)*stride
        out=(y+top)*PW3_W+left
        for x in range(dw):
            sx=x*w//dw
            i=line+sx*ch
            blue,green,red=b[i],b[i+1],b[i+2]
            gray[out+x]=(2126*red+7152*green+722*blue+5000)//10000
    Path(destination).write_bytes(PGM_HEADER+gray)
    print(f"CODEX_DIRECT_NETSURF_SDL_PIXEL_PASS {w}x{h} "
          f"black={black} white={white} css_magenta={magenta} "
          f"pw3_gray={PW3_W}x{PW3_H}")
    return gray

if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("usage: verify_direct_sdl.py direct.bmp output-pw3.pgm")
    try:
        validate_and_convert(sys.argv[1],sys.argv[2])
    except (ValueError,OSError) as e:
        raise SystemExit("CODEX_DIRECT_NETSURF_SDL_FAIL: "+str(e))
