# 来源：https://pypi.org/project/micropython-ssd1306/
# MicroPython SSD1306 OLED driver, I2C and SPI interfaces
import math
import framebuf
from machine import Pin
from micropython import const

# register definitions
SET_CONTRAST = const(0x81)
SET_ENTIRE_ON = const(0xA4)
SET_NORM_INV = const(0xA6)
SET_DISP = const(0xAE)
SET_MEM_ADDR = const(0x20)
SET_COL_ADDR = const(0x21)
SET_PAGE_ADDR = const(0x22)
SET_DISP_START_LINE = const(0x40)
SET_SEG_REMAP = const(0xA0)
SET_MUX_RATIO = const(0xA8)
SET_COM_OUT_DIR = const(0xC0)
SET_DISP_OFFSET = const(0xD3)
SET_COM_PIN_CFG = const(0xDA)
SET_DISP_CLK_DIV = const(0xD5)
SET_PRECHARGE = const(0xD9)
SET_VCOM_DESEL = const(0xDB)
SET_CHARGE_PUMP = const(0x8D)


# Subclassing FrameBuffer provides support for graphics primitives
# http://docs.micropython.org/en/latest/pyboard/library/framebuf.html
class SSD1306(framebuf.FrameBuffer):
    def __init__(self, width, height, external_vcc, rotate=0):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()
        self.rotate(rotate)

    def init_display(self):
        for cmd in (
                SET_DISP | 0x00,  # off
                # address setting
                SET_MEM_ADDR, 0x00,  # horizontal
                # resolution and layout
                SET_DISP_START_LINE | 0x00,
                SET_SEG_REMAP | 0x01,  # column addr 127 mapped to SEG0
                SET_MUX_RATIO,
                self.height - 1,
                SET_COM_OUT_DIR | 0x08,  # scan from COM[N] to COM0
                SET_DISP_OFFSET, 0x00,
                SET_COM_PIN_CFG,
                0x02 if self.width > 2 * self.height else 0x12,
                # timing and driving scheme
                SET_DISP_CLK_DIV, 0x80,
                SET_PRECHARGE,
                0x22 if self.external_vcc else 0xF1,
                SET_VCOM_DESEL, 0x30,  # 0.83*Vcc
                # display
                SET_CONTRAST,
                0xFF,  # maximum
                SET_ENTIRE_ON,  # output follows RAM contents
                SET_NORM_INV,  # not inverted
                # charge pump
                SET_CHARGE_PUMP,
                0x10 if self.external_vcc else 0x14,
                SET_DISP | 0x01,
        ):  # on
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def poweroff(self):
        self.write_cmd(SET_DISP | 0x00)

    def poweron(self):
        self.write_cmd(SET_DISP | 0x01)

    def contrast(self, contrast):
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast)

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
        self.write_cmd(SET_SEG_REMAP | (0x01 if mir_v else 0x00))
        self.write_cmd(SET_COM_OUT_DIR | (0x08 if mir_h else 0x00))
        self.show()

    def invert(self, invert):
        """
        Invert mode, If true, switch to invert mode (black-on-white), else normal mode (white-on-black)
        """
        self.write_cmd(SET_NORM_INV | (invert & 1))

    def show(self):
        x0 = 0
        x1 = self.width - 1
        if self.width == 64:
            # displays with width of 64 pixels are shifted by 32
            x0 += 32
            x1 += 32
        self.write_cmd(SET_COL_ADDR)
        self.write_cmd(x0)
        self.write_cmd(x1)
        self.write_cmd(SET_PAGE_ADDR)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_data(self.buffer)

    def back_light(self, value):
        """
        背光调节

        Args:
            value: 背光等级 0 ~ 255
        """
        self.contrast(value)

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


class SSD1306_I2C(SSD1306):
    def __init__(self, width, height, i2c, addr=0x3C, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        self.write_list = [b"\x40", None]  # Co=0, D/C#=1
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80  # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_data(self, buf):
        self.write_list[1] = buf
        self.i2c.writevto(self.addr, self.write_list)


class SSD1306_SPI(SSD1306):
    def __init__(self, width, height, spi, dc, res, cs, external_vcc=False):
        self.rate = 10 * 1024 * 1024
        self.res = Pin(res, Pin.OUT, Pin.PULL_DOWN)
        self.dc = Pin(dc, Pin.OUT, Pin.PULL_DOWN)
        if cs is None:
            self.cs = int
        else:
            self.cs = Pin(cs, Pin.OUT, Pin.PULL_DOWN)
        self.spi = spi
        self.dc = dc
        self.res = res
        self.cs = cs
        import time
        self.res(1)
        time.sleep_ms(1)
        self.res(0)
        time.sleep_ms(10)
        self.res(1)
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(buf)
        self.cs(1)
