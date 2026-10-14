#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证右键菜单（动词）真实可用性：
   测试1：ShellExecuteW 按动词名触发单个文件（与 Explorer 同一路径）
   测试2：并发启动 N 个进程各带 1 个文件（模拟 Explorer 多选行为），验证聚合成一批
"""
import ctypes
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, "RenameTime.exe")
BASE = os.path.join(HERE, "shellexec_test")
HOME = os.path.join(BASE, "home")

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS  %s" % name)
    else:
        FAIL += 1
        print("  FAIL  %s  %s" % (name, detail))


def make_items(names):
    if os.path.exists(BASE):
        shutil.rmtree(BASE)
    os.makedirs(HOME)
    with open(os.path.join(HOME, "config.json"), "w", encoding="utf-8") as f:
        json.dump({"date_source": "modified", "direct_mode": True,
                   "show_result": False}, f, ensure_ascii=False)
    t = time.mktime(datetime.datetime(2015, 10, 10).timetuple())
    for name in names:
        p = os.path.join(BASE, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write("x")
        os.utime(p, (t, t))


def names():
    return sorted(n for n in os.listdir(BASE) if n != "home")


def tail(n=30):
    p = os.path.join(HOME, "launch.log")
    if not os.path.exists(p):
        return "(无 launch.log)"
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return "".join(f.readlines()[-n:])


def shell_execute_verb(path, verb="RenameTime"):
    return ctypes.windll.shell32.ShellExecuteW(
        wintypes.HWND(None), ctypes.c_wchar_p(verb), ctypes.c_wchar_p(path),
        None, None, 1)


def main():
    os.environ["RENAMETIME_HOME"] = HOME
    env = dict(os.environ)

    print("== 测试1：真实动词调用（单个文件，带空格） ==")
    make_items(["单个文件.txt", "带 空格 的文件.txt", "c.dat", "d.dat", "e.dat"])
    rc = shell_execute_verb(os.path.join(BASE, "带 空格 的文件.txt"))
    time.sleep(8)
    print("  ShellExecuteW rc=%s  目录: %s" % (rc, names()))
    check("单个文件已重命名", "20151010 带 空格 的文件.txt" in names(), str(names()))
    print(tail(6))

    print("\n== 测试2：模拟 Explorer 多选（5 个进程各带 1 个文件，并发） ==")
    for n in ("batch_queue.txt", "batch.lock", "launch.log"):
        p = os.path.join(HOME, n)
        if os.path.exists(p):
            os.remove(p)
    make_items(["f1.txt", "f2.txt", "f3.txt", "f4.txt", "f5.txt"])
    procs = []
    for n in ("f1.txt", "f2.txt", "f3.txt", "f4.txt", "f5.txt"):
        procs.append(subprocess.Popen([EXE, "--run", os.path.join(BASE, n)],
                                      env=env, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL))
    t0 = time.time()
    for pr in procs:
        pr.wait(timeout=60)
    elapsed = time.time() - t0
    time.sleep(1)
    got = names()
    print("  用时 %.1fs  目录: %s" % (elapsed, got))
    check("5 个文件全部重命名", sum(1 for x in got if x.startswith("20151010")) == 5, str(got))
    log = tail(40)
    leaders = log.count("批次主控")
    followers = log.count("跟随进程")
    print("  主控进程数=%d  跟随进程数=%d" % (leaders, followers))
    check("只有 1 个主控进程", leaders == 1, log[-800:])
    check("其余 4 个为跟随进程", followers == 4, log[-800:])
    check("队列文件已清理", not os.path.exists(os.path.join(HOME, "batch_queue.txt")))
    check("锁文件已释放", not os.path.exists(os.path.join(HOME, "batch.lock")))

    print("\n== 测试3：收到无效路径时明确报告原因（而非静默） ==")
    r = subprocess.run([EXE, "--run", "Z:\\不存在的路径\\x.txt"], env=env,
                       capture_output=True, timeout=30)
    time.sleep(1)
    log = tail(5)
    print("  " + (log.strip().splitlines()[-1] if log.strip() else "(无)"))
    check("无效路径被记录为失败原因", "路径不存在" in log or "跳过 1" in log, log[-300:])
    subprocess.run(["taskkill", "/F", "/IM", "RenameTime.exe"],
                   capture_output=True)

    shutil.rmtree(BASE, ignore_errors=True)
    print("\n结果：%d 通过，%d 失败" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
