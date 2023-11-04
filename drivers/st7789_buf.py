# 适用于 ST7789 的 Framebuffer 驱动
# Github: https://github.com/funnygeeker/micropython-easydisplay
# Author: funnygeeker
# Licence: MIT
# Date: 2023/11/2
#
# 参考资料:
# https://github.com/russhughes/st7789py_mpy/
# https://github.com/AntonVanke/MicroPython-uFont
import gc
import time
import math
import struct
import framebuf
from machine import Pin, PWM
from micropython import const

# commands
ST7789_NOP = const(0x00)
ST7789_SWRESET = const(0x01)
ST7789_RDDID = const(0x04)
ST7789_RDDST = const(0x09)

ST7789_SLPIN = const(0x10)
ST7789_SLPOUT = const(0x11)
ST7789_PTLON = const(0x12)
ST7789_NORON = const(0x13)

ST7789_INVOFF = const(0x20)
ST7789_INVON = const(0x21)
ST7789_DISPOFF = const(0x28)
ST7789_DISPON = const(0x29)
ST7789_CASET = const(0x2A)
ST7789_RASET = const(0x2B)
ST7789_RAMWR = const(0x2C)
ST7789_RAMRD = const(0x2E)

ST7789_PTLAR = const(0x30)
ST7789_VSCRDEF = const(0x33)
ST7789_COLMOD = const(0x3A)
ST7789_MADCTL = const(0x36)
ST7789_VSCSAD = const(0x37)

ST7789_MADCTL_MY = const(0x80)
ST7789_MADCTL_MX = const(0x40)
ST7789_MADCTL_MV = const(0x20)
ST7789_MADCTL_ML = const(0x10)
ST7789_MADCTL_BGR = const(0x08)
ST7789_MADCTL_MH = const(0x04)
ST7789_MADCTL_RGB = const(0x00)

ST7789_RDID1 = const(0xDA)
ST7789_RDID2 = const(0xDB)
ST7789_RDID3 = const(0xDC)
ST7789_RDID4 = const(0xDD)

COLOR_MODE_65K = const(0x50)
COLOR_MODE_262K = const(0x60)
COLOR_MODE_12BIT = const(0x03)
COLOR_MODE_16BIT = const(0x05)
COLOR_MODE_18BIT = const(0x06)
COLOR_MODE_16M = const(0x07)
#
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

# Color definitions
BLACK = const(0x0000)
BLUE = const(0x001F)
RED = const(0xF800)
GREEN = const(0x07E0)
CYAN = const(0x07FF)
MAGENTA = const(0xF81F)
YELLOW = const(0xFFE0)
WHITE = const(0xFFFF)

_ENCODE_PIXEL = ">H"
_ENCODE_POS = ">HH"
_DECODE_PIXEL = ">BBB"

_BUFFER_SIZE = const(256)

_BIT7 = const(0x80)
_BIT6 = const(0x40)
_BIT5 = const(0x20)
_BIT4 = const(0x10)
_BIT3 = const(0x08)
_BIT2 = const(0x04)
_BIT1 = const(0x02)
_BIT0 = const(0x01)

# Rotation tables (width, height, xstart, ystart)[rotation % 4]

WIDTH_320 = [(240, 320, 0, 0),
             (320, 240, 0, 0),
             (240, 320, 0, 0),
             (320, 240, 0, 0)]  # 320x240 Untested
WIDTH_240 = [(240, 240, 0, 0),
             (240, 240, 0, 0),
             (240, 240, 80, 0),
             (240, 240, 0, 80)]  # 240x240
WIDTH_135 = [(135, 240, 52, 40),
             (240, 135, 40, 53),
             (135, 240, 53, 40),
             (240, 135, 40, 52)]  # 135x240 Untested

# MADCTL ROTATIONS[rotation % 4]
ROTATIONS = [0x00, 0x60, 0xc0, 0xa0]


def _encode_pos(x, y):
    """Encode a postion into bytes."""
    return struct.pack(_ENCODE_POS, x, y)


def _encode_pixel(c):
    """Encode a pixel color into bytes."""
    return struct.pack(_ENCODE_PIXEL, c)


