[简体中文 (Chinese)](https://github.com/funnygeeker/micropython-easydisplay/blob/main/README.ZH-CN.md)

# micropython-easydisplay
- A display library for `Micropython`: high versatility, multifunctionality, implemented purely in `Micropython`.
-  This `README` may contain translations that are not entirely accurate.

### Display Effects
The following are the display effects of version `2.0`.
![IMG_20231107_235742](https://github.com/funnygeeker/micropython-easydisplay/assets/96659329/f76a7713-7397-4a99-8ccd-37af7ebe0cbe)
![IMG_20231107_004226](https://github.com/funnygeeker/micropython-easydisplay/assets/96659329/e765b55a-45bb-486a-b15e-5161b4d876fa)
![IMG_20231107_004229](https://github.com/funnygeeker/micropython-easydisplay/assets/96659329/f82910c4-b515-4ffd-a00c-9eafffcbb0bf)

### Project Features
- Ability to display non-ASCII characters, such as Chinese and special symbols, by importing `bmf` font files.
- Supports displaying `PBM` images in `P4`/`P6` format and `BMP` images in `24-bit`.
- Default parameters can be set during initialization, making function calls more concise. Additionally, the current function call can override the default parameters.
- Compatible with most official and unofficial versions of `MicroPython`. It is implemented purely with native `MicroPython` and does not require firmware compilation. Additionally, it maintains high efficiency as much as possible.
- Supports multiple screen models such as `SSD1306`, `ST7735`, and `ST7789`. It also supports driving high-resolution screens on low-memory development boards (e.g., `ESP32C3` driving `240*240 ST7789` screens).

### Usage
- Please refer to the source code comments.（The comments section is written in Chinese and may need translation in order to read.）

### Note
For images in the `dat` format, make sure that they do not exceed the screen display area when using non-framebuffer driver modes. Otherwise, the image may not be displayed correctly.

### Example Code
```python
# This is an example of usage
import time
import framebuf
from machine import SPI, Pin
from drivers import st7735_buf
from libs.easydisplay import EasyDisplay

# ESP32C3 & ST7735
spi = SPI(1, baudrate=20000000, polarity=0, phase=0, sck=Pin(19), mosi=Pin(18))
dp = st7735_buf.ST7735(width=160, height=128, spi=spi, cs=0, dc=1, rst=11, rotation=1)
ed = EasyDisplay(display=dp, font="/text_lite_16px_2311.v3.bmf", show=True, color=0xFFFF, clear=True,
                 color_type=framebuf.RGB565, auto_wrap=True)

ed.bmp("/img/test.bmp", 0, 0)
time.sleep(3)
ed.pbm("/img/test.pbm", 0, 0, color_type=framebuf.MONO_HLSB)
time.sleep(3)
ed.text("你好，世界！\nHello World!\nこんにちは、世界！", 0, 0)

# For more advanced usage, please refer to the source code comments: /libs/easydisplay.py
```

### Special Thanks
Reference projects:

Chinese display: [https://github.com/AntonVanke/MicroPython-Chinese-Font](https://github.com/AntonVanke/MicroPython-Chinese-Font)

BMP image display: [https://github.com/boochow/MicroPython-ST7735/blob/master/tftbmp.py](https://github.com/boochow/MicroPython-ST7735/blob/master/tftbmp.py)

### References
PBM image display: [https://www.bilibili.com/video/av798158808/](https://www.bilibili.com/video/av798158808/)

PBM file format: [https://www.cnblogs.com/SeekHit/p/7055748.html](https://www.cnblogs.com/SeekHit/p/7055748.html)

PBM file conversion: [https://blog.csdn.net/jd3096/article/details/121319042](https://blog.csdn.net/jd3096/article/details/121319042)

Grayscale, binarization: [https://blog.csdn.net/li_wen01/article/details/72867057](https://blog.csdn.net/li_wen01/article/details/72867057)

### Others
Thanks to all contributors for their contributions to open source!
