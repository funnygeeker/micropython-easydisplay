__version__ = 3
"""
usage: bitmapfonts.py [-h] [-v] -ff FONT_FILE [-tf TEXT_FILE | -t TEXT] [-fs FONT_SIZE] [-o [OFFSET ...]] [-bfn BITMAP_FONT_NAME]

生成点阵字体文件

https://github.com/AntonVanke/MicroPython-Chinese-Font

options:
  -h, --help            show this help message and exit
  -v, --version         显示生成的点阵字体版本
  -ff FONT_FILE, --font-file FONT_FILE
                        字体文件
  -tf TEXT_FILE, --text-file TEXT_FILE
                        文字字符集文件
  -t TEXT, --text TEXT  文字字符集
  -fs FONT_SIZE, --font-size FONT_SIZE
                        生成字体字号
  -o [OFFSET ...], --offset [OFFSET ...]
                        生成字体偏移
  -bfn BITMAP_FONT_NAME, --bitmap-font-name BITMAP_FONT_NAME
                        生成的点阵字体文件名称
example:
    python bitmapfonts.py -ff unifont-14.0.04.ttf -tf text.txt -fs 16 -o 0 0 -bfn example.bmf
"""
import sys
import struct
import argparse

try:
    import numpy as np
    from PIL import ImageFont, ImageDraw, Image
except ImportError as err:
    print(err, "尝试运行 `python -m pip install requirements.txt`")
    exit()


def get_im(word, width, height, font, offset: tuple = (0, 0)) -> Image.Image:
    """获取生成的图像

    Args:
        word: 字
        width: 宽度
        height: 高度
        font: 字体
        offset: 偏移

    Returns:
        PIL.Image.Image
    """
    im = Image.new('1', (width, height), (1,))
    draw = ImageDraw.Draw(im)
    draw.text(offset, word, font=font)
    return im


def to_bitmap(word: str, font_size: int, font, offset=(0, 0)) -> bytearray:
    """ 获取点阵字节数据

    Args:
        word: 字
        font_size: 字号
        font: 字体
        offset: 偏移

    Returns:
        字节数据
    """
    code = 0x00
    data_code = word.encode("utf-8")

    # 获取字节码
    try:
        for byte in range(len(data_code)):
            code |= data_code[byte] << (len(data_code) - byte - 1) * 8
    except IndexError:
        print(word, word.encode("utf-8"))

    # 获取点阵图
    bp = np.pad(
        (~np.asarray(get_im(word, width=font_size, height=font_size, font=font, offset=offset))).astype(np.int32),
        ((0, 0), (0, int(np.ceil(font_size / 8) * 8 - font_size))), 'constant',
        constant_values=(0, 0))

    # 点阵映射 MONO_HLSB
    bmf = []
    for line in bp.reshape((-1, 8)):
        v = 0x00
        for _ in line:
            v = (v << 1) + _
        bmf.append(v)
    return bytearray(bmf)


def get_unicode(word) -> bytes:
    """返回 Unicode 编码

    Args:
        word:

    Returns:

    """
    o = ord(word)
    if o > 65535:
        o = 65311  # ord("？")
    return struct.pack(">H", o)


def run(font_file, font_size=16, offset=(0, 0), text_file=None, text=None, bitmap_fonts_name=None,
        bitmap_fonts_file=None):
    # 生成的点阵字体文件

    font = ImageFont.truetype(font=font_file, size=font_size)

    if text:
        words = list(set(list(text)))
    else:
        words = list(set(list(open(text_file, encoding="utf-8").read())))
    words.sort()
    font_num = len(words)
    # print(args)
    bitmap_fonts_name = bitmap_fonts_name or font_file.split('.')[0] + "-" + str(font_num) + "-" + str(
        font_size) + f".v{__version__}.bmf"
    bitmap_fonts = bitmap_fonts_file or open(bitmap_fonts_name, "wb")
    print(f"正在生成点阵字体文件，字体数量{font_num}：")
    # 字节记录占位
    bitmap_fonts.write(bytearray([
        66, 77,  # 标记
        3,  # 版本
        0,  # 映射方式
        0, 0, 0,  # 位图开始字节
        font_size,  # 字号
        int(np.ceil(font_size / 8)) * font_size,  # 每个字占用的大小
        0, 0, 0, 0, 0, 0, 0  # 兼容项
    ]))

    for w in words:
        bitmap_fonts.write(get_unicode(w))

    # 位图开始字节
    start_bitmap = bitmap_fonts.tell()
    print("\t位图起始字节：", hex(start_bitmap))
    for w in words:
        bitmap_fonts.write(to_bitmap(w, font_size, font, offset=offset))
    file_size = bitmap_fonts.tell()
    print(f"\t文件大小：{file_size / 1024:.4f}KByte")
    bitmap_fonts.seek(4, 0)
    bitmap_fonts.write(struct.pack(">i", start_bitmap)[1:4])
    print(f"生成成功，文件名称：{bitmap_fonts_name}")
    return font_num, start_bitmap, file_size, bitmap_fonts_name, font_size, offset


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="生成点阵字体文")
    group = parser.add_mutually_exclusive_group()
    parser.add_argument('-v', '--version', action='version',
                        version=f'点阵字体版本 : {__version__}',
                        help='显示生成的点阵字体版本')
    parser.add_argument("-ff", "--font-file", help="字体文件", type=str, required=True)
    group.add_argument("-tf", "--text-file", help="文字字符集文件", type=str, default="text.txt")
    group.add_argument("-t", "--text", help="文字字符集", type=str)
    parser.add_argument("-fs", "--font-size", help="生成字体字号", default=16, type=int)
    parser.add_argument("-o", "--offset", nargs="*", help="生成字体偏移", type=int, default=[0, 0])
    parser.add_argument("-bfn", "--bitmap-font-name", help="生成的点阵字体文件名称", type=str)
    args = parser.parse_args()
    run(font_file=args.font_file, font_size=args.font_size, offset=args.offset, text_file=args.text_file,
        text=args.text, bitmap_fonts_name=args.bitmap_font_name)
