from smbus2 import SMBus, i2c_msg
from PIL import Image, ImageDraw

from config import BATCH_CHUNK_SZ

class SSD1306Vals:
    CMD_PREFIX =           0x00
    DATA_PREFIX =          0x40

    MEMORY_MODE =          0x20
    COL_ADDR =             0x21
    PAGE_ADDR =            0x22
    DISABLE_SCROLL =       0x2E
    SET_START_LINE =       0x40
    SET_CONTRAST =         0x81
    SET_CHARGE_PUMP =      0x8D
    SET_SEGMENT_REMAP =    0xA0
    DISPLAY_VRAM =         0xA4
    DISPLAY_FORCE_WHITE =  0xA5
    DISPLAY_NORMAL =       0xA6
    MULTIPLEX_RATIO =      0xA8
    DISPLAY_OFF =          0xAE
    DISPLAY_ON =           0xAF
    SET_COM_SCAN_DIR =     0xC8
    SET_DISPLAY_OFFSET =   0xD3
    SET_DISPLAY_CLK_DIV =  0xD5
    SET_PRECHARGE_PERIOD = 0xD9
    SET_COMPINS =          0xDA
    SET_VCOM_LEVEL =       0xDB
    CONT_RHOR_SCROLL =     0x29
    ACTIVATE_SCROLL =      0x2F

class SSD1306:
    def __init__(self, bus=0, addr=0x3C):
        # create interfacing objects
        self.bus = SMBus(bus)
        self.addr = addr
        self.last_fb = None

        # create PIL objects
        self.img = Image.new("1", (128, 64), 0)
        self.draw = ImageDraw.Draw(self.img)

        # initialize display
        self.cmd(SSD1306Vals.DISPLAY_OFF)
        self.cmd(SSD1306Vals.SET_DISPLAY_CLK_DIV, 0xf0)
        self.cmd(SSD1306Vals.MULTIPLEX_RATIO, 63)
        self.cmd(SSD1306Vals.SET_DISPLAY_OFFSET, 0)
        self.cmd(SSD1306Vals.SET_START_LINE | 0)
        self.cmd(SSD1306Vals.SET_CHARGE_PUMP, 0x14)
        self.cmd(SSD1306Vals.MEMORY_MODE, 0)
        self.cmd(SSD1306Vals.SET_SEGMENT_REMAP | 1)
        self.cmd(SSD1306Vals.SET_COM_SCAN_DIR)
        self.cmd(SSD1306Vals.SET_COMPINS, 0x12)
        self.cmd(SSD1306Vals.SET_CONTRAST, 0xff)
        self.cmd(SSD1306Vals.SET_PRECHARGE_PERIOD, 0x11)
        self.cmd(SSD1306Vals.SET_VCOM_LEVEL, 0x30)
        self.cmd(SSD1306Vals.DISPLAY_VRAM)
        self.cmd(SSD1306Vals.DISPLAY_NORMAL)
        self.cmd(SSD1306Vals.DISABLE_SCROLL)
        self.cmd(SSD1306Vals.DISPLAY_ON)

        # black
        self.flip()

    def cmd(self, cmd, *args):
        self.bus.write_i2c_block_data(self.addr, SSD1306Vals.CMD_PREFIX, [cmd] + list(args))
    def batch(self, batch):
        for i in range(0, len(batch), BATCH_CHUNK_SZ):
            chunk = batch[i : i + BATCH_CHUNK_SZ]
            self.bus.i2c_rdwr(*[i2c_msg.write(self.addr, bytes(buf)) for buf in chunk])

    def flip(self, optimize_transfer=True):
        optimize_transfer = optimize_transfer and self.last_fb

        # create framebuffer
        fb = bytearray([0] * (128 * 64 // 8))

        # convert PIL image data into framebuffer data
        for coord, pix in enumerate(self.img.getdata()):
            x, y = coord % 128, coord // 128
            idx, shift = x + ((y // 8) * 128), y & 0x7
            if pix == 1:
                fb[idx] |= 1 << shift
            else:
                fb[idx] &= ~(1 << shift)

        # construct transfers
        transfer = []
        if optimize_transfer:
            # find contiguous blocks of change that do not cross the page boundary
            changed = [fb[i] != self.last_fb[i] for i in range(len(fb))]
            for i in range(8):
                page_offs = 128 * i
                blocks_of_change = []
                page = changed[page_offs : page_offs + 128]
                first_in_blk = None
                for j, c in enumerate(page):
                    if c and (first_in_blk is None):
                        first_in_blk = j
                    if (first_in_blk is not None) and (not c):
                        blocks_of_change.append((first_in_blk, j))
                        first_in_blk = None
                    if j == 127 and (first_in_blk is not None):
                        blocks_of_change.append((first_in_blk, j + 1))

                # chunk blocks by 8 bytes
                blk_chunks = []
                for blk in blocks_of_change:
                    start, end = blk
                    for j in range(start, end, 8):
                        blk_chunks.append((j, min(j + 8, end)))

                # construct transfer for page
                transfer.append([SSD1306Vals.CMD_PREFIX, SSD1306Vals.PAGE_ADDR, i, i])
                last_col = None
                for start, end in blk_chunks:
                    if start != last_col:
                        transfer.append([SSD1306Vals.CMD_PREFIX, SSD1306Vals.COL_ADDR, start, 0x7F])
                    transfer.append(bytes([SSD1306Vals.DATA_PREFIX]) + fb[page_offs + start : page_offs + end])
                    last_col = end
        else:
            # no optimizations
            # still pretty fast, about 7.8FPS @ 100kHz
            transfer.append([SSD1306Vals.CMD_PREFIX, SSD1306Vals.PAGE_ADDR, 0, 0x07])
            transfer.append([SSD1306Vals.CMD_PREFIX, SSD1306Vals.COL_ADDR, 0, 0x7F])
            for i in range(0, 128 * 64 // 8, 8):
                transfer.append(bytes([SSD1306Vals.DATA_PREFIX]) + fb[i : i + 8])
            
        # perform transfer
        self.batch(transfer)

        # remember last framebuffer
        self.last_fb = fb

        return sum([len(arr) for arr in transfer]), 1160 # transfer size, max transfer size

    def power(self, val):
        self.cmd(SSD1306Vals.DISPLAY_ON if val else SSD1306Vals.DISPLAY_OFF)

    def sleep_mode(self, sleep):
        # low brightness
        self.cmd(SSD1306Vals.SET_CONTRAST, 0x00 if sleep else 0xff)

        # continuous hardware horizontal scrolling
        self.cmd(SSD1306Vals.DISABLE_SCROLL)
        if sleep:
            self.cmd(SSD1306Vals.CONT_RHOR_SCROLL,
                     0, # dummy byte
                     0, # starting page
                     7, # 2 frames between each scroll
                     7, # ending page
                     0, # no vertical scroll
                     )
            self.cmd(SSD1306Vals.ACTIVATE_SCROLL)
