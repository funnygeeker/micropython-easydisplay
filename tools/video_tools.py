import os

try:
    import cv2
except ImportError:
    os.system('pip3 install opencv-python -i https://mirrors.aliyun.com/pypi/simple/')
    import cv2

def convert_video_to_png(video_path:str, output_path:str, interval:int = 10):
    """
    将视频转换为图片

    Args:
        video_path: 视频文件路径
        output_path: 图片输出路径（文件夹）
        interval: 每间隔 X 帧，截取取一张图片
    """
    num = 1
    vid = cv2.VideoCapture(video_path)
    while vid.isOpened():
        is_read, frame = vid.read()
        if is_read:
            if num % interval == 1:
                file_num = '%08d' % num
                cv2.imwrite(f"{output_path.rstrip('/')}/{file_num}.png", frame)
                # 00000100.jpg 代表第111帧
                cv2.waitKey(1)
            num += 1
        else:
            break
