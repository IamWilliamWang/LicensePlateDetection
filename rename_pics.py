import time
import xlrd
import os
from LPDetector import getInconflictFileName

"""
将系统监测到的车牌图片重命名为车牌号脚本（根据xlsx文件储存的地址和车牌号）
"""
if __name__ == '__main__':
    # 文件路径
    xlsx_file = r"C:\Users\william\Desktop\抓拍.xlsx"
    # 获取数据
    data = xlrd.open_workbook(xlsx_file)
    log = open('log.txt', mode='a', encoding='utf-8')
    log.write('------------------- @time -------------------\n'.replace('@time', time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())))
    # 是否将log内容变为redo语句
    log_redo_bat = True
    # 获取sheet 此处有图注释（见图1）
    for table in data.sheets():
        # 获取总行数
        nrows = table.nrows
        # 获取总列数
        ncols = table.ncols
        if ncols is not 5:
            continue

        for row in range(1, nrows):
            if table.cell(row, 3).value == '无车牌' or table.cell(row, 4).value[-1] == '\\':
                continue
            filename = table.cell(row, 4).value  # 提取表格中的文件名
            filename = filename[:filename.rfind('\\') + 1] + 'Plate' + filename[
                                                                       filename.rfind('\\') + 1:]  # 文件名前加Plate
            license_plate = table.cell(row, 3).value[1:]  # 提取车牌号
            new_filename = filename[:filename.rfind('\\') + 1] + license_plate + '.jpg'  # 新文件名
            if not os.path.exists(filename):
                continue
            try:
                os.rename(filename, new_filename)  # 执行重命名
            except FileNotFoundError as e:  # 文件找不到证明已经重命名过了
                continue
            except FileExistsError as e:
                new_filename, _ = getInconflictFileName(new_filename)
                os.rename(filename, new_filename)
            finally:
                print('Renamed', filename, 'to', new_filename)
                if log_redo_bat:
                    log.write('rename \"' + new_filename + '\" \"' + filename[filename.rfind('\\') + 1:] + '\"\n')
                else:
                    log.write('Renamed ' + filename + ' to ' + new_filename + '\n')
    log.close()
