# 您可以通过使用 python3 的 pillow 库将图片转换为 pbm 格式，比如：
# convert_type = "1"  # 1 为黑白图像，RGBA 为彩色图像
# from PIL import Image
# with Image.open("文件名.png", "r") as img:
#   img2 = img.convert(convert_type)
#   img2.save("文件名.pbm")

import os

try:
    from PIL import Image
except ImportError:
    os.system('pip3 install pillow -i https://mirrors.aliyun.com/pypi/simple/')
    from PIL import Image


def _get_output_path(file: str, path: str, extension: str = None):
    """
    根据文件路径和输出路径，获取输出文件的路径

    Args:
        file: 文件路径
        path: 输出路径
        extension: 文件扩展名，为 None 时保持扩展名不变

    Returns:
        文件名
    """
    file_name = file.split("/")[-1]  # 除去原路径，保留文件名
    file_name = file_name.split(".")
    if extension:
        if len(file_name) > 1:  # 若需要更改扩展名且已存在文件扩展名，则去除
            del file_name[-1]
        file_name[-1] += ".{}".format(extension.lstrip("."))  # 增加扩展名

    file_name = ".".join(file_name)  # 考虑文件名含多个 "." 的情况
    return "{}/{}".format(path.rstrip("/"), file_name)  # 将文件名与输出路径合并

def _color(r: int, g: int, b: int) -> int:
    """
    将 (0-255) 值的：红绿蓝 转换为 16-bit 的 565 编码

    Args:
        r: 红
        g: 绿
        b: 蓝

    Returns:
        color (int): 0-65535
    """
    return (r & 0xf8) << 8 | (g & 0xfc) << 3 | b >> 3


def _calculate_palette(color, bg_color) -> tuple:
    """
    通过 主体颜色 和 背景颜色 计算调色板

    Args:
        color: 主体颜色
        bg_color: 背景颜色
    """
    return [bg_color & 0xFF, (bg_color & 0xFF00) >> 8], [color & 0xFF, (color & 0xFF00) >> 8]


def _flatten_byte_data(byte_data, palette) -> bytearray:
    """
    将 二进制 黑白图像渲染为 RGB565 彩色图像
    Args:
        byte_data: 图像数据
        palette: 调色板

    Returns:

    """
    _temp = []
    r = range(7, -1, -1)
    for _byte in byte_data:
        for _b in r:
            _temp.extend(palette[(_byte >> _b) & 0x01])
    return bytearray(_temp)

def _convert_image(file, output_path=".", convert_type="1", size: tuple = None, image_type: str = "pbm"):
    """
    将图片转换为 指定 格式

    Args:
        file: 原图片路径
        output_path: 输出路径（文件夹）
        convert_type: 图像类型（"1" 为黑白图像，"RGBA" 为彩色图像）
        size: 图像大小
        image_type: 图像类型（图像文件后缀名）
    """
    with Image.open(file, "r") as img:
        img2 = img.convert(convert_type)
        if size:
            img2 = img2.resize(size, Image.LANCZOS)
        file_path = _get_output_path(file, output_path, image_type)
        path = file_path.split('/')
        del path[-1]
        path = "/".join(path)
        if not os.path.exists(path):
            os.makedirs(path)
        img2.save(file_path)

def image_to_pbm(file, output_path=".", convert_type="1", size: tuple = None):
    """
    将图片转换为 PBM 格式

    Args:
        file: 原图片路径
        output_path: 输出路径（文件夹）
        convert_type: 图像类型（"1" 为黑白图像，"RGBA" 为彩色图像）
        size: 图像大小
    """
    _convert_image(file, output_path, convert_type, size, "pbm")

def image_to_bmp(file, output_path=".", convert_type="1", size: tuple = None):
    """
    将图片转换为 BMP 格式

    Args:
        file: 原图片路径
        output_path: 输出路径（文件夹）
        convert_type: 图像类型（"1" 为黑白图像，"RGBA" 为彩色图像）
        size: 图像大小
    """
    _convert_image(file, output_path, convert_type, size, "bmp")

def pbm_to_dat(file, output_path=".", color: int = 65535, bg_color: int = 0, reverse: bool = False):
    """
    将 PBM 图片转换为 micropython-easydisplay 专用的 DAT 格式

    Args:
        file: 原图片路径
        output_path: 输出路径（文件夹）
        color: 图案颜色（仅黑白两色的 PBM 图片生效）
        bg_color: 背景颜色（仅黑白两色的 PBM 图片生效）
        reverse: 图像颜色反转
    """
    with open(file, "rb") as img:
        file_format = img.readline()  # 读取文件格式
        if file_format == b"P4\n" or file_format == b"P6\n":
            _width, _height = [int(value) for value in img.readline().split()]  # 获取图片的宽度和高度
            with open(_get_output_path(file, output_path, "dat"), "wb") as f:
                f.write('EasyDisplay\nV1\n{} {}\n'.format(_width, _height).encode('utf-8'))  # 写入文件头
                print(_width, _height)
                if file_format == b"P4\n":
                    palette = _calculate_palette(color, bg_color)  # 计算调色板
                    data = img.read(4096)
                    while data:
                        if reverse:
                            data = bytes([~b & 0xFF for b in data])
                        f.write(_flatten_byte_data(data, palette))
                        data = img.read(4096)
                elif file_format == b"P6\n":
                    max_pixel_value = img.readline()  # 获取最大像素值
                    buffer = bytearray(_width * 2)
                    for _y in range(_height):  # 逐行处理图片
                        for _x in range(_width):  # 逐像素处理
                            color_bytearray = img.read(3)
                            r, g, b = color_bytearray[0], color_bytearray[1], color_bytearray[2]
                            if reverse:
                                r = 255 - r
                                g = 255 - g
                                b = 255 - b
                            buffer[_x * 2: (_x + 1) * 2] = _color(r, g, b).to_bytes(2, 'big')  # 通过索引赋值
                        f.write(buffer)
        else:
            try:
                raise TypeError("[ERROR] Unsupported File Format {} !".format(file_format.rstrip(b"\n")))
            except:
                raise TypeError("[ERROR] Unsupported File Format!")


if __name__ == "__main__":
    # 使用示例
    image_to_pbm("(image_file_path)", "(image_output_folder)", "RGBA", size=(64, 64))
    pbm_to_dat("(pbm_file_path)", "(image_output_folder)")
    image_to_bmp("(image_file_path)", "(image_output_folder)", "RGBA", size=(64, 64))

