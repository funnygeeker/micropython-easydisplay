# 这是一个使用示例
import time
import framebuf
from drivers import st7735
from machine import SPI, Pin
from libs.easydisplay import EasyDisplay


spi = SPI(1, baudrate=20000000, polarity=0, phase=0, sck=Pin(1), mosi=Pin(0))
dp = st7735.ST7735(width=160, height=128, spi=spi, cs=Pin(19), dc=Pin(18), rst=Pin(3), rot=1)
ed = EasyDisplay(display=dp, font_file="/fonts/harmonyos_sans/harmonyos16.bmf", show=True, font_color=0xFFFF, clear=True,
                 img_format=framebuf.RGB565, img_color=0xFFFF)

ed.bmp("/img/test.bmp", 0, 0)
time.sleep(3)
ed.pbm("/img/test.pbm", 0, 0, format=framebuf.MONO_HLSB)
time.sleep(3)
ed.text("测试一下\nTest\nテスト", 0, 0)

# 更多高级使用方式详见源码注释：/libs/easydisplay.py
