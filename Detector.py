import cv2
import numpy
import socket
import struct
import sys
from datetime import datetime


class VideoUtil:

    @staticmethod
    def OpenVideos(inputVideoSource=None, outputVideoFilename=None, outputVideoEncoding='DIVX'):  # MPEG-4编码
        '''
        打开输入输出视频文件
        :param inputVideoSource: 输入文件名或视频流
        :param outputVideoFilename: 输出文件名或视频流
        :param outputVideoEncoding: 输出文件的视频编码
        :return: 输入输出文件流
        '''
        videoInput = None
        videoOutput = None
        if inputVideoSource is not None:
            videoInput = VideoUtil.OpenInputVideo(inputVideoSource)  # 打开输入视频文件
        if outputVideoFilename is not None:
            videoOutput = VideoUtil.OpenOutputVideo(outputVideoFilename, videoInput, outputVideoEncoding)
        return videoInput, videoOutput

    @staticmethod
    def OpenInputVideo(inputVideoSource):
        '''
        打开输入视频文件
        :param inputVideoSource: 输入文件名或视频流
        :return: 输入文件流
        '''
        return cv2.VideoCapture(inputVideoSource)

    @staticmethod
    def OpenOutputVideo(outputVideoFilename, inputFileStream, outputVideoEncoding='DIVX'):
        '''
        打开输出视频文件
        :param outputVideoFilename: 输出文件名
        :param inputFileStream: 输入文件流（用户获得视频基本信息）
        :param outputVideoEncoding: 输出文件编码
        :return: 输出文件流
        '''
        # 获得码率及尺寸
        fps = int(inputFileStream.get(cv2.CAP_PROP_FPS))
        size = (int(inputFileStream.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(inputFileStream.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        return cv2.VideoWriter(outputVideoFilename, cv2.VideoWriter_fourcc(*outputVideoEncoding), fps, size,
                               False)

    @staticmethod
    def ReadFrames(stream, readFramesCount):
        '''
        从输入流中读取最多readFramesCount个帧并返回，如果没有读取则返回None
        :param stream: 输入流
        :param readFramesCount: 要读取的帧数
        :return:
        '''
        frames = []
        while stream.isOpened():
            ret, frame = stream.read()
            if ret is False:
                break
            frames += [frame]
            if len(frames) >= readFramesCount:
                break
        if len(frames) is 0:
            return None
        return frames

    @staticmethod
    def GetFps(videoStream):
        '''
        获得视频流的FPS
        :param videoStream: 视频输入流
        :return: 每秒多少帧
        '''
        return int(videoStream.get(cv2.CAP_PROP_FPS))

    @staticmethod
    def GetVideoFileFrameCount(videoFileStream):
        '''
        获得视频文件的总帧数
        :param videoFileStream: 视频文件流
        :return: 视频文件的总帧数
        '''
        return videoFileStream.get(cv2.CAP_PROP_FRAME_COUNT)

    @staticmethod
    def GetWidthAndHeight(videoStream):
        '''
        获得视频流的宽度和高度
        :param videoStream: 视频流
        :return: 视频流的宽度和高度
        '''
        return int(videoStream.get(cv2.CAP_PROP_FRAME_WIDTH)), int(videoStream.get(cv2.CAP_PROP_FRAME_HEIGHT))

    @staticmethod
    def CloseVideos(*videoStreams):
        '''
        关闭所有视频文件
        :param videoStreams: 所有视频的文件流
        :return:
        '''
        for videoSteam in videoStreams:
            videoSteam.release()


class Transformer:
    '''
    图像转换器，负责图像的读取，变灰度，边缘检测和线段识别。
    《请遵守以下命名规范：前缀image、img代表彩色图。前缀为gray代表灰度图。前缀为edges代表含有edge的黑白图。前缀为lines代表edges中各个线段的结构体。前缀为static代表之后的比较要以该变量为基准进行比较。可以有双前缀》
    '''

    @staticmethod
    def Imread(filename_unicode):
        '''
        读取含有unicode文件名的图片
        :param filename_unicode: 含有unicode的图片名
        :return:
        '''
        return cv2.imdecode(numpy.fromfile(filename_unicode, dtype=numpy.uint8), -1)

    @staticmethod
    def IsGrayImage(grayOrImg):
        '''
        检测是否为灰度图，灰度图为True，彩图为False
        :param grayOrImg: 图片
        :return: 是否为灰度图
        '''
        return len(grayOrImg.shape) is 2

    @staticmethod
    def GetGrayFromBGRImage(image):
        '''
        将读取的BGR转换为单通道灰度图
        :param image: BGR图片
        :return: 灰度图
        '''
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def GetEdgesFromGray(grayFrame):
        '''
        将灰度图调用canny检测出edges，返回灰度edges图
        :param grayFrame: 灰度图
        :return: 含有各个edges的黑白线条图
        '''
        grayFrame = cv2.GaussianBlur(grayFrame, (3, 3), 0)  # 高斯模糊，去除图像中不必要的细节
        edges = cv2.Canny(grayFrame, 50, 150, apertureSize=3)
        return edges

    @staticmethod
    def GetEdgesFromImage(imageBGR):
        '''
        将彩色图转变为带有所有edges信息的黑白线条图
        :param imageBGR: 彩色图
        :return:
        '''
        return Transformer.GetEdgesFromGray(Transformer.GetGrayFromBGRImage(imageBGR))

    @staticmethod
    def GetLinesFromEdges(edgesFrame, threshold=200):
        '''
        单通道灰度图中识别内部所有线段并返回
        :param edgesFrame: edges图
        :param threshold: 阈值限定，线段越明显阈值越大。小于该阈值的线段将被剔除
        :return:
        '''
        return cv2.HoughLines(edgesFrame, 1, numpy.pi / 180, threshold)


class PlotUtil:
    '''
    用于显示图片的帮助类。可以在彩图中画霍夫线
    '''

    @staticmethod
    def PaintLinesOnImage(img, houghLines, paintLineCount=1, color=(0, 0, 255)):
        '''
        在彩色图中划指定条霍夫线，线段的优先级由长到短
        :param img: BGR图片
        :param houghLines: 霍夫线，即HoughLines函数返回的变量
        :param paintLineCount: 要画线的个数
        :return:
        '''
        for i in range(paintLineCount):
            for rho, theta in houghLines[i]:
                a = numpy.cos(theta)
                b = numpy.sin(theta)
                x0 = a * rho
                y0 = b * rho
                x1 = int(x0 + 1000 * (-b))
                y1 = int(y0 + 1000 * a)
                x2 = int(x0 - 1000 * (-b))
                y2 = int(y0 - 1000 * a)
                cv2.line(img, (x1, y1), (x2, y2), color, 2)

    @staticmethod
    def PutText(img, text, location=(30, 30)):
        '''
        在彩图img上使用默认字体写字
        :param img: 需要放置文字的图片
        :param text: 要写上去的字
        :param location: 字的位置
        :return:
        '''
        cv2.putText(img, text, location, cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2, cv2.LINE_AA)


class SocketServer:
    @staticmethod
    def StartServer():
        return SocketServer()

    def __init__(self):
        try:
            self.mSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 防止socket server重启后端口被占用（socket.error: [Errno 98] Address already in use）
            self.mSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.mSocket.bind(('127.0.0.1', 6666))
            # print('Bind socket success.')
            self.mSocket.listen(1)  # 最多接受一个连接请求
            print('Waiting connection to receive image...')
            self.connection, self.address = self.mSocket.accept()  # 一直等待连接请求
            print('Accept new connection from {0}'.format(self.address))
        except socket.error as msg:
            print(msg)
            sys.exit(1)

    def SendFrameShape(self, image):
        try:
            header = struct.pack('hhh', image.shape[0], image.shape[1], image.shape[2])  # 发送三个short型(16bit)的shape信息
            self.connection.sendall(header)
        except socket.error as msg:
            print(msg)
            sys.exit(1)

    def SendFrameImage(self, image):
        try:
            packet = struct.pack('=%sh' % image.size, *image.flatten())  # 将image展开为一维（没看懂）
            print('Sending frame...')
            self.connection.sendall(packet)
        except socket.error as msg:
            print(msg)
            sys.exit(1)

    def CloseConnection(self):
        self.connection.close()
        print('Close connection from {0}'.format(self.address))


lastSendSec = -1


def CanIgnore():
    global lastSendSec
    now_second = datetime.now().second
    pauseSec = 1
    if (now_second + 60 - lastSendSec) % 60 >= pauseSec:  # 相差大于pauseSec秒
        lastSendSec = now_second
        return False
    return True


def SendUDP(content: str, ipAddress: str, port: int):
    if CanIgnore():
        return
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(content.encode(), (ipAddress, port))


class Detector:
    def __init__(self):
        self.__firstFramePosition = None  # 处理视频文件时记录的当前片段在视频中的开始帧号
        self.__lastFramePosition = None  # 处理视频文件时记录的当前片段在视频中的结束帧号
        self.__originalFrames = None  # 处理视频流时记录当前片段的原始录像
        self.__showWarningMutex = 0  # 用于切换警报状态的信号量

    def LinesEquals(self, lines1, lines2, comparedLinesCount):
        '''
        HoughLines函数返回的lines判断是否相等
        :param lines1: 第一个lines
        :param lines2: 第二个lines
        :param comparedLinesCount: 比较前几条line
        :return: 是否二者相等
        '''
        if lines1 is None or lines2 is None:
            return False
        sameCount = 0
        diffCount = 0
        try:
            for i in range(comparedLinesCount):
                for rho1, theta1 in lines1[i]:
                    for rho2, theta2 in lines2[i]:
                        if rho1 != rho2 or theta1 != theta2:
                            diffCount += 1
                        else:
                            sameCount += 1
        except IndexError:  # 阈值过高的话会导致找不到那么多条line，报错可以忽略
            pass
        return sameCount / (sameCount + diffCount) > 0.9  # 不同到一定程度再报警

    def GetNoChangeEdges_fromVideo(self, videoFilename, startFrameRate=0., endFrameRate=1., outputEdgesFilename=None):
        '''
        @Deprecated 从视频文件中提取不动物体的帧
        :param videoFilename: 文件名
        :param startFrameRate: 开始读取帧处于视频的比例，必须取0-1之间
        :param endFrameRate: 结束读取帧处于视频的比例，必须取0-1之间
        :param outputEdgesFilename: EdgesFrame全部输出到视频为该名的文件中（测试时用）
        :return: 不动物体的Edges帧
        '''
        # 打开输入输出视频文件
        videoInput = VideoUtil.OpenInputVideo(videoFilename)
        frame_count = videoInput.get(cv2.CAP_PROP_FRAME_COUNT)  # 获取视频总共的帧数
        outputVideo = None  # 声明输出文件
        if outputEdgesFilename is not None:
            outputVideo = VideoUtil.OpenOutputVideo(outputEdgesFilename, videoInput)
        staticEdges = None  # 储存固定的Edges
        videoInput.set(cv2.CAP_PROP_POS_FRAMES, int(frame_count * startFrameRate))  # 指定读取的开始位置
        self.__firstFramePosition = int(frame_count * startFrameRate)  # 记录第一帧的位置
        self.__lastFramePosition = int(frame_count * endFrameRate)  # 记录最后一帧的位置
        if endFrameRate != 1:  # 如果提前结束，则对总帧数进行修改
            frame_count = int(frame_count * (endFrameRate - startFrameRate))
        while videoInput.isOpened() and frame_count >= 0:  # 循环读取
            ret, frame = videoInput.read()
            if ret is False:
                break
            edges = Transformer.GetEdgesFromImage(frame)  # 对彩色帧进行边缘识别
            if staticEdges is None:
                staticEdges = edges  # 初始化staticEdges
            else:
                staticEdges &= edges  # 做与运算，不同点会被去掉
            if outputEdgesFilename is not None:
                outputVideo.write(edges)  # 写入边缘识别结果
            frame_count -= 1
            VideoUtil.CloseVideos(videoInput, outputVideo)
        return staticEdges

    def GetNoChangeEdges_fromSteam(self, inputStream, frame_count=20, outputEdgesFilename=None):
        '''
        从输入流中提取不动物体的Edges帧
        :param inputStream: 输入文件流
        :param frame_count: 要读取的帧数
        :param outputEdgesFilename: EdgesFrame全部输出到视频为该名的文件中（测试用）
        :return: 不动物体的Edges帧、原本的彩色帧组
        '''
        outputVideo = None
        if outputEdgesFilename is not None:
            outputVideo = VideoUtil.OpenOutputVideo(outputEdgesFilename, inputStream)
        staticEdges = None
        self.__originalFrames = []
        while inputStream.isOpened() and frame_count >= 0:
            ret, frame = inputStream.read()
            if ret is False:
                break
            self.__originalFrames += [frame]
            edges = Transformer.GetEdgesFromImage(frame)  # 边缘识别
            if staticEdges is None:
                staticEdges = edges  # 初始化staticEdges
            else:
                staticEdges &= edges  # 做与运算，不同点会被去掉
            if outputEdgesFilename is not None:
                outputVideo.write(edges)  # 写入边缘识别结果
            frame_count -= 1
        return staticEdges

    def StartUsingFileStream(self, videoFilename='开关柜3.mp4', compareLineCount=3,
                             videoClipCount=26):  # 2.mp4用10、3.mp4用26
        '''
        @Deprecated 针对视频文件进行的开关柜检测主函数
        :param videoFilename: 视频文件名
        :param compareLineCount: 需要比较几条线是一样的
        :param videoClipCount: 视频要分成多少段
        :return:
        '''
        staticLines = None  # 储存基准帧
        # 开始生成静态基准并进行检测
        for segmentIndex in range(0, videoClipCount):
            segmentRate = 1 / videoClipCount  # 一小段是百分之多少
            videoInput = cv2.VideoCapture(videoFilename)  # 打开视频文件
            videoFps = int(videoInput.get(cv2.CAP_PROP_FPS))  # 读取Fps，取整
            edges = self.GetNoChangeEdges_fromVideo(videoFilename, startFrameRate=segmentRate * segmentIndex,
                                                    endFrameRate=segmentRate * (segmentIndex + 1))  # 获得不动的物体
            lines = Transformer.GetLinesFromEdges(edges, threshold=50)
            error = False
            if staticLines is None:
                staticLines = lines  # 以第一段视频检测出的线为基准（因为第一段视频没有人）
            else:
                frameCount = videoInput.get(cv2.CAP_PROP_FRAME_COUNT)
                startFrameIndex = int(segmentIndex * segmentRate * frameCount)
                endFrameIndex = int((segmentIndex + 1) * segmentRate * frameCount) - 1
                if self.LinesEquals(lines, staticLines, compareLineCount):
                    print('未检测到异常。', startFrameIndex / videoFps, '-', endFrameIndex / videoFps, '秒', sep='')
                else:
                    print('检测到异常！！', startFrameIndex / videoFps, '-', endFrameIndex / videoFps, '秒', sep='')
                    error = True

            # 获得检测线条的视频片段每一帧
            videoInput.set(cv2.CAP_PROP_POS_FRAMES, self.__firstFramePosition)
            for i in range(self.__firstFramePosition, self.__lastFramePosition):
                if videoInput.isOpened() is False:
                    break
                ret, frame = videoInput.read()
                if ret is False:
                    cv2.destroyAllWindows()
                    return
                # 向这帧图像画线
                PlotUtil.PaintLinesOnImage(frame, lines, compareLineCount)
                if error:
                    PlotUtil.PutText(frame, 'Warning')
                cv2.imshow('result', frame)
                if cv2.waitKey(1) is 27:  # Esc按下
                    cv2.destroyAllWindows()
                    return

    def IsWarningStatusChanged(self, exceptionOccurred, consecutiveOccurrencesNumber=3):
        '''
        显示warning状态是否需要改变，True为需要显示Warning。False为需要关闭Warning。None为保持不变
        :param exceptionOccurred: 是否发生异常
        :param consecutiveOccurrencesNumber: 连续几次同样时间发生后给予改变当前警报状态的指示
        :return:
        '''
        if exceptionOccurred:  # 如果发生异常
            if self.__showWarningMutex < 0:  # 清除信号量向正方向
                self.__showWarningMutex = 0
            else:  # 在正方向，则增添信号量
                self.__showWarningMutex += 1
            if self.__showWarningMutex > (consecutiveOccurrencesNumber - 1):
                return True  # 连续3次就返回显示warning
        else:
            if self.__showWarningMutex > 0:
                self.__showWarningMutex = 0
            else:
                self.__showWarningMutex -= 1
            if self.__showWarningMutex < -(consecutiveOccurrencesNumber - 1):
                return False  # 连续3次就返回撤销warning
        return None

    def StartUsingVideoStream(self, source='rtsp://admin:1234abcd@192.168.1.64', compareLineCount=3):
        '''
        解析输入视频流，并在柜子出现变动时输出警告
        :param source: 视频源
        :param compareLineCount: 需要比较的主要线条个数
        :return:
        '''
        # 初始化输入流
        # 获得静态Edges的Lines信息
        inputStream = VideoUtil.OpenInputVideo(source)
        staticEdges = self.GetNoChangeEdges_fromSteam(inputStream, 20)
        staticLines = Transformer.GetLinesFromEdges(staticEdges)
        # 启动Socket，用于发送每帧
        SEND_FRAMES = False
        if SEND_FRAMES:
            mSocket = SocketServer.StartServer()
            mSocket.SendFrameShape(self.__originalFrames[0])
        # 发送UDP报警信息
        SEND_WARNING = True
        # 初始化处理参数
        showWarning = False  # 显示警告提示
        # 启动检测
        while inputStream.isOpened():
            # Capture frame-by-frame
            edges = self.GetNoChangeEdges_fromSteam(inputStream, 20)
            lines = Transformer.GetLinesFromEdges(edges, threshold=50)
            if lines is None:
                break
            if self.LinesEquals(staticLines, lines, compareLineCount):
                exceptionOccurred = False  # 当前帧下没有发生异常
                print('未检测到异常。', self.__showWarningMutex)
            else:
                exceptionOccurred = True
                print('检测到异常！！', self.__showWarningMutex)
            changeShowWarningStatus = self.IsWarningStatusChanged(exceptionOccurred)  # 是否改变报警状态
            if changeShowWarningStatus is None:
                pass
            elif changeShowWarningStatus is True:
                showWarning = True
            else:
                showWarning = False
            for frame in self.__originalFrames:
                PlotUtil.PaintLinesOnImage(frame, lines, compareLineCount, (255, 0, 0))
                if showWarning:
                    PlotUtil.PutText(frame, 'Warning')
                    if SEND_WARNING:
                        SendUDP('01', '202.199.6.204', 5002)
                if SEND_FRAMES:
                    mSocket.SendFrameImage(frame)
                cv2.imshow('Result', frame)
                if cv2.waitKey(1) == 27:
                    inputStream.release()
                    break
        # When everything done, release the capture  
        cv2.destroyAllWindows()
        mSocket.CloseConnection()


if __name__ == '__main__':
    argn = len(sys.argv)
    if argn is 1:
        Detector().StartUsingVideoStream()
    elif argn is 2:
        Detector().StartUsingVideoStream(sys.argv[1])
    else:
        Detector().StartUsingVideoStream(sys.argv[1], int(sys.argv[2]))
