# 这是一个使用示例 This is an example of usage
import time
import framebuf
from machine import SPI, Pin
from drivers import st7735_buf
from libs.easydisplay import EasyDisplay

# ESP32C3 & ST7735
spi = SPI(1, baudrate=20000000, polarity=0, phase=0, sck=Pin(19), mosi=Pin(18))
dp = st7735_buf.ST7735(width=160, height=128, spi=spi, cs=0, dc=1, rst=11, rotation=1)
ed = EasyDisplay(display=dp, font="/text_lite_16px_2311.v3.bmf", show=True, color=0xFFFF, clear=True,
                 color_type=framebuf.RGB565, text_half_char=True, text_auto_wrap=True)

ed.bmp("/img/test.bmp", 0, 0)
time.sleep(3)
ed.pbm("/img/test.pbm", 0, 0, color_type=framebuf.MONO_HLSB)
time.sleep(3)
ed.text("你好，世界！\nHello World!\nこんにちは、世界！", 0, 0)


# 更多高级使用方式详见源码注释：/libs/easydisplay.py