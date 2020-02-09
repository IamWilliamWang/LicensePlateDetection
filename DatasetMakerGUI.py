import argparse
import os
import tkinter
import tkinter.messagebox

import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont

import LPDetector
from DetectorUtil import Transformer
from DetectorUtil import VideoUtil

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='数据集图像裁剪器')
    parser.add_argument('--save_dir', type=str, help='截取后所保存的文件夹', default='dataset/')
    parser.add_argument('-video', '--video', type=str, help='视频文件名', default=None)
    parser.add_argument('-imgdir', '--image_dir', type=str, help='存放照片的文件夹名', default=None)
    parser.add_argument('-image', '--image', type=str, help='单个图片的文件名', default=None)
    parser.add_argument('-smart', '--enable_smart_tool', type=int, help='开启自动标注插件，识别出车牌会自动提前标注', default=1)
    args = parser.parse_args()


# region 数据库
class DbLite:
    fp = None

    @staticmethod
    def OpenConnect():
        DbLite.databaseName = args.save_dir + 'database.csv'
        if os.path.exists(DbLite.databaseName):
            DbLite.fp = open(DbLite.databaseName, 'a')
        else:
            DbLite.fp = open(DbLite.databaseName, 'w')
            DbLite.fp.write('原文件,新文件,左,右,上,下,宽度,高度\n')

    @staticmethod
    def append(originalFileName, newFileName, left, right, top, bottom):
        DbLite.fp.write(
            originalFileName + ',' + newFileName + ',' + str(left) + ',' + str(right) + ',' + str(top) + ',' + str(
                bottom) + ',' + str(right - left) + ',' + str(bottom - top) + '\n')

    @staticmethod
    def close():
        DbLite.fp.close()


# endregion

# region 自制InputBox
class _Inputbox():
    def __init__(self, title, description, defaultText):
        self._root = tkinter.Tk()
        scrrenWidth = self._root.winfo_screenwidth()  # 获取桌面宽度
        screenHeight = self._root.winfo_screenheight()  # 获取桌面高度
        width = 320  # 输入框的宽度
        height = 100  # 输入框的高度
        startx = (scrrenWidth - width) / 2  # 起始x坐标（居中显示用)
        starty = (screenHeight - height) / 2  # 起始y坐标
        # self._root.geometry("%dx%d%+d%+d" % (width, height, startx, starty))
        self._root.geometry("%+d%+d" % (startx, starty))
        self._root.resizable(False, False)
        self._root.title(title)
        if description is not '':
            self.label = tkinter.Label(self._root, text=description)
            self.label.pack()
        self.textbox = tkinter.Entry(self._root, width=36, textvariable=tkinter.StringVar(value=defaultText))
        self.textbox.pack(padx=3, side=tkinter.LEFT)
        self.textbox.focus()
        self.textbox.bind_all("<Return>", self._enterPressed)  # 绑定回车键
        self.button = tkinter.Button(self._root, text='确定', command=self._buttonClicked)  # 确定按钮
        self.button.pack(padx=2, side=tkinter.RIGHT)  # 放在右边
        self.text = ''
        self._root.focus_force()
        self._root.mainloop()

    def _buttonClicked(self):
        self.text = self.textbox.get()
        self._root.destroy()
        self._root.quit()

    def _enterPressed(self, event):
        self._buttonClicked()


def inputbox(title="请输入", description="", defaultText=""):
    inputForm = _Inputbox(title, description, defaultText)
    return inputForm.text


# endregion

