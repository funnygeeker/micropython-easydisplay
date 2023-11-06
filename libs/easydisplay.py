# Github: https://github.com/funnygeeker/micropython-easydisplay
# Author: funnygeeker
# Licence: MIT
# Date: 2023/11/5
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

from struct import unpack
from framebuf import FrameBuffer, MONO_HLSB, RGB565


class EasyDisplay:
    BUFFER_SIZE = 32

    def __init__(self, display,
                 font: str = None,
                 key: int = -1,
                 show: bool = None,
                 clear: bool = None,
                 reversion: bool = False,
                 color_type=RGB565,
                 color: int = 0xFFFF,
                 bg_color: int = 0,
                 text_size: int = 16,
                 text_auto_wrap: bool = False,
                 text_half_char: bool = True,
                 text_line_spacing: int = 0,
                 *args, **kwargs):
        """
        初始化 EasyDisplay

        Args:
            display: 显示实例
            font: 字体文件所在位置
            key: 指定的颜色将被视为透明（仅适用于 Framebuffer 模式）
            show: 立即显示（仅适用于 Framebuffer 模式）
            clear: 清理屏幕
            reversion: 反转颜色
            color_type: 图像格式，RGB565 屏幕用 framebuf.RGB565，MONO_HLSB 屏幕用 framebuf.MONO_HLSB
            color: 图像主体颜色（仅彩色屏幕显示黑白图像时生效）
            bg_color: 图像背景颜色（仅彩色屏幕显示黑白图像时生效）
            text_size: 文本字号大小
            text_auto_wrap: 文本自动换行
            text_half_char： 半宽显示 ASCII 字符
            text_line_spacing: 文本行间距
        """
        self.display = display
        try:
            _buffer = display.buffer
            # buffer: 驱动是否使用了帧缓冲区，False（SPI 直接驱动模式） / True（Framebuffer 模式）
            buffer = True
        except AttributeError:
            buffer = False
        self._buffer = buffer
        self._font = None
        self._key = key
        self._show = show
        self._clear = clear
        self._reversion = reversion
        self._color_type = color_type
        self._color = color
        self._bg_color = bg_color
        self.text_size = text_size
        self.text_auto_wrap = text_auto_wrap
        self.text_half_char = text_half_char
        self.text_line_spacing = text_line_spacing
        self.font_bmf_info = None
        self.font_version = None
        self.font_file = None
        self.font_map_mode = None
        self.font_start_bitmap = None
        self.font_bitmap_size = None
        if font:
            self.load_font(font)

    def clear(self):
        """
        清屏
        """
        self.display.fill(0)

    @staticmethod
    def _calculate_palette(color, bg_color) -> tuple:
        """
        通过 主体颜色 和 背景颜色 计算调色板

        Args:
            color: 主体颜色
            bg_color: 背景颜色
        """
        return [bg_color & 0xFF, (bg_color & 0xFF00) >> 8], [color & 0xFF, (color & 0xFF00) >> 8]

    @staticmethod
    def _flatten_byte_data(byte_data, palette) -> bytearray:
        """
        将 二进制 MONO_HLSB 黑白图像渲染为 RGB565 彩色图像
        Args:
            byte_data: 图像数据
            palette: 调色板

        Returns:
            RGB565 图像数据
        """
        _temp = []
        r = range(7, -1, -1)
        _t_extend = _temp.extend
        for _byte in byte_data:
            for _b in r:
                _t_extend(palette[(_byte >> _b) & 0x01])
        return bytearray(_temp)

    def _get_index(self, word: str) -> int:
        """
        获取文字索引
        Args:
            word: 字符
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

    @staticmethod
    def _reverse_byte_data(byte_data) -> bytearray:
        """
        反转字节数据

        Args:
            byte_data: 二进制 黑白图像

        Returns:
            反转后的数据 (0->1, 1->0)
        """
        r = range(len(byte_data))
        for _pixel in r:
            byte_data[_pixel] = ~byte_data[_pixel] & 0xff
        return byte_data

    # @timeit
    @staticmethod
    def _HLSB_font_size(bytearray_data: bytearray, new_size: int, old_size: int) -> bytearray:
        """
        缩放 HLSB 字符

        Args:
            bytearray_data: 源字符数据
            new_size: 新字符大小
            old_size: 旧字符大小

        Returns:
            缩放后的字符数据
        """
        r = range(new_size)  # 对于 micropython 来说可以提高效率
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

    @staticmethod
    def _RGB565_font_size(bytearray_data, new_size: int, palette: tuple, old_size: int) -> bytearray:
        """
        缩放 RGB565 字符

        Args:
            bytearray_data: 源字符数据
            new_size: 新字符大小
            old_size: 旧字符大小

        Returns:
            缩放后的字符数据
        """
        r = range(new_size)
        if old_size == new_size:
            return bytearray_data
        _t = []
        _t_extend = _t.extend
        _new_index = -1
        for _col in r:
            for _row in r:
                if (_row % 8) == 0:
                    _new_index += 1
                _old_index = int(_col / (new_size / old_size)) * old_size + int(_row / (new_size / old_size))
                _t_extend(palette[bytearray_data[_old_index // 8] >> (7 - _old_index % 8) & 1])
        return bytearray(_t)

    def get_bitmap(self, word: str) -> bytes:
        """
        获取点阵图

        Args:
            word: 单个字符

        Returns:
            bytes 字符点阵
        """
        index = self._get_index(word)
        if index == -1:
            return b'\xff\xff\xff\xff\xff\xff\xff\xff\xf0\x0f\xcf\xf3\xcf\xf3\xff\xf3\xff\xcf\xff?\xff?\xff\xff\xff' \
                   b'?\xff?\xff\xff\xff\xff'
        self._font.seek(self.font_start_bitmap + index * self.font_bitmap_size, 0)
        return self._font.read(self.font_bitmap_size)

    def load_font(self, file: str):
        """
        加载字体文件

        Args:
            file: 字体文件路径
        """
        self.font_file = file
        # 载入字体文件
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
        # 映射方式，目前映射方式并没有加以验证，原因是 MONO_HLSB 最易于处理
        self.font_map_mode = self.font_bmf_info[3]
        # 位图开始字节，位图数据位于文件尾，需要通过位图开始字节来确定字体数据实际位置
        self.font_start_bitmap = unpack(">I", b'\x00' + self.font_bmf_info[4:7])[0]
        # 字体大小，默认的文字字号，用于缩放方面的处理
        self.text_size = self.font_bmf_info[7]
        # 点阵所占字节，用来定位字体数据位置
        self.font_bitmap_size = self.font_bmf_info[8]

    def text(self, s: str, x: int, y: int,
             color: int = 0xFFFF, bg_color: int = 0, size: int = None,
             half_char: bool = None, auto_wrap: bool = None, show: bool = None, clear: bool = None,
             key: bool = None, reversion: bool = None, color_type: int = None, line_spacing: int = None, *args,
             **kwargs):
        """
        Args:
            s: 字符串
            x: 字符串 x 坐标
            y: 字符串 y 坐标
            color: 文字颜色 (RGB565 范围为 0-65535，MONO_HLSB 范围为 0 和 大于零-通常为1)
            bg_color: 文字背景颜色 (RGB565 范围为 0-65535，MONO_HLSB 范围为 0 和 大于零-通常为1)
            key: 透明色，当颜色与 key 相同时则透明 (仅适用于 Framebuffer 模式)
            size: 文字大小
            show: 立即显示
            clear: 清理缓冲区 / 清理屏幕
            reversion: 逆置(MONO)
            auto_wrap: 自动换行
            half_char: 半宽显示 ASCII 字符
            color_type: 色彩模式 0:MONO_HLSB 1:RGB565
            line_spacing: 行间距
        """
        if color is None:
            color = self._color
        if bg_color is None:
            bg_color = self._bg_color
        if key is None:
            key = self._key
        if size is None:
            size = self.text_size
        if show is None:
            show = self._show
        if clear is None:
            clear = self._clear
        if reversion is None:
            reversion = self._reversion
        if auto_wrap is None:
            auto_wrap = self.text_auto_wrap
        if half_char is None:
            half_char = self.text_half_char
        if color_type is None:
            color_type = self._color_type
        if line_spacing is None:
            line_spacing = self.text_line_spacing

        # 如果没有指定字号则使用默认字号
        font_size = size or self.text_size
        # 记录初始的 x 位置
        initial_x = x

        try:
            _seek = self._font.seek
        except AttributeError:
            raise AttributeError("The font file is not loaded... Did you forget?")

        # 清屏
        try:
            self.display.clear() if clear else 0
        except AttributeError:
            # print("请自行调用 display.fill() 清屏")
            pass

        dp = self.display
        if font_size == 16:
            font_offset = 12
        elif font_size > 16:
            font_offset = int(font_size * 0.69) + 1
        else:  # 例如：8px
            font_offset = font_size // 2
        for char in s:
            if char in ('M', 'O', 'Q', 'V', 'W', 'X', 'm', 'w'):  # 更好的适配英文字符
                _half_char = False
            else:
                _half_char = half_char

            if auto_wrap and ((x + font_offset > dp.width and ord(char) < 128 and _half_char) or
                              (x + font_size > dp.width and (not _half_char or ord(char) > 128))):
                y += font_size + line_spacing
                x = initial_x

            # 对控制字符的处理
            if char == '\n':
                y += font_size + line_spacing
                x = initial_x
                continue
            elif char == '\t':
                x = ((x // font_size) + 1) * font_size + initial_x % font_size
                continue
            elif ord(char) < 16:
                continue

            # 超过范围的字符不会显示*
            if x > dp.width or y > dp.height:
                continue

            # 获取字体的点阵数据
            byte_data = list(self.get_bitmap(char))

            # 分四种情况逐个优化
            #   1. 黑白屏幕/无放缩
            #   2. 黑白屏幕/放缩
            #   3. 彩色屏幕/无放缩
            #   4. 彩色屏幕/放缩
            byte_data = self._reverse_byte_data(byte_data) if reversion else byte_data
            if color_type == MONO_HLSB:
                if font_size == self.text_size:
                    dp.blit(
                        FrameBuffer(bytearray(byte_data), font_size, font_size, MONO_HLSB),
                        x, y,
                        key)
                else:
                    dp.blit(
                        FrameBuffer(self._HLSB_font_size(byte_data, font_size, self.text_size), font_size,
                                    font_size, MONO_HLSB), x, y, key)
            elif color_type == RGB565:
                palette = self._calculate_palette(color, bg_color)
                if font_size == self.text_size:
                    data = self._flatten_byte_data(byte_data, palette)
                    if self._buffer:
                        dp.blit(
                            FrameBuffer(data, font_size, font_size,
                                        RGB565), x, y, key)
                    else:
                        dp.set_window(x, y, x + font_size - 1, y + font_size + 1)
                        dp.write_data(data)
                else:
                    data = self._RGB565_font_size(byte_data, font_size, palette, self.text_size)
                    if self._buffer:
                        dp.blit(
                            FrameBuffer(data,
                                        font_size, font_size, RGB565), x, y, key)
                    else:
                        dp.set_window(x, y, x + font_size - 1, y + font_size + 1)
                        dp.write_data(data)
            # 英文字符半格显示
            if ord(char) < 128 and _half_char:
                x += font_offset
            else:
                x += font_size

        try:
            dp.show() if show else 0
        except AttributeError:
            pass

    def pbm(self, file: str, x, y, key: int = -1, show: bool = None, clear: bool = None, reversion: bool = False,
            color_type=RGB565, color: int = None, bg_color: int = None):
        """
        显示 pbm 图片

        # 您可以通过使用 python3 的 pillow 库将图片转换为 pbm 格式，比如：
        # convert_type = "1"  # 1 为黑白图像，RGBA 为彩色图像
        # from PIL import Image
        # with Image.open("文件名.png", "r") as img:
        #   img2 = img.convert(convert_type)
        #   img2.save("文件名.pbm")

        Args:
            file: pbm 文件位置
            x: 显示图片的 x 坐标
            y: 显示图片的 y 坐标
            key: 指定的颜色将被视为透明（仅适用于 Framebuffer 模式）
            show: 立即显示（仅适用于 Framebuffer 模式）
            clear: 清理屏幕
            reversion: 反转颜色
            color_type: 图像格式，RGB565 屏幕用 framebuf.RGB565，MONO_HLSB 屏幕用 framebuf.MONO_HLSB
            color: 图像主体颜色（仅彩色屏幕显示黑白图像时生效）
            bg_color: 图像背景颜色（仅彩色屏幕显示黑白图像时生效）
        """
        if key is None:
            key = self._key
        if show is None:
            show = self._show
        if clear is None:
            clear = self._clear
        if reversion is None:
            reversion = self._reversion
        if color_type is None:
            color_type = self._color_type
        if color is None:
            color = self._color
        if bg_color is None:
            bg_color = self._bg_color
        if clear:  # 清屏
            self.clear()
        dp = self.display
        with open(file, "rb") as f:
            file_format = f.readline()  # 获取文件格式
            _width, _height = [int(value) for value in f.readline().split()]  # 获取图片的宽度和高度
            f_read = f.read
            if file_format == b"P4\n":  # P4 位图 二进制
                if self._buffer == 0:  # 直接驱动
                    buffer_size = self.BUFFER_SIZE
                    if reversion:  # New
                        color, bg_color = bg_color, color
                    palette = self._calculate_palette(color, bg_color)  # 计算调色板
                    dp.set_window(x, y, x + _width - 1, y + _height + 1)  # 设置窗口
                    data = f_read(buffer_size)
                    write_data = dp.write_data
                    while data:
                        # if reversion:  # Old
                        #     data = bytes([~b & 0xFF for b in data])
                        buffer = self._flatten_byte_data(data, palette)
                        write_data(buffer)
                        data = f_read(buffer_size)  # 30 * 8 = 240, 理论上 ESP8266 的内存差不多能承载这个大小的彩色图片
                else:  # Framebuffer 模式
                    data = bytearray(f_read())
                    if reversion:
                        # data = bytearray([~b & 0xFF for b in data])  # Old
                        color, bg_color = bg_color, color  # New
                        # data = self._reverse_byte_data(data)
                    if color_type == MONO_HLSB:
                        fbuf = FrameBuffer(data, _width, _height, MONO_HLSB)
                        dp.blit(fbuf, x, y, key)
                    elif color_type == RGB565:
                        fbuf = FrameBuffer(data, _width, _height, MONO_HLSB)
                        palette = FrameBuffer(bytearray(2 * 2), 2, 1, RGB565)
                        palette.pixel(1, 0, color)
                        palette.pixel(0, 0, bg_color)
                        # palette = FrameBuffer(bytearray((color, bg_color)), 2, 1, RGB565)
                        dp.blit(fbuf, x, y, key, palette)
                    if show:  # 立即显示
                        try:
                            dp.show()
                        except AttributeError:
                            pass

            elif file_format == b"P6\n":  # P6 像素图 二进制
                max_pixel_value = f.readline()  # 获取最大像素值
                r_height = range(_height)
                r_width = range(_width)
                color_bytearray = bytearray(3)  # 为变量预分配内存
                f_rinto = f.readinto
                try:
                    dp_color = dp.color
                except AttributeError:
                    pass
                dp_pixel = dp.pixel
                if self._buffer:  # Framebuffer 模式
                    buffer = bytearray(_width * 2)
                    for _y in r_height:  # 逐行显示图片
                        for _x in r_width:
                            f_rinto(color_bytearray)
                            r, g, b = color_bytearray[0], color_bytearray[1], color_bytearray[2]
                            if reversion:
                                r = 255 - r
                                g = 255 - g
                                b = 255 - b
                            if color_type == RGB565:
                                buffer[_x * 2: (_x + 1) * 2] = dp_color(
                                    r, g, b).to_bytes(2, 'big')  # 通过索引赋值
                            elif color_type == MONO_HLSB:
                                _color = int((r + g + b) / 3) >= 127
                                if _color:
                                    _color = color
                                else:
                                    _color = bg_color
                                if _color != key:  # 不显示指定颜色
                                    dp_pixel(_x + x, _y + y, _color)
                        if color_type == RGB565:
                            fbuf = FrameBuffer(buffer, _width, 1, RGB565)
                            dp.blit(fbuf, x, y + _y, key)
                    if show:  # 立即显示
                        try:
                            dp.show()
                        except AttributeError:
                            pass
                else:  # 直接驱动
                    dp.set_window(x, y, x + _width - 1, y + _height + 1)  # 设置窗口
                    buffer = bytearray(_width * 2)
                    for _y in r_height:  # 逐行显示图片
                        for _x in r_width:
                            color_bytearray = f_read(3)
                            r, g, b = color_bytearray[0], color_bytearray[1], color_bytearray[2]
                            if reversion:
                                r = 255 - r
                                g = 255 - g
                                b = 255 - b
                            if color_type == RGB565:
                                buffer[_x * 2: (_x + 1) * 2] = dp_color(
                                    r, g, b).to_bytes(2, 'big')  # 通过索引赋值
                            elif color_type == MONO_HLSB:
                                _color = int((r + g + b) / 3) >= 127
                                if _color:
                                    _color = color
                                else:
                                    _color = bg_color
                                if _color != key:  # 不显示指定颜色
                                    dp_pixel(_x + x, _y + y, _color)  # NOTE 可使用缓冲区进行性能优化，考虑到兼容性，暂不修改
                        if color_type == RGB565:
                            dp.write_data(buffer)
                        # NOTE 可使用缓冲区进行性能优化，考虑到兼容性，暂不修改

            else:
                raise TypeError("Unsupported File Format Type.")

    def bmp(self, file: str, x, y, key: int = -1, show: bool = None, clear: bool = None, reversion: bool = False,
            color_type=RGB565, color: int = None, bg_color: int = None):
        """
        显示 bmp 图片

        # 您可以通过使用 windows 的 画图 将图片转换为 `24-bit` 的 `bmp` 格式
        # 也可以使用 `Image2Lcd` 这款软件将图片转换为 `24-bit` 的 `bmp` 格式（水平扫描，包含图像头数据，灰度二十四位）

        Args:
            file: bmp 文件位置
            x: 显示图片的 x 坐标
            y: 显示图片的 y 坐标
            key: 指定的颜色将被视为透明（仅适用于 Framebuffer 模式）
            show: 立即显示（仅适用于 Framebuffer 模式）
            clear: 清理屏幕
            reversion: 反转颜色
            color_type: 图像格式，RGB565 屏幕用 framebuf.RGB565，MONO_HLSB 屏幕用 framebuf.MONO_HLSB
            color: 图像主体颜色（仅彩色图片显示以黑白形式显示时生效）
            bg_color: 图像背景颜色（仅彩色图片显示以黑白形式显示时生效）
        """
        if key is None:
            key = self._key
        if show is None:
            show = self._show
        if clear is None:
            clear = self._clear
        if reversion is None:
            reversion = self._reversion
        if color_type is None:
            color_type = self._color_type
        if color is None:
            color = self._color
        if bg_color is None:
            bg_color = self._bg_color
        with open(file, 'rb') as f:
            f_read = f.read
            f_rinto = f.readinto
            f_seek = f.seek
            f_tell = f.tell()
            dp = self.display
            try:
                dp_color = dp.color
            except AttributeError:
                pass
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
                        if _width > dp.width:  # 限制图像显示的最大大小（多余部分将被舍弃）
                            _width = dp.width
                        if _height > dp.height:
                            _height = dp.height
                        _color_bytearray = bytearray(3)  # 像素的二进制颜色
                        if clear:  # 清屏
                            self.clear()
                        buffer = bytearray(_width * 2)
                        self_buf = self._buffer
                        if not self_buf:
                            dp.set_window(x, y, x + _width - 1, y + _height + 1)  # 设置窗口
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
                                if reversion:  # 颜色反转
                                    r = 255 - r
                                    g = 255 - g
                                    b = 255 - b
                                if self_buf:  # Framebuffer 模式
                                    if color_type == RGB565:
                                        buffer[_x * 2: (_x + 1) * 2] = dp_color(
                                            r, g, b).to_bytes(2, 'big')  # 通过索引赋值
                                    elif color_type == MONO_HLSB:
                                        _color = int((r + g + b) / 3) >= 127
                                        if _color:
                                            _color = color
                                        else:
                                            _color = bg_color
                                        if _color != key:  # 不显示指定颜色
                                            dp_pixel(_x + x, _y + y, _color)
                                else:
                                    if color_type == RGB565:
                                        buffer[_x * 2: (_x + 1) * 2] = dp_color(
                                            r, g, b).to_bytes(2, 'big')  # 通过索引赋值
                                    elif color_type == MONO_HLSB:
                                        _color = int((r + g + b) / 3) >= 127
                                        if _color:
                                            _color = color
                                        else:
                                            _color = bg_color
                                        if _color != key:  # 不显示指定颜色
                                            dp_pixel(_x + x, _y + y, _color)  # NOTE 可使用缓冲区进行性能优化，考虑到兼容性，暂不修改

                            if color_type == RGB565:
                                if self_buf:
                                    fbuf = FrameBuffer(buffer, _width, 1, RGB565)
                                    dp.blit(fbuf, x, y + _y, key)
                                else:
                                    dp.write_data(buffer)
                            # NOTE 可使用缓冲区进行性能优化，考虑到兼容性，暂不修改

                        if show:  # 立即显示
                            try:
                                dp.show()
                            except AttributeError:
                                pass
                    else:
                        raise TypeError("Unsupported file type: only 24-bit uncompressed BMP images are supported.")
            else:
                raise TypeError("Unsupported file type: only BMP images are supported.")

    def dat(self, file, x, y, key=-1):
        """
        显示屏幕原始数据文件，拥有极高的效率，仅支持 RGB565 格式

        Args:
            file: DAT 文件路径
            x: X坐标
            y: Y 坐标
            key: 指定的颜色将被视为透明（仅适用于 Framebuffer 模式）
        """
        if key is None:
            key = self._key
        with open(file, "rb") as f:
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
                        size = self.BUFFER_SIZE * 10
                        data = f_read(size)
                        dp_write = self.display.write_data
                        self.display.set_window(x, y, x + _width - 1, y + _height + 1)
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
