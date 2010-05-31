#!/usr/bin/python

"""
Extract images from MP3 file tags.

The script takes names of MP3 files as command line arguments and dumps the
first image it encounters in each file to the current directory.
"""

# The MIT License {{{
# 
# Copyright (c) 2009-2010 Denis Kobozev <d.v.kobozev@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# }}}


import os
import sys
import locale
from optparse import OptionParser


def main(argv):
    from mutagen.id3 import ID3

    # parse CLI arguments
    parser = OptionParser()
    (options, args) = parser.parse_args(argv[1:])
    if not args:
        raise SystemExit(parser.print_help() or 1)

    enc = locale.getpreferredencoding()
    for filename in args:
        print "--", filename
        f = ID3(filename);
        for frame in f.getall("APIC"):
            print frame.pprint().encode(enc, 'replace')

            # try to determine correct extension
            ext = '.img'
            if frame.mime in ['image/jpeg', 'image/jpg']:
                ext = '.jpg'
            elif frame.mime == 'image/png':
                ext = '.png'
            elif frame.mime == 'image/gif':
                ext = '.gif'
            (proot, pext) = os.path.splitext(filename)
            imgfilename = proot + '_' + str(frame.type) + ext

            if os.path.exists(imgfilename):
                print "File " + imgfilename + " exists. Skipping..."
            else:
                print "Writing image to " + imgfilename
                myfile = file(imgfilename, 'wb')
                myfile.write(frame.data)
                myfile.close()
        print


if __name__ == '__main__':
    main(sys.argv)
