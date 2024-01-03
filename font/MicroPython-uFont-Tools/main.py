import tkinter as tk
from tkinter.filedialog import askopenfilename, asksaveasfile
from tkinter.messagebox import showinfo, showerror

from PIL import ImageTk, ImageDraw, Image, ImageFont

from bitmapfonts import run


def set_font_file():
    """设置字体文件

    Returns:

    """
    global font_file
    font_file = askopenfilename(title='选择字体文件',
                                filetypes=[('Font File', '*.ttf'), ('Font File', '*.ttc'), ('Font File', '*.otf'),
                                           ('All Files', '*')],
                                initialdir="./")
    font_file_show.set(font_file)
    get_image()


def set_text_file():
    """选择字体集文件

    Returns:

    """
    global text_file, text
    text_file = askopenfilename(title='选择字符集文件',
                                filetypes=[('文本文件', '*.txt'), ('All Files', '*')], initialdir="./")
    text_file_buf = open(text_file, "r", encoding="utf-8")
    text = text_file_buf.read()
    text_input.delete("1.0", tk.END)
    text_input.insert(tk.END, text)
    text_len.set(f'字符数量: {len(set(text))}')
    text_file_show.set(text_file)
    get_image()


def save_file():
    """生成点阵字体文件
    Returns:

    """
    if font_size.get() == 0 or text == "" or font_file == "":
        showerror(title="生成失败", message="信息填写不完全!")
        return False
    bitmap_fonts_file = tk.filedialog.asksaveasfile(mode='wb',
                                                    title="选择棋谱",
                                                    initialdir="./",
                                                    defaultextension=".bmf",
                                                    filetypes=[("BitMap Font", ".bmf")])
    if bitmap_fonts_file is None:
        return False
    data = run(font_file=font_file, font_size=font_size.get(), offset=(offset_x.get(), offset_y.get()),
               text=text, bitmap_fonts_file=bitmap_fonts_file)
    showinfo(title="生成成功", message=f"字体文件:{data[3]}\n字符数量:{data[0]}个\n字体大小:{data[2] / 1024:.2f}KByte\n字号大小:{data[4]}px")


def text_input_update(_):
    global text
    text = text_input.get("1.0", tk.END)[:-1]
    text_len.set(f'字符数量: {len(set(text))}')


def get_image(*args):
    global img
    if font_file == "":
        return False
    im = Image.new('1', (font_size.get(), font_size.get()), (1,))
    draw = ImageDraw.Draw(im)
    if len(preview_text.get()) >= 1:
        estimated_size.set(
            f"预计大小:{(16 + len(set(text)) * font_size.get() ** 2 // 8 + len(set(text)) * 2) / 1024:.2f}KBytes")
        draw.text((offset_x.get(), offset_y.get()), preview_text.get()[0],
                  font=ImageFont.truetype(font=font_file, size=font_size.get()))
        img = ImageTk.BitmapImage(im)
        img_label = tk.Label(font_preview, bd=1, relief="sunken", image=img)
        img_label.place(x=95, y=100, width=50, height=50, anchor="center")
        return True
    return False


root = tk.Tk()
root.title("BitMap Font Tools")
root.geometry("620x620")
root.minsize(620, 620)
root.maxsize(620, 620)

font_file = ""
text_file = ""
text = ""

estimated_size = tk.StringVar()
font_size = tk.IntVar()
font_file_show = tk.StringVar()
text_file_show = tk.StringVar()
offset_x = tk.IntVar()
offset_y = tk.IntVar()
font_size.set(16)

#
# 第一部分
#
setting_frame = tk.LabelFrame(root, text="参数设置")
setting_frame.place(x=10, y=10, width=400, height=300)

# 字体文件设置
font_file_frame = tk.LabelFrame(setting_frame, text="字体选择")
font_file_frame.pack()
tk.Entry(font_file_frame, textvariable=font_file_show, width=30).grid(row=1, column=1)
tk.Button(font_file_frame, text="选择文件", command=set_font_file).grid(row=1, column=2)

# 字符集设置
text_file_frame = tk.LabelFrame(setting_frame, text="字体集选择")
text_file_frame.pack()
tk.Entry(text_file_frame, textvariable=text_file_show, width=30).grid(row=1, column=1)
tk.Button(text_file_frame, text="选择文件", command=set_text_file).grid(row=1, column=2)

# 字号设置
font_size_frame = tk.LabelFrame(setting_frame, text="字号")
font_size_frame.pack()
tk.Scale(font_size_frame, variable=font_size, from_=8, to=40, orient=tk.HORIZONTAL, length=280, command=get_image).grid(
    row=1, column=1)
tk.Button(font_size_frame, text="重置大小", command=lambda: font_size.set(16) or get_image()).grid(row=1, column=2)

# 偏移设置
offset_frame = tk.LabelFrame(setting_frame, text="偏移")
offset_frame.pack()
tk.Label(offset_frame, text="x轴偏移").grid(row=1, column=1)
tk.Scale(offset_frame, variable=offset_x, from_=-16, to=16, orient=tk.HORIZONTAL, length=230, command=get_image).grid(
    row=1, column=2)

tk.Label(offset_frame, text="y轴偏移").grid(row=2, column=1)
tk.Scale(offset_frame, variable=offset_y, from_=-16, to=16, orient=tk.HORIZONTAL, length=230, command=get_image).grid(
    row=2, column=2)
tk.Button(offset_frame, text="重置偏移", command=lambda: offset_y.set(0) or offset_x.set(0) or get_image()).grid(row=2,
                                                                                                             column=3)

#
# 第二部分
#
text_len = tk.StringVar()
text_len.set("字符数量: 0")

text_frame = tk.LabelFrame(root, text="字体集预览")
text_frame.place(x=10, y=310, width=400, height=300)

tk.Label(text_frame, textvariable=text_len).pack(side=tk.BOTTOM)

text_scroll = tk.Scrollbar(text_frame)
text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

text_input = tk.Text(text_frame, wrap=tk.CHAR, undo=True, yscrollcommand=text_scroll.set, width=50)
text_input.pack()

text_scroll.config(command=text_input.yview)
text_input.bind('<KeyRelease>', text_input_update)

#
# 第三部分
#
preview_text = tk.StringVar()
preview_text.set("你")

font_preview = tk.LabelFrame(root, text="预览")
font_preview.place(x=420, y=10, width=190, height=200)
preview_text_input = tk.Entry(font_preview, textvariable=preview_text, width=8)
preview_text_input.bind("<KeyRelease>", get_image)
preview_text_input.grid(row=1, column=1)
tk.Button(font_preview, text="更新图像", command=get_image).grid(row=1, column=2)

#
# 第四部分
#
bmf_generate = tk.LabelFrame(root, text="生成")
bmf_generate.place(x=420, y=220, width=190, height=390)
tk.Label(bmf_generate, textvariable=estimated_size).grid(row=1, column=1)
tk.Button(bmf_generate, text="生成点阵文件", command=save_file).grid(row=2, column=1)

root.mainloop()
