#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RenameTime 重命名引擎自测脚本
在 test_sandbox/ 下构造各种场景，验证 build_plans / execute_plans / undo 等逻辑。
运行：python test_engine.py
"""
import datetime
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX = os.path.join(HERE, "test_sandbox")
os.environ["RENAMETIME_HOME"] = os.path.join(SANDBOX, "config_home")

sys.path.insert(0, HERE)
import rename_time as rt  # noqa: E402

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS  %s" % name)
    else:
        FAIL += 1
        print("  FAIL  %s  %s" % (name, detail))


def fresh(cfg_over=None):
    """重建沙箱并返回配置。"""
    if os.path.exists(SANDBOX):
        shutil.rmtree(SANDBOX)
    os.makedirs(SANDBOX)
    cfg = dict(rt.DEFAULT_CONFIG)
    if cfg_over:
        cfg.update(cfg_over)
    return cfg


def mk(path, mtime=None, atime=None, content=""):
    full = os.path.join(SANDBOX, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    if mtime is not None:
        t = time.mktime(mtime.timetuple())
        a = time.mktime(atime.timetuple()) if atime else t
        os.utime(full, (a, t))
    return full


def mkdir(path, mtime=None):
    """创建目录并设置 mtime（须在创建完内部文件之后调用）。"""
    full = os.path.join(SANDBOX, path)
    os.makedirs(full, exist_ok=True)
    if mtime is not None:
        t = time.mktime(mtime.timetuple())
        os.utime(full, (t, t))
    return full


def names_in(sub=""):
    d = os.path.join(SANDBOX, sub)
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def run(paths, cfg):
    plans = rt.build_plans(rt.collect_targets(paths, cfg), cfg)
    stats = rt.execute_plans(plans, cfg)
    return plans, stats


def preview(paths, cfg):
    return rt.build_plans(rt.collect_targets(paths, cfg), cfg)


def main():
    print("== 1. 单文件：修改日期 -> 20151010 前缀 ==")
    cfg = fresh({"date_source": "modified"})
    mk("某某文件.pdf", mtime=datetime.datetime(2015, 10, 10, 8, 0, 0))
    plans, stats = run([os.path.join(SANDBOX, "某某文件.pdf")], cfg)
    check("执行成功 1 项", stats["ok"] == 1 and stats["error"] == 0, str(stats))
    check("文件名为 20151010 某某文件.pdf",
          os.path.exists(os.path.join(SANDBOX, "20151010 某某文件.pdf")),
          str(names_in()))

    print("== 2. 多文件批量 + 文件夹 ==")
    cfg = fresh({"date_source": "modified"})
    mk("a.txt", mtime=datetime.datetime(2020, 1, 2))
    mk("b.txt", mtime=datetime.datetime(2020, 1, 2))
    mk("资料目录/子.txt", mtime=datetime.datetime(2020, 1, 2))
    mkdir("资料目录", mtime=datetime.datetime(2020, 1, 2))  # 子文件创建后再设文件夹时间
    run([os.path.join(SANDBOX, "a.txt"), os.path.join(SANDBOX, "b.txt"),
         os.path.join(SANDBOX, "资料目录")], cfg)
    check("a.txt -> 20200102 a.txt", os.path.exists(os.path.join(SANDBOX, "20200102 a.txt")))
    check("b.txt -> 20200102 b.txt", os.path.exists(os.path.join(SANDBOX, "20200102 b.txt")))
    check("文件夹 -> 20200102 资料目录",
          os.path.isdir(os.path.join(SANDBOX, "20200102 资料目录")), str(names_in()))

    print("== 3. 日期格式与时间 ==")
    cfg = fresh({"date_source": "modified", "date_format": "%Y-%m-%d",
                 "include_time": "hm", "time_sep": "_"})
    mk("报告.docx", mtime=datetime.datetime(2021, 6, 15, 9, 5))
    run([os.path.join(SANDBOX, "报告.docx")], cfg)
    check("2021-06-15_0905 报告.docx",
          os.path.exists(os.path.join(SANDBOX, "2021-06-15_0905 报告.docx")), str(names_in()))

    cfg = fresh({"date_source": "modified", "date_format": "%Y年%m月%d日"})
    mk("合同.pdf", mtime=datetime.datetime(2019, 3, 8))
    run([os.path.join(SANDBOX, "合同.pdf")], cfg)
    check("2019年03月08日 合同.pdf",
          os.path.exists(os.path.join(SANDBOX, "2019年03月08日 合同.pdf")), str(names_in()))

    print("== 4. 分隔符 / 后缀位置 / 自定义格式 ==")
    cfg = fresh({"date_source": "modified", "date_format": "%Y%m%d",
                 "separator": "_", "position": "suffix"})
    mk("照片.jpg", mtime=datetime.datetime(2022, 12, 25))
    run([os.path.join(SANDBOX, "照片.jpg")], cfg)
    check("照片_20221225.jpg",
          os.path.exists(os.path.join(SANDBOX, "照片_20221225.jpg")), str(names_in()))

    print("== 5. 已有日期前缀：跳过 / 替换 / 仍添加 ==")
    for mode, expect in (("skip", "20151010 某某文件.pdf"),
                         ("replace", "20200101 某某文件.pdf"),
                         ("add", "20200101 20151010 某某文件.pdf")):
        cfg = fresh({"date_source": "modified", "existing_date": mode})
        mk("20151010 某某文件.pdf", mtime=datetime.datetime(2020, 1, 1))
        run([os.path.join(SANDBOX, "20151010 某某文件.pdf")], cfg)
        check("existing_date=%s -> %s" % (mode, expect),
              os.path.exists(os.path.join(SANDBOX, expect)), str(names_in()))

    print("== 6. 冲突处理 ==")
    cfg = fresh({"date_source": "modified", "conflict": "suffix"})
    mk("x.txt", mtime=datetime.datetime(2020, 5, 5))
    mk("20200505 x.txt", mtime=datetime.datetime(2020, 5, 5))
    run([os.path.join(SANDBOX, "x.txt")], cfg)
    check("冲突加序号 20200505 x (1).txt",
          os.path.exists(os.path.join(SANDBOX, "20200505 x (1).txt")), str(names_in()))

    cfg = fresh({"date_source": "modified", "conflict": "skip"})
    mk("x.txt", mtime=datetime.datetime(2020, 5, 5))
    mk("20200505 x.txt", mtime=datetime.datetime(2020, 5, 5))
    plans, stats = run([os.path.join(SANDBOX, "x.txt")], cfg)
    check("conflict=skip 时跳过", stats["ok"] == 0 and stats["skip"] >= 1, str(stats))

    print("== 7. 递归文件夹 ==")
    cfg = fresh({"date_source": "modified", "recursive": True})
    mk("项目/文件1.txt", mtime=datetime.datetime(2020, 2, 2))
    mk("项目/子目录/文件2.txt", mtime=datetime.datetime(2020, 2, 2))
    mkdir("项目/子目录", mtime=datetime.datetime(2020, 2, 2))
    mkdir("项目", mtime=datetime.datetime(2020, 2, 2))
    run([os.path.join(SANDBOX, "项目")], cfg)
    ok1 = os.path.exists(os.path.join(SANDBOX, "20200202 项目", "20200202 文件1.txt"))
    ok2 = os.path.exists(os.path.join(SANDBOX, "20200202 项目", "20200202 子目录",
                                      "20200202 文件2.txt"))
    check("递归：子文件重命名", ok1, str(names_in("20200202 项目")))
    check("递归：子文件夹重命名", ok2)

    print("== 8. 排除扩展名 / 处理范围 / 隐藏文件 ==")
    cfg = fresh({"date_source": "modified", "exclude_exts": ".lnk, .tmp"})
    mk("快捷方式.lnk", mtime=datetime.datetime(2020, 3, 3))
    mk("正常.txt", mtime=datetime.datetime(2020, 3, 3))
    plans, stats = run([os.path.join(SANDBOX, "快捷方式.lnk"),
                        os.path.join(SANDBOX, "正常.txt")], cfg)
    check("排除 .lnk", os.path.exists(os.path.join(SANDBOX, "快捷方式.lnk"))
          and os.path.exists(os.path.join(SANDBOX, "20200303 正常.txt")))

    cfg = fresh({"date_source": "modified", "scope": "files"})
    mkdir("目录甲", mtime=datetime.datetime(2020, 4, 4))
    mk("文件乙.txt", mtime=datetime.datetime(2020, 4, 4))
    run([os.path.join(SANDBOX, "目录甲"), os.path.join(SANDBOX, "文件乙.txt")], cfg)
    check("scope=files 不动文件夹",
          os.path.isdir(os.path.join(SANDBOX, "目录甲"))
          and os.path.exists(os.path.join(SANDBOX, "20200404 文件乙.txt")))

    print("== 9. 序号 ==")
    cfg = fresh({"date_source": "modified", "sequence": True, "seq_digits": 3})
    mk("一.txt", mtime=datetime.datetime(2020, 7, 7))
    mk("二.txt", mtime=datetime.datetime(2020, 7, 7))
    run([os.path.join(SANDBOX, "一.txt"), os.path.join(SANDBOX, "二.txt")], cfg)
    check("序号 20200707_001 一.txt",
          os.path.exists(os.path.join(SANDBOX, "20200707_001 一.txt")), str(names_in()))
    check("序号 20200707_002 二.txt",
          os.path.exists(os.path.join(SANDBOX, "20200707_002 二.txt")), str(names_in()))

    print("== 10. 创建日期（Windows 创建时间不可编程设置，验证管线） ==")
    cfg = fresh({"date_source": "created"})
    mk("新文件.txt")
    plans = preview([os.path.join(SANDBOX, "新文件.txt")], cfg)
    today = datetime.datetime.now().strftime("%Y%m%d")
    check("创建日期取当天", plans and plans[0]["new_name"].startswith(today),
          plans[0]["new_name"] if plans else "no plan")

    print("== 11. 撤销 ==")
    cfg = fresh({"date_source": "modified"})
    mk("撤销测试.txt", mtime=datetime.datetime(2020, 8, 8))
    run([os.path.join(SANDBOX, "撤销测试.txt")], cfg)
    check("撤销前新名存在", os.path.exists(os.path.join(SANDBOX, "20200808 撤销测试.txt")))
    hist = rt.History()
    ok, err = rt.undo_batch(hist.batches[0])
    check("撤销成功 1 项", ok == 1 and err == 0, "ok=%d err=%d" % (ok, err))
    check("撤销后恢复原名", os.path.exists(os.path.join(SANDBOX, "撤销测试.txt")),
          str(names_in()))

    print("== 12. 多路径参数解析（模拟 Explorer 传参） ==")
    args = rt.normalize_paths(['"C:\\a b.txt" "C:\\c d.txt"'])
    check("合并引号参数拆成两个路径", args == ["C:\\a b.txt", "C:\\c d.txt"], str(args))
    args2 = rt.normalize_paths(["C:\\x y.txt", "C:\\x y.txt"])
    check("去重", len(args2) == 1, str(args2))

    print("== 13. 时间格式边界 ==")
    cfg = fresh({"date_source": "modified", "date_format": "%Y%m%d",
                 "include_time": "hms", "time_sep": "-"})
    mk("t.log", mtime=datetime.datetime(2023, 11, 30, 23, 59, 58))
    run([os.path.join(SANDBOX, "t.log")], cfg)
    check("时分秒 20231130-23-59-58 t.log",
          os.path.exists(os.path.join(SANDBOX, "20231130-23-59-58 t.log")), str(names_in()))

    print("\n结果：%d 通过，%d 失败" % (PASS, FAIL))
    # 清理沙箱
    try:
        shutil.rmtree(SANDBOX)
    except Exception:
        pass
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