class GUI:
    """
    对视频、图片进行批量裁剪的主窗体类。
    鼠标功能：<bold>添加</bold>标注图片。拖动截选区域后输入对应的车牌号，可以标记车牌。
    键盘功能：
    数字1-9：视频剪辑状态下，跳过n秒后读取一帧。图片裁剪状态下跳到下n张图片（0代表10）
    Enter：<bold>修改</bold>当前已标的车牌数据
    Delete：<bold>删除</bold>当前的所有标记
    Space：<bold>保存</bold>截取的图片，并按下1键
    -：逆向跳转，可读取之前的帧，跳转幅度取反（只适用于视频模式）
    a：增加跳转幅度（每次跳过的秒数要乘跳转幅度，只适用于视频模式）
    d：减小跳转幅度（每次跳过的秒数要乘跳转幅度，只适用于视频模式）
    """
    __slots__ = (
        'videoStream',  # 储存视频流
        'staticText',  # 标题中一直显示的文字
        'root',  # 主窗口
        'canvas',  # 主画布
        'X', 'Y',  # 储存鼠标选中时的坐标
        '偏移系数',  # 读取下一帧需要跨越的秒数
        'baseFrame',  # 读取视频或图片的原视帧
        'baseTkImg',  # baseFrame转换成TkImage格式
        'draging',  # 是否正在拖拽操作
        'boxesAndLabels',  # 储存当前画面中各个车牌信息的字典列表。[{'left': ,'right': ,'top': ,'bottom': ,'label': }]
        'rectanglesAndLabels'  # 储存当前画面中各个方框和添加的文字信息的元组列表[(rectangle, text)]
    )

    def __init__(self, videoStream):
        # 初始化属性
        self.videoStream = videoStream
        self.staticText = None
        # 初始化一般变量
        global lastDragedRectangle, lastDrawedText, imageFiles, imageFilesIndex, saveRawFileName
        lastDragedRectangle, lastDrawedText = None, None
        imageFiles = None
        imageFilesIndex = 0
        self.偏移系数 = 1
        self.boxesAndLabels = []
        self.rectanglesAndLabels = []
        # 创建主窗口
        self.root = tkinter.Tk()
        self.root.state("zoomed")
        self.baseFrame = self.readFrame()
        self.baseTkImg = self.frame2TkImage(self.baseFrame)
        # 设定主窗口大小，绑定事件
        self.root.geometry(str(self.baseTkImg.width()) + 'x' + str(self.baseTkImg.height()))
        self.root.bind_all('<Return>', self.enter_Press)  # enter键
        self.root.bind_all('<Key>', self.key_Press)  # 数字键
        self.root.bind_all('<space>', self.space_Press)  # 空格键
        self.root.bind_all('<Delete>', self.removeRectanglesAndLabels)  # delete键清空
        self.root.resizable(False, False)
        self.title()  # 刷新界面标题
        # 创建canvas，绑定事件
        screenWidth = self.baseTkImg.width()  # root.winfo_screenwidth()
        screenHeight = self.baseTkImg.height()  # root.winfo_screenheight()
        self.canvas = tkinter.Canvas(self.root, bg='white', width=screenWidth, height=screenHeight)
        self.setCanvasImg(self.baseTkImg)
        self.canvas.bind('<Button-1>', self.mouseDownLeft)  # 鼠标左键
        self.canvas.bind('<B1-Motion>', self.mouseDrag)  # 鼠标拖动
        self.canvas.bind('<ButtonRelease-1>', self.mouseUpLeft)  # 鼠标抬起
        self.canvas.place(x=0, y=0)  # pack(fill=tkinter.Y,expand=tkinter.YES)
        self.canvas.pack()
        # 打开标记记录数据库
        DbLite.OpenConnect()
        # 初始化鼠标事件的位置容器
        self.X = tkinter.IntVar(value=0)
        self.Y = tkinter.IntVar(value=0)

    def on_closing(self):
        DbLite.close()
        self.root.quit()

    def showDialog(self):
        """
        启动消息主循环
        """
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    # region 工具函数
    def frame2TkImage(self, frame: np.ndarray) -> ImageTk.PhotoImage:
        """
        转换frame为tkImage。（潜在的bug：只能转换一次，多次转换同一张图会返回空白！！）
        Args:
            frame: 原始帧

        Returns: 对应的tkImage

        """
        return ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))

    def isVideoMode(self) -> bool:
        """
        当前是否为视频模式
        Returns:

        """
        return self.videoStream is not None

    def isImageMode(self) -> bool:
        """
        当前是否是图片模式
        Returns:

        """
        return args.image is not None

    def isImageDirMode(self) -> bool:
        """
        当前是否是图片文件夹模式
        Returns:

        """
        return args.image_dir is not None

    def title(self, titleText=None, staticText=None) -> None:
        """
        设置显示窗口标题
        Args:
            titleText: 当前要显示的临时内容
            staticText: 需要一直在标题显示的内容
        """
        if staticText is not None:
            self.staticText = staticText
        mTitle = '智能车牌数据标注器'
        if self.staticText is not None:
            mTitle += ' [' + self.staticText + ']'
        if titleText is not None:
            mTitle += ' (' + titleText + ')'
        self.root.title(mTitle)

    def cv2ImgAddText(self, img, text, pos, textColor=(255, 0, 0), textSize=12):
        """
        @see LPRNet.LPRNet_Test.cv2ImgAddText
        """
        if (isinstance(img, np.ndarray)):  # detect opencv format or not
            img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img)
        fontText = ImageFont.truetype("LPRNet/data/NotoSansCJK-Regular.ttc", textSize, encoding="utf-8")
        draw.text(pos, text, textColor, font=fontText)

        return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

    # endregion

    # region 读取与显示
    def setCanvasImg(self, tkImage):
        self.canvas.create_image(0, 0, anchor='nw', image=tkImage)

    def readFrame(self) -> np.ndarray:
        """
        读取一帧，无论何种模式
        Returns:

        """
        if self.isVideoMode():
            frame = VideoUtil.ReadFrame(self.videoStream)
            return frame
        elif self.isImageMode():
            frame = Transformer.Imread(args.image)
            return frame
        elif self.isImageDirMode():
            global imageFiles, imageFilesIndex
            if imageFiles is None:
                imageFiles = os.listdir(args.image_dir)
                imageFiles = [os.path.join(args.image_dir, filename) for filename in imageFiles]
            frame = Transformer.Imread(imageFiles[imageFilesIndex % len(imageFiles)])
            imageFilesIndex += 1
            return frame

    def removeRectangleAndLabelAt(self, removeIndex=-1, removeRectangle=False, removeLabel=False):
        if removeRectangle:
            lastDrawedRectangle = self.rectanglesAndLabels[removeIndex][0]
            self.canvas.delete(lastDrawedRectangle)
        if removeLabel:
            lastDrawedText = self.rectanglesAndLabels[removeIndex][1]
            self.canvas.delete(lastDrawedText)

    def removeRectanglesAndLabels(self, event=None):
        for rectangleLabel in self.rectanglesAndLabels:
            self.canvas.delete(rectangleLabel[0])
            self.canvas.delete(rectangleLabel[1])

    def refreshRectanglesAndLabels(self):
        self.removeRectanglesAndLabels()
        self.rectanglesAndLabels = []
        for licensePlateDict in self.boxesAndLabels:
            lastDrawedRectangle = self.canvas.create_rectangle(licensePlateDict['left'], licensePlateDict['top'],
                                                               licensePlateDict['right'], licensePlateDict['bottom'],
                                                               outline="red")
            lastDrawedText = self.canvas.create_text(licensePlateDict['left'] + 37, licensePlateDict['top'] - 10,
                                                     text=licensePlateDict['label'], font=('宋体', 15), fill='red')
            self.rectanglesAndLabels += [(lastDrawedRectangle, lastDrawedText)]

    def loadNextFrame(self, skipSteps=None) -> None:
        '''
        加载并显示之后的图像/图片。
        Args:
            skipSteps: 如果是文件夹模式则为跳过几张图片。如果是视频模式则为跳过几秒（偏移系数未变时）。

        Returns:

        '''
        skipSteps = skipSteps if skipSteps is not None else 1
        if self.isVideoMode():
            VideoUtil.SkipReadFrames(self.videoStream, VideoUtil.GetFps(self.videoStream) * skipSteps * self.偏移系数)
            self.baseFrame = self.readFrame()
        else:
            global imageFilesIndex
            imageFilesIndex += skipSteps - 1  # 标记完索引已自动跳到下一张
            self.baseFrame = self.readFrame()
        self.baseTkImg = self.frame2TkImage(self.baseFrame)
        self.setCanvasImg(self.baseTkImg)
        if args.enable_smart_tool is 1:
            # 开始检测车牌号
            self.boxesAndLabels = LPDetector.getBoxesAndLabels(self.baseFrame, 1, (50, 15), None)
        self.refreshRectanglesAndLabels()

    # endregion

    # region 键盘事件
    def key_Press(self, event):
        """
        键盘按下事件
        Args:
            event:

        Returns:

        """
        if '1' <= event.char <= '9':
            self.loadNextFrame(int(event.char))
        elif event.char is '0':
            self.loadNextFrame(10)
        elif self.isVideoMode():
            if event.char is '-':
                self.偏移系数 *= -1
                self.title(staticText='倍率=' + str(self.偏移系数))
            elif event.char is 'a' or event.char is 'A':
                self.偏移系数 *= 2
                self.title(staticText='倍率=' + str(self.偏移系数))
            elif event.char is 'd' or event.char is 'D':
                self.偏移系数 /= 2
                self.title(staticText='倍率=' + str(self.偏移系数))

    def enter_Press(self, event):
        """
        回车按下事件
        Args:
            event:

        Returns:

        """
        changeIndex = 0
        if len(self.boxesAndLabels) > 1:
            help = ''
            for dict in self.boxesAndLabels:
                label = dict['label']
                help += label + ': ' + str(changeIndex) + ', '
                changeIndex += 1
            help = help[:-2]
            input = inputbox('要修改的对应数字:', help)
            if input is '':
                return
            changeIndex = int(input)
        input = inputbox('车牌号修改为:')
        if input is '':
            return
        self.removeRectangleAndLabelAt(removeIndex=changeIndex, removeLabel=True)
        self.boxesAndLabels[changeIndex]['label'] = input
        self.refreshRectanglesAndLabels()

    def space_Press(self, event):
        """
        空格按下事件
        Args:
            event:

        Returns:

        """
        self.cutSavePicture()
        self.loadNextFrame()

    # endregion

    # region 鼠标事件
    # 鼠标左键按下的位置
    def mouseDownLeft(self, event):
        """
        鼠标左键KeyDown事件
        Args:
            event:

        Returns:

        """
        self.X.set(event.x)
        self.Y.set(event.y)
        # 开始画框的标志
        self.draging = True

    # 鼠标左键移动，显示选取的区域
    def mouseDrag(self, event):
        """
        鼠标左键拖拽事件
        Args:
            event:

        Returns:

        """
        if not self.draging:
            return
        global lastDragedRectangle
        try:
            # 删除刚画完的图形，否则鼠标移动的时候是黑乎乎的一片矩形
            self.canvas.delete(lastDragedRectangle)
        except Exception as e:
            pass
        lastDragedRectangle = self.canvas.create_rectangle(self.X.get(), self.Y.get(), event.x, event.y,
                                                           outline='yellow')

    # 获取鼠标左键抬起的位置，记录区域
    def mouseUpLeft(self, event):
        """
        鼠标左键KeyUp事件
        Args:
            event:

        Returns:

        """
        self.draging = False
        try:
            self.canvas.delete(lastDragedRectangle)
        except Exception as e:
            pass
        upx = event.x
        upy = event.y
        myleft, myright = sorted([self.X.get(), upx])
        mytop, mybottom = sorted([self.Y.get(), upy])
        vehicle = {'left': myleft, 'right': myright, 'top': mytop, 'bottom': mybottom}
        print("选择区域：xmin:" + str(myleft) + ' ymin:' + str(mytop) + ' xmax:' + str(myright) + ' ymax:' + str(
            mybottom))  # 对应image中坐标信息
        input = inputbox('输入车辆车牌号')
        if input is not '':
            vehicle['label'] = input
            self.boxesAndLabels += [vehicle]
            print('已选中:', input)
        self.refreshRectanglesAndLabels()

    # endregion

    # region 裁剪与储存
    def cutSavePicture(self) -> None:
        """
        裁剪图片，保存，并显示
        Returns:

        """
        for dict in self.boxesAndLabels:
            left, right, top, bottom = dict['left'], dict['right'], dict['top'], dict['bottom']
            saveFullFileName, _ = LPDetector.getInconflictFileName(args.save_dir + dict['label'] + '.jpg')
            GUI.cutImwrite(saveFullFileName, self.baseFrame, left, right, top, bottom)
            if self.isImageDirMode():
                DbLite.append(imageFiles[imageFilesIndex], saveFullFileName, left, right, top, bottom)
            elif self.isImageMode():
                DbLite.append(args.image, saveFullFileName, left, right, top, bottom)
            elif self.isVideoMode():
                DbLite.append('', saveFullFileName, left, right, top, bottom)
            print(saveFullFileName, '已保存')
            self.title(saveFullFileName + ' 已保存')

    @staticmethod
    def cutImwrite(savedFileName: str, image: np.ndarray, left: int, right: int, top: int, bottom: int):
        """
        
        Args:
            savedFileName: 要保存的图片文件名
            image: 需要被裁减的图片
            left, right, top, bottom: 左，右，上，下坐标。要求：左<右，上<下

        """""
        clipFrame = image[top:bottom, left:right]
        Transformer.Imwrite(savedFileName, clipFrame)
    # endregion


if __name__ == '__main__':
    LPDetector.initialize()
    if args.video is not None:
        video = args.video
        video = video.replace('\"', '')
        GUI(VideoUtil.OpenInputVideo(video)).showDialog()
    elif args.image is not None:
        GUI(None).showDialog()
    elif args.image_dir is not None:
        GUI(None).showDialog()