class ST7789(framebuf.FrameBuffer):
    def __init__(self, width: int, height: int, spi, rst: int, dc: int,
                 cs: int = None, bl: int = None, rotation: int = 0, inversion: bool = True):
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
            rotation: 旋转图像，数值为 0-3
            inversion: 颜色反转
        """
        if height != 240 or width not in [320, 240, 135]:
            raise ValueError(
                "Unsupported display. 320x240, 240x240 and 135x240 are supported."
            )

        self.width = width
        self.height = height
        self.x_start = 0
        self.y_start = 0
        self.spi = spi
        self.rst = Pin(rst, Pin.OUT, Pin.PULL_DOWN)
        self.dc = Pin(dc, Pin.OUT, Pin.PULL_DOWN)
        if cs is not None:
            self.cs = Pin(cs, Pin.OUT, Pin.PULL_DOWN)
        else:
            self.cs = int
        if bl is not None:
            self.bl = PWM(Pin(bl, Pin.OUT))
            self.bl.duty(1023)
        else:
            self.bl = None
        self._rotation = rotation % 4

        self.hard_reset()
        self.soft_reset()
        self.sleep_mode(False)
        #
        time.sleep_us(300)
        self._write(FRMCTR1, bytearray([0x01, 0x2C, 0x2D]))
        self._write(FRMCTR2, bytearray([0x01, 0x2C, 0x2D]))
        self._write(FRMCTR3, bytearray([0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D]))
        time.sleep_us(10)
        self._write(INVCTR, bytearray([0x07]))
        self._write(PWCTR1, bytearray([0xA2, 0x02, 0x84]))
        self._write(PWCTR2, bytearray([0xC5]))
        self._write(PWCTR3, bytearray([0x0A, 0x00]))
        self._write(PWCTR4, bytearray([0x8A, 0x2A]))
        self._write(PWCTR5, bytearray([0x8A, 0xEE]))
        self._write(VMCTR1, bytearray([0x0E]))
        #
        self._set_color_mode(COLOR_MODE_65K | COLOR_MODE_16BIT)
        time.sleep_ms(50)
        self.rotation(self._rotation)
        self.inversion_mode(inversion)
        time.sleep_ms(10)
        self._write(ST7789_NORON)
        time.sleep_ms(10)
        self._write(ST7789_DISPON)
        time.sleep_ms(500)
        gc.collect()  # 垃圾收集
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)
        self.fill(0)

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
        """
        写命令

        Args:
            cmd: 命令内容
        """
        self.cs(0)
        self.dc(0)
        self.spi.write(bytes([cmd]))
        self.cs(1)

    def write_data(self, data):
        """
        写数据

        Args:
            data: 数据内容
        """
        self.cs(0)
        self.dc(1)
        self.spi.write(data)
        self.cs(1)

    def hard_reset(self):
        """
        Hard reset display.
        """
        self.cs(0)
        self.rst(1)
        time.sleep_ms(50)
        self.rst(0)
        time.sleep_ms(50)
        self.rst(1)
        time.sleep_ms(150)
        self.cs(1)

    def soft_reset(self):
        """
        Soft reset display.
        """
        self._write(ST7789_SWRESET)
        time.sleep_ms(150)

    def sleep_mode(self, value):
        """
        Enable or disable display sleep mode.

        Args:
            value (bool): if True enable sleep mode. if False disable sleep mode
        """
        if value:
            self._write(ST7789_SLPIN)
        else:
            self._write(ST7789_SLPOUT)

    def inversion_mode(self, value):
        """
        Enable or disable display inversion mode.

        Args:
            value (bool): if True enable inversion mode. if False disable
            inversion mode
        """
        if value:
            self._write(ST7789_INVON)
        else:
            self._write(ST7789_INVOFF)

    def _set_color_mode(self, mode):
        """
        Set display color mode.

        Args:
            mode (int): color mode
                COLOR_MODE_65K, COLOR_MODE_262K, COLOR_MODE_12BIT,
                COLOR_MODE_16BIT, COLOR_MODE_18BIT, COLOR_MODE_16M
        """
        self._write(ST7789_COLMOD, bytes([mode & 0x77]))

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
        madctl = ROTATIONS[rotation]
        if self.width == 320:
            table = WIDTH_320
        elif self.width == 240:
            table = WIDTH_240
        elif self.width == 135:
            table = WIDTH_135
        else:
            raise ValueError(
                "Unsupported display. 320x240, 240x240 and 135x240 are supported."
            )

        self.width, self.height, self.x_start, self.y_start = table[rotation]
        self._write(ST7789_MADCTL, bytes([madctl]))

    def _set_columns(self, start, end):
        """
        Send CASET (column address set) command to display.

        Args:
            start (int): column start address
            end (int): column end address
        """
        if start <= end <= self.width:
            self._write(ST7789_CASET, _encode_pos(
                start + self.x_start, end + self.x_start))

    def _set_rows(self, start, end):
        """
        Send RASET (row address set) command to display.

        Args:
            start (int): row start address
            end (int): row end address
       """
        if start <= end <= self.height:
            self._write(ST7789_RASET, _encode_pos(
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
        self._set_columns(x0, x1)
        self._set_rows(y0, y1)
        self._write(ST7789_RAMWR)

    def clear(self):
        """
        清屏
        """
        self.fill(0)

    def show(self):
        """
        显示
        """
        self.set_window(0, 0, self.width - 1, self.height - 1)  # 如果没有这行就会偏移
        self.write_data(self.buffer)

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
