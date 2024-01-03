## 屏幕驱动（Chinese）

### 说明
- 文件名含有 `buf` 的驱动是使用 `Framebuffer` 的帧缓冲区驱动，具有较高的效率和丰富的功能，
在开发板内存充足的情况下请尽量选择该驱动


- 文件名含有 `spi` 的驱动是使用 `SPI` 对屏幕进行直接驱动，配合 `micropython-easydisplay` 使用时效率略低，
但是对内存不足以使用 `Framebuffer` 的开发板非常友好


- 部分驱动可能存在一些错误，如果您遇到了错误并修复了 `BUG`，别忘记提交 `Pull Request` 来向项目提交您的更改建议。


## Screen Drivers

### Description
- Drivers with filenames containing `buf` are `Framebuffer` drivers, which have higher efficiency and richer features. Please choose these drivers when there is sufficient memory available on the development board.


- Drivers with filenames containing `spi` are SPI drivers used for direct driving of the screen. When used with `micropython-easydisplay`, they have slightly lower efficiency but are very friendly for development boards with insufficient memory to use `Framebuffer`.


- Some drivers may have some errors. If you encounter an error and fix a bug, don't forget to submit a pull request to contribute your suggested changes to the project.