from PIL import Image, ImageFont, ImageDraw
import time
import ctypes
import os
import sys
import pystray
from pystray import MenuItem as item
from threading import Thread
import win32gui
import win32con
import win32api
import win32process
import atexit

# ========== 修复核心：优化隐藏和退出机制 ==========
def hide_console():
    if not getattr(sys, 'frozen', False):
        return
    try:
        hwnd = win32gui.GetConsoleWindow()
        if hwnd != 0:
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
    except Exception as e:
        print(f"隐藏控制台失败：{e}")

def force_quit(icon=None, item=None):
    if icon:
        icon.stop()
    os._exit(0)

atexit.register(force_quit)

# ========== 原有功能保留，优化路径和兼容性 ==========
def get_user_paths():
    user_home = os.path.expanduser("~")
    desktop_path = os.path.join(user_home, "Desktop")
    pictures_path = os.path.join(user_home, "Pictures")
    memo_file = os.path.join(desktop_path, "备忘.txt")
    bg_image = os.path.join(pictures_path, "背景图片.jpg")
    output_image = os.path.join(pictures_path, "工作备忘背景.jpg")
    
    return {
        "memo_file": memo_file,
        "bg_image": bg_image,
        "output_image": output_image
    }

def pic_open(filepath):
    try:
        image = Image.open(filepath)
        return image
    except FileNotFoundError:
        print(f"警告：未找到背景图片 {filepath}")
        default_image = Image.new('RGB', (1920, 1080), color='white')
        return default_image

def get_size(image):
    width, height = image.size
    return width, height

def get_work_text(textpath):
    workdict = {"now": [], "fire": [], "follow": [], "done": [], "memo": [], "total": None}
    
    if not os.path.exists(textpath):
        print(f"警告：未找到备忘文件 {textpath}")
        workdict["total"] = 0
        return workdict
    
    with open(textpath, "r", encoding="utf-8-sig") as file:
        worklist = [i.strip() for i in file.readlines() if i.strip()]
    
    workdict["total"] = len(worklist)
    
    for work in worklist:
        if work.startswith("★"):
            workdict["now"].append(work)
        elif work.startswith("▲"):
            workdict["fire"].append(work)
        elif work.startswith("□"):
            workdict["follow"].append(work)
        elif work.startswith("√"):
            workdict["done"].append(work)
        elif work.startswith("备"):
            workdict["memo"].append(work)
    
    return workdict

# ========== 核心修改：统一左对齐+右侧30像素 ==========
def pic_text(image, text, coordinate_H, align_left_x):
    """
    绘制左对齐文字
    align_left_x: 统一的左侧对齐X坐标（所有文字都从这个X开始绘制，实现左对齐）
    """
    draw = ImageDraw.Draw(image)
    fillcolour = {
        "★": (255, 0, 0),
        "▲": (255, 127, 39),
        "□": (0, 128, 255),
        "√": (0, 255, 0),
        "备": (255, 128, 128)
    }
    
    # 字体保持原有配置（清晰化优化保留）
    try:
        setFont = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 20)
    except:
        try:
            setFont = ImageFont.truetype(r"C:\Windows\Fonts\simsun.ttc", 20)
        except:
            try:
                setFont = ImageFont.truetype(r"C:\Windows\Fonts\simhei.ttf", 20)
            except:
                setFont = ImageFont.load_default(size=20)
    
    # 所有文字都从统一的align_left_x开始绘制 → 完美左对齐
    draw.text(
        (align_left_x, coordinate_H),
        text,
        font=setFont,
        fill=fillcolour.get(text[0], (0, 0, 0)),
        antialias=True  # 保留抗锯齿，字体清晰
    )
    return image

