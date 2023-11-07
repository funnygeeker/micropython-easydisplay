[English (英语)](https://github.com/funnygeeker/micropython-easydisplay/blob/main/README.md)

# micropython-easydisplay
- 适用于 `Micropython` 的：高通用性，多功能，纯 `Micropython` 实现的显示库
- 自用，顺便开源，希望能够推动 `Micropython` 生态的发展


### 显示效果
以下为 `2.0` 版本的显示效果
![IMG_20231107_235742](https://github.com/funnygeeker/micropython-easydisplay/assets/96659329/f76a7713-7397-4a99-8ccd-37af7ebe0cbe)
![IMG_20231107_004226](https://github.com/funnygeeker/micropython-easydisplay/assets/96659329/e765b55a-45bb-486a-b15e-5161b4d876fa)
![IMG_20231107_004229](https://github.com/funnygeeker/micropython-easydisplay/assets/96659329/f82910c4-b515-4ffd-a00c-9eafffcbb0bf)

### 项目特点
- 可以通过导入 `bmf` 字体文件，显示非 `ASCII` 字符，比如：中文 和 特殊符号
- 支持 `P4`/`P6` 格式的 `PBM` 图片显示，以及 `24-bit` 的 `BMP` 图片显示
- 初始化时可以设置默认参数，调用函数时更简洁，同时调用指定函数时，本次调用可覆盖默认参数
- 兼容大多数 `MicroPython` 官方和非官方版本，纯 `MicroPython` 原生实现，不需要进行固件编译，同时尽可能保持了高效率
- 支持多种屏幕的多种工作模式 `SSD1306`，`ST7735`，`ST7789`，支持低内存开发板驱动高分辨率屏幕（如 `ESP32C3` 驱动 `240*240` `ST7789`）

### 使用方法
- 详见源码注释

### 示例代码
```python
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
```

### 特别致谢
参考项目：

中文显示：[https://github.com/AntonVanke/MicroPython-Chinese-Font](https://github.com/AntonVanke/MicroPython-Chinese-Font)

BMP图片显示：[https://github.com/boochow/MicroPython-ST7735/blob/master/tftbmp.py](https://github.com/boochow/MicroPython-ST7735/blob/master/tftbmp.py)


### 参考资料
PBM图像显示：[https://www.bilibili.com/video/av798158808/](https://www.bilibili.com/video/av798158808/)

PBM文件格式：[https://www.cnblogs.com/SeekHit/p/7055748.html](https://www.cnblogs.com/SeekHit/p/7055748.html)

PBM文件转换：[https://blog.csdn.net/jd3096/article/details/121319042](https://blog.csdn.net/jd3096/article/details/121319042)

灰度化、二值化：[https://blog.csdn.net/li_wen01/article/details/72867057](https://blog.csdn.net/li_wen01/article/details/72867057)


### 其他
感谢各位大佬对开源做出的贡献！

交流QQ群：[748103265](https://jq.qq.com/?_wv=1027&k=I74bKifU)
