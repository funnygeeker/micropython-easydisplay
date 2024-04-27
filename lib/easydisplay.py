# Github: https://github.com/funnygeeker/micropython-easydisplay
# Author: funnygeeker
# Licence: MIT
# Date: 2023/2/18
#
# 参考项目:
# https://github.com/AntonVanke/micropython-ufont
# https://github.com/boochow/MicroPython-ST7735/blob/master/tftbmp.py
#
# 参考资料:
# PBM图像显示：https://www.bilibili.com/video/av798158808
# PBM文件格式：https://www.cnblogs.com/SeekHit/p/7055748.html
# PBM文件转换：https://blog.csdn.net/jd3096/article/details/121319042
# 灰度化、二值化：https://blog.csdn.net/li_wen01/article/details/72867057
# Framebuffer 的 Palette: https://forum.micropython.org/viewtopic.php?t=12857
from io import BytesIO
from struct import unpack
from framebuf import FrameBuffer, MONO_HLSB, RGB565


class EasyDisplay:
    READ_SIZE = 32  # Limit the picture read size to prevent memory errors in low-performance development boards

    def __init__(self, display,
                 color_type,
                 font: str = None,
                 key: int = -1,
                 show: bool = None,
                 clear: bool = None,
                 invert: bool = False,
                 color: int = 0xFFFF,
                 bg_color: int = 0,
                 size: int = None,
                 auto_wrap: bool = False,
                 half_char: bool = True,
                 line_spacing: int = 0,
                 *args, **kwargs):
        """
        初始化 EasyDisplay

        Args:
            display: The display instance
                表示显示的实例
            color_type: Color type of screen, "MONO" or "RGB565"
                屏幕的颜色类型，"MONO" 或者 “RGB565”
            font: The location of the font file
                字体文件位置
            key: The specified color will be treated as transparent (only applicable for Framebuffer mode)
                指定的颜色将被视为透明（仅适用于 Framebuffer 模式）
            show: Show immediately (only applicable for Framebuffer mode)
                立即显示（仅适用于 Framebuffer 模式）
            clear: Clear the screen
                清理屏幕
            invert: Invert colors
                反转颜色
            color_type: Image format, "RGB565" for RGB565 screen, "MONO" for black and white screen
                图像格式，RGB565 屏幕用 "RGB565"，黑白 屏幕用 "MONO"
            color: The main color of the image (only effective when displaying black and white images on a color screen)
                图像主体颜色（仅彩色屏幕显示黑白图像时生效）
            bg_color: The background color of the image (only effective when displaying black and white images on a color screen)
                图像背景颜色（仅彩色屏幕显示黑白图像时生效）
            size: Font size
                文本字体大小
            auto_wrap: Automatically wrap text
                文本自动换行
            half_char: Display ASCII characters in half width
                半宽显示 ASCII 字符
            line_spacing: Line spacing for text
                文本行间距
        """
        self.display = display
        self._buffer = hasattr(display, 'buffer')  # buffer: 驱动是否使用了帧缓冲区，False（SPI 直接驱动） / True（Framebuffer）
        self._font = None
        self._key = key
        self._show = show
        self._clear = clear
        self.invert = invert
        self.color_type = color_type
        self.color = color
        self.bg_color = bg_color
        self.size = size
        self.auto_wrap = auto_wrap
        self.half_char = half_char
        self.line_spacing = line_spacing
        self.font_size = None
        self.font_bmf_info = None
        self.font_version = None
        self.font_file = None
        self.font_map_mode = None
        self.font_start_bitmap = None
        self.font_bitmap_size = None
        if font:
            self.load_font(font)

    # Framebuffer Function: https://docs.micropython.org/en/latest/library/framebuf.html
    def fill(self, *args, **kwargs):
        self.display.fill(*args, **kwargs)

    def pixel(self, *args, **kwargs):
        return self.display.pixel(*args, **kwargs)

    def hline(self, *args, **kwargs):
        self.display.hline(*args, **kwargs)

    def vline(self, *args, **kwargs):
        self.display.vline(*args, **kwargs)

    def line(self, *args, **kwargs):
        self.display.line(*args, **kwargs)

    def rect(self, *args, **kwargs):
        self.display.rect(*args, **kwargs)

    def fill_rect(self, *args, **kwargs):
        self.display.fill_rect(*args, **kwargs)

    def scroll(self, *args, **kwargs):
        self.display.scroll(*args, **kwargs)

    def blit(self, *args, **kwargs):
        self.display.blit(*args, **kwargs)

    def ellipse(self, *args, **kwargs):
        self.display.ellipse(*args, **kwargs)

    def poly(self, *args, **kwargs):
        self.display.poly(*args, **kwargs)

    # Only partial screen driver support
    def circle(self, *args, **kwargs):
        self.display.circle(*args, **kwargs)

    def fill_circle(self, *args, **kwargs):
        self.display.fill_circle(*args, **kwargs)

    def clear(self):
        """
        Clear screen
        """
        self.display.fill(0)

    def show(self):
        """
        Display
        """
        try:
            self.display.show()
        except AttributeError:
            pass

    @staticmethod
    def rgb565_color(r, g, b):
        """
        Convert red, green and blue values (0-255) into a 16-bit 565 encoding.
        """
        return (r & 0xf8) << 8 | (g & 0xfc) << 3 | b >> 3

    def _get_index(self, word: str) -> int:
        """
        Get Text Index 获取文字索引

        Args:
            word: Character 字符
        """
        word_code = ord(word)
        start = 0x10
        end = self.font_start_bitmap
        _seek = self._font.seek
        _font_read = self._font.read
        while start <= end:
            mid = ((start + end) // 4) * 2
            _seek(mid, 0)
            target_code = unpack(">H", _font_read(2))[0]
            if word_code == target_code:
                return (mid - 16) >> 1
            elif word_code < target_code:
                end = mid - 2
            else:
                start = mid + 2
        return -1

    # @timeit
    @staticmethod
    def _hlsb_font_size(bytearray_data: bytearray, new_size: int, old_size: int) -> bytearray:
        """
        Scale HLSB Characters 缩放字符

        Args:
            bytearray_data: Source char data 源字符数据
            new_size: New char size 新字符大小
            old_size: Old char size 旧字符大小

        Returns:
            Scaled character data 缩放后的数据
        """
        r = range(new_size)  # Preload functions to avoid repeated execution and improve efficiency
        if old_size == new_size:
            return bytearray_data
        _t = bytearray(new_size * ((new_size >> 3) + 1))
        _new_index = -1
        for _col in r:
            for _row in r:
                if _row % 8 == 0:
                    _new_index += 1
                _old_index = int(_col / (new_size / old_size)) * old_size + int(_row / (new_size / old_size))
                _t[_new_index] = _t[_new_index] | (
                        (bytearray_data[_old_index >> 3] >> (7 - _old_index % 8) & 1) << (7 - _row % 8))
        return _t

    def get_bitmap(self, word: str) -> bytes:
        """
        Get Dot Matrix Image 获取点阵图

        Args:
            word: Single character 单个字符

        Returns:
            Bytes representing the dot matrix image of the character 字符点阵
        """
        index = self._get_index(word)
        if index == -1:
            return b'\xff\xff\xff\xff\xff\xff\xff\xff\xf0\x0f\xcf\xf3\xcf\xf3\xff\xf3\xff\xcf\xff?\xff?\xff\xff\xff' \
                   b'?\xff?\xff\xff\xff\xff'  # Returns the question mark icon
        self._font.seek(self.font_start_bitmap + index * self.font_bitmap_size, 0)
        return self._font.read(self.font_bitmap_size)

    def load_font(self, file: str):
        """
        Load Font File 加载字体文件

        Args:
            file: Path to the font file 文件路径
        """
        self.font_file = file
        self._font = open(file, "rb")
        # 获取字体文件信息
        #  字体文件信息大小 16 byte ,按照顺序依次是
        #   文件标识 2 byte
        #   版本号 1 byte
        #   映射方式 1 byte
        #   位图开始字节 3 byte
        #   字号 1 byte
        #   单字点阵字节大小 1 byte
        #   保留 7 byte
        self.font_bmf_info = self._font.read(16)
        # 判断字体是否正确，文件头和常用的图像格式 BMP 相同，需要添加版本验证来辅助验证
        if self.font_bmf_info[0:2] != b"BM":
            raise TypeError("Incorrect font file format: {}".format(file))
        self.font_version = self.font_bmf_info[2]
        if self.font_version != 3:
            raise TypeError("Incorrect font file version: {}".format(self.font_version))
        # 映射方式，目前映射方式并没有加以验证，原因是 MONO 最易于处理
        self.font_map_mode = self.font_bmf_info[3]
        # 位图开始字节，位图数据位于文件尾，需要通过位图开始字节来确定字体数据实际位置
        self.font_start_bitmap = unpack(">I", b'\x00' + self.font_bmf_info[4:7])[0]
        # 字体大小，默认的文字字号，用于缩放方面的处理
        self.font_size = self.font_bmf_info[7]
        if self.size is None:
            self.size = int(self.font_size)
        # 点阵所占字节，用来定位字体数据位置
        self.font_bitmap_size = self.font_bmf_info[8]

    def text(self, s: str, x: int, y: int,
             color: int = None, bg_color: int = None, size: int = None,
             half_char: bool = None, auto_wrap: bool = None, show: bool = None, clear: bool = None,
             key: bool = None, invert: bool = None, line_spacing: int = None, *args, **kwargs):
        """
        Args:
            s: String
                字符串
            x: X-coordinate of the string
                x 坐标
            y: Y-coordinate of the string
                y 坐标
            color: Text color (RGB565 range is 0-65535, MONO range is 0 and greater than zero - typically use 1)
                文字颜色 (RGB565 范围为 0-65535，MONO 范围为 0 和 大于零-通常使用 1)
            bg_color: Text background color (RGB565 range is 0-65535, MONO range is 0 and greater than zero - typically use 1)\
                文字背景颜色 (RGB565 范围为 0-65535，MONO 范围为 0 和 大于零-通常使用 1)
            key: Transparent color, when color matches key, it becomes transparent (only applicable in Framebuffer mode)
                透明色，当颜色与 key 相同时则透明 (仅适用于 Framebuffer 模式)
            size: Text size
                文字大小
            show: Show immediately
                立即显示
            clear: Clear buffer / Clear screen
                清理缓冲区 / 清理屏幕
            invert: Invert (MONO)
                逆置(MONO)
            auto_wrap: Enable auto wrap
                自动换行
            half_char: Display ASCII characters in half width
                半宽显示 ASCII 字符
            line_spacing: Line spacing
                行间距
        """
        if color is None:
            color = self.color
        if bg_color is None:
            bg_color = self.bg_color
        if key is None:
            key = self._key
        if size is None:
            size = self.size
        if show is None:
            show = self._show
        if clear is None:
            clear = self._clear
        if invert is None:
            invert = self.invert
        if auto_wrap is None:
            auto_wrap = self.auto_wrap
        if half_char is None:
            half_char = self.half_char
        color_type = self.color_type
        if line_spacing is None:
            line_spacing = self.line_spacing

        # 如果没有指定字号则使用默认字号
        font_size = size or self.font_size
        # 记录初始的 x 位置
        init_x = x

        try:
            _seek = self._font.seek
        except AttributeError:
            raise AttributeError("The font file is not loaded... Did you forgot?")

        dp = self.display
        font_offset = font_size // 2

        # 颜色反转
        if invert:
            color, bg_color = bg_color, color

        # 配置调色板
        if color_type == "MONO":
            palette = FrameBuffer(bytearray(1), 2, 1, MONO_HLSB)  # MONO pixels occupy 1 byte for every 8 pixels
        elif color_type == "RGB565":
            palette = FrameBuffer(bytearray(4), 2, 1, RGB565)  # RGB565 pixels occupy 2 bytes for every 1 pixel
        else:
            raise KeyError("Unsupported color_type: {}".format(color_type))
        palette.pixel(1, 0, color)
        palette.pixel(0, 0, bg_color)

        # 清屏
        if clear:
            self.clear()

        for char in s:
            if auto_wrap and ((x + font_offset > dp.width and ord(char) < 128 and half_char) or
                              (x + font_size > dp.width and (not half_char or ord(char) > 128))):
                y += font_size + line_spacing
                x = init_x

            # 对控制字符的处理
            if char == '\n':
                y += font_size + line_spacing
                x = init_x
                continue
            elif char == '\t':
                x = ((x // font_size) + 1) * font_size + init_x % font_size
                continue
            elif ord(char) < 16:
                continue

            # 超过范围的字符不会显示
            if x > dp.width or y > dp.height:
                continue

            # 获取字体的点阵数据
            byte_data = self.get_bitmap(char)

            # 准备并缩放字符数据
            byte_data = bytearray(byte_data)
            if font_size != self.font_size:
                byte_data = self._hlsb_font_size(byte_data, font_size, self.font_size)

            # 显示字符
            fbuf = FrameBuffer(byte_data, font_size, font_size, MONO_HLSB)
            if self._buffer:  # FrameBuffer Driven
                dp.blit(fbuf, x, y, key, palette)
            else:
                if color_type == "RGB565":
                    n_fbuf = FrameBuffer(bytearray(font_size * font_size * 2), font_size, font_size, RGB565)
                    n_fbuf.blit(fbuf, 0, 0, key, palette)  # Render black and white pixels to color
                elif color_type == "MONO":
                    n_fbuf = fbuf  # Not tested
                else:
                    raise ValueError("Unsupported color_type: {}".format(color_type))
                dp.set_window(x, y, x + font_size - 1, y + font_size - 1)
                dp.write_data(n_fbuf)

            # 英文字符半格显示
            if ord(char) < 128 and half_char:
                x += font_offset
            else:
                x += font_size

        self.show() if show else 0

    def ppm(self, *args, **kwargs):
        self.pbm(*args, **kwargs)

    def pbm(self, file, x, y, key: int = None, show: bool = None, clear: bool = None, invert: bool = False,
            color: int = None, bg_color: int = None):
        """
        Display PBM / PPM Image
        显示 pbm / ppm 图片

        # You can use the Pillow library in python3 to convert the image to PBM format. For example:
        # 您可以通过使用 python3 的 pillow 库将图片转换为 pbm 格式，比如：
        # convert_type = "1"  # "1" for black and white image, "RGBA" for colored image
        # convert_type = "1"  # 1 为黑白图像，RGBA 为彩色图像
        #
        # from PIL import Image
        # with Image.open("filename.png", "r") as img:
        #   img2 = img.convert(convert_type)
        #   img2.save("filename.pbm")

        Args:
            file: PBM file
                pbm 文件
                File path (str)
                文件路径
                Raw data (BytesIO)
                原始数据
            x: X-coordinate
                 X 坐标
            y: Y-coordinate
                 Y 坐标
            key: Specified color to be treated as transparent (only applicable in Framebuffer mode)
                指定的颜色将被视为透明（仅适用于 Framebuffer 模式）
            show: Show immediately (only applicable in Framebuffer mode)
                立即显示（仅适用于 Framebuffer 模式）
            clear: Clear screen
                清理屏幕
            invert: Invert colors
                反转颜色
            color: Image main color (only effective when displaying black and white image on a color screen)
                图像主体颜色（仅彩色屏幕显示黑白图像时生效）
            bg_color: Image background color (only effective when displaying black and white image on a color screen)
                图像背景颜色（仅彩色屏幕显示黑白图像时生效）
        """
        if key is None:
            key = self._key
        if show is None:
            show = self._show
        if clear is None:
            clear = self._clear
        if invert is None:
            invert = self.invert
        color_type = self.color_type
        if color is None:
            color = self.color
        if bg_color is None:
            bg_color = self.bg_color
        if clear:  # 清屏
            self.clear()
        dp = self.display
        if isinstance(file, BytesIO):
            func = file
        else:
            func = open(file, "rb")
        with func as f:
            file_format = f.readline()  # 获取文件格式
            _width, _height = [int(value) for value in f.readline().split()]  # 获取图片的宽度和高度
            f_read = f.read
            if file_format == b"P4\n":  # P4 位图 二进制
                # 颜色反转
                if invert:
                    color, bg_color = bg_color, color
                # 配置调色板
                if color_type == "MONO":
                    palette = FrameBuffer(bytearray(1), 2, 1, MONO_HLSB)
                elif color_type == "RGB565":
                    palette = FrameBuffer(bytearray(4), 2, 1, RGB565)
                else:
                    raise KeyError("Unsupported color_type: {}".format(color_type))
                palette.pixel(1, 0, color)
                palette.pixel(0, 0, bg_color)

                if self._buffer:  # Framebuffer 模式
                    data = bytearray(f_read())  # 读取并显示图像
                    fbuf = FrameBuffer(data, _width, _height, MONO_HLSB)
                    dp.blit(fbuf, x, y, key, palette)
                else:  # 直接驱动
                    write_data = dp.write_data
                    dp.set_window(x, y, x + _width - 1, y + _height - 1)  # 设置窗口
                    buffer_size = self.READ_SIZE
                    width = buffer_size * 8
                    # Use different types of buffers according to different color types
                    if color_type == "RGB565":
                        data_fbuf = FrameBuffer(bytearray(buffer_size * 16), width, 1, RGB565)
                    elif color_type == "MONO":
                        data_fbuf = FrameBuffer(bytearray(buffer_size), width, 1, MONO_HLSB)  # Not tested
                    else:
                        raise ValueError("Unsupported color_type: {}".format(color_type))
                    data_fbuf_blit = data_fbuf.blit
                    # Read a picture several times, taking a part of it each time
                    data = bytearray(f_read(buffer_size))
                    while data:
                        fbuf = FrameBuffer(data, width, 1, MONO_HLSB)
                        data_fbuf_blit(fbuf, 0, 0, key, palette)  # Render MONO pixels into RGB565 pixels
                        len_data = len(data)
                        if len_data < buffer_size:  # Limit the data sent to no more than the Buffer size, so as to avoid data overflow and affect the display
                            if color_type == "RGB565":
                                fbuf_data = bytearray(data_fbuf)[:len_data * 16]
                            elif color_type == "MONO":
                                fbuf_data = bytearray(data_fbuf)[:len_data]
                            else:
                                raise ValueError("Unsupported color_type: {}".format(color_type))
                        else:
                            fbuf_data = bytearray(data_fbuf)
                        write_data(fbuf_data)
                        data = bytearray(f_read(buffer_size))

            elif file_format == b"P6\n":  # P6 像素图 二进制
                max_pixel_value = f.readline()  # 获取最大像素值
                r_height = range(_height)
                r_width = range(_width)
                color_bytearray = bytearray(3)  # 为变量预分配内存
                f_rinto = f.readinto
                try:
                    dp_color = dp.color
                except AttributeError:
                    dp_color = self.rgb565_color
                dp_pixel = dp.pixel
                if self._buffer:  # Framebuffer 模式
                    if color_type == "RGB565":
                        buffer = bytearray(_width * 2)
                    for _y in r_height:  # 逐行显示图片
                        for _x in r_width:
                            f_rinto(color_bytearray)
                            r, g, b = color_bytearray[0], color_bytearray[1], color_bytearray[2]
                            if invert:
                                r = 255 - r
                                g = 255 - g
                                b = 255 - b
                            if color_type == "RGB565":
                                buffer[_x * 2: (_x + 1) * 2] = dp_color(r, g, b).to_bytes(2, 'big')  # 通过索引赋值
                            elif color_type == "MONO":
                                _color = int((r + g + b) / 3) >= 127
                                if _color:
                                    _color = color
                                else:
                                    _color = bg_color
                                if _color != key:  # 不显示指定颜色
                                    dp_pixel(_x + x, _y + y, _color)
                        if color_type == "RGB565":
                            fbuf = FrameBuffer(buffer, _width, 1, RGB565)
                            dp.blit(fbuf, x, y + _y, key)
                else:  # 直接驱动
                    dp.set_window(x, y, x + _width - 1, y + _height - 1)  # 设置窗口
                    buffer = bytearray(_width * 2)
                    for _y in r_height:  # 逐行显示图片
                        for _x in r_width:
                            color_bytearray = f_read(3)
                            r, g, b = color_bytearray[0], color_bytearray[1], color_bytearray[2]
                            if invert:
                                r = 255 - r
                                g = 255 - g
                                b = 255 - b
                            if color_type == "RGB565":
                                buffer[_x * 2: (_x + 1) * 2] = dp_color(
                                    r, g, b).to_bytes(2, 'big')  # 通过索引赋值
                            elif color_type == "MONO":
                                _color = int((r + g + b) / 3) >= 127
                                if _color:
                                    _color = color
                                else:
                                    _color = bg_color
                                if _color != key:  # 不显示指定颜色
                                    dp_pixel(_x + x, _y + y, _color)
                        if color_type == "RGB565":
                            dp.write_data(buffer)
            else:
                raise TypeError("Unsupported File Format Type.")

            self.show() if show else 0  # 立即显示

    def bmp(self, file, x, y, key: int = None, show: bool = None, clear: bool = None, invert: bool = False,
            color: int = None, bg_color: int = None):
        """
        Display BMP Image  显示 bmp 图片

        # You can convert the image to `24-bit` `bmp` format using the Paint application in Windows.
        # Alternatively, you can use software like `Image2Lcd` to convert the image to `24-bit` `bmp` format (horizontal scan, includes image header data, 24-bit grayscale).
        # 您可以通过使用 windows 的 画图 将图片转换为 `24-bit` 的 `bmp` 格式
        # 也可以使用 `Image2Lcd` 这款软件将图片转换为 `24-bit` 的 `bmp` 格式（水平扫描，包含图像头数据，灰度二十四位）

        Args:
            file: bmp file
                bmp 文件
                File path (str)
                文件路径
                Raw data (BytesIO)
                原始数据
            x: X-coordinate
                X 坐标
            y: Y-coordinate
                Y 坐标
            key: Specified color to be treated as transparent (only applicable in Framebuffer mode)
                指定的颜色将被视为透明（仅适用于 Framebuffer 模式）
            show: Show immediately (only applicable in Framebuffer mode)
                立即显示（仅适用于 Framebuffer 模式）
            clear: Clear screen
                清理屏幕
            invert: Invert colors
                反转颜色
            color: Image main color (only effective when displaying black and white image on a color screen)
                   图像主体颜色（仅彩色图片显示以黑白形式显示时生效）
            bg_color: Image background color (only effective when displaying black and white image on a color screen)
                   图像背景颜色（仅彩色图片显示以黑白形式显示时生效）
        """
        if key is None:
            key = self._key
        if show is None:
            show = self._show
        if clear is None:
            clear = self._clear
        if invert is None:
            invert = self.invert
        color_type = self.color_type
        if color is None:
            color = self.color
        if bg_color is None:
            bg_color = self.bg_color
        if isinstance(file, BytesIO):
            func = file
        else:
            func = open(file, "rb")
        with func as f:
            f_read = f.read
            f_rinto = f.readinto
            f_seek = f.seek
            f_tell = f.tell()
            dp = self.display
            try:
                dp_color = dp.color
            except AttributeError:
                dp_color = self.rgb565_color
            dp_pixel = dp.pixel
            if f_read(2) == b'BM':  # 检查文件头
                dummy = f_read(8)  # 文件大小占四个字节，文件作者占四个字节，file size(4), creator bytes(4)
                int_fb = int.from_bytes
                offset = int_fb(f_read(4), 'little')  # 像素存储位置占四个字节
                hdrsize = int_fb(f_read(4), 'little')  # DIB header 占四个字节
                _width = int_fb(f_read(4), 'little')  # 图像宽度
                _height = int_fb(f_read(4), 'little')  # 图像高度
                if int_fb(f_read(2), 'little') == 1:  # 色彩平面数 planes must be 1
                    depth = int_fb(f_read(2), 'little')  # 像素位数
                    # 转换时只支持二十四位彩色，不压缩的图像
                    if depth == 24 and int_fb(f_read(4), 'little') == 0:  # compress method == uncompressed
                        row_size = (_width * 3 + 3) & ~3
                        if _height < 0:
                            _height = -_height
                            flip = False
                        else:
                            flip = True
                        if _width > dp.width:  # Limit the maximum size of image display
                            _width = dp.width
                        if _height > dp.height:
                            _height = dp.height
                        _color_bytearray = bytearray(3)  # 像素的二进制颜色
                        if clear:  # 清屏
                            self.clear()
                        buffer = bytearray(_width * 2)
                        self_buf = self._buffer
                        if not self_buf:
                            dp.set_window(x, y, x + _width - 1, y + _height - 1)  # 设置窗口
                        r_width = range(_width)
                        r_height = range(_height)
                        for _y in r_height:
                            if flip:
                                pos = offset + (_height - 1 - _y) * row_size
                            else:
                                pos = offset + _y * row_size
                            if f_tell != pos:
                                f_seek(pos)  # 调整指针位置
                            for _x in r_width:
                                f_rinto(_color_bytearray)
                                r, g, b = _color_bytearray[2], _color_bytearray[1], _color_bytearray[0]
                                if invert:  # 颜色反转
                                    r = 255 - r
                                    g = 255 - g
                                    b = 255 - b
                                if self_buf:  # Framebuffer 模式
                                    if color_type == "RGB565":
                                        buffer[_x * 2: (_x + 1) * 2] = dp_color(
                                            r, g, b).to_bytes(2, 'big')  # 通过索引赋值
                                    elif color_type == "MONO":
                                        _color = int((r + g + b) / 3) >= 127
                                        if _color:
                                            _color = color
                                        else:
                                            _color = bg_color
                                        if _color != key:  # 不显示指定颜色
                                            dp_pixel(_x + x, _y + y, _color)
                                else:
                                    if color_type == "RGB565":
                                        buffer[_x * 2: (_x + 1) * 2] = dp_color(
                                            r, g, b).to_bytes(2, 'big')  # 通过索引赋值
                                    elif color_type == "MONO":
                                        _color = int((r + g + b) / 3) >= 127
                                        if _color:
                                            _color = color
                                        else:
                                            _color = bg_color
                                        if _color != key:  # 不显示指定颜色
                                            dp_pixel(_x + x, _y + y, _color)

                            if color_type == "RGB565":
                                if self_buf:
                                    fbuf = FrameBuffer(buffer, _width, 1, RGB565)
                                    dp.blit(fbuf, x, y + _y, key)
                                else:
                                    dp.write_data(buffer)

                        self.show() if show else 0  # 立即显示
                    else:
                        raise TypeError("Unsupported file type: only 24-bit uncompressed BMP images are supported.")
            else:
                raise TypeError("Unsupported file type: only BMP images are supported.")

    def dat(self, file, x, y, key=None):
        """
        Display screen raw data file, with extremely high efficiency, only supports RGB565 format.
        显示表示屏幕原始数据的文件，拥有极高的效率，仅支持 RGB565 格式

        Args:
            file: dat file  dat 文件
                File path (str)  文件路径
                Raw data (BytesIO)  原始数据
            x: X-coordinate  X坐标
            y: Y-coordinate  Y 坐标
            key: Specified color to be treated as transparent (only applicable in Framebuffer mode)
                指定的颜色将被视为透明（仅适用于 Framebuffer 模式）
        """
        if key is None:
            key = self._key
        if isinstance(file, BytesIO):
            func = file
        else:
            func = open(file, "rb")
        with func as f:
            f_readline = f.readline
            f_read = f.read
            file_head = f_readline().rstrip(b'\n')
            if file_head == b'EasyDisplay':  # 文件头
                version = f_readline().rstrip(b'\n')
                if version == b'V1':  # 文件格式版本
                    _width, _height = f_readline().rstrip(b'\n').split(b' ')
                    _width, _height = int(_width), int(_height)
                    if self._buffer:  # Framebuffer 模式
                        data = f_read(_width)
                        dp_blit = self.display.blit
                        y_offset = 0
                        while data:
                            buf = FrameBuffer(bytearray(data), _width, 1, RGB565)
                            dp_blit(buf, x, y + y_offset, key)
                            data = f_read(_width)
                            y_offset += 1
                    else:  # 直接驱动模式
                        size = self.READ_SIZE * 10
                        data = f_read(size)
                        dp_write = self.display.write_data
                        self.display.set_window(x, y, x + _width - 1, y + _height - 1)
                        while data:
                            dp_write(data)
                            data = f_read(size)
                else:
                    raise TypeError("Unsupported Version: {}".format(version))

            else:
                try:
                    raise TypeError("Unsupported File Type: {}".format(file_head))
                except:
                    raise TypeError("Unsupported File Type!")
