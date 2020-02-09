import os
import re
import shutil
from LPDetector import getInconflictFileName

"""
基于正则的复制脚本：用于批量复制，命名冲突时可以自动重命名
"""
if __name__ == '__main__':
    fromDirs = input('复制哪个(些)文件夹：').split(';')  # 用;隔开多个文件夹名
    toDir = input('复制到哪个文件夹：')
    regex = input('复制哪些文件（使用正则表示）：')
    for fromDir in fromDirs:
        selectedFiles = os.listdir(fromDir)
        for select in selectedFiles:
            if re.compile(regex).match(select):
                targetFile, postfix = getInconflictFileName(select)
                shutil.copy2(os.path.join(fromDir, select), os.path.join(toDir, targetFile))
                print('已复制 ' + os.path.join(fromDir, select) + ' 到 ' + os.path.join(toDir, targetFile))