# 生成带任务表的桌面图片（核心修改：计算统一左对齐坐标）
def main():
    paths = get_user_paths()
    workdict = get_work_text(paths["memo_file"])
    image = pic_open(paths["bg_image"])
    width, height = get_size(image)
    
    line_height = 25  # 保持原有行高
    total_lines = workdict["total"]
    total_text_height = total_lines * line_height
    coordinate_H = int(height * 0.6) - (total_text_height // 2)  # 保持原有垂直位置
    coordinate_H = max(50, coordinate_H)
    max_y = height - 50
    if coordinate_H + total_text_height > max_y:
        coordinate_H = max_y - total_text_height
    
    # 第一步：收集所有要绘制的文字，计算最大文字宽度（关键）
    all_texts = []
    draw_order = [ "now", "fire", "follow", "done", "memo"]
    for work_key in draw_order:
        all_texts.extend(workdict[work_key])
    
    # 计算最大文字宽度（用于确定统一左对齐坐标）
    try:
        setFont = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 20)
    except:
        try:
            setFont = ImageFont.truetype(r"C:\Windows\Fonts\simsun.ttc", 20)
        except:
            setFont = ImageFont.load_default(size=20)
    
    max_text_width = 0
    draw_temp = ImageDraw.Draw(image)
    for text in all_texts:
        text_width = draw_temp.textlength(text, font=setFont)
        if text_width > max_text_width:
            max_text_width = text_width
    
    # 第二步：计算统一的左对齐X坐标
    # 逻辑：最长文字的右边界距离屏幕右侧30像素 → 所有文字左对齐到同一竖线
    align_left_x = width - 30 - max_text_width
    # 安全边界：避免左对齐位置超出左侧屏幕，最少留10像素边距
    align_left_x = max(10, align_left_x)
    
    # 第三步：按左对齐绘制所有文字
    for work_key in draw_order:
        for work in workdict[work_key]:
            image = pic_text(image, work, coordinate_H, align_left_x)
            coordinate_H += line_height
    
    # 高质量保存（保留原有优化）
    image.save(
        paths["output_image"],
        quality=100,
        subsampling=0
    )
    return paths["output_image"]

# 定时检查文件更新（保持原有逻辑）
def check_update():
    paths = get_user_paths()
    workdict = get_work_text(paths["memo_file"])
    output_image = main()
    ctypes.windll.user32.SystemParametersInfoW(20, 0, output_image, 0)
    
    while True:
        time.sleep(10)
        try:
            works_load = get_work_text(paths["memo_file"])
            if workdict != works_load:
                output_image = main()
                time.sleep(1)
                ctypes.windll.user32.SystemParametersInfoW(20, 0, output_image, 0)
                workdict = works_load
        except Exception as e:
            print(f"检查更新时出错：{e}")
            continue

# 托盘图标（保持原有）
def create_tray_icon():
    icon_image = Image.new('RGBA', (64, 64), (255, 0, 0, 255))
    draw = ImageDraw.Draw(icon_image)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\simsun.ttc", 60)
        draw.text((2, 2), "备", font=font, fill=(255, 255, 255, 255))
    except:
        draw.text((10, 10), "备", font=ImageFont.load_default(size=40), fill='white')
    
    menu = (
        item('工作备忘壁纸 - 右键退出', lambda: None, enabled=False),
        item('退出程序', force_quit)
    )
    
    icon = pystray.Icon(
        name="WorkMemo",
        icon=icon_image,
        title="工作备忘壁纸",
        menu=menu
    )
    
    return icon

# 快捷键注册（保持原有）
def register_hotkey():
    def hotkey_callback(_, __):
        force_quit()
    
    try:
        hotkey_id = 1
        modifiers = win32con.MOD_CONTROL | win32con.MOD_ALT
        key = ord('Q')
        win32api.RegisterHotKey(None, hotkey_id, modifiers, key)
        
        def listen_hotkey():
            while True:
                try:
                    msg = win32gui.GetMessage(None, 0, 0)
                    if msg.message == win32con.WM_HOTKEY:
                        hotkey_callback(None, None)
                    win32gui.TranslateMessage(msg)
                    win32gui.DispatchMessage(msg)
                except:
                    break
    
    except Exception as e:
        print(f"注册快捷键失败：{e}")

# 主程序入口（保持原有）
if __name__ == "__main__":
    hide_console()
    hotkey_thread = Thread(target=register_hotkey, daemon=True)
    hotkey_thread.start()
    update_thread = Thread(target=check_update, daemon=True)
    update_thread.start()
    
    try:
        icon = create_tray_icon()
        icon.run()
    except Exception as e:
        print(f"托盘图标启动失败：{e}")
        hwnd = win32gui.GetConsoleWindow()
        if hwnd != 0:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        input("程序运行中，按Enter退出...")
        force_quit()