import os
import re
import shutil

"""
基于正则的复制脚本：用于批量复制，命名冲突时可以自动重命名
"""
if __name__ == '__main__':
    fromDir = input('复制哪个文件夹：')
    toDir = input('复制到哪个文件夹：')
    regex = input('复制哪些文件（使用正则表示）：')
    # selectedFiles = [os.path.join(fromDir, filename) for filename in os.listdir(fromDir)]
    selectedFiles = os.listdir(fromDir)
    for select in selectedFiles:
        if re.compile(regex).match(select):
            targetFile = select
            postfix = 2
            while os.path.exists(os.path.join(toDir, targetFile)):
                targetFile = targetFile.split('.')[0].split(' (')[0] + ' (' + str(postfix) + ')' + '.jpg'
                postfix += 1
            shutil.copy2(os.path.join(fromDir, select), os.path.join(toDir, targetFile))
            print('已复制 ' + os.path.join(fromDir, select) + ' 到 ' + os.path.join(toDir, targetFile))
