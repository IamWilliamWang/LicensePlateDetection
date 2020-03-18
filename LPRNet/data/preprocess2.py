import os
import cv2
import numpy as np


def Imread(filename_unicode: str) -> np.ndarray:
    '''
    读取含有unicode文件名的图片
    :param filename_unicode: 含有unicode的图片名
    :return:
    '''
    return cv2.imdecode(np.fromfile(filename_unicode, dtype=np.uint8), -1)


def Imwrite(filename_unicode: str, frame) -> None:
    """
    向文件写入该帧
    Args:
        filename_unicode: unicode文件名
        frame: 该帧
    """
    extension = filename_unicode[filename_unicode.rfind('.'):]
    cv2.imencode(extension, frame)[1].tofile(filename_unicode)


for root, dirs, files in os.walk(r'E:\PycharmProjects\License_Plate_Detection_Pytorch-master\dataset'):
    for filename in files:
        if filename.endswith('.jpg') is False:
            continue
        fullfilename = os.path.join(root, filename)
        image = Imread(fullfilename)
        img_crop = cv2.resize(image, (94, 24), interpolation=cv2.INTER_LINEAR)
        if os.path.exists(os.path.join(root, 'crop')) is False:
            os.makedirs(os.path.join(root, 'crop'))
        print('正在写入', os.path.join(root, 'crop', filename))
        Imwrite(os.path.join(root, 'crop', filename), img_crop)
