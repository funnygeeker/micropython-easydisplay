# 这是一个使用示例 This is an example of usage
import time
from machine import SPI, Pin
from driver import st7735_buf
from lib.easydisplay import EasyDisplay

# ESP32S3 & ST7735
spi = SPI(1, baudrate=20000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(17))
dp = st7735_buf.ST7735(width=128, height=128, spi=spi, cs=14, dc=15, res=16, rotate=1, bl=13, invert=False, rgb=False)
ed = EasyDisplay(dp, "RGB565", font="/text_lite_16px_2312.v3.bmf", show=True, color=0xFFFF, clear=True)

ed.bmp("/img/test.bmp", 0, 0)
time.sleep(3)
ed.pbm("/img/test.pbm", 0, 0)
time.sleep(3)
ed.text("你好，世界！\nHello World!\nこんにちは、世界！", 0, 0)

# 更多高级使用方式详见源码注释：/lib/easydisplay.py
# For more advanced usage, please refer to the source code comments: /lib/easydisplay.py