import os.path
import cv2
import shutil

import numpy
from moviepy.editor import *
import argparse
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import subprocess
import time

import tkinter
import tkinter.messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
from time import sleep
from tkinter import IntVar, StringVar
from Detector import VideoUtil
from Detector import Transformer
import math
import random

lastDraw = None
if len(os.listdir('dataset/')) is not 0:
    jpgs = os.listdir('dataset/')
    jpgs.sort()
    savedIndex = int(jpgs[-1].split('.')[0]) + 1
else:
    savedIndex = 1


class GUI:

    def __init__(self, videoStream):
        self.videoStream = videoStream
        self.root = tkinter.Tk()  # my创建主窗口
        self.root.state("zoomed")
        self.tkImg = ImageTk.PhotoImage(
            Image.fromarray(cv2.cvtColor(VideoUtil.ReadFrame(self.videoStream), cv2.COLOR_BGR2RGB)))
        # canvas尺寸
        screenWidth = self.tkImg.width()  # root.winfo_screenwidth()
        screenHeight = self.tkImg.height()  # root.winfo_screenheight()
        self.canvas = tkinter.Canvas(self.root, bg='white', width=screenWidth, height=screenHeight)
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor='nw', image=self.tkImg)
        self.root.title('DatasetMaker')
        self.root.geometry(str(self.tkImg.width()) + 'x' + str(self.tkImg.height()))
        self.canvas.bind('<Button-1>', self.onLeftButtonDown)  # 鼠标左键
        self.canvas.bind('<B1-Motion>', self.onLeftButtonMove)  # 鼠标拖动
        self.canvas.bind('<ButtonRelease-1>', self.onLeftButtonUp)  # 鼠标抬起
        self.root.bind('<Return>', self.enter_Press)  # enter键
        self.root.bind('<Key>', self.key_Press)  # 数字键
        self.root.bind('<space>', self.space_Press)  # 空格键
        self.canvas.place(x=0, y=0)  # pack(fill=tkinter.Y,expand=tkinter.YES)
        # self.root.resizable(False, False)
        self.X = tkinter.IntVar(value=0)
        self.Y = tkinter.IntVar(value=0)
        self.selectPosition = None
        self.单张图片含有的车牌数 = 1
        # 启动消息主循环
        self.root.mainloop()

    def next(self, skippedSeconds=None):
        if skippedSeconds is None:
            skippedSeconds = VideoUtil.GetFps(self.videoStream)
        else:
            skippedSeconds *= VideoUtil.GetFps(self.videoStream)
        for i in range(skippedSeconds):
            # self.img = Image.open(r"C:\Users\william\ITCP Web\ScenePics\正常\20200109\20200109091040849.jpg")
            # self.img = ImageTk.PhotoImage(self.img)
            self.frame = VideoUtil.ReadFrame(self.videoStream)
        frameCov = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frameCov)
        self.tkImg = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tkImg)

    def key_Press(self, event):
        if '1' <= event.char <= '9':
            self.next(int(event.char))
        elif event.char is '0':
            self.next(10)

    def enter_Press(self, event):
        self.next(30)

    def space_Press(self, event):
        self.单张图片含有的车牌数 += 1

    # 鼠标左键按下的位置
    def onLeftButtonDown(self, event):
        self.X.set(event.x)
        self.Y.set(event.y)
        # 开始画框的标志
        self.sel = True

    # 鼠标左键移动，显示选取的区域
    def onLeftButtonMove(self, event):
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
    def onLeftButtonUp(self, event):
        self.sel = False
        try:
            self.canvas.delete(lastDraw)
        except Exception as e:
            pass
        # sleep(0.1)
        # print(event.x, event.y)
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
        self.but_addCaptureClick()

    def but_addCaptureClick(self):
        myleft, myright, mytop, mybottom = [x for x in self.selectPosition]
        # 新添加Label控件和Entry控件以及Button，接收在canvas中点出的框坐标
        self.canvas.create_rectangle(self.selectPosition[0], self.selectPosition[2], self.selectPosition[1],
                                     self.selectPosition[3], outline="red")
        w = self.selectPosition[1] - self.selectPosition[0]
        h = self.selectPosition[3] - self.selectPosition[2]
        clipFrame = self.frame[mytop:mybottom, myleft:myright]
        global savedIndex
        savedFile = 'dataset/' + str(savedIndex) + '.jpg'
        Transformer.Imwrite(savedFile, clipFrame)
        savedIndex += 1
        print(savedFile, '已保存')
        if self.单张图片含有的车牌数 is 1:
            self.next()
        else:
            self.单张图片含有的车牌数 -= 1


video = input('输入视频文件名：')
video = video.replace('\"', '')
GUI(VideoUtil.OpenInputVideo(video))
