import cv2
import os
import numpy as np
import tkinter
import tkinter.messagebox
from PIL import Image, ImageTk
from Detector import VideoUtil
from Detector import Transformer
import argparse

if __name__ == '__main__':
    lastDraw = None
    parser = argparse.ArgumentParser(description='数据集图像裁剪器')
    parser.add_argument('--save_dir', type=str, help='截取后所保存的文件夹', default='dataset/')
    parser.add_argument('-video', '--video', type=str, help='视频文件名', default=None)
    parser.add_argument('-imgdir', '--image_dir', type=str, help='存放照片的文件夹名', default=None)
    parser.add_argument('-image', '--image', type=str, help='单个图片的文件名', default=None)
    args = parser.parse_args()

    if len(os.listdir(args.save_dir)) is not 0:
        savedjpgs = os.listdir(args.save_dir)
        savedjpgs.sort()
        try:
            savedIndex = int(savedjpgs[-1].split('.')[0]) + 1
        except ValueError as e:
            savedIndex = 1
    else:
        savedIndex = 1
    imageFiles = None
    imageFilesIndex: int = 0


class GUI:
    """
    对视频、图片进行批量裁剪的主窗体类。鼠标功能：拖动即可截取图片，拖动完毕切换到下一张。
    键盘功能：
    1：视频剪辑状态下，跳过一秒后读取一帧。图片裁剪状态下跳到下一张图片
    2：视频剪辑状态下，跳过二秒后读取一帧。图片裁剪状态下跳到下两张图片
    3-9同理。0代表10，Enter代表30
    Space：同一张图片可多拖拽截取一次
    -：逆向跳转，可读取之前的帧，跳转幅度取反（只适用于视频模式）
    a：增加跳转幅度（每次跳过的秒数要乘跳转幅度，只适用于视频模式）
    d：减小跳转幅度（每次跳过的秒数要乘跳转幅度，只适用于视频模式）
    """

    def __init__(self, videoStream):
        self.videoStream = videoStream
        self.root = tkinter.Tk()  # 创建主窗口
        self.root.state("zoomed")
        self.staticText = None
        self.tkImg = self.frame2TkImage(self.readFrame())
        # canvas尺寸
        screenWidth = self.tkImg.width()  # root.winfo_screenwidth()
        screenHeight = self.tkImg.height()  # root.winfo_screenheight()
        self.canvas = tkinter.Canvas(self.root, bg='white', width=screenWidth, height=screenHeight)
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor='nw', image=self.tkImg)
        self.title()
        self.root.geometry(str(self.tkImg.width()) + 'x' + str(self.tkImg.height()))
        self.canvas.bind('<Button-1>', self.leftMouse_Down)  # 鼠标左键
        self.canvas.bind('<B1-Motion>', self.mouse_Drag)  # 鼠标拖动
        self.canvas.bind('<ButtonRelease-1>', self.leftMouse_Up)  # 鼠标抬起
        self.root.bind('<Return>', self.enter_Press)  # enter键
        self.root.bind('<Key>', self.key_Press)  # 数字键
        self.root.bind('<space>', self.space_Press)  # 空格键
        self.canvas.place(x=0, y=0)  # pack(fill=tkinter.Y,expand=tkinter.YES)
        # self.root.resizable(False, False)
        self.X = tkinter.IntVar(value=0)
        self.Y = tkinter.IntVar(value=0)
        self.selectPosition = None
        self.LPCountInPicture = 1
        self.偏移系数 = 1
        # 启动消息主循环
        self.root.mainloop()

    def frame2TkImage(self, frame: np.ndarray) -> ImageTk.PhotoImage:
        """
        转换frame为tkImage
        Args:
            frame: 原始帧

        Returns: 对应的tkImage

        """
        return ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))

    def videoMode(self) -> bool:
        """
        当前是否为视频模式
        Returns:

        """
        return self.videoStream is not None

    def imageMode(self) -> bool:
        """
        当前是否是图片模式
        Returns:

        """
        return args.image is not None

    def imagedirMode(self) -> bool:
        """
        当前是否是图片文件夹模式
        Returns:

        """
        return args.image_dir is not None

    def readFrame(self) -> np.ndarray:
        """
        读取一帧，无论何种模式
        Returns:

        """
        if self.videoMode():
            self.frame = VideoUtil.ReadFrame(self.videoStream)
            return self.frame
        elif self.imageMode():
            self.frame = Transformer.Imread(args.image)
            return self.frame
        elif self.imagedirMode():
            global imageFiles, imageFilesIndex
            if imageFiles is None:
                imageFiles = os.listdir(args.image_dir)
                imageFiles = [os.path.join(args.image_dir, filename) for filename in imageFiles]
            # return Transformer.Imread(str(param))
            self.frame = Transformer.Imread(imageFiles[imageFilesIndex % len(imageFiles)])
            imageFilesIndex += 1
            return self.frame

    def showNextFrame(self, skipTimes=None) -> None:
        '''
        加载并显示视频之后的图像。
        Args:
            skipTimes: 如果是文件夹模式则为跳过几张图片。如果是视频模式则为跳过几秒（偏移系数未变时）。

        Returns:

        '''
        # if skippedSeconds is None:
        #     skippedSeconds = VideoUtil.GetFps(self.videoStream) if self.videoMode() else 1
        # else:
        #     skippedSeconds *= VideoUtil.GetFps(self.videoStream) if self.videoMode() else 1
        skipTimes = skipTimes if skipTimes is not None else 1
        if self.videoMode():
            VideoUtil.SkipReadFrames(self.videoStream, VideoUtil.GetFps(self.videoStream) * skipTimes * self.偏移系数)
            self.frame = self.readFrame()
        else:
            global imageFilesIndex
            imageFilesIndex += skipTimes - 1  # 标记完索引已自动跳到下一张
            # self.img = Image.open(r"C:\Users\william\ITCP Web\ScenePics\正常\20200109\20200109091040849.jpg")
            # self.img = ImageTk.PhotoImage(self.img)
            self.frame = self.readFrame()

        self.tkImg = self.frame2TkImage(self.frame)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tkImg)

    def title(self, titleText=None, staticText=None) -> None:
        """
        设置显示窗口标题
        Args:
            titleText: 当前要显示的临时内容
            staticText: 需要一直在标题显示的内容

        Returns:

        """
        if staticText is not None:
            self.staticText = staticText
        mTitle = 'DatasetMaker'
        if self.staticText is not None:
            mTitle += ' [' + self.staticText + ']'
        if titleText is not None:
            mTitle += ' (' + titleText + ')'
        self.root.title(mTitle)

    def key_Press(self, event):
        """
        键盘按下事件
        Args:
            event:

        Returns:

        """
        if '1' <= event.char <= '9':
            self.showNextFrame(int(event.char))
        elif event.char is '0':
            self.showNextFrame(10)
        elif self.videoMode():
            if event.char is '-':
                self.偏移系数 *= -1
                self.title(staticText='倍率=' + str(self.偏移系数))
            elif event.char is 'a':
                self.偏移系数 *= 2
                self.title(staticText='倍率=' + str(self.偏移系数))
            elif event.char is 'd':
                self.偏移系数 /= 2
                self.title(staticText='倍率=' + str(self.偏移系数))

    def enter_Press(self, event):
        """
        回车按下事件
        Args:
            event:

        Returns:

        """
        self.showNextFrame(30)

    def space_Press(self, event):
        """
        空格按下事件
        Args:
            event:

        Returns:

        """
        self.LPCountInPicture += 1

    # 鼠标左键按下的位置
    def leftMouse_Down(self, event):
        """
        鼠标左键KeyDown事件
        Args:
            event:

        Returns:

        """
        self.X.set(event.x)
        self.Y.set(event.y)
        # 开始画框的标志
        self.sel = True

    # 鼠标左键移动，显示选取的区域
    def mouse_Drag(self, event):
        """
        鼠标左键拖拽事件
        Args:
            event:

        Returns:

        """
        if not self.sel:
            return
        global lastDraw
        try:
            # 删除刚画完的图形，否则鼠标移动的时候是黑乎乎的一片矩形
            self.canvas.delete(lastDraw)
        except Exception as e:
            pass
        lastDraw = self.canvas.create_rectangle(self.X.get(), self.Y.get(), event.x, event.y, outline='yellow')

    # 获取鼠标左键抬起的位置，记录区域
    def leftMouse_Up(self, event):
        """
        鼠标左键KeyUp事件
        Args:
            event:

        Returns:

        """
        self.sel = False
        try:
            self.canvas.delete(lastDraw)
        except Exception as e:
            pass
        upx = event.x
        upy = event.y
        upx = upx
        upy = upy
        myleft, myright = sorted([self.X.get(), upx])
        mytop, mybottom = sorted([self.Y.get(), upy])
        self.selectPosition = (myleft, myright, mytop, mybottom)
        print("选择区域：xmin:" + str(self.selectPosition[0]) + ' ymin:' + str(
            self.selectPosition[2]) + ' xmax:' + str(self.selectPosition[1]) + ' ymax:' + str(
            self.selectPosition[3]))  # my，对应image中坐标信息
        self.cutPictureAndShow()

    def cutPictureAndShow(self) -> None:
        """
        裁剪图片，保存，并显示
        Returns:

        """
        myleft, myright, mytop, mybottom = [x for x in self.selectPosition]
        # 新添加Label控件和Entry控件以及Button，接收在canvas中点出的框坐标
        self.canvas.create_rectangle(myleft, mytop, myright, mybottom, outline="red")
        global savedIndex
        savedFile = args.save_dir + str(savedIndex) + '.jpg'
        GUI.cutImwrite(savedFile, self.frame, self.selectPosition)
        savedIndex += 1
        print(savedFile, '已保存')
        self.title(savedFile + ' 已保存')
        if self.imageMode():
            return
        if self.LPCountInPicture is 1:
            self.showNextFrame()
        else:
            self.LPCountInPicture -= 1

    @staticmethod
    def cutImwrite(savedFileName: str, image: np.ndarray, *positions: int):
        """
        裁剪图片并保存
        Args:
            savedFileName: 要保存的图片文件名
            image: 需要被裁减的图片
            *positions: [左，右，上，下坐标]。要求：左<右，上<下

        Returns:

        """
        myleft, myright, mytop, mybottom = [x for x in positions]
        clipFrame = image[mytop:mybottom, myleft:myright]
        Transformer.Imwrite(savedFileName, clipFrame)


if __name__ == '__main__':
    if args.video is not None:
        video = args.video
        video = video.replace('\"', '')
        GUI(VideoUtil.OpenInputVideo(video))
    elif args.image is not None:
        GUI(None)
    elif args.image_dir is not None:
        GUI(None)
