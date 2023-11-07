# 适用于 ST7735 的 Framebuffer 驱动
# Github: https://github.com/funnygeeker/micropython-easydisplay
# Author: funnygeeker
# Licence: MIT
# Date: 2023/11/2
#
# 参考资料:
# https://github.com/AntonVanke/micropython-ufont
# https://blog.csdn.net/weixin_57604547/article/details/120535485
# Forget....

import math
import framebuf
from struct import pack
from time import sleep_us, sleep_ms
from machine import Pin, PWM
from micropython import const

_ENCODE_PIXEL = ">H"
_ENCODE_POS = ">HH"
_DECODE_PIXEL = ">BBB"
_BUFFER_SIZE = const(256)


def _encode_pos(x, y):
    """Encode a postion into bytes."""
    return pack(_ENCODE_POS, x, y)


def _encode_pixel(c):
    """Encode a pixel color into bytes."""
    return pack(_ENCODE_PIXEL, c)


#   ST7735V registers definitions

SWRESET = const(0x01)
SLPOUT = const(0x11)
SLPIN = const(0x10)
NORON = const(0x13)

INVOFF = const(0x20)
INVON = const(0x21)
DISPON = const(0x29)
CASET = const(0x2A)
RASET = const(0x2B)
RAMWR = const(0x2C)

MADCTL = const(0x36)
COLMOD = const(0x3A)

FRMCTR1 = const(0xB1)
FRMCTR2 = const(0xB2)
FRMCTR3 = const(0xB3)

INVCTR = const(0xB4)

PWCTR1 = const(0xC0)
PWCTR2 = const(0xC1)
PWCTR3 = const(0xC2)
PWCTR4 = const(0xC3)
PWCTR5 = const(0xC4)
VMCTR1 = const(0xC5)

GMCTRP1 = const(0xE0)
GMCTRN1 = const(0xE1)

ROTATIONS = [0x00, 0x60, 0xC0, 0xA0]  # 旋转方向

BLACK = const(0x0000)
BLUE = const(0x001F)
RED = const(0xF800)
GREEN = const(0x07E0)
CYAN = const(0x07FF)
MAGENTA = const(0xF81F)
YELLOW = const(0xFFE0)
WHITE = const(0xFFFF)


