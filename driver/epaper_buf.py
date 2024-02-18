# 适用于 E-Paper 的 Framebuffer 驱动
# Github: https://github.com/funnygeeker/micropython-easydisplay
# Author: funnygeeker
# Licence: MIT
# Date: 2024/2/17
#
# 参考资料:
# https://github.com/mcauser/micropython-waveshare-epaper
# https://github.com/AntonVanke/MicroPython-uFont/blob/master/driver/e1in54.py
import math
from struct import pack
from time import sleep_ms
from machine import Pin, PWM
from micropython import const
from framebuf import FrameBuffer, MONO_HLSB

# Display resolution
EPD_WIDTH  = const(200)
EPD_HEIGHT = const(200)

# Display commands
DRIVER_OUTPUT_CONTROL                = const(0x01)
BOOSTER_SOFT_START_CONTROL           = const(0x0C)
#GATE_SCAN_START_POSITION             = const(0x0F)
DEEP_SLEEP_MODE                      = const(0x10)
DATA_ENTRY_MODE_SETTING              = const(0x11)
#SW_RESET                             = const(0x12)
#TEMPERATURE_SENSOR_CONTROL           = const(0x1A)
MASTER_ACTIVATION                    = const(0x20)
#DISPLAY_UPDATE_CONTROL_1             = const(0x21)
DISPLAY_UPDATE_CONTROL_2             = const(0x22)
WRITE_RAM                            = const(0x24)
WRITE_VCOM_REGISTER                  = const(0x2C)
WRITE_LUT_REGISTER                   = const(0x32)
SET_DUMMY_LINE_PERIOD                = const(0x3A)
SET_GATE_TIME                        = const(0x3B) # not in datasheet
#BORDER_WAVEFORM_CONTROL              = const(0x3C)
SET_RAM_X_ADDRESS_START_END_POSITION = const(0x44)
SET_RAM_Y_ADDRESS_START_END_POSITION = const(0x45)
SET_RAM_X_ADDRESS_COUNTER            = const(0x4E)
SET_RAM_Y_ADDRESS_COUNTER            = const(0x4F)
TERMINATE_FRAME_READ_WRITE           = const(0xFF) # aka NOOP

BUSY = const(1)  # 1=busy, 0=idle

