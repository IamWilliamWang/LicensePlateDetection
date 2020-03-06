import os
import re
import shutil
from LPDetector import getInconflictFileName


def copy_files():
    """
    基于正则的复制脚本：用于批量复制，命名冲突时可以自动重命名
    """
    fromDirs = input('从哪个/哪些文件夹复制文件：').split(';')  # 用;隔开多个文件夹名
    toDir = input('复制到哪个文件夹：')
    regex = input('复制的文件的名称需要满足条件（使用正则表示）：')
    for fromDir in fromDirs:
        selectedFiles = os.listdir(fromDir)
        for sourceFile in selectedFiles:
            if re.compile(regex).match(sourceFile):
                targetFile, _ = getInconflictFileName(os.path.join(toDir, sourceFile))
                shutil.copy2(os.path.join(fromDir, sourceFile), targetFile)
                print('已复制 ' + os.path.join(fromDir, sourceFile) + ' 到 ' + targetFile)


def move_files():
    fromDirs = input('从哪个/哪些文件夹移动文件：').split(';')  # 用;隔开多个文件夹名
    toDir = input('移动到哪个文件夹：')
    regex = input('移动的文件的名称需要满足条件（使用正则表示）：')
    for fromDir in fromDirs:
        selectedFiles = os.listdir(fromDir)
        for sourceFile in selectedFiles:
            if re.compile(regex).match(sourceFile):
                targetFile, _ = getInconflictFileName(os.path.join(toDir, sourceFile))
                os.system(
                    'move "$1" "$2" >nul'.replace('$1', os.path.join(fromDir, sourceFile)).replace('$2', targetFile))
                print('已移动 ' + os.path.join(fromDir, sourceFile) + ' 到 ' + targetFile)


if __name__ == '__main__':
    move_files()