class ST7735(framebuf.FrameBuffer):
    def __init__(self, width, height, spi, rst: int, dc: int, cs: int = None, bl: int = None,
                 offset: tuple = None, rotation=0, rgb=True):
        """
        初始化屏幕驱动

        Args:
            width: 宽度
            height: 高度
            spi: SPI 实例
            rst: RESET 引脚
            dc: Data / Command 引脚
            cs: 片选引脚
            bl: 背光引脚
            offset: 图像偏移 (x, y)，例如：(23, -1)
            rotation: 旋转图像，数值为 0-3
            rgb: 使用 RGB 颜色模式，而不是 BGR
        """
        # 根据方向自动设置偏移
        self.width = width
        self.height = height
        self.x_start = 0
        self.y_start = 0
        self.spi = spi
        self.rst = Pin(rst, Pin.OUT, Pin.PULL_DOWN)
        self.dc = Pin(dc, Pin.OUT, Pin.PULL_DOWN)
        if cs is None:
            self.cs = int
        else:
            self.cs = Pin(cs, Pin.OUT, Pin.PULL_DOWN)
        if bl is not None:
            self.bl = PWM(Pin(bl))
        self.offset = offset
        self._rotation = rotation % 4
        self.rgb = rgb
        if offset is None and rotation == 1:
            self.offset = (-1, 23)
        elif offset is None and rotation == 0:
            self.offset = (23, -1)
        self.init()
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565, self.width)
        self.clear()

    def init(self):
        self.hard_reset()
        self.soft_reset()
        self.sleep_mode(False)
        sleep_us(300)
        self.write_cmd(FRMCTR1)
        self.write_data(bytearray([0x01, 0x2C, 0x2D]))
        self.write_cmd(FRMCTR2)
        self.write_data(bytearray([0x01, 0x2C, 0x2D]))
        self.write_cmd(FRMCTR3)
        self.write_data(bytearray([0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D]))
        sleep_us(10)
        self.write_cmd(INVCTR)
        self.write_data(bytearray([0x07]))
        self.write_cmd(PWCTR1)
        self.write_data(bytearray([0xA2, 0x02, 0x84]))
        self.write_cmd(PWCTR2)
        self.write_data(bytearray([0xC5]))
        self.write_cmd(PWCTR3)
        self.write_data(bytearray([0x0A, 0x00]))
        self.write_cmd(PWCTR4)
        self.write_data(bytearray([0x8A, 0x2A]))
        self.write_cmd(PWCTR5)
        self.write_data(bytearray([0x8A, 0xEE]))
        self.write_cmd(VMCTR1)
        self.write_data(bytearray([0x0E]))
        self.inversion_mode(False)
        self.rotation(self._rotation)
        self.write_cmd(COLMOD)  # color mode
        self.write_data(bytearray([0x05]))
        self.write_cmd(GMCTRP1)
        self.write_data(
            bytearray([0x02, 0x1c, 0x07, 0x12, 0x37, 0x32, 0x29, 0x2d, 0x29, 0x25, 0x2b, 0x39, 0x00, 0x01, 0x03, 0x10]))
        self.write_cmd(GMCTRN1)
        self.write_data(
            bytearray([0x03, 0x1d, 0x07, 0x06, 0x2e, 0x2c, 0x29, 0x2d, 0x2e, 0x2e, 0x37, 0x3f, 0x00, 0x00, 0x02, 0x10]))
        self.write_cmd(NORON)
        sleep_us(10)
        self.write_cmd(DISPON)
        sleep_us(100)

    def _write(self, command=None, data=None):
        """SPI write to the device: commands and data."""
        self.cs(0)
        if command is not None:
            self.dc(0)
            self.spi.write(bytes([command]))
        if data is not None:
            self.dc(1)
            self.spi.write(data)
        self.cs(1)

    def write_cmd(self, cmd):
        self.cs(0)
        self.dc(0)
        self.spi.write(bytes([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(0)
        self.dc(1)
        self.spi.write(buf)
        self.cs(1)

    def hard_reset(self):
        """
        Hard reset display.
        """
        self.cs(0)
        self.rst(1)
        sleep_ms(50)
        self.rst(0)
        sleep_ms(50)
        self.rst(1)
        sleep_ms(150)
        self.cs(1)

    def soft_reset(self):
        """
        Soft reset display.
        """
        self._write(SWRESET)
        sleep_ms(150)

    def sleep_mode(self, value):
        """
        Enable or disable display sleep mode.

        Args:
            value (bool): if True enable sleep mode. if False disable sleep mode
        """
        if value:
            self._write(SLPIN)
        else:
            self._write(SLPOUT)

    def inversion_mode(self, value):
        """
        Enable or disable display inversion mode.

        Args:
            value (bool): if True enable inversion mode. if False disable
            inversion mode
        """
        if value:
            self._write(INVON)
        else:
            self._write(INVOFF)

    def rotation(self, rotation):
        """
        Set display rotation.

        Args:
            rotation (int):
                - 0-Portrait
                - 1-Landscape
                - 2-Inverted Portrait
                - 3-Inverted Landscape
        """
        rotation %= 4
        self._rotation = rotation
        self._write(MADCTL, bytearray([ROTATIONS[self._rotation] | 0x00 if self.rgb else 0x08]))

    def _set_columns(self, start, end):
        """
        Send CASET (column address set) command to display.

        Args:
            start (int): column start address
            end (int): column end address
        """
        if start <= end <= self.width:
            self._write(CASET, _encode_pos(
                start + self.x_start, end + self.x_start))

    def _set_rows(self, start, end):
        """
        Send RASET (row address set) command to display.

        Args:
            start (int): row start address
            end (int): row end address
       """
        if start <= end <= self.height:
            self._write(RASET, _encode_pos(
                start + self.y_start, end + self.y_start))

    def set_window(self, x0, y0, x1, y1):
        """
        Set window to column and row address.

        Args:
            x0 (int): column start address
            y0 (int): row start address
            x1 (int): column end address
            y1 (int): row end address
        """
        if x0 < self.width and y0 < self.height:
            self._set_columns(x0, x1)
            self._set_rows(y0, y1)
            self._write(RAMWR)

    def clear(self):
        """
        清屏
        """
        self.fill(0)

    def show(self):
        """
        将帧缓冲区数据发送到屏幕
        """
        if self.width == 80 or self.height == 80:
            if self._rotation == 0 or self._rotation == 2:
                self._write(CASET, pack(">HH", 26, self.width + 26 - 1))
                self._write(RASET, pack(">HH", 1, self.height + 1 - 1))
            else:
                self._write(CASET, pack(">HH", 1, self.width + 1 - 1))
                self._write(RASET, pack(">HH", 26, self.height + 26 - 1))
        else:
            if self._rotation == 0 or self._rotation == 2:
                self._write(CASET, pack(">HH", 0, self.width - 1))
                self._write(RASET, pack(">HH", 0, self.height - 1))
            else:
                self._write(CASET, pack(">HH", 0, self.width - 1))
                self._write(RASET, pack(">HH", 0, self.height - 1))
        self._write(RAMWR, self.buffer)

    # @staticmethod
    # def rgb(r, g, b):
    #     c = ((b & 0xF8) << 8) | ((g & 0xFC) << 3) | (r >> 3)
    #     return (c >> 8) | ((c & 0xFF) << 8)

    @staticmethod
    def color(r, g, b):
        """
        Convert red, green and blue values (0-255) into a 16-bit 565 encoding.
        """
        return (r & 0xf8) << 8 | (g & 0xfc) << 3 | b >> 3

    def back_light(self, value):
        """
        背光调节

        Args:
            value: 背光等级 0 ~ 255
        """
        self.bl.freq(1000)
        if value >= 0xff:
            value = 0xff
        data = value * 0xffff >> 8
        self.bl.duty_u16(data)

    def circle(self, center, radius, c, section=100):
        """
        画圆

        Args:
            c: 颜色
            center: 中心(x, y)
            radius: 半径
            section: 分段
        """
        arr = []
        for m in range(section + 1):
            x = round(radius * math.cos((2 * math.pi / section) * m - math.pi) + center[0])
            y = round(radius * math.sin((2 * math.pi / section) * m - math.pi) + center[1])
            arr.append([x, y])
        for i in range(len(arr) - 1):
            self.line(*arr[i], *arr[i + 1], c)

    def fill_circle(self, center, radius, c):
        """
        画填充圆

        Args:
            c: 颜色
            center: 中心(x, y)
            radius: 半径
        """
        rsq = radius * radius
        for x in range(radius):
            y = int(math.sqrt(rsq - x * x))  # 计算 y 坐标
            y0 = center[1] - y
            end_y = y0 + y * 2
            y0 = max(0, min(y0, self.height))  # 将 y0 限制在画布的范围内
            length = abs(end_y - y0) + 1
            self.vline(center[0] + x, y0, length, c)  # 绘制左右两侧的垂直线
            self.vline(center[0] - x, y0, length, c)