class EPD(FrameBuffer):
    LUT_FULL_UPDATE    = bytearray(b'\x02\x02\x01\x11\x12\x12\x22\x22\x66\x69\x69\x59\x58\x99\x99\x88\x00\x00\x00\x00\xF8\xB4\x13\x51\x35\x51\x51\x19\x01\x00')
    LUT_PARTIAL_UPDATE = bytearray(b'\x10\x18\x18\x08\x18\x18\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x13\x14\x44\x12\x00\x00\x00\x00\x00\x00')

    def __init__(self, width: int, height: int, spi, res: int, dc: int, busy:int,
                 cs: int = None, bl: int = None):
        """
        初始化屏幕驱动

        Args:
            width: 宽度
            height: 高度
            spi: SPI 实例
            res: RESET 引脚
            dc: Data / Command 引脚
            busy:
            cs: 片选引脚
            bl: 背光引脚
        """
        self.width = width
        self.height = height
        self.spi = spi
        self.res = Pin(res, Pin.OUT, Pin.PULL_DOWN, value=0)
        self.dc = Pin(dc, Pin.OUT, Pin.PULL_DOWN, value=0)
        self.busy = Pin(busy, Pin.IN)
        if cs is None:
            self.cs = int
        else:
            self.cs = Pin(cs, Pin.OUT, Pin.PULL_DOWN, value=1)
        if bl is not None:
            self.bl = PWM(Pin(bl, Pin.OUT))
            self.back_light(255)
        else:
            self.bl = None
        self.pages = self.height // 8
        self.buffer = bytearray(self.width * self.pages)
        super().__init__(self.buffer, self.width, self.height, MONO_HLSB)
        self.init()
        
    def init(self):
        self.hard_reset()
        self._write(DRIVER_OUTPUT_CONTROL)
        self.write_data(bytearray([(EPD_HEIGHT - 1) & 0xFF]))
        self.write_data(bytearray([((EPD_HEIGHT - 1) >> 8) & 0xFF]))
        self.write_data(bytearray([0x00])) # GD = 0 SM = 0 TB = 0
        self._write(BOOSTER_SOFT_START_CONTROL, b'\xD7\xD6\x9D')
        self._write(WRITE_VCOM_REGISTER, b'\xA8') # VCOM 7C
        self._write(SET_DUMMY_LINE_PERIOD, b'\x1A') # 4 dummy lines per gate
        self._write(SET_GATE_TIME, b'\x08') # 2us per line
        self._write(DATA_ENTRY_MODE_SETTING, b'\x03') # X increment Y increment
        self.set_lut(self.LUT_FULL_UPDATE)

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

    def wait_until_idle(self):
        while self.busy.value() == BUSY:
            sleep_ms(50)

    def hard_reset(self):
        """
        Hard reset display.
        """
        self.res(0)
        sleep_ms(100)
        self.res(1)
        sleep_ms(100)

    def soft_reset(self):
        # Function not realized
        pass

    def set_lut(self, lut):
        self._write(WRITE_LUT_REGISTER, lut)

    def set_refresh(self, full_update=True):
        """
        Set the refresh mode

        Args:
            full_update: Full screen refresh
        """
        self.set_lut(self.LUT_FULL_UPDATE) if full_update else self.set_lut(self.LUT_PARTIAL_UPDATE)

    # put an image in the frame memory
    def set_frame_memory(self, image, x, y, w, h):
        # x point must be the multiple of 8 or the last 3 bits will be ignored
        x = x & 0xF8
        w = w & 0xF8

        if x + w >= self.width:
            x_end = self.width - 1
        else:
            x_end = x + w - 1

        if y + h >= self.height:
            y_end = self.height - 1
        else:
            y_end = y + h - 1

        self.set_window(x, y, x_end, y_end)
        self.set_memory_pointer(x, y)
        self._write(WRITE_RAM, image)

    # replace the frame memory with the specified color
    def clear_frame_memory(self, color):
        self.set_window(0, 0, self.width - 1, self.height - 1)
        self.set_memory_pointer(0, 0)
        self._write(WRITE_RAM)
        # send the color data
        for i in range(0, self.width // 8 * self.height):
            self.write_data(bytearray([color]))

    # draw the current frame memory and switch to the next memory area
    def display_frame(self):
        self._write(DISPLAY_UPDATE_CONTROL_2, b'\xC4')
        self._write(MASTER_ACTIVATION)
        self._write(TERMINATE_FRAME_READ_WRITE)
        self.wait_until_idle()

    # specify the memory area for data R/W
    def set_memory_area(self, x_start, y_start, x_end, y_end):
        self._write(SET_RAM_X_ADDRESS_START_END_POSITION)
        # x point must be the multiple of 8 or the last 3 bits will be ignored
        self.write_data(bytearray([(x_start >> 3) & 0xFF]))
        self.write_data(bytearray([(x_end >> 3) & 0xFF]))
        self._write(SET_RAM_Y_ADDRESS_START_END_POSITION, pack("<HH", y_start, y_end))

    # specify the start point for data R/W
    def set_memory_pointer(self, x, y):
        self._write(SET_RAM_X_ADDRESS_COUNTER)
        # x point must be the multiple of 8 or the last 3 bits will be ignored
        self.write_data(bytearray([(x >> 3) & 0xFF]))
        self._write(SET_RAM_Y_ADDRESS_COUNTER, pack("<H", y))
        self.wait_until_idle()

    def clear(self):
        self.fill(0)


    def show(self):
        self.set_frame_memory(self.buffer, 0, 0, 200, 200)
        self.display_frame()

    # to wake call reset() or init()
    def poweroff(self):
        """Enable display sleep mode."""
        self._write(DEEP_SLEEP_MODE, b'\x01') # enter deep sleep A0=1, A0=0 power on
        self.wait_until_idle()

    def poweron(self):
        """Disable display sleep mode."""
        self.hard_reset()
        self.wait_until_idle()

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