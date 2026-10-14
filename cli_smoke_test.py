#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 subprocess 调用 RenameTime.exe 做端到端 CLI 冒烟测试。"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, "RenameTime.exe")
BASE = os.path.join(HERE, "cli_test")
DATA = os.path.join(BASE, "data")
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


def mk(rel, dt):
    p = os.path.join(DATA, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("x")
    t = time.mktime(dt.timetuple())
    os.utime(p, (t, t))
    return p


def run_exe(args, env_extra=None):
    env = dict(os.environ)
    env["RENAMETIME_HOME"] = HOME
    if env_extra:
        env.update(env_extra)
    return subprocess.run([EXE] + args, capture_output=True, env=env, timeout=60)


def main():
    if os.path.exists(BASE):
        shutil.rmtree(BASE)
    os.makedirs(HOME)
    os.makedirs(DATA)

    # 独立配置：直接执行、不弹结果窗口
    with open(os.path.join(HOME, "config.json"), "w", encoding="utf-8") as f:
        json.dump({"date_source": "modified", "date_format": "%Y%m%d",
                   "separator": " ", "direct_mode": True, "show_result": False},
                  f, ensure_ascii=False)

    print("== A. 多选（2 文件 + 1 文件夹）一次性重命名 ==")
    mk("项目建议书.pdf", datetime.datetime(2015, 10, 10, 9, 30))
    mk("会议纪要.txt", datetime.datetime(2021, 6, 15, 14, 0))
    mk("附件资料/附表.xlsx", datetime.datetime(2020, 1, 2))
    t = time.mktime(datetime.datetime(2020, 1, 2).timetuple())
    os.utime(os.path.join(DATA, "附件资料"), (t, t))

    r = run_exe(["--run",
                 os.path.join(DATA, "项目建议书.pdf"),
                 os.path.join(DATA, "会议纪要.txt"),
                 os.path.join(DATA, "附件资料")])
    out = r.stdout.decode("utf-8", "replace")
    print("  输出:", out.strip())
    check("进程退出码 0", r.returncode == 0, str(r.returncode))
    check("摘要包含 成功 3", "成功 3" in out, out)
    check("项目建议书.pdf -> 20151010 项目建议书.pdf",
          os.path.exists(os.path.join(DATA, "20151010 项目建议书.pdf")),
          str(sorted(os.listdir(DATA))))
    check("会议纪要.txt -> 20210615 会议纪要.txt",
          os.path.exists(os.path.join(DATA, "20210615 会议纪要.txt")))
    check("附件资料 -> 20200102 附件资料",
          os.path.isdir(os.path.join(DATA, "20200102 附件资料")))

    print("== B. 撤销最近一批 ==")
    r = run_exe(["--undo"])
    out = r.stdout.decode("utf-8", "replace")
    print("  输出:", out.strip())
    check("撤销成功 3 项", "成功 3" in out, out)
    check("原文件名恢复",
          os.path.exists(os.path.join(DATA, "项目建议书.pdf"))
          and os.path.exists(os.path.join(DATA, "会议纪要.txt"))
          and os.path.isdir(os.path.join(DATA, "附件资料")),
          str(sorted(os.listdir(DATA))))

    print("== C. 已有日期前缀时跳过（防重复叠加） ==")
    mk("20151010 旧文件.txt", datetime.datetime(2022, 3, 3))
    r = run_exe(["--run", os.path.join(DATA, "20151010 旧文件.txt")])
    out = r.stdout.decode("utf-8", "replace")
    print("  输出:", out.strip())
    check("跳过且名称不变",
          os.path.exists(os.path.join(DATA, "20151010 旧文件.txt")), str(sorted(os.listdir(DATA))))

    print("== D. 带空格路径 ==")
    mk("带 空格 的文件.txt", datetime.datetime(2022, 5, 5))
    r = run_exe(["--run", os.path.join(DATA, "带 空格 的文件.txt")])
    out = r.stdout.decode("utf-8", "replace")
    check("带空格路径重命名成功",
          os.path.exists(os.path.join(DATA, "20220505 带 空格 的文件.txt")), str(sorted(os.listdir(DATA))))

    print("\n结果：%d 通过，%d 失败" % (PASS, FAIL))
    shutil.rmtree(BASE, ignore_errors=True)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
