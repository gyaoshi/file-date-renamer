#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包后 exe 的 GUI 冒烟测试：四种语言下启动 exe，检查窗口标题是否正确。

为什么单独写：onefile 打包的脚本崩溃时进程仍然存活（bootloader 会弹错误框），
必须检查 MainWindowTitle 才能确认界面真的起来了。
"""
import ctypes
import io
import json
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, "RenameTime.exe")
BASE = os.path.join(HERE, "exe_gui_test")

PASS = []
FAIL = []

user32 = ctypes.windll.user32
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def find_renametime_titles():
    buf = ctypes.create_unicode_buffer(512)
    titles = []

    def cb(hwnd, _l):
        if user32.IsWindowVisible(hwnd):
            if user32.GetWindowTextLengthW(hwnd):
                user32.GetWindowTextW(hwnd, buf, 512)
                if "RenameTime" in buf.value:
                    titles.append(buf.value)
        return True

    user32.EnumWindows(EnumProc(cb), 0)
    return titles


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print("  %s  %s%s" % ("PASS" if cond else "FAIL", name,
                          ("  -> " + str(extra)) if extra and not cond else ""))


EXPECTED = {
    "zh": "RenameTime — 文件日期重命名设置",
    "en": "RenameTime — Date rename settings",
    "ja": "RenameTime — 日付リネーム設定",
    "ru": "RenameTime — Настройки переименования по дате",
}

print("== exe 四语GUI 启动 ==")
for code in ("zh", "en", "ja", "ru"):
    home = os.path.join(BASE, code)
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(home)
    with io.open(os.path.join(home, "config.json"), "w", encoding="utf-8") as f:
        json.dump({"language": code}, f, ensure_ascii=False)
    env = dict(os.environ)
    env["RENAMETIME_HOME"] = home

    before = set(find_renametime_titles())
    p = subprocess.Popen([EXE], env=env)
    title = ""
    for _ in range(30):                #最多等 30 秒
        time.sleep(1)
        new = [t for t in find_renametime_titles() if t not in before]
        if new:
            title = new[0]
            break
    check("%s exe 窗口已打开" % code, bool(title), title or "(30s内未出现窗口)")
    check("%s 窗口标题正确" % code, title == EXPECTED[code],
          "实际=%r 期望=%r" % (title, EXPECTED[code]))
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    time.sleep(1.5)

subprocess.run(["taskkill", "/F", "/IM", "RenameTime.exe"], capture_output=True)
shutil.rmtree(BASE, ignore_errors=True)

print("")
print("结果：%d 通过，%d 失败" % (len(PASS), len(FAIL)))
for f in FAIL:
    print("  -", f)
sys.exit(1 if FAIL else 0)