## 字体文件（Chinese）

### 文件格式
- `.bmf` 文件均为本 `micropython-easydisplay` 项目的字体文件，包含了一些常见字体。
- `.txt` 文件为字体文件生成时的原始字体集，一般包含了常见的中文，英文，日文，以及其他文字和符号。

### 说明
- `text_full` 拥有完善的字体集和符号，可用于绝大部分使用场景，需要较大的存储空间
- `text_lite` 拥有精简的字体集和符号，能够应对基本的使用场景，需要较小的存储空间

### 分辨率
- 该版本字体提供了 `8px`，`16px`，`24px`，`36px` 像素的字体，请根据实际情况按需选择
- 一般 `8px` 用于点阵屏（`MAX7219`），`16px` 用于低分辨率屏幕（`SSD1306` `ST7735`），`24px` 一般用于 （`ST7789`）
### 兼容性
- 当前字体版本为 `V3` 版本，与 [MicroPython-uFont](https://github.com/AntonVanke/MicroPython-uFont) 项目通用

### TTF 字体文件
- `8px`：[观致8px](https://www.maoken.com/freefonts/11358.html)
- `16px` `24px` `32px`：[Unifont](https://unifoundry.com/)

### 制作 BMF 字体文件
- [https://github.com/AntonVanke/MicroPython-uFont-Tools](https://github.com/AntonVanke/MicroPython-uFont-Tools)


## Font Files

### File Format
- `.bmf` files are font files for the `micropython-easydisplay` project, containing various common fonts.
- `.txt` files are the original font sets used to generate the font files and typically include common Chinese, English, Japanese, and other characters and symbols.

### Explanation
- `text_full` has a complete font set and symbols, suitable for most scenarios but requires larger storage space.
- `text_lite` has a streamlined font set and symbols, suitable for basic scenarios with smaller storage space requirements.

### Resolution
- This version of the font provides fonts in pixel sizes of `8px`, `16px`, `24px`, and `36px`. Please select the appropriate size based on your needs.
- Typically, `8px` is used for dot matrix screens (`MAX7219`), `16px` for low-resolution screens (`SSD1306` `ST7735`), and `24px` is commonly used for (`ST7789`).

### Compatibility
- The current font version is `V3` and is compatible with the [MicroPython-uFont](https://github.com/AntonVanke/MicroPython-uFont) project.

### TTF Font File
- `8px`：[观致8px](https://www.maoken.com/freefonts/11358.html)
- `16px` `24px` `32px`：[Unifont](https://unifoundry.com/)

### Create BMF Font Files
- [https://github.com/AntonVanke/MicroPython-uFont-Tools](https://github.com/AntonVanke/MicroPython-uFont-Tools)
