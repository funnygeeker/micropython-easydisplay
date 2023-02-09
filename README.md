# micropython-easydisplay
适用于 micropython 的简易显示库（自用，顺便开源，测试图是自己画的）

#### 显示效果
![font_display](https://user-images.githubusercontent.com/96659329/217912388-32b67ae0-c586-426a-8409-15d66626af67.jpg)
![bmp_color_display](https://user-images.githubusercontent.com/96659329/217912256-576ae657-9355-4384-a8b3-1430f295f700.jpg)
![pbm_display](https://user-images.githubusercontent.com/96659329/217912280-92b902f8-b177-4b37-bc25-84ffdb13978b.jpg)


#### 适用范围
- 基于一些开源项目，对适用于 `MicroPython` 的一些常用的显示功能进行了整合和封装，采用 `Framebuf` 缓冲区的驱动才能够使用

- 可通过导入字库支持中文显示，支持 `P4`/`P6` 格式的 `PBM` 图片显示在黑白或彩色屏幕

- 已通过测试的屏幕：`SSD1306`，`ST7735`，已通过测试的开发板：`ESP32C3`

- 支持 24位彩色 BMP 图片显示在黑白或彩色屏幕

- 还可以反转需要显示的图片的颜色


#### 特别说明
一般情况下 `ESP32C3` 开发版配一套 `16px` 的字体就够了，真的没有必要传那么多到板子上面...


#### 使用方法
嗯，你们先看示例代码或者库源码吧...

详细的文档最近忙着没空写呢，至少我注释齐全的（无法理解的部分除外）...


#### 示例代码
```python
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
ed.font("测试一下\nTest\nテスト", 0, 0)

# 更多高级使用方式详见源码注释：/libs/easydisplay.py
```

#### 特别致谢
基于以下项目整合或二次开发，如需深入了解，请务必阅读：

中文显示：[https://github.com/AntonVanke/MicroPython-Chinese-Font](https://github.com/AntonVanke/MicroPython-Chinese-Font)

BMP图片显示：[https://github.com/boochow/MicroPython-ST7735/blob/master/tftbmp.py](https://github.com/boochow/MicroPython-ST7735/blob/master/tftbmp.py)


#### 参考资料
PBM图像显示：[https://www.bilibili.com/video/av798158808/](https://www.bilibili.com/video/av798158808/)

PBM文件格式：[https://www.cnblogs.com/SeekHit/p/7055748.html](https://www.cnblogs.com/SeekHit/p/7055748.html)

PBM文件转换：[https://blog.csdn.net/jd3096/article/details/121319042](https://blog.csdn.net/jd3096/article/details/121319042)

灰度化、二值化：[https://blog.csdn.net/li_wen01/article/details/72867057](https://blog.csdn.net/li_wen01/article/details/72867057)


#### 字体
使用 Mi Sans（小米），HarmonyOS Sans（鸿蒙），Smiley Sans（得意黑），Source Han Sans（思源）等商用字体的 ttf 格式进行生成的 bmf 格式

原始字体集来自：[https://github.com/AntonVanke/MicroPython-Chinese-Font/blob/master/text.txt](https://github.com/AntonVanke/MicroPython-Chinese-Font/blob/master/text.txt)

补充字体集来自：[https://github.com/shinchanZ/-3500-/blob/master/3500](https://github.com/shinchanZ/-3500-/blob/master/3500)

现在的字体文件能够显示日文啦！現在のフォントファイルは日本語を表示できるようになりました。


#### 其他
感谢各位大佬对开源做出的贡献！
