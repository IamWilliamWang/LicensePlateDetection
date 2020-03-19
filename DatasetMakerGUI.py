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
    parser = argparse.ArgumentParser(description='智能车牌数据标注器 v2.2')
    parser.add_argument('-v', '--video', type=str, help='想打开的视频文件名。对应模式：视频模式', default=None)  # 视频模式
    parser.add_argument('-dir', '--image_dir', type=str, help='储存原始照片的文件夹名。对应模式：图片文件夹模式', default=None)  # 图片文件夹模式
    parser.add_argument('-img', '--image', type=str, help='单个图片的文件名。对应模式：图片模式', default=None)  # 图片模式
    parser.add_argument('-folder', '--save_folder', type=str, help='将裁好的数据库保存在哪个文件夹。对应模式：不限',
                        default='dataset/')  # 输出文件夹设置
    parser.add_argument('-crop', '--crop_mode', action='store_true',
                        help='打开裁剪模式，只裁剪图片而不变文件名。对应模式：图片文件夹模式')  # 图片文件夹-裁剪模式（与2.0以前版本相似）
    parser.add_argument('-detail', '--show_file_detail', action='store_true',
                        help='标题栏显示当前操作的图片文件名。对应模式：不限')  # 文件名实时输出（用于调试）
    parser.add_argument('-info', '--information', action='store_true', help='显示使用说明')
    parser.add_argument('-smart', '--enable_smart_tool', action='store_true',
                        help='开启自动标注插件，每张图会自动识别出车牌后提前标注。对应模式：不限')  # 自助标注LPRNet插件
    args = parser.parse_args()
    if args.information:
        print("鼠标功能：添加标注图片。拖动截选区域后输入对应的车牌号，可以标记车牌。\n" +
              "滚轮向下滚动作为1键的快捷方式，向上滚动与之相反\n" +
              "键盘功能：\n" +
              "数字1-9：视频剪辑状态下，跳过n秒后读取一帧。图片裁剪状态下跳到下n张图片（0代表10）\n" +
              "Enter：修改当前已标的车牌数据\n" +
              "Delete：删除当前的所有标记\n" +
              "Space：保存截取的图片，并按下1键\n" +
              "-：逆向跳转，可读取之前的帧，跳转幅度取反（只适用于视频模式）\n" +
              "a：增加跳转幅度（每次跳过的秒数要乘跳转幅度，只适用于视频模式）\n" +
              "d：减小跳转幅度（每次跳过的秒数要乘跳转幅度，只适用于视频模式）")
        exit(0)
    args.save_folder = args.save_folder.replace('\"', '')
    if not os.path.exists(args.save_folder):
        os.makedirs(args.save_folder)
    if args.save_folder[-1] is not '/' and args.save_folder[-1] is not '\\':
        args.save_folder += '/'


# region 数据库
class DbLite:
    fp = None

    @staticmethod
    def open():
        """
        打开数据库。用于存储GUI.boxesAndLabels
        """
        DbLite.databaseName = args.save_folder + 'database.csv'
        if os.path.exists(DbLite.databaseName):
            DbLite.fp = open(DbLite.databaseName, 'a')
        else:
            DbLite.fp = open(DbLite.databaseName, 'w')
            DbLite.fp.write('原文件,新文件,左,右,上,下,宽度,高度\n')

    @staticmethod
    def append(originalFileName, newFileName, left, right, top, bottom):
        """
        向数据库追加数据
        Args:
            originalFileName: 源图片/源视频的地址
            newFileName: 截图文件地址
            left: 左坐标(方框中x轴最小的坐标)
            right: 右坐标(方框中x轴最大的坐标)
            top: 上坐标(方框中y轴最小的坐标)
            bottom: 下坐标(方框中y轴最大的坐标)
        """
        DbLite.fp.write(
            originalFileName + ',' + newFileName + ',' + str(left) + ',' + str(right) + ',' + str(top) + ',' + str(
                bottom) + ',' + str(right - left) + ',' + str(bottom - top) + '\n')

    @staticmethod
    def close():
        """
        关闭数据库
        """
        DbLite.fp.close()


# endregion

