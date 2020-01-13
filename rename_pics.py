import xlrd
import os

"""
将系统监测到的车牌图片重命名为车牌号脚本（根据xlsx文件储存的地址和车牌号）
"""
if __name__ == '__main__':
    # 文件路径
    xlsx_file = r"D:\抓拍.xlsx"
    # 获取数据
    data = xlrd.open_workbook(xlsx_file)
    log = open('log.txt', mode='a', encoding='utf-8')
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
            if table.cell(row, 3).value != '无车牌' and table.cell(row, 4).value[-1] != '\\':
                filename = table.cell(row, 4).value  # 提取表格中的文件名
                filename = filename[:filename.rfind('\\') + 1] + 'Plate' + filename[
                                                                           filename.rfind('\\') + 1:]  # 文件名前加Plate
                license_plate = table.cell(row, 3).value[1:]  # 提取车牌号
                new_filename = filename[:filename.rfind('\\') + 1] + license_plate + '.jpg'  # 新文件名
                try:
                    os.rename(filename, new_filename)  # 执行重命名
                except FileNotFoundError as e:  # 文件找不到证明已经重命名过了
                    continue
                except FileExistsError as e:
                    postfix = 2
                    new_filerawname = new_filename.split('.')[0].split(' (')[0]
                    while True:
                        new_filename = new_filerawname + ' (' + str(postfix) + ').jpg'
                        if os.path.exists(new_filename):
                            postfix += 1
                            continue
                        break
                    os.rename(filename, new_filename)
                finally:
                    print('Renamed', filename, 'to', new_filename)
                    if log_redo_bat:
                        log.write('rename \"' + new_filename + '\" \"' + filename[filename.rfind('\\') + 1:] + '\"\n')
                    else:
                        log.write('Renamed ' + filename + ' to ' + new_filename + '\n')
    log.close()
