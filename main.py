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
from Detector import Transformer
from Detector import VideoUtil
import traceback

from DatasetMakerGUI import GUI


def detectLP(image: np.ndarray) -> np.ndarray:
    """
    检测车牌并在image上用方框和文字标出并返回
    Args:
        image: 原始图片

    Returns: 标好的图片

    """
    image = cv2.resize(image, (0, 0), fx=args.scale, fy=args.scale, interpolation=cv2.INTER_CUBIC)
    bboxes = create_mtcnn_net(image, args.mini_lp, device, p_model_path='MTCNN/weights/pnet_Weights',
                              o_model_path='MTCNN/weights/onet_Weights')

    try:
        for i in range(bboxes.shape[0]):
            bbox = bboxes[i, :4]
            x1, y1, x2, y2 = [int(bbox[j]) for j in range(4)]
            # 车牌在边缘的时候，处理方框
            x1 = 0 if x1 < 0 else x1
            y1 = 0 if y1 < 0 else y1
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
            # 截图保存阶段
            savedFileName = 'dataset/LPR_detection/%s.jpg' % labels[0]
            postfix = 2
            while os.path.exists(savedFileName):
                savedFileName = savedFileName.split('.')[0].split(' (')[0] + ' (' + str(postfix) + ')' + '.jpg'
                postfix += 1
            if postfix <= 10:  # 同一辆车超过10次就放弃保存
                GUI.cutImwrite(savedFileName, image, x1, x2, y1, y2)
            # 图像显示阶段
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 1)
            image = cv2ImgAddText(image, labels[0], (x1, y1 - 12), textColor=(255, 255, 0), textSize=15)

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