# region 自制InputBox
class _InputBox:
    """
    InputBox内部实现类
    """

    def __init__(self, title, description, defaultText):
        """
        初始化InputBox部件
        Args:
            title: 标题显示的内容
            description: 标题下的label显示的内容
            defaultText: 默认输入内容
        """
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
        # self._root.attributes("-toolwindow", 0)  # 去掉最大最小化按钮
        self._root.title(title)
        # 如果不为空，就添加一行label
        if description is not '':
            self.label = tkinter.Label(self._root, text=description)
            self.label.pack()
        # 添加输入框
        self.textbox = tkinter.Entry(self._root, width=36, textvariable=tkinter.StringVar(value=defaultText))
        self.textbox.pack(padx=3, side=tkinter.LEFT)
        self.textbox.focus()  # 获得焦点
        self.textbox.bind_all("<Return>", self._enterPressed)  # 绑定回车键
        self.button = tkinter.Button(self._root, text='确定', command=self._buttonClicked)  # 确定按钮
        self.button.pack(padx=2, side=tkinter.LEFT)  # 放在界面左边
        self.text = ''  # 需要得到的答案
        self._root.focus_force()  # 使窗体强制获得焦点
        self._root.mainloop()

    def _buttonClicked(self):
        """
        确认键按下事件
        """
        self.text = self.textbox.get()
        self._root.destroy()  # 销毁窗体
        self._root.quit()  # 退出窗口

    def _enterPressed(self, event):
        """
        回车键按下事件
        """
        self._buttonClicked()


def inputbox(title="请输入", description="", defaultText="") -> str:
    """
    弹出输入框，获取用户填入的文字。
    Args:
        title: 简要描述问题的问题
        description: 具体描述问题的文字
        defaultText: 输入的默认值，弹出后会先填入文本框内

    Returns:
        用户输入的文字
    """
    inputForm = _InputBox(title, description, defaultText)
    return inputForm.text


# endregion

