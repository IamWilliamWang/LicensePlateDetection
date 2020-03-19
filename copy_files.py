import os
import re
import shutil
from LPDetector import getInconflictFileName
import random


def getFromAndToDir(prompt1, prompt2, prompt3, prompt4):
    fromDirs = []
    print(prompt1)
    while True:
        inputLine = input('>> ')
        if inputLine == '':
            break
        inputLine = inputLine.replace('"', '')
        if inputLine[-1] == '\\':
            inputLine = inputLine[:-1]
        fromDirs += [inputLine]
    toDir = input(prompt2).replace('"', '')
    if toDir[-1] == '\\':
        toDir = toDir[:-1]
    regex = input(prompt3)
    recursion = input(prompt4)
    return fromDirs, toDir, regex, recursion


def copy_files():
    """
    基于正则的复制脚本：用于批量复制，命名冲突时可以自动重命名
    """
    fromDirs, toDir, regex, recursion = getFromAndToDir('从哪个/哪些文件夹复制文件：', '复制到哪个文件夹：', '复制的文件名需要满足条件（使用正则表示）：',
                                                        '是否递归子文件夹(y/n)：')
    probability = float(input('输入复制概率(0-1)：')) if regex is '' else 0.0
    for fromDir in fromDirs:
        if recursion is 'y':
            for root, dirs, files in os.walk(fromDir):
                for sourceFile in files:
                    if (regex and re.findall(regex, sourceFile)) or random.random() <= probability:
                        targetFile, _ = getInconflictFileName(os.path.join(toDir, sourceFile))
                        shutil.copy2(os.path.join(fromDir, sourceFile), targetFile)
                        print('已复制 ' + os.path.join(fromDir, sourceFile) + ' 到 ' + targetFile)
        else:
            selectedFiles = os.listdir(fromDir)
            for sourceFile in selectedFiles:
                # if re.compile(regex).match(sourceFile):
                if (regex and re.findall(regex, sourceFile)) or random.random() <= probability:
                    targetFile, _ = getInconflictFileName(os.path.join(toDir, sourceFile))
                    shutil.copy2(os.path.join(fromDir, sourceFile), targetFile)
                    print('已复制 ' + os.path.join(fromDir, sourceFile) + ' 到 ' + targetFile)


def move_files():
    fromDirs, toDir, regex, recursion = getFromAndToDir('从哪个/哪些文件夹移动文件：', '移动到哪个文件夹：', '移动的文件名需要满足条件（使用正则表示）：',
                                                        '是否递归子文件夹(y/n)：')
    probability = float(input('输入移动概率(0-1)：')) if regex is '' else 0.0
    for fromDir in fromDirs:
        if recursion is 'y':
            for root, dirs, files in os.walk(fromDir):
                for sourceFile in files:
                    if (regex and re.findall(regex, sourceFile)) or random.random() <= probability:
                        targetFile, _ = getInconflictFileName(os.path.join(toDir, sourceFile))
                        os.system('move "$1" "$2" >nul'.replace('$1', os.path.join(fromDir, sourceFile)).replace('$2',
                                                                                                                 targetFile))
                        print('已移动 ' + os.path.join(fromDir, sourceFile) + ' 到 ' + targetFile)
        else:
            selectedFiles = os.listdir(fromDir)
            for sourceFile in selectedFiles:
                # if re.compile(regex).match(sourceFile):
                if (regex and re.findall(regex, sourceFile)) or random.random() <= probability:
                    targetFile, _ = getInconflictFileName(os.path.join(toDir, sourceFile))
                    os.system('move "$1" "$2" >nul'.replace('$1', os.path.join(fromDir, sourceFile)).replace('$2',
                                                                                                             targetFile))
                    print('已移动 ' + os.path.join(fromDir, sourceFile) + ' 到 ' + targetFile)


if __name__ == '__main__':
    if input('复制(c)还是移动(m):') is 'm':
        move_files()
    else:
        copy_files()
