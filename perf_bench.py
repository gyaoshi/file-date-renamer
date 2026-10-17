# -*- coding: utf-8 -*-
"""右键改名端到端基准：耗时 + 是否漏改。

用例目录放在系统临时目录下，运行结束不主动删除（避免触发批量删除保护）。
"""
import os, sys, time, tempfile, shutil, ctypes, json, io, glob

HOME = os.path.join(os.environ["APPDATA"], "RenameTime")


def e2e(n, root):
    sb = tempfile.mkdtemp(prefix="rtb%d_" % n, dir=root)
    names = []
    for i in range(n):
        p = os.path.join(sb, "f%d.txt" % i)
        with open(p, "w") as f:
            f.write("x")
        names.append(p)
    with io.open(os.path.join(HOME, "config.json"), "w", encoding="utf-8") as f:
        json.dump({"direct_mode": True, "show_result": False,
                   "record_history": False}, f, ensure_ascii=False)
    t = time.perf_counter()
    for p in names:
        ctypes.windll.shell32.ShellExecuteW(None, "RenameTime", p, None, None, 1)
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 20:
        if not glob.glob(os.path.join(sb, "f*.txt")):
            break
        time.sleep(0.02)
    left = len(glob.glob(os.path.join(sb, "f*.txt")))
    return (time.perf_counter() - t) * 1000, left


def main():
    sizes = [int(x) for x in sys.argv[1:]] or [1, 2, 3, 5, 5, 5, 8, 10, 20, 20, 30, 50]
    root = tempfile.mkdtemp(prefix="rtbench_")
    bad = 0
    times = []
    for n in sizes:
        el, left = e2e(n, root)
        times.append(el)
        if left:
            bad += 1
        sys.stdout.write("%s %2d 个文件 %7.0f ms  漏改=%d\n"
                         % ("OK  " if not left else "FAIL", n, el, left))
        sys.stdout.flush()
    times.sort()
    sys.stdout.write("\n漏改批次 %d/%d   中位数 %.0f ms   最快 %.0f ms   最慢 %.0f ms\n"
                     % (bad, len(times), times[len(times) // 2], times[0], times[-1]))
    sys.stdout.write("临时目录: %s\n" % root)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
