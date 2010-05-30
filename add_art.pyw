#!/usr/bin/python


"""Add a front cover image to ID3v2 tags."""


# The MIT License
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


# mutagen.id3.APIC attributes:
#
# encoding -- text encoding for the description
# mime -- a MIME type (e.g. image/jpeg) or '-->' if the data is a URI
# type -- the source of the image (3 is the album front cover)
# desc -- a text description of the image
# data -- raw image data, as a byte string

import wx
import wx.lib.newevent
import add_art_gui

import os
import os.path
import threading
from mutagen.id3 import ID3, APIC


FRONT_COVER = 3
ID3V2_UNICODE = 1

# emitted when files have been added and their id3 data loaded
AddFilesEvent, EVT_ADD_FILES = wx.lib.newevent.NewEvent()
# emitted when tags have been written
WriteTagsEvent, EVT_WRITE_TAGS = wx.lib.newevent.NewEvent()


class AddFilesThread(threading.Thread):
    """Thread to load ID3 tags from files."""
    
    def __init__(self, frame, paths):
        threading.Thread.__init__(self)
        
        self.frame = frame
        self.paths = paths
        
    def run(self):
        self.frame.metadata = {}
        for abs_path in self.paths:
            self.frame.metadata[abs_path] = ID3(abs_path)
        wx.PostEvent(self.frame, AddFilesEvent())

        
class AddDirThread(threading.Thread):
    """Thread to add mp3s recursively."""
    
    def __init__(self, frame, path):
        threading.Thread.__init__(self)
        
        self.frame = frame
        self.path = path
        
    def run(self):
        self.frame.metadata = {}
        self.add_mp3_recurse(self.path)
        wx.PostEvent(self.frame, AddFilesEvent())
        
    def add_mp3_recurse(self, abs_path):
        for file in os.listdir(abs_path):
            abs_file = os.path.join(abs_path, file)
            if os.path.isdir(abs_file):
                self.add_mp3_recurse(abs_file)
            elif os.path.splitext(abs_file).lower() == '.mp3':
                self.frame.metadata[abs_file] = ID3(abs_file)
     
     
class WriteTagsThread(threading.Thread):
    """Thread to write covers to ID3 tags."""

    def __init__(self, frame):
        threading.Thread.__init__(self)
        
        self.frame = frame
        
    def run(self):
        for abs_path, meta in frame.metadata.iteritems():
            cover_frame = APIC(encoding=0, mime='image/jpeg', type=FRONT_COVER,
                desc='', data=frame.img_data)
            meta.add(cover_frame)
            meta.save()
        wx.PostEvent(self.frame, WriteTagsEvent())


class AddArtFrame(add_art_gui.MainFrame):
    def __init__(self, parent):
        add_art_gui.MainFrame.__init__(self, parent)

        self.metadata = {} # id3 data of loaded files
        self.img_data = None # image to write to files
        self.img_wx = None # wx.Image created from `img_data`
        
        # attrs for running threads
        self.add_files_t = None
        self.write_tags_t = None

        self.Bind(wx.EVT_BUTTON, self.onAddFiles, self.button_add_files)
        self.Bind(wx.EVT_BUTTON, self.onAddDir, self.button_add_dir)
        self.Bind(wx.EVT_BUTTON, self.onOpenImage, self.button_open_image)
        self.Bind(wx.EVT_BUTTON, self.onWriteTags, self.button_write_tags)
        
        self.Bind(EVT_ADD_FILES, self.onAddFilesEnd)
        self.Bind(EVT_WRITE_TAGS, self.onWriteTagsEnd)

    def onAddFiles(self, event):
        open_dialog = wx.FileDialog(self,
            message='Choose mp3 files',
            wildcard='*.mp3',
            style=wx.FD_MULTIPLE | wx.FD_OPEN # multiple selection
            )
        if open_dialog.ShowModal() == wx.ID_OK:
            # show directory path in text_ctrl
            self.textctrl_curpath.SetValue(open_dialog.GetDirectory())
            
            if not self.add_files_t: # lauch a thread to load tags
                self.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
                self.add_files_t = AddFilesThread(self, open_dialog.GetPaths())
                self.add_files_t.start()
                
    def onAddDir(self, event):
        """Add all mp3 files within a directory recursively."""
        open_dialog = wx.FileDialog(self,
            message="Choose a directory",
            wildcard='*.*',
            style=wx.FD_OPEN
            )
        if open_dialog.ShowModal() == wx.ID_OK:
            self.textctrl_curpath.SetValue(open_dialog.GetDirectory())
            
            if not self.add_files_t: # launch a new thread
                self.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
                self.add_files_t = AddDirThread(self, open_dialog.GetDirectory())
                self.add_files_t.start()
                
    def onAddFilesEnd(self, event):
        # show file name in the listbox
        paths = self.metadata.keys()
        paths.sort()
        self.list_files.Clear()
        for p in paths:
            self.list_files.Append(os.path.basename(p))

        # enable the write button
        if not self.button_write_tags.IsEnabled() and self.img_data:
            self.button_write_tags.Enable(True)
        
        self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW)) # restore regular cursor
        
        self.add_files_t = None # get rid of the thread

    def onOpenImage(self, event):
        """Load a jpeg image."""
        open_dialog = wx.FileDialog(self,
            message='Choose an image',
            wildcard='*.jpeg|*.jpg',
            )
        if open_dialog.ShowModal() == wx.ID_OK:
            abs_path = open_dialog.GetPath()

            self.img_data = open(abs_path, 'rb').read()
            self.img_wx = wx.Image(abs_path, wx.BITMAP_TYPE_ANY)
            self._scale_art()

            # enable the write button
            if not self.button_write_tags.IsEnabled() and self.metadata:
                self.button_write_tags.Enable(True)

    def onWriteTags(self, event):
        """Write APIC tags to files."""
        if not self.write_tags_t: # start a thread to write tags
            self.button_write_tags.Enable(False)
            self.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
            self.write_tags_t = WriteTagsThread(self)
            self.write_tags_t.start()
            
    def onWriteTagsEnd(self, event):
        self.button_write_tags.Enable(True)
        self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        # notify the user
        self.main_frame_statusbar.SetStatusText(str(len(self.metadata)) +
            ' covers written!')
            
        self.write_tags_t = None

    def _scale_art(self):
        """Scale and display opened image."""
        w, h = self.bitmap_art.GetClientSize()
        img_w, img_h = self.img_wx.GetSize()
        a_ratio = float(img_h) / img_w
        if a_ratio > 1:
            # tall image
            img = self.img_wx.Scale(h / a_ratio, h, wx.IMAGE_QUALITY_HIGH)
        else:
            # wide or square image
            img = self.img_wx.Scale(w, w * a_ratio, wx.IMAGE_QUALITY_HIGH)
        bmp = wx.BitmapFromImage(img)
        self.bitmap_art.SetBitmap(bmp)


if __name__ == '__main__':
    app = wx.App(redirect=None)
    frame = AddArtFrame(None)
    frame.Show(True)
    app.MainLoop()
