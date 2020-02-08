#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 15:49:57 2019

@author: xingyu
"""
import sys

sys.path.append('./LPRNet')
sys.path.append('./MTCNN')
from LPRNet_Test import *
from MTCNN import *
import numpy as np
import argparse
import torch
import time
import cv2
import os
from DetectorUtil import Transformer
from DetectorUtil import VideoUtil
import traceback


def cutImwrite(savedFileName: str, image: np.ndarray, left: int, right: int, top: int, bottom: int):
    """
    @see DatasetMakerGUI.GUI.cutImwrite
    """""
    clipFrame = image[top:bottom, left:right]
    Transformer.Imwrite(savedFileName, clipFrame)


def getBoxesAndLabels(image: np.ndarray, scale, mini_lp, device) -> list:
    """
    输入图片帧，输出{left:方框的左坐标, right:右坐标, top:上坐标, bottom:下坐标, label:检测出的车牌号}的列表
    Args:
        image: 输入的彩色图像

    Returns:
        含有多个dict的list（取绝于图片中车牌的数量）
    """
    boxesLabelsList = []
    image = cv2.resize(image, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    bboxes = create_mtcnn_net(image, mini_lp, device, p_model_path='MTCNN/weights/pnet_Weights',
                              o_model_path='MTCNN/weights/onet_Weights')

    for i in range(bboxes.shape[0]):
        resultDict = {}
        bbox = bboxes[i, :4]
        x1, y1, x2, y2 = bbox.astype(int)
        # 车牌在边缘的时候，处理方框
        x1 = 0 if x1 < 0 else x1
        y1 = 0 if y1 < 0 else y1
        resultDict['left'], resultDict['right'], resultDict['top'], resultDict['bottom'] = x1, x2, y1, y2
        w = int(x2 - x1 + 1.0)
        h = int(y2 - y1 + 1.0)
        img_box = np.zeros((h, w, 3))
        img_box = image[y1:y2 + 1, x1:x2 + 1, :]
        im = cv2.resize(img_box, (94, 24), interpolation=cv2.INTER_CUBIC)
        im = (np.transpose(np.float32(im), (2, 0, 1)) - 127.5) * 0.0078125
        data = torch.from_numpy(im).float().unsqueeze(0).to(device)  # torch.Size([1, 3, 24, 94])
        transfer = STN(data)
        preds = lprnet(transfer)
        preds = preds.cpu().detach().numpy()  # (1, 68, 18)
        labels, pred_labels = decode(preds, CHARS)
        resultDict['label'] = labels[0]
        boxesLabelsList += [resultDict]
    return boxesLabelsList


def getInconflictFileName(fullFileName: str) -> tuple:
    """
    如果存在该文件，则将1.jpg改为 1 (2).jpg或1 (3).jpg等等
    Args:
        fullFileName:

    Returns:
        重命名后的文件名，重命名索引号
    """
    postfix = 1
    while os.path.exists(fullFileName):
        postfix += 1
        fullFileName = fullFileName.split('.')[0].split(' (')[0] + ' (' + str(postfix) + ')' + '.jpg'
    return fullFileName, postfix


def detectLP(image: np.ndarray) -> np.ndarray:
    """
    检测车牌并在image上用方框和文字标出并返回
    Args:
        image: 原始图片

    Returns: 标好的图片

    """
    try:
        detectList = getBoxesAndLabels(image, args.scale, args.mini_lp, device)
        for i in range(len(detectList)):
            dict = detectList[i]
            x1, x2, y1, y2, label = dict['left'], dict['right'], dict['top'], dict['bottom'], dict['label']
            # 截图保存阶段
            savedFileName = 'dataset/LPR_detection/%s.jpg' % label
            savedFileName, postfix = getInconflictFileName(savedFileName)
            if postfix <= 10:  # 同一辆车超过10次就放弃保存
                cutImwrite(savedFileName, image, x1, x2, y1, y2)
            # 图像显示阶段
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 1)
            image = cv2ImgAddText(image, label, (x1, y1 - 12), textColor=(255, 255, 0), textSize=15)
            print('检测到', label)

        image = cv2.resize(image, (0, 0), fx=1 / args.scale, fy=1 / args.scale, interpolation=cv2.INTER_CUBIC)
        return image
    except Exception as e:
        traceback.print_exc()
        return image


def detectAndShow(image: np.ndarray) -> np.ndarray:
    image = detectLP(image)
    cv2.imshow('image', image)
    cv2.waitKey(args.wait_time)
    # cv2.destroyAllWindows()
    return image


def initialize():
    global device, lprnet, STN
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    # 初始化LPRNet
    lprnet = LPRNet(class_num=len(CHARS), dropout_rate=0)
    lprnet.to(device)
    lprnet.load_state_dict(
        torch.load('LPRNet/weights/Final_LPRNet_model.pth', map_location=lambda storage, loc: storage))
    lprnet.eval()
    # 初始化STNet
    STN = STNet()
    STN.to(device)
    STN.load_state_dict(torch.load('LPRNet/weights/Final_STN_model.pth', map_location=lambda storage, loc: storage))
    STN.eval()
    print("Successful to build LPR network!")


if __name__ == '__main__':
    # 解析参数
    parser = argparse.ArgumentParser(description='MTCNN & LPR Demo')
    parser.add_argument('-image', '--image', help='image path', default='test/8.jpg', type=str)
    parser.add_argument('--scale', dest='scale', help="scale the iamge", default=1, type=int)
    parser.add_argument('--mini_lp', dest='mini_lp', help="Minimum face to be detected", default=(50, 15), type=int)
    parser.add_argument('-folder', '--image_folder', help='存放图片的文件夹名', default=None, type=str)
    parser.add_argument('-video', '--video', help='录像文件名', default=None, type=str)
    parser.add_argument('-wait', '--wait_time', help='显示窗口暂停时长', default=0, type=int)
    parser.add_argument('-time', '--time_limit', help='执行时间不超过多少秒', default=None, type=int)
    parser.add_argument('-output', '--output_video', help='是否输出处理后的视频（1或0）', default=0, type=int)
    args = parser.parse_args()
    initialize()
    # 开始遍历，启动模型
    since = time.time()
    if args.image_folder is not None:
        for root, _, files in os.walk(args.image_folder):
            for name in files:
                image = Transformer.Imread(os.path.join(root, name))
                # image = cv2.imread(os.path.join(root, name))
                detectAndShow(image)
    elif args.video is not None:
        steamI = VideoUtil.OpenInputVideo(args.video)
        steamO = None
        if args.output_video is 1:
            steamO = VideoUtil.OpenOutputVideo(args.video.replace('.mp4', '.out.mp4'), steamI, 'mp4v')
        fps = VideoUtil.GetFps(steamI)
        eof = False
        loopI = 0
        while True:
            ret, frame = steamI.read()
            if ret is False:
                break
            loopI += 1
            if args.output_video is 1:
                VideoUtil.WriteFrame(steamO, detectAndShow(frame))
            else:
                detectAndShow(frame)
            # print('已处理%d秒' % loopI)
            if args.time_limit is not None and time.time() - since > args.time_limit:
                break
            VideoUtil.SkipReadFrames(steamI, fps * 0.2)  # 跳过一秒
        if args.output_video is 1:
            VideoUtil.CloseVideos(steamO)
        VideoUtil.CloseVideos(steamI)

    print("model inference in {:2.3f} seconds".format(time.time() - since))