class GUI:
    """
    对视频、图片进行批量裁剪的主窗体类。
    鼠标功能：<bold>添加</bold>标注图片。拖动截选区域后输入对应的车牌号，可以标记车牌。
    滚轮向下滚动作为1键的快捷方式，向上滚动与之相反
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
        'videoStream',  # 传入的视频流
        '_staticText',  # 标题中要一直显示的文字
        'root',  # 主窗口
        'canvas',  # 主画布
        '_X', '_Y',  # 储存鼠标选中时的坐标
        '_偏移系数',  # 读取下一帧需要跨越的秒数
        'baseFrame',  # 读取视频或图片的原视帧
        '_baseTkImg',  # TkImage格式的baseFrame
        '_draging',  # 是否正在拖拽操作
        '_lastDragedRectangle',  # 鼠标拖拽时屏幕显示的黄色方框
        'imageFiles', 'imageFilesIndex',  # 文件夹模式下的文件列表和当前显示的图片索引
        # 以下二者一一对应，len(boxesAndLabels) == len(rectanglesAndLabels)。对车牌进行处理的核心变量是boxesAndLabels
        'boxesAndLabels',  # 储存当前画面中各个车牌信息的字典列表[{'left': ,'right': ,'top': ,'bottom': ,'label': }]
        'rectanglesAndLabels'  # 储存当前画面中各个方框和添加的文字信息的元组列表[(rectangle, text)]
    )

    def __init__(self, videoStream: cv2.VideoCapture):
        # 初始化属性
        self.videoStream = videoStream
        self._staticText = None
        # 初始化一般变量
        self._lastDragedRectangle = None
        self.imageFiles = None
        self.imageFilesIndex = -1
        self._偏移系数 = 1
        self.boxesAndLabels = []
        self.rectanglesAndLabels = []
        # 创建主窗口
        self.root = tkinter.Tk()
        self.root.state("zoomed")
        self.baseFrame = self.readFrame()
        self._baseTkImg = self.frame2TkImage(self.baseFrame)
        # 设定主窗口大小，绑定事件
        self.root.geometry(str(self._baseTkImg.width()) + 'x' + str(self._baseTkImg.height()))
        self.root.bind_all('<Return>', self.enterPress)  # enter键
        self.root.bind_all('<Key>', self.keyPress)  # 数字键
        self.root.bind_all('<space>', self.spacePress)  # 空格键
        self.root.bind_all('<Delete>', self.removeRectanglesAndLabels)  # delete键清空
        self.root.bind_all("<MouseWheel>", self.mouseWheel)
        self.root.resizable(False, False)
        self.title()  # 刷新界面标题
        # 创建canvas，绑定事件
        screenWidth = self._baseTkImg.width()  # root.winfo_screenwidth()
        screenHeight = self._baseTkImg.height()  # root.winfo_screenheight()
        self.canvas = tkinter.Canvas(self.root, bg='white', width=screenWidth, height=screenHeight)
        self.setCanvasImg(self._baseTkImg)
        self.canvas.bind('<Button-1>', self.mouseDownLeft)  # 鼠标左键
        self.canvas.bind('<B1-Motion>', self.mouseDrag)  # 鼠标拖动
        self.canvas.bind('<ButtonRelease-1>', self.mouseUpLeft)  # 鼠标抬起
        self.canvas.place(x=0, y=0)  # pack(fill=tkinter.Y,expand=tkinter.YES)
        self.canvas.pack(fill='both', expand='yes')
        # 打开标记记录数据库
        DbLite.open()
        # 初始化鼠标事件的位置容器
        self._X = tkinter.IntVar(value=0)
        self._Y = tkinter.IntVar(value=0)

    def onClosing(self):
        """
        窗口关闭事件
        Returns:

        """
        DbLite.close()
        self.root.quit()

    def showDialog(self):
        """
        显示主窗口
        """
        self.root.protocol("WM_DELETE_WINDOW", self.onClosing)  # 注册关闭窗口事件
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

    def title(self, titleText=None, staticText=None):
        """
        设置显示窗口标题
        Args:
            titleText: 当前要显示的临时内容
            staticText: 需要一直在标题显示的内容
        """
        if staticText is not None:
            self._staticText = staticText
        mTitle = '智能车牌数据标注器'
        if self._staticText is not None:
            mTitle += ' [' + self._staticText + ']'
        if titleText is not None:
            mTitle += ' (' + titleText + ')'
        self.root.title(mTitle)

    def cv2ImgAddText(self, img, text, pos, textColor=(255, 0, 0), textSize=12) -> np.ndarray:
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

    # region 读取、显示有关操作
    def setCanvasImg(self, tkImage: ImageTk.PhotoImage):
        """
        设置主画板的图片
        Args:
            tkImage: ImageTk.PhotoImage格式的图片
        """
        self.canvas.create_image(0, 0, anchor='nw', image=tkImage)

    def getJPGs(self, dir):
        jpgFullFileNames = []
        for root, dirs, files in os.walk(args.image_dir):
            for file in files:
                if file.endswith('.jpg') or file.endswith('.JPG'):
                    jpgFullFileNames += [os.path.join(root, file)]
        return jpgFullFileNames

    def readFrame(self) -> np.ndarray:
        """
        无论当前为何种模式，读取一帧
        Returns:

        """
        if self.isVideoMode():
            return VideoUtil.ReadFrame(self.videoStream)
        elif self.isImageMode():
            return Transformer.Imread(args.image)
        elif self.isImageDirMode():
            if self.imageFiles is None:  # 初始化imageFiles
                # self.imageFiles = os.listdir(args.image_dir)
                # self.imageFiles = [os.path.join(args.image_dir, filename) for filename in self.imageFiles]
                self.imageFiles = self.getJPGs(args.image_dir)
            self.imageFilesIndex += 1  # 移到下一个图片，再读取
            if self.imageFilesIndex >= len(self.imageFiles):
                self.imageFilesIndex %= len(self.imageFiles)
                print('已读取所有的照片，已回到第一张！')
            frame = Transformer.Imread(self.imageFiles[self.imageFilesIndex])
            return frame

    def removeRectangleAndLabelAt(self, removeIndex=-1, removeRectangle=False, removeLabel=False):
        """
        从canvas画板上删除当前标注过的第几个方框或文字。注意：如果同时删除，则清除其对应的坐标记录。
        Args:
            removeIndex: 第几个标注。从0开始计数，默认为-1
            removeRectangle: 是否删除该方框
            removeLabel: 是否删除该方框上的文字
        """
        # 只删一边的情况
        if removeRectangle:
            lastDrawedRectangle = self.rectanglesAndLabels[removeIndex][0]
            self.canvas.delete(lastDrawedRectangle)
        if removeLabel:
            lastDrawedText = self.rectanglesAndLabels[removeIndex][1]
            self.canvas.delete(lastDrawedText)
        # 如果都要删掉就清除内部储存的记录
        if removeRectangle and removeLabel:
            self.rectanglesAndLabels.pop(removeIndex)  # 删掉方框和线
            self.boxesAndLabels.pop(removeIndex)  # 删除车牌坐标

    def removeRectanglesAndLabels(self, event=None):
        """
        从canvas画板上删除当前标注过的所有方框和文字，清除对应的坐标记录。
        Args:
            event: delete键按下时传入的变量
        """
        for rectangleLabel in self.rectanglesAndLabels:
            self.canvas.delete(rectangleLabel[0])
            self.canvas.delete(rectangleLabel[1])
        self.rectanglesAndLabels = []  # 删掉方框和线
        self.boxesAndLabels = []  # 删除车牌坐标

    def drawRectanglesAndLabels(self):
        """
        根据现有的所有车牌坐标，在canvas画板上画出对应的框、写下车牌号文字
        """
        for licensePlateDict in self.boxesAndLabels:
            lastDrawedRectangle = self.canvas.create_rectangle(licensePlateDict['left'], licensePlateDict['top'],
                                                               licensePlateDict['right'], licensePlateDict['bottom'],
                                                               outline="red")
            lastDrawedText = self.canvas.create_text(licensePlateDict['left'] + 37, licensePlateDict['top'] - 10,
                                                     text=licensePlateDict['label'], font=('宋体', 15), fill='red')
            self.rectanglesAndLabels += [(lastDrawedRectangle, lastDrawedText)]

    def loadNextFrame(self, skipSteps=None) -> None:
        '''
        加载并显示之后的帧/图片。
        Args:
            skipSteps: 如果是文件夹模式则为跳过几张图片。如果是视频模式则为跳过 skipSteps*偏移系数 秒。

        Returns:

        '''
        self.removeRectanglesAndLabels()  # 加载新帧前先删除之前画的线和文字

        skipSteps = skipSteps if skipSteps is not None else 1
        # 视频模式
        if self.isVideoMode():
            VideoUtil.SkipReadFrames(self.videoStream, VideoUtil.GetFps(self.videoStream) * skipSteps * self._偏移系数)
            self.baseFrame = self.readFrame()
            if args.show_file_detail:
                self.title(args.video + ' ' + str(VideoUtil.GetPosition(self.videoStream)) + '/' + str(
                    VideoUtil.GetVideoFileFrameCount(self.videoStream)))
        # 文件夹模式
        elif self.isImageDirMode():
            self.imageFilesIndex += skipSteps - 1  # 因为readFrame读取前会imageFilesIndex++，所以skipSteps=1时无需操作
            self.baseFrame = self.readFrame()
            if args.show_file_detail:
                self.title(self.imageFiles[self.imageFilesIndex])
        else:
            self.baseFrame = self.readFrame()
            if args.show_file_detail:
                self.title(args.image)
        # 判断是否读取结束
        if self.baseFrame is None:
            self.root.destroy()
            self.root.quit()
            return
        # 转换为TkImage格式后放置到canvas画板上
        self._baseTkImg = self.frame2TkImage(self.baseFrame)
        self.setCanvasImg(self._baseTkImg)
        if args.enable_smart_tool:  # 开始检测新图像的车牌号
            self.boxesAndLabels = LPDetector.getBoxesAndLabels(self.baseFrame, 1, (50, 15), None)
        else:  # 禁止自动标注，则初始化为空的
            self.boxesAndLabels = []
        self.drawRectanglesAndLabels()  # 画框、写文字

    # endregion

    # region 键盘事件
    def keyPress(self, event):
        """
        键盘按下事件。负责无保存跳转功能
        Args:
            event:
        """
        if '1' <= event.char <= '9':
            self.loadNextFrame(int(event.char))
        elif event.char is '0':
            self.loadNextFrame(10)
        elif self.isVideoMode():
            if event.char is '-':
                self._偏移系数 *= -1
                self.title(staticText='倍率=' + str(self._偏移系数))
            elif event.char is 'a' or event.char is 'A':
                self._偏移系数 *= 2
                self.title(staticText='倍率=' + str(self._偏移系数))
            elif event.char is 'd' or event.char is 'D':
                self._偏移系数 /= 2
                self.title(staticText='倍率=' + str(self._偏移系数))

    def enterPress(self, event):
        """
        回车按下事件。负责修改车牌号功能
        Args:
            event:
        """
        changeIndex = 0  # 第几个车牌
        if len(self.boxesAndLabels) > 1:
            help = ''  # 要输出的描述性文字
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
        self.removeRectangleAndLabelAt(removeIndex=changeIndex, removeLabel=True)  # 删除canvas对应的文字
        self.boxesAndLabels[changeIndex]['label'] = input  # 修改储存的label
        self.drawRectanglesAndLabels()  # 重新绘图

    def spacePress(self, event):
        """
        空格按下事件
        Args:
            event:

        Returns:

        """
        self.cutSavePicture()  # 截图并保存
        self.loadNextFrame()  # 加载下一幅图

    # endregion

    # region 鼠标事件
    # 鼠标左键按下的位置
    def mouseDownLeft(self, event):
        """
        鼠标左键KeyDown事件
        Args:
            event:
        """
        self._X.set(event.x)
        self._Y.set(event.y)
        self._draging = True  # 开始画框的标志

    # 鼠标左键移动，显示选取的区域
    def mouseDrag(self, event):
        """
        鼠标左键拖拽事件
        Args:
            event:
        """
        if not self._draging:
            return
        try:
            # 删除刚画完的图形，否则鼠标移动的时候是黑乎乎的一片矩形
            self.canvas.delete(self._lastDragedRectangle)
        except Exception as e:
            pass
        self._lastDragedRectangle = self.canvas.create_rectangle(self._X.get(), self._Y.get(), event.x, event.y,
                                                                 outline='yellow')

    # 获取鼠标左键抬起的位置，记录区域
    def mouseUpLeft(self, event):
        """
        鼠标左键KeyUp事件
        Args:
            event:

        Returns:

        """
        self._draging = False
        try:
            self.canvas.delete(self._lastDragedRectangle)  # 删除拖拽时画的框
        except Exception as e:
            pass
        upx = event.x
        upy = event.y
        myleft, myright = sorted([self._X.get(), upx])
        mytop, mybottom = sorted([self._Y.get(), upy])
        vehicle = {'left': myleft, 'right': myright, 'top': mytop, 'bottom': mybottom}
        print('选择区域：left:%d top:%d right:%d bottom:%d' % (myleft, mytop, myright, mybottom))  # 对应image中坐标信息
        if args.crop_mode:
            inputStr = os.path.basename(self.imageFiles[self.imageFilesIndex]).split('.')[0]
        else:
            inputStr = inputbox('输入车辆车牌号')
            if inputStr is '':
                return
        vehicle['label'] = inputStr
        self.boxesAndLabels += [vehicle]
        print('已录入车牌号：' + inputStr)
        self.drawRectanglesAndLabels()  # 画图和标文字
        if args.crop_mode:
            self.spacePress(event)

    def mouseWheel(self, event):
        """
        滚轮滚动操作。向下滚动作为按键1的快捷方式，向上滚动与之相反
        Args:
            event:
        """
        if event.delta > 0:
            self.loadNextFrame(-1)
        else:
            self.loadNextFrame(1)

    # endregion

    # region 裁剪与储存
    def cutSavePicture(self):
        """
        裁剪图片中的所有车牌并保存为车牌号.jpg
        """
        for dict in self.boxesAndLabels:
            left, right, top, bottom = dict['left'], dict['right'], dict['top'], dict['bottom']
            saveFullFileName, _ = LPDetector.getInconflictFileName(args.save_folder + dict['label'] + '.jpg')
            left, right, top, bottom = GUI.cutImwrite(saveFullFileName, self.baseFrame, left, right, top, bottom)
            if self.isImageDirMode():
                DbLite.append(self.imageFiles[self.imageFilesIndex], saveFullFileName, left, right, top, bottom)
            elif self.isImageMode():
                DbLite.append(args.image, saveFullFileName, left, right, top, bottom)
            elif self.isVideoMode():
                DbLite.append(args.video, saveFullFileName, left, right, top, bottom)
            print('截图已保存：' + saveFullFileName)
            self.title(saveFullFileName + ' 已保存')

    @staticmethod
    def cutImwrite(savedFileName: str, image: np.ndarray, left: int, right: int, top: int, bottom: int):
        """
        根据传入的坐标裁剪图片，并保存为图片文件
        Args:
            savedFileName: 要保存的图片文件名
            image: 需要被裁减的图片
            left, right, top, bottom: 左，右，上，下坐标。要求：左<右，上<下
        Returns:
            真实裁剪的left, right, top, bottom（只有出现异常才会与传入的不同）
        """""
        # 合理化检查并纠正
        originalPositions = (left, right, top, bottom)
        imgHeight, imgWidth, _ = image.shape
        left = left if left >= 0 else 0
        right = right if right <= imgWidth else imgWidth
        top = top if top >= 0 else 0
        bottom = bottom if bottom <= imgHeight else imgHeight
        if originalPositions != (left, right, top, bottom):
            print('坐标越界，已纠正为left:%d top:%d right:%d bottom:%d' % (left, top, right, bottom))
        # 开始裁剪
        clipFrame = image[top:bottom, left:right]
        Transformer.Imwrite(savedFileName, clipFrame)
        return left, right, top, bottom
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
