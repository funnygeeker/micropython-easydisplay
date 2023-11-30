import math
import framebuf
import utime as time
from micropython import const

# a few register definitions
_SET_CONTRAST = const(0x81)
_SET_NORM_INV = const(0xa6)
_SET_DISP = const(0xae)
_SET_SCAN_DIR = const(0xc0)
_SET_SEG_REMAP = const(0xa0)
_LOW_COLUMN_ADDRESS = const(0x00)
_HIGH_COLUMN_ADDRESS = const(0x10)
_SET_PAGE_ADDRESS = const(0xB0)


class SH1106(framebuf.FrameBuffer):
    def __init__(self, width, height, external_vcc, rotate=0):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.flip_en = rotate == 180 or rotate == 270
        self.rotate90 = rotate == 90 or rotate == 270
        self.pages = self.height // 8
        self.bufsize = self.pages * self.width
        self.buffer = bytearray(self.bufsize)
        self.pages_to_update = 0

        if self.rotate90:
            self.displaybuf = bytearray(self.bufsize)
            # HMSB is required to keep the bit order in the render buffer
            # compatible with byte-for-byte remapping to the display buffer,
            # which is in VLSB. Else we'd have to copy bit-by-bit!
            super().__init__(self.buffer, self.height, self.width,
                             framebuf.MONO_HMSB)
        else:
            self.displaybuf = self.buffer
            super().__init__(self.buffer, self.width, self.height,
                             framebuf.MONO_VLSB)

        # flip() was called rotate() once, provide backwards compatibility.
        self.rotate = self.flip
        self.init_display()
        self.back_light(255)

    def init_display(self):
        self.reset()
        self.fill(0)
        self.show()
        self.poweron()
        # rotate90 requires a call to flip() for setting up.
        self.flip(self.flip_en)

    def poweroff(self):
        self.write_cmd(_SET_DISP | 0x00)

    def poweron(self):
        self.write_cmd(_SET_DISP | 0x01)
        if self.delay:
            time.sleep_ms(self.delay)

    def flip(self, flag=None, update=True):
        if flag is None:
            flag = not self.flip_en
        mir_v = flag ^ self.rotate90
        mir_h = flag
        self.write_cmd(_SET_SEG_REMAP | (0x01 if mir_v else 0x00))
        self.write_cmd(_SET_SCAN_DIR | (0x08 if mir_h else 0x00))
        self.flip_en = flag
        if update:
            self.show(True)  # full update

    def sleep(self, value):
        self.write_cmd(_SET_DISP | (not value))

    def contrast(self, contrast):
        self.write_cmd(_SET_CONTRAST)
        self.write_cmd(contrast)

    def back_light(self, value):
        """
        背光调节

        Args:
            value: 背光等级 0 ~ 255
        """
        self.contrast(value)

    def rotate(self, rotate):
        """
        设置显示旋转

        Args:
            rotate(int):
                - 0-Portrait
                - 1-Upper right printing left (backwards) (X Flip)
                - 2-Inverted Portrait
                - 3-Lower left printing up (backwards) (Y Flip)
        """
        rotate %= 4
        mir_v = False
        mir_h = False
        if rotate == 0:
            mir_v = True
            mir_h = True
        elif rotate == 1:
            mir_h = True
        elif rotate == 2:
            pass
        elif rotate == 3:
            mir_v = True
        self.write_cmd(_SET_SEG_REMAP | (0x01 if mir_v else 0x00))
        self.write_cmd(_SET_SCAN_DIR | (0x08 if mir_h else 0x00))
        self.show()

    def invert(self, invert):
        """
        Invert mode, If true, switch to invert mode (black-on-white), else normal mode (white-on-black)
        """
        self.write_cmd(_SET_NORM_INV | (invert & 1))

    def show(self, full_update=False):
        # self.* lookups in loops take significant time (~4fps).
        (w, p, db, rb) = (self.width, self.pages,
                          self.displaybuf, self.buffer)
        if self.rotate90:
            for i in range(self.bufsize):
                db[w * (i % p) + (i // p)] = rb[i]
        if full_update:
            pages_to_update = (1 << self.pages) - 1
        else:
            pages_to_update = self.pages_to_update
        # print("Updating pages: {:08b}".format(pages_to_update))
        for page in range(self.pages):
            if (pages_to_update & (1 << page)):
                self.write_cmd(_SET_PAGE_ADDRESS | page)
                self.write_cmd(_LOW_COLUMN_ADDRESS | 2)
                self.write_cmd(_HIGH_COLUMN_ADDRESS | 0)
                self.write_data(db[(w * page):(w * page + w)])
        self.pages_to_update = 0

    def pixel(self, x, y, color=None):
        if color is None:
            return super().pixel(x, y)
        else:
            super().pixel(x, y, color)
            page = y // 8
            self.pages_to_update |= 1 << page

    def text(self, text, x, y, color=1):
        super().text(text, x, y, color)
        self.register_updates(y, y + 7)

    def line(self, x0, y0, x1, y1, color):
        super().line(x0, y0, x1, y1, color)
        self.register_updates(y0, y1)

    def hline(self, x, y, w, color):
        super().hline(x, y, w, color)
        self.register_updates(y)

    def vline(self, x, y, h, color):
        super().vline(x, y, h, color)
        self.register_updates(y, y + h - 1)

    def fill(self, color):
        super().fill(color)
        self.pages_to_update = (1 << self.pages) - 1

    def blit(self, fbuf, x, y, key=-1, palette=None):
        super().blit(fbuf, x, y, key, palette)
        self.register_updates(y, y + self.height)

    def scroll(self, x, y):
        # my understanding is that scroll() does a full screen change
        super().scroll(x, y)
        self.pages_to_update = (1 << self.pages) - 1

    def fill_rect(self, x, y, w, h, color):
        super().fill_rect(x, y, w, h, color)
        self.register_updates(y, y + h - 1)

    def rect(self, x, y, w, h, color):
        super().rect(x, y, w, h, color)
        self.register_updates(y, y + h - 1)

    def circle(self, x, y, radius, c, section=100):
        """
        画圆

        Args:
            c: 颜色
            x: 中心 x 坐标
            y: 中心 y 坐标
            radius: 半径
            section: 分段
        """
        arr = []
        for m in range(section + 1):
            _x = round(radius * math.cos((2 * math.pi / section) * m - math.pi) + x)
            _y = round(radius * math.sin((2 * math.pi / section) * m - math.pi) + y)
            arr.append([_x, _y])
        for i in range(len(arr) - 1):
            self.line(*arr[i], *arr[i + 1], c)

    def fill_circle(self, x, y, radius, c):
        """
        画填充圆

        Args:
            c: 颜色
            x: 中心 x 坐标
            y: 中心 y 坐标
            radius: 半径
        """
        rsq = radius * radius
        for _x in range(radius):
            _y = int(math.sqrt(rsq - _x * _x))  # 计算 y 坐标
            y0 = y - _y
            end_y = y0 + _y * 2
            y0 = max(0, min(y0, self.height))  # 将 y0 限制在画布的范围内
            length = abs(end_y - y0) + 1
            self.vline(x + _x, y0, length, c)  # 绘制左右两侧的垂直线
            self.vline(x - _x, y0, length, c)

    def register_updates(self, y0, y1=None):
        # this function takes the top and optional bottom address of the changes made
        # and updates the pages_to_change list with any changed pages
        # that are not yet on the list
        start_page = max(0, y0 // 8)
        end_page = max(0, y1 // 8) if y1 is not None else start_page
        # rearrange start_page and end_page if coordinates were given from bottom to top
        if start_page > end_page:
            start_page, end_page = end_page, start_page
        for page in range(start_page, end_page + 1):
            self.pages_to_update |= 1 << page

    def reset(self, res):
        if res is not None:
            res(1)
            time.sleep_ms(1)
            res(0)
            time.sleep_ms(20)
            res(1)
            time.sleep_ms(20)


class SH1106_I2C(SH1106):
    def __init__(self, width, height, i2c, res=None, addr=0x3c,
                 rotate=0, external_vcc=False, delay=0):
        self.i2c = i2c
        self.addr = addr
        self.res = res
        self.temp = bytearray(2)
        self.delay = delay
        if res is not None:
            res.init(res.OUT, value=1)
        super().__init__(width, height, external_vcc, rotate)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80  # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_data(self, buf):
        self.i2c.writeto(self.addr, b'\x40' + buf)

    def reset(self):
        super().reset(self.res)


class SH1106_SPI(SH1106):
    def __init__(self, width, height, spi, dc, res=None, cs=None,
                 rotate=0, external_vcc=False, delay=0):
        dc.init(dc.OUT, value=0)
        if res is not None:
            res.init(res.OUT, value=0)
        if cs is not None:
            cs.init(cs.OUT, value=1)
        self.spi = spi
        self.dc = dc
        self.res = res
        self.cs = cs
        self.delay = delay
        super().__init__(width, height, external_vcc, rotate)

    def write_cmd(self, cmd):
        if self.cs is not None:
            self.cs(1)
            self.dc(0)
            self.cs(0)
            self.spi.write(bytearray([cmd]))
            self.cs(1)
        else:
            self.dc(0)
            self.spi.write(bytearray([cmd]))

    def write_data(self, buf):
        if self.cs is not None:
            self.cs(1)
            self.dc(1)
            self.cs(0)
            self.spi.write(buf)
            self.cs(1)
        else:
            self.dc(1)
            self.spi.write(buf)

    def reset(self):
        super().reset(self.res)
