#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RenameTime — Windows 右键菜单「文件日期重命名」工具
====================================================

功能概述
--------
把文件/文件夹重命名为「日期 + 原文件名」，例如：

    某某文件.pdf（创建于 2015-10-10）  →  20151010 某某文件.pdf

在资源管理器中选中一个或多个文件/文件夹，右键 → 「添加日期前缀」即可批量处理。
双击运行本程序（或运行时不带参数）打开「设置界面」，可配置：

  * 日期来源：创建日期 / 修改日期 / 访问日期
  * 日期格式：20151010、2015-10-10、2015_10_10、2015年10月10日 …（支持 strftime 自定义）
  * 是否包含时间：不包含 / 时分 / 时分秒
  * 日期与文件名之间的分隔符、日期在前还是在后
  * 已有日期前缀的处理：跳过 / 替换 / 仍然添加
  * 文件名冲突处理：自动加序号 / 跳过
  * 只处理文件 / 只处理文件夹 / 两者；是否递归子文件夹；是否包含隐藏文件
  * 追加序号；排除指定扩展名
  * 右键菜单显示文字；是否同时注册「文件夹空白处」右键
  * 撤销最近的批量重命名（保留最近 50 批历史）

命令行用法
----------
    rename_time.exe                 打开设置界面
    rename_time.exe --run 文件...   右键菜单调用（按设置直接执行或弹预览）
    rename_time.exe 文件...         把文件拖到 exe 上：打开预览窗口
    rename_time.exe --register      注册右键菜单
    rename_time.exe --unregister    注销右键菜单
    rename_time.exe --status        查看注册状态
    rename_time.exe --undo          撤销最近一批重命名

注册位置为 HKCU\\Software\\Classes（每用户），无需管理员权限。
多选文件时通过 MultiSelectModel=Player + "%*" 一次性传入所有选中项。
"""

import argparse
import datetime
import json
import os
import re
import shlex
import sys
import time

APP_NAME = "RenameTime"
VERB_KEY_NAME = "RenameTime"            # 注册表 verb 键名（保持 ASCII）
DEFAULT_VERB_TEXT = "添加日期前缀"
MAX_HISTORY = 50

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    # 基本
    "date_source": "created",           # created | modified | accessed
    "date_format": "%Y%m%d",            # strftime 格式
    "include_time": "none",             # none | hm | hms
    "time_sep": "_",                    # 日期与时间的连接符
    "separator": " ",                   # 日期与原名之间的分隔符
    "position": "prefix",               # prefix | suffix
    # 高级
    "existing_date": "skip",            # skip | replace | add
    "conflict": "suffix",               # suffix | skip
    "scope": "both",                    # both | files | folders
    "recursive": False,                 # 文件夹是否递归处理内部内容
    "include_hidden": False,            # 是否处理隐藏/系统文件
    "sequence": False,                  # 是否追加序号
    "seq_digits": 3,                    # 序号位数
    "seq_sep": "_",                     # 日期与序号之间的连接符
    "exclude_exts": "",                 # 排除的扩展名，如 ".lnk, .tmp"
    # 运行方式
    "direct_mode": True,                # 右键菜单点击后直接执行（不弹预览）
    "show_result": True,                # 执行后显示结果窗口
    # 右键菜单
    "verb_text": DEFAULT_VERB_TEXT,     # 菜单显示文字
    "register_background": False,       # 是否注册「文件夹空白处」右键
}

# 日期格式预设：（下拉显示文本, date_format, include_time, time_sep）
FORMAT_PRESETS = [
    ("20151010 某某文件.pdf", "%Y%m%d", "none", "_"),
    ("2015-10-10 某某文件.pdf", "%Y-%m-%d", "none", "_"),
    ("2015_10_10 某某文件.pdf", "%Y_%m_%d", "none", "_"),
    ("2015.10.10 某某文件.pdf", "%Y.%m.%d", "none", "_"),
    ("2015年10月10日 某某文件.pdf", "%Y年%m月%d日", "none", "_"),
    ("151010 某某文件.pdf", "%y%m%d", "none", "_"),
    ("20151010_1430 某某文件.pdf", "%Y%m%d", "hm", "_"),
    ("2015-10-10 14-30-05 某某文件.pdf", "%Y-%m-%d", "hms", " "),
]

SAMPLE_DT = datetime.datetime(2015, 10, 10, 14, 30, 5)


def app_dir():
    """配置/历史/日志目录。可用环境变量 RENAMETIME_HOME 覆盖（便于测试）。"""
    home = os.environ.get("RENAMETIME_HOME")
    d = home if home else os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def config_path():
    return os.path.join(app_dir(), "config.json")


def history_path():
    return os.path.join(app_dir(), "history.json")


BATCH_QUEUE = "batch_queue.txt"
BATCH_LOCK = "batch.lock"


def _queue_path():
    return os.path.join(app_dir(), BATCH_QUEUE)


def _lock_path():
    return os.path.join(app_dir(), BATCH_LOCK)


def queue_paths(paths):
    """把本次收到的路径写入批次队列（供主控进程汇总）。"""
    p = _queue_path()
    for _ in range(30):
        try:
            try:                                # 清理上次异常退出残留的陈旧队列
                if time.time() - os.path.getmtime(p) > 30:
                    os.remove(p)
            except OSError:
                pass
            with open(p, "a", encoding="utf-8") as f:
                for x in paths:
                    f.write(x + "\n")
                f.flush()
            return True
        except OSError:
            time.sleep(0.05)
    return False


def read_queue():
    try:
        with open(_queue_path(), "r", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip()]
    except OSError:
        return []


def try_become_leader():
    """尝试成为批次主控进程（先到先得）。返回 True 表示本进程负责执行这一批。"""
    lp = _lock_path()
    try:                                    # 清理上次异常退出留下的过期锁
        if time.time() - os.path.getmtime(lp) > 30:
            os.remove(lp)
    except OSError:
        pass
    try:
        fd = os.open(lp, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, ("%d %s" % (os.getpid(),
                                      datetime.datetime.now().isoformat())).encode("ascii"))
        finally:
            os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError:
        return False


def collect_batch(quiet=1.0, cap=25.0):
    """主控进程：等待其它进程投递完毕后取走整批路径。

    资源管理器多选时每个文件各启动一个进程，这里等待“队列不再增长”一段时间，
    收齐全部路径后清空队列与锁，返回整批路径。
    若个别进程启动过慢超出上限，它们会在锁释放后自己成为下一批的主控，不会漏改。
    """
    t0 = last_change = time.time()
    last_n = -1
    while time.time() - t0 < cap:
        n = len(read_queue())
        now = time.time()
        if n != last_n:
            last_n, last_change = n, now
        elif now - last_change >= quiet:
            break
        time.sleep(0.12)
    paths = read_queue()
    for p in (_queue_path(), _lock_path()):  # 先清空再执行，避免崩溃后残留
        try:
            os.remove(p)
        except OSError:
            pass
    return normalize_paths(paths)


def log_path():
    return os.path.join(app_dir(), "rename_time.log")


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
    except Exception:
        pass
    _validate(cfg)
    return cfg


def save_config(cfg):
    _validate(cfg)
    try:
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
        return True
    except Exception as e:
        print("保存配置失败: %s" % e, file=sys.stderr)
        return False


def _validate(cfg):
    if not cfg.get("date_format"):
        cfg["date_format"] = "%Y%m%d"
    if cfg.get("date_source") not in ("created", "modified", "accessed"):
        cfg["date_source"] = "created"
    if cfg.get("include_time") not in ("none", "hm", "hms"):
        cfg["include_time"] = "none"
    if cfg.get("position") not in ("prefix", "suffix"):
        cfg["position"] = "prefix"
    if cfg.get("existing_date") not in ("skip", "replace", "add"):
        cfg["existing_date"] = "skip"
    if cfg.get("conflict") not in ("suffix", "skip"):
        cfg["conflict"] = "suffix"
    if cfg.get("scope") not in ("both", "files", "folders"):
        cfg["scope"] = "both"
    if not cfg.get("verb_text"):
        cfg["verb_text"] = DEFAULT_VERB_TEXT
    try:
        cfg["seq_digits"] = max(1, min(6, int(cfg.get("seq_digits", 3))))
    except Exception:
        cfg["seq_digits"] = 3


def parse_exclude_exts(text):
    if not text:
        return set()
    parts = re.split(r"[,;，；\s]+", text)
    out = set()
    for p in parts:
        p = p.strip().lower()
        if not p:
            continue
        if not p.startswith("."):
            p = "." + p
        out.add(p)
    return out


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def long_path(p):
    """Windows 长路径（>260 字符）支持。"""
    p = os.path.abspath(p)
    if p.startswith("\\\\?\\"):
        return p
    if p.startswith("\\\\"):
        return "\\\\?\\UNC" + p[1:]
    return "\\\\?\\" + p


FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4


def is_hidden_or_system(path):
    try:
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        if attrs == 0xFFFFFFFF:
            return False
        return bool(attrs & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM))
    except Exception:
        return False


def split_arg(a):
    """把一个命令行参数拆成一个或多个路径。

    兼容 Explorer 各种传参方式：
      * 每个文件一个参数（C:\\a.txt）
      * 多个带引号路径挤在一个参数里（"C:\\a b.txt" "C:\\c d.txt"）
      * 双层引号（""C:\\a.txt""，%1 被 shell 预先加引号时会出现）
    （Windows 文件名不允许包含引号，因此该拆分是安全的。）
    """
    a = a.strip()
    if not a:
        return []
    if '"' not in a:
        return [a]
    # 反复剥掉成对的首尾引号（处理 ""C:\path"" 这类双层引号）
    while len(a) > 1 and a.startswith('"') and a.endswith('"'):
        inner = a[1:-1]
        if '"' in inner:
            break
        a = inner.strip()
    if not a:
        return []
    if '"' not in a:
        return [a]
    lex = shlex.shlex(a, posix=False)
    lex.whitespace_split = True
    try:
        toks = list(lex)
    except ValueError:
        toks = [a]
    out = []
    for t in toks:
        t = t.strip()
        if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
            t = t[1:-1]
        if t:
            out.append(t)
    return out


def normalize_paths(args):
    paths = []
    for a in args:
        paths.extend(split_arg(a))
    # 去重保序
    seen, out = set(), []
    for p in paths:
        k = os.path.normcase(os.path.abspath(p))
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def write_log(lines):
    try:
        with open(log_path(), "a", encoding="utf-8") as f:
            f.write("[%s]\n" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            for ln in lines:
                f.write("  %s\n" % ln)
    except Exception:
        pass


def append_launch_log(msg):
    """启动/调用日志：windowed 模式下没有控制台，出问题时靠它排查。"""
    try:
        p = os.path.join(app_dir(), "launch.log")
        with open(p, "a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
        # 只保留最近 300 行，避免无限增长
        try:
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > 300:
                with open(p, "w", encoding="utf-8") as f:
                    f.writelines(lines[-300:])
        except Exception:
            pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 重命名引擎
# ---------------------------------------------------------------------------

# 匹配文件名开头已有的“日期Token”（用于 跳过/替换 逻辑）
_DATE_TOKEN_RE = re.compile(
    r"^\s*(?:"
    r"\d{4}[-_.]?\d{1,2}[-_.]?\d{1,2}(?:[T _\-]\d{2}[-.:]?\d{2}(?:[-.:]?\d{2})?)?"  # 2015-10-10 / 20151010 / 2015-10-10 14-30
    r"|\d{8}(?:\d{2}){0,3}"                                                          # 20151010 / 20151010143005
    r"|\d{2,4}[-_.]\d{1,2}[-_.]\d{1,2}"                                              # 15-10-10 / 2015.10.10
    r"|\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"                                      # 2015年10月10日
    r")"
)
_LEAD_SEP_RE = re.compile(r"^[\s_\-\.。，,、:：]+")


def leading_date_token(name):
    m = _DATE_TOKEN_RE.match(name)
    return m.group(0).strip() if m else None


def strip_leading_date(base):
    """去掉开头的日期Token，返回 (剩余名字, Token)。剩余为空则原样返回。"""
    m = _DATE_TOKEN_RE.match(base)
    if not m:
        return base, None
    token = m.group(0).strip()
    rest = _LEAD_SEP_RE.sub("", base[m.end():])
    return (rest if rest.strip() else base), token


def file_datetime(path, cfg):
    st = os.stat(long_path(path))
    src = cfg.get("date_source", "created")
    if src == "modified":
        ts = st.st_mtime
    elif src == "accessed":
        ts = st.st_atime
    else:
        ts = st.st_ctime          # Windows 上为创建时间
    return datetime.datetime.fromtimestamp(ts)


def build_stamp(dt, cfg):
    """按配置把日期(可选时间)格式化成字符串。"""
    date_str = dt.strftime(cfg.get("date_format", "%Y%m%d"))
    mode = cfg.get("include_time", "none")
    if mode == "hm":
        return date_str + cfg.get("time_sep", "_") + dt.strftime("%H%M")
    if mode == "hms":
        return date_str + cfg.get("time_sep", "_") + dt.strftime("%H-%M-%S")
    return date_str


def sample_new_name(cfg, name="某某文件.pdf", is_dir=False):
    """设置界面里的效果示例。"""
    root, ext = (name, "") if is_dir else os.path.splitext(name)
    stamp = build_stamp(SAMPLE_DT, cfg)
    sep = cfg.get("separator", " ")
    if cfg.get("position") == "prefix":
        new_base = stamp + sep + root if sep else stamp + root
    else:
        new_base = root + sep + stamp if sep else root + stamp
    return new_base + ext


def collect_targets(paths, cfg):
    """把传入路径展开为待处理条目列表（含跳过原因）。"""
    scope = cfg.get("scope", "both")
    include_hidden = bool(cfg.get("include_hidden"))

    def allowed(is_dir):
        if scope == "files" and is_dir:
            return False
        if scope == "folders" and not is_dir:
            return False
        return True

    items, seen = [], set()

    def add(p):
        p = os.path.abspath(p)
        key = os.path.normcase(p)
        if key in seen:
            return
        seen.add(key)
        exists = os.path.exists(p)
        is_dir = os.path.isdir(p) if exists else False
        reason = None
        if not exists:
            reason = "路径不存在"
        elif not allowed(is_dir):
            reason = "按设置跳过该类型"
        elif is_hidden_or_system(p) and not include_hidden:
            reason = "隐藏/系统项，按设置跳过"
        items.append({"path": p, "is_dir": is_dir, "skip": reason})

    for p in paths:
        p0 = os.path.abspath(p)
        if os.path.isdir(p0) and cfg.get("recursive"):
            # 先收集所有文件，再按“自底向上”收集文件夹，最后处理文件夹自身
            dirs = []
            for root, dnames, fnames in os.walk(p0):
                for f in fnames:
                    add(os.path.join(root, f))
                for d in dnames:
                    dirs.append(os.path.join(root, d))
                dirs.append(root)
            for d in sorted(set(dirs), key=lambda x: x.count(os.sep), reverse=True):
                add(d)
            add(p0)
        else:
            add(p0)
    return items


def build_plans(items, cfg):
    """生成重命名计划。每个计划: path/new_path/is_dir/old_name/new_name/status/reason"""
    exclude_exts = parse_exclude_exts(cfg.get("exclude_exts", ""))
    plans = []
    seq = 0

    for it in items:
        path, is_dir = it["path"], it["is_dir"]
        name = os.path.basename(path.rstrip("\\/")) or path

        if it["skip"]:
            plans.append(dict(path=path, new_path="", is_dir=is_dir,
                              old_name=name, new_name="", status="skip",
                              reason=it["skip"], checked=False))
            continue

        root, ext = (name, "") if is_dir else os.path.splitext(name)
        if ext.lower() in exclude_exts:
            plans.append(dict(path=path, new_path="", is_dir=is_dir,
                              old_name=name, new_name="", status="skip",
                              reason="扩展名在排除列表中", checked=False))
            continue

        existing = leading_date_token(name)
        if existing and cfg.get("existing_date") == "skip":
            plans.append(dict(path=path, new_path="", is_dir=is_dir,
                              old_name=name, new_name="", status="skip",
                              reason="文件名已包含日期前缀", checked=False))
            continue

        try:
            dt = file_datetime(path, cfg)
        except OSError as e:
            plans.append(dict(path=path, new_path="", is_dir=is_dir,
                              old_name=name, new_name="", status="skip",
                              reason="读取日期失败: %s" % e, checked=False))
            continue

        base = root
        if existing and cfg.get("existing_date") == "replace":
            base, _tok = strip_leading_date(root)

        stamp = build_stamp(dt, cfg)
        seq_str = ""
        if cfg.get("sequence"):
            seq += 1
            seq_str = cfg.get("seq_sep", "_") + str(seq).zfill(int(cfg.get("seq_digits", 3)))

        sep = cfg.get("separator", " ")
        if cfg.get("position") == "prefix":
            new_base = stamp + seq_str + sep + base if sep else stamp + seq_str + base
        else:
            new_base = base + sep + stamp + seq_str if sep else base + stamp + seq_str

        new_name = new_base + ext
        if new_name == name:
            plans.append(dict(path=path, new_path="", is_dir=is_dir,
                              old_name=name, new_name="", status="skip",
                              reason="名称未变化", checked=False))
            continue

        parent = os.path.dirname(path)
        new_path = os.path.join(parent, new_name)
        if os.path.exists(new_path) and os.path.normcase(new_path) != os.path.normcase(path):
            if cfg.get("conflict") == "skip":
                plans.append(dict(path=path, new_path="", is_dir=is_dir,
                                  old_name=name, new_name="", status="skip",
                                  reason="目标已存在，按设置跳过", checked=False))
                continue
            i = 1
            while i <= 999:
                cand_name = "%s (%d)%s" % (new_base, i, ext)
                cand_path = os.path.join(parent, cand_name)
                if not os.path.exists(cand_path):
                    new_name, new_path = cand_name, cand_path
                    break
                i += 1
            else:
                plans.append(dict(path=path, new_path="", is_dir=is_dir,
                                  old_name=name, new_name="", status="skip",
                                  reason="冲突项过多，跳过", checked=False))
                continue

        plans.append(dict(path=path, new_path=new_path, is_dir=is_dir,
                          old_name=name, new_name=new_name, status="ok",
                          reason="", checked=True))
    return plans


def execute_plans(plans, cfg, use_check=True):
    """执行计划。返回统计与结果列表；成功的批次写入撤销历史。"""
    ok = skip = err = 0
    done_items = []
    results = []
    for pl in plans:
        if pl["status"] != "ok" or (use_check and not pl.get("checked", True)):
            pl["status"] = pl["status"] if pl["status"] != "ok" else "skip"
            if not pl.get("reason"):
                pl["reason"] = "未勾选，跳过"
            skip += 1
            results.append(pl)
            continue
        try:
            os.rename(long_path(pl["path"]), long_path(pl["new_path"]))
            pl["status"] = "done"
            ok += 1
            done_items.append({"old": pl["path"], "new": pl["new_path"],
                               "is_dir": pl["is_dir"]})
        except OSError as e:
            pl["status"] = "error"
            pl["reason"] = str(e)
            err += 1
        results.append(pl)

    if done_items:
        History().add_batch(done_items)
        write_log(["成功 %d / 跳过 %d / 失败 %d" % (ok, skip, err)] +
                  ["%s -> %s" % (os.path.basename(d["old"]), os.path.basename(d["new"]))
                   for d in done_items])
    return {"ok": ok, "skip": skip, "error": err, "results": results}


# ---------------------------------------------------------------------------
# 撤销历史
# ---------------------------------------------------------------------------

class History(object):
    def __init__(self):
        self.path = history_path()
        self.batches = []
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.batches = data[:MAX_HISTORY]
        except Exception:
            self.batches = []

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.batches[:MAX_HISTORY], f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def add_batch(self, items):
        self.batches.insert(0, {
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": items,
        })
        self.batches = self.batches[:MAX_HISTORY]
        self.save()

    def remove(self, index):
        if 0 <= index < len(self.batches):
            del self.batches[index]
            self.save()


def undo_batch(batch):
    """按相反顺序还原一个批次，返回 (成功数, 失败数)。"""
    ok = err = 0
    for item in reversed(batch.get("items", [])):
        src, dst = item.get("new", ""), item.get("old", "")
        if not src or not dst:
            err += 1
            continue
        if not os.path.exists(long_path(src)):
            continue                      # 已被还原 / 不存在
        if os.path.exists(long_path(dst)):
            err += 1                      # 原路径被占用
            continue
        try:
            os.rename(long_path(src), long_path(dst))
            ok += 1
        except OSError:
            err += 1
    return ok, err


# ---------------------------------------------------------------------------
# 右键菜单注册（HKCU\Software\Classes，无需管理员）
# ---------------------------------------------------------------------------

def _verb_key_paths():
    base = r"Software\Classes"
    return {
        "files": base + r"\*\shell\\" + VERB_KEY_NAME,
        "dirs": base + r"\Directory\shell\\" + VERB_KEY_NAME,
        "background": base + r"\Directory\Background\shell\\" + VERB_KEY_NAME,
    }


def _set_verb(key_path, text, command, icon=None):
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, text)
        # Player：一次传入所有选中项（配合命令行的 "%*"）
        winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
        # 菜单项排在右键菜单最前面，避免与“打开”混淆
        winreg.SetValueEx(key, "Position", 0, winreg.REG_SZ, "Top")
        if icon:
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon)
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path + r"\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)


def _reg_delete_tree(root, path):
    import winreg
    try:
        key = winreg.OpenKey(root, path)
    except FileNotFoundError:
        return
    except OSError:
        return
    try:
        while True:
            try:
                sub = winreg.EnumKey(key, 0)
            except OSError:
                break
            _reg_delete_tree(root, path + "\\" + sub)
    finally:
        winreg.CloseKey(key)
    try:
        winreg.DeleteKey(root, path)
    except OSError:
        pass


def launcher_commands():
    """根据当前运行形态返回 (文件/文件夹菜单命令, 空白处菜单命令)。

    注意：传统静态 verb 只认 %1（第一个参数）；%* 不是有效占位符（会被展开成空串）。
    多选时资源管理器为每个选中项各启动一次进程，程序内部用队列聚合（见 queue_paths）。
    """
    if getattr(sys, "frozen", False):
        exe = os.path.abspath(sys.executable)
        return ('"%s" --run "%%1"' % exe, '"%s" --run "%%V"' % exe)
    pyw = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = os.path.abspath(sys.executable)
    script = os.path.abspath(__file__)
    return ('"%s" "%s" --run "%%1"' % (pyw, script),
            '"%s" "%s" --run "%%V"' % (pyw, script))


def icon_path():
    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable)
    ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
    return ico if os.path.exists(ico) else None


def register_context_menu(cfg=None):
    """注册右键菜单。返回 (成功标志, 信息列表)。"""
    cfg = cfg or load_config()
    cmd_files, cmd_bg = launcher_commands()
    icon = icon_path()
    keys = _verb_key_paths()
    msgs = []
    try:
        _set_verb(keys["files"], cfg.get("verb_text", DEFAULT_VERB_TEXT), cmd_files, icon)
        msgs.append("已注册：所有文件的右键菜单")
        _set_verb(keys["dirs"], cfg.get("verb_text", DEFAULT_VERB_TEXT), cmd_files, icon)
        msgs.append("已注册：文件夹的右键菜单")
        if cfg.get("register_background"):
            _set_verb(keys["background"], cfg.get("verb_text", DEFAULT_VERB_TEXT),
                      cmd_bg, icon)
            msgs.append("已注册：文件夹空白处右键")
        else:
            import winreg
            _reg_delete_tree(winreg.HKEY_CURRENT_USER, keys["background"])
        return True, msgs
    except Exception as e:
        return False, ["注册失败: %s" % e]


def unregister_context_menu():
    """注销右键菜单。返回 (成功标志, 信息列表)。"""
    import winreg
    hkcu = winreg.HKEY_CURRENT_USER
    msgs = []
    ok = True
    for name, path in _verb_key_paths().items():
        try:
            _reg_delete_tree(hkcu, path)
            msgs.append("已移除：%s" % path)
        except Exception as e:
            ok = False
            msgs.append("移除失败 %s: %s" % (path, e))
    return ok, msgs


def registration_status():
    import winreg
    out = {}
    for name, path in _verb_key_paths().items():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path):
                out[name] = True
        except OSError:
            out[name] = False
    return out


# ---------------------------------------------------------------------------
# GUI（wxPython）
# ---------------------------------------------------------------------------

try:
    import wx
except Exception:  # 无 GUI 环境时仅提供命令行能力
    wx = None


if wx is not None:

    class _Page(wx.Panel):
        """设置页基类：收集控件值 / 回填控件值。"""

        def load(self, cfg):
            raise NotImplementedError

        def collect(self, cfg):
            raise NotImplementedError

    # ----------------------------- 基本设置页 -----------------------------

    class BasicPage(_Page):
        def __init__(self, parent):
            super().__init__(parent)
            self.ctl = {}
            box = wx.BoxSizer(wx.VERTICAL)

            # 日期来源
            sb = wx.StaticBox(self, label="日期来源")
            sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
            row = wx.BoxSizer(wx.HORIZONTAL)
            self.ctl["date_source"] = {}
            for val, label in (("created", "创建日期"), ("modified", "修改日期"),
                               ("accessed", "访问日期")):
                rb = wx.RadioButton(self, label=label, style=wx.RB_GROUP if val == "created" else 0)
                self.ctl["date_source"][val] = rb
                row.Add(rb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 16)
            sbs.Add(row, 0, wx.EXPAND | wx.ALL, 6)
            box.Add(sbs, 0, wx.EXPAND | wx.ALL, 8)

            # 日期格式
            sb = wx.StaticBox(self, label="日期格式（选择预设，或直接输入 strftime 代码）")
            sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
            self.ctl["date_format"] = wx.ComboBox(
                self, value="%Y%m%d",
                choices=[p[0] for p in FORMAT_PRESETS])
            self.ctl["date_format"].Bind(wx.EVT_COMBOBOX, self.on_preset)
            sbs.Add(self.ctl["date_format"], 0, wx.EXPAND | wx.ALL, 6)
            hint = wx.StaticText(
                self, label="可用代码：%Y 年(4位)  %y 年(2位)  %m 月  %d 日  %H 时  %M 分  %S 秒  %j 年积日\n"
                            "中文可直接输入“年月日”，如：%Y年%m月%d日")
            hint.SetForegroundColour(wx.Colour(0x60, 0x60, 0x60))
            sbs.Add(hint, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
            box.Add(sbs, 0, wx.EXPAND | wx.ALL, 8)

            # 时间
            sb = wx.StaticBox(self, label="是否包含时间")
            sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
            row = wx.BoxSizer(wx.HORIZONTAL)
            self.ctl["include_time"] = {}
            for val, label in (("none", "不包含"), ("hm", "时分(1430)"), ("hms", "时分秒(14-30-05)")):
                rb = wx.RadioButton(self, label=label, style=wx.RB_GROUP if val == "none" else 0)
                self.ctl["include_time"][val] = rb
                row.Add(rb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 16)
            row.Add(wx.StaticText(self, label="日期与时间的连接符："), 0,
                    wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
            self.ctl["time_sep"] = wx.TextCtrl(self, size=(40, -1))
            row.Add(self.ctl["time_sep"], 0, wx.ALIGN_CENTER_VERTICAL)
            sbs.Add(row, 0, wx.EXPAND | wx.ALL, 6)
            box.Add(sbs, 0, wx.EXPAND | wx.ALL, 8)

            # 分隔符与位置
            sb = wx.StaticBox(self, label="日期与文件名的组合方式")
            sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
            row = wx.BoxSizer(wx.HORIZONTAL)
            row.Add(wx.StaticText(self, label="分隔符："), 0,
                    wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
            self.ctl["separator"] = wx.ComboBox(self, value=" ",
                                                choices=[" ", "_", "-", ".", ""])
            self.ctl["separator"].SetMinSize((60, -1))
            row.Add(self.ctl["separator"], 0, wx.RIGHT, 24)
            row.Add(wx.StaticText(self, label="位置："), 0,
                    wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
            self.ctl["position"] = {}
            for val, label in (("prefix", "文件名前(前缀)"), ("suffix", "文件名后(后缀)")):
                rb = wx.RadioButton(self, label=label, style=wx.RB_GROUP if val == "prefix" else 0)
                self.ctl["position"][val] = rb
                row.Add(rb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
            sbs.Add(row, 0, wx.EXPAND | wx.ALL, 6)
            box.Add(sbs, 0, wx.EXPAND | wx.ALL, 8)

            # 运行方式
            sb = wx.StaticBox(self, label="右键菜单的运行方式")
            sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
            self.ctl["direct_mode"] = wx.CheckBox(self, label="直接执行（右键点击后立即重命名，不弹预览窗口）")
            self.ctl["show_result"] = wx.CheckBox(self, label="执行后显示结果窗口（可撤销）")
            sbs.Add(self.ctl["direct_mode"], 0, wx.ALL, 4)
            sbs.Add(self.ctl["show_result"], 0, wx.ALL, 4)
            box.Add(sbs, 0, wx.EXPAND | wx.ALL, 8)

            # 示例
            sb = wx.StaticBox(self, label="效果示例（创建于 2015-10-10 14:30:05 的文件/文件夹）")
            sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
            self.sample_file = wx.StaticText(self, label="")
            self.sample_dir = wx.StaticText(self, label="")
            font = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
            self.sample_file.SetFont(font)
            self.sample_dir.SetFont(font)
            self.sample_file.SetForegroundColour(wx.Colour(0x1F, 0x5F, 0xB0))
            self.sample_dir.SetForegroundColour(wx.Colour(0x1F, 0x5F, 0xB0))
            sbs.Add(self.sample_file, 0, wx.ALL, 6)
            sbs.Add(self.sample_dir, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
            box.Add(sbs, 0, wx.EXPAND | wx.ALL, 8)

            self.SetSizer(box)

        def on_preset(self, event):
            """选择预设时，同步设置日期格式/时间/连接符。"""
            label = self.ctl["date_format"].GetValue()
            for lbl, fmt, tmode, tsep in FORMAT_PRESETS:
                if lbl == label:
                    self.ctl["date_format"].SetValue(fmt)
                    self.ctl["include_time"].get(tmode, self.ctl["include_time"]["none"]).SetValue(True)
                    self.ctl["time_sep"].SetValue(tsep)
                    break
            self.refresh_sample()
            event.Skip()

        def load(self, cfg):
            for val, rb in self.ctl["date_source"].items():
                rb.SetValue(cfg.get("date_source") == val)
            self.ctl["date_format"].SetValue(cfg.get("date_format", ""))
            for val, rb in self.ctl["include_time"].items():
                rb.SetValue(cfg.get("include_time") == val)
            self.ctl["time_sep"].SetValue(cfg.get("time_sep", "_"))
            self.ctl["separator"].SetValue(cfg.get("separator", " "))
            for val, rb in self.ctl["position"].items():
                rb.SetValue(cfg.get("position") == val)
            self.ctl["direct_mode"].SetValue(bool(cfg.get("direct_mode")))
            self.ctl["show_result"].SetValue(bool(cfg.get("show_result")))

        def collect(self, cfg):
            for val, rb in self.ctl["date_source"].items():
                if rb.GetValue():
                    cfg["date_source"] = val
            cfg["date_format"] = self.ctl["date_format"].GetValue().strip() or "%Y%m%d"
            for val, rb in self.ctl["include_time"].items():
                if rb.GetValue():
                    cfg["include_time"] = val
            cfg["time_sep"] = self.ctl["time_sep"].GetValue()
            cfg["separator"] = self.ctl["separator"].GetValue()
            for val, rb in self.ctl["position"].items():
                if rb.GetValue():
                    cfg["position"] = val
            cfg["direct_mode"] = self.ctl["direct_mode"].GetValue()
            cfg["show_result"] = self.ctl["show_result"].GetValue()

        def refresh_sample(self):
            cfg = dict(load_config())
            self.collect(cfg)
            self.sample_file.SetLabel("文件：某某文件.pdf  →  %s" % sample_new_name(cfg))
            self.sample_dir.SetLabel("文件夹：项目资料  →  %s" % sample_new_name(cfg, "项目资料", True))

    # ----------------------------- 高级设置页 -----------------------------

    class AdvancedPage(_Page):
        def __init__(self, parent):
            super().__init__(parent)
            self.ctl = {}
            box = wx.BoxSizer(wx.VERTICAL)

            sb = wx.StaticBox(self, label="原文件名已包含日期前缀时")
            sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
            self.ctl["existing_date"] = {}
            for i, (val, label) in enumerate((
                    ("skip", "跳过（推荐，避免重复添加日期）"),
                    ("replace", "替换已有日期（去掉旧日期再加新日期）"),
                    ("add", "仍然再添加一个"))):
                rb = wx.RadioButton(self, label=label, style=wx.RB_GROUP if i == 0 else 0)
                self.ctl["existing_date"][val] = rb
                sbs.Add(rb, 0, wx.ALL, 4)
            box.Add(sbs, 0, wx.EXPAND | wx.ALL, 8)

            sb = wx.StaticBox(self, label="新文件名已存在时")
            sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
            self.ctl["conflict"] = {}
            for i, (val, label) in enumerate((
                    ("suffix", "自动加序号：某某文件 (1).pdf"),
                    ("skip", "跳过该文件"))):
                rb = wx.RadioButton(self, label=label, style=wx.RB_GROUP if i == 0 else 0)
                self.ctl["conflict"][val] = rb
                sbs.Add(rb, 0, wx.ALL, 4)
            box.Add(sbs, 0, wx.EXPAND | wx.ALL, 8)

            sb = wx.StaticBox(self, label="处理范围")
            sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
            self.ctl["scope"] = {}
            for i, (val, label) in enumerate((
                    ("both", "文件和文件夹都处理"),
                    ("files", "仅处理文件"),
                    ("folders", "仅处理文件夹"))):
                rb = wx.RadioButton(self, label=label, style=wx.RB_GROUP if i == 0 else 0)
                self.ctl["scope"][val] = rb
                sbs.Add(rb, 0, wx.ALL, 4)
            self.ctl["recursive"] = wx.CheckBox(self, label="右键文件夹时，连同里面的子文件、子文件夹一起处理")
            self.ctl["include_hidden"] = wx.CheckBox(self, label="包含隐藏/系统文件")
            sbs.Add(self.ctl["recursive"], 0, wx.ALL, 4)
            sbs.Add(self.ctl["include_hidden"], 0, wx.ALL, 4)
            box.Add(sbs, 0, wx.EXPAND | wx.ALL, 8)

            sb = wx.StaticBox(self, label="序号")
            sbs = wx.StaticBoxSizer(sb, wx.HORIZONTAL)
            self.ctl["sequence"] = wx.CheckBox(self, label="在日期后追加序号")
            sbs.Add(self.ctl["sequence"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
            sbs.Add(wx.StaticText(self, label="位数："), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
            self.ctl["seq_digits"] = wx.TextCtrl(self, size=(40, -1))
            sbs.Add(self.ctl["seq_digits"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
            sbs.Add(wx.StaticText(self, label="连接符："), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
            self.ctl["seq_sep"] = wx.TextCtrl(self, size=(40, -1))
            sbs.Add(self.ctl["seq_sep"], 0, wx.ALIGN_CENTER_VERTICAL)
            box.Add(sbs, 0, wx.EXPAND | wx.ALL, 8)

            sb = wx.StaticBox(self, label="排除的扩展名（不处理这些文件）")
            sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
            self.ctl["exclude_exts"] = wx.TextCtrl(self, value="")
            self.ctl["exclude_exts"].SetHint("例如：.lnk, .tmp, .url（留空表示不排除）")
            sbs.Add(self.ctl["exclude_exts"], 0, wx.EXPAND | wx.ALL, 6)
            box.Add(sbs, 0, wx.EXPAND | wx.ALL, 8)

            self.SetSizer(box)

        def load(self, cfg):
            for val, rb in self.ctl["existing_date"].items():
                rb.SetValue(cfg.get("existing_date") == val)
            for val, rb in self.ctl["conflict"].items():
                rb.SetValue(cfg.get("conflict") == val)
            for val, rb in self.ctl["scope"].items():
                rb.SetValue(cfg.get("scope") == val)
            self.ctl["recursive"].SetValue(bool(cfg.get("recursive")))
            self.ctl["include_hidden"].SetValue(bool(cfg.get("include_hidden")))
            self.ctl["sequence"].SetValue(bool(cfg.get("sequence")))
            self.ctl["seq_digits"].SetValue(str(cfg.get("seq_digits", 3)))
            self.ctl["seq_sep"].SetValue(cfg.get("seq_sep", "_"))
            self.ctl["exclude_exts"].SetValue(cfg.get("exclude_exts", ""))

        def collect(self, cfg):
            for val, rb in self.ctl["existing_date"].items():
                if rb.GetValue():
                    cfg["existing_date"] = val
            for val, rb in self.ctl["conflict"].items():
                if rb.GetValue():
                    cfg["conflict"] = val
            for val, rb in self.ctl["scope"].items():
                if rb.GetValue():
                    cfg["scope"] = val
            cfg["recursive"] = self.ctl["recursive"].GetValue()
            cfg["include_hidden"] = self.ctl["include_hidden"].GetValue()
            cfg["sequence"] = self.ctl["sequence"].GetValue()
            try:
                cfg["seq_digits"] = int(self.ctl["seq_digits"].GetValue())
            except ValueError:
                cfg["seq_digits"] = 3
            cfg["seq_sep"] = self.ctl["seq_sep"].GetValue()
            cfg["exclude_exts"] = self.ctl["exclude_exts"].GetValue().strip()

    # ----------------------------- 右键菜单页 -----------------------------

    class MenuPage(_Page):
        def __init__(self, parent, on_change):
            super().__init__(parent)
            self.on_change = on_change
            self.ctl = {}
            box = wx.BoxSizer(wx.VERTICAL)

            sb = wx.StaticBox(self, label="右键菜单")
            sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
            row = wx.BoxSizer(wx.HORIZONTAL)
            row.Add(wx.StaticText(self, label="菜单显示文字："), 0,
                    wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
            self.ctl["verb_text"] = wx.TextCtrl(self, size=(200, -1))
            row.Add(self.ctl["verb_text"], 1, wx.RIGHT, 12)
            self.ctl["register_background"] = wx.CheckBox(
                self, label="同时注册到“文件夹空白处”右键（对当前文件夹生效）")
            row.Add(self.ctl["register_background"], 0, wx.ALIGN_CENTER_VERTICAL)
            sbs.Add(row, 0, wx.EXPAND | wx.ALL, 6)

            row = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_register = wx.Button(self, label="注册到右键菜单")
            self.btn_unregister = wx.Button(self, label="从右键菜单移除")
            self.btn_status = wx.Button(self, label="检查注册状态")
            row.Add(self.btn_register, 0, wx.RIGHT, 8)
            row.Add(self.btn_unregister, 0, wx.RIGHT, 8)
            row.Add(self.btn_status, 0)
            sbs.Add(row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

            self.status = wx.StaticText(self, label="")
            self.status.SetForegroundColour(wx.Colour(0x60, 0x60, 0x60))
            sbs.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
            box.Add(sbs, 0, wx.EXPAND | wx.ALL, 8)

            info = wx.StaticText(self, label=(
                "说明：\n"
                "· 注册写入当前用户注册表（HKCU\\Software\\Classes），不需要管理员权限；\n"
                "· 注册目标为本程序当前位置（exe 或 pythonw + 脚本），移动程序后请重新注册；\n"
                "· 资源管理器中多选文件/文件夹时，会一次性把所有选中项传给本程序批量处理；\n"
                "· 修改“菜单显示文字”或“空白处”选项后，需要重新点击“注册到右键菜单”生效；\n"
                "· 卸载：点击“从右键菜单移除”，然后删除本程序文件即可。"))
            info.SetForegroundColour(wx.Colour(0x60, 0x60, 0x60))
            box.Add(info, 0, wx.EXPAND | wx.ALL, 10)

            self.SetSizer(box)

            self.btn_register.Bind(wx.EVT_BUTTON, self.on_register)
            self.btn_unregister.Bind(wx.EVT_BUTTON, self.on_unregister)
            self.btn_status.Bind(wx.EVT_BUTTON, lambda e: self.refresh_status())

        def load(self, cfg):
            self.ctl["verb_text"].SetValue(cfg.get("verb_text", DEFAULT_VERB_TEXT))
            self.ctl["register_background"].SetValue(bool(cfg.get("register_background")))
            self.refresh_status()

        def collect(self, cfg):
            cfg["verb_text"] = self.ctl["verb_text"].GetValue().strip() or DEFAULT_VERB_TEXT
            cfg["register_background"] = self.ctl["register_background"].GetValue()

        def refresh_status(self):
            st = registration_status()
            labels = {"files": "文件菜单", "dirs": "文件夹菜单", "background": "空白处菜单"}
            parts = []
            for k in ("files", "dirs", "background"):
                if st.get(k):
                    parts.append("%s:已注册" % labels[k])
                elif k == "background":
                    continue
                else:
                    parts.append("%s:未注册" % labels[k])
            self.status.SetLabel("当前状态 — " + "；".join(parts))

        def on_register(self, event):
            cfg = dict(load_config())
            self.collect(cfg)
            ok, msgs = register_context_menu(cfg)
            save_config(cfg)
            self.on_change()
            self.refresh_status()
            dlg = wx.MessageDialog(
                self, "\n".join(msgs) + ("\n\n注册成功。" if ok else "\n\n注册失败。"),
                "注册右键菜单", wx.OK | (wx.ICON_INFORMATION if ok else wx.ICON_ERROR))
            dlg.ShowModal()
            dlg.Destroy()

        def on_unregister(self, event):
            ok, msgs = unregister_context_menu()
            self.refresh_status()
            dlg = wx.MessageDialog(self, "\n".join(msgs), "移除右键菜单",
                                   wx.OK | (wx.ICON_INFORMATION if ok else wx.ICON_ERROR))
            dlg.ShowModal()
            dlg.Destroy()

    # ----------------------------- 撤销页 -----------------------------

    class UndoPage(_Page):
        def __init__(self, parent):
            super().__init__(parent)
            box = wx.BoxSizer(wx.VERTICAL)
            self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
            for i, (label, w) in enumerate((("时间", 180), ("项目数", 70), ("说明", 220))):
                self.list.InsertColumn(i, label, width=w)
            box.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)

            row = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_undo = wx.Button(self, label="撤销选中批次")
            self.btn_refresh = wx.Button(self, label="刷新列表")
            row.Add(self.btn_undo, 0, wx.RIGHT, 8)
            row.Add(self.btn_refresh, 0)
            box.Add(row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

            hint = wx.StaticText(self, label="提示：撤销会按相反顺序把文件名改回去；"
                                             "若原文件名已被占用，该项会被跳过。")
            hint.SetForegroundColour(wx.Colour(0x60, 0x60, 0x60))
            box.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            self.SetSizer(box)

            self.btn_undo.Bind(wx.EVT_BUTTON, self.on_undo)
            self.btn_refresh.Bind(wx.EVT_BUTTON, lambda e: self.refresh())
            self.refresh()

        def load(self, cfg):
            self.refresh()

        def collect(self, cfg):
            pass

        def refresh(self):
            self.list.DeleteAllItems()
            hist = History()
            for idx, batch in enumerate(hist.batches):
                pos = self.list.InsertItem(self.list.GetItemCount(), batch.get("time", ""))
                self.list.SetItem(pos, 1, str(len(batch.get("items", []))))
                first = batch["items"][0] if batch.get("items") else {}
                desc = ""
                if first:
                    desc = "%s → %s" % (os.path.basename(first.get("old", "")),
                                        os.path.basename(first.get("new", "")))
                self.list.SetItem(pos, 2, desc)
                self.list.SetItemData(pos, idx)

        def on_undo(self, event):
            sel = self.list.GetFirstSelected()
            if sel < 0:
                wx.MessageBox("请先选择要撤销的批次。", "提示")
                return
            idx = self.list.GetItemData(sel)
            hist = History()
            if not (0 <= idx < len(hist.batches)):
                return
            batch = hist.batches[idx]
            ok, err = undo_batch(batch)
            if err == 0:
                hist.remove(idx)
            self.refresh()
            wx.MessageBox("撤销完成：成功 %d 项，跳过 %d 项。" % (ok, err), "撤销")

    # ----------------------------- 关于页 -----------------------------

    class AboutPage(_Page):
        def __init__(self, parent):
            super().__init__(parent)
            box = wx.BoxSizer(wx.VERTICAL)
            text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_AUTO_URL,
                               value=(
                "RenameTime 使用说明\n"
                "====================\n\n"
                "1. 注册：在“右键菜单”页点击【注册到右键菜单】。\n"
                "   之后在资源管理器中选中文件/文件夹，右键即可看到菜单项。\n\n"
                "2. 使用：选中一个或多个文件/文件夹 → 右键 → “添加日期前缀”。\n"
                "   多选时一次性全部处理；混合选择文件和文件夹也可以。\n\n"
                "3. 拖拽：把文件或文件夹拖到本窗口，可以先预览再执行。\n\n"
                "4. 默认行为：文件名已包含日期前缀时会跳过，避免反复右键\n"
                "   造成“20151010 20151010 某某.pdf”。如需替换旧日期，\n"
                "   在“高级选项”里选择“替换已有日期”。\n\n"
                "5. 撤销：每次批量重命名都会记录在“撤销”页，可整批还原。\n\n"
                "6. 常见格式示例：\n"
                "   20151010 某某.pdf        (%Y%m%d)\n"
                "   2015-10-10 某某.pdf      (%Y-%m-%d)\n"
                "   2015年10月10日 某某.pdf  (%Y年%m月%d日)\n"
                "   20151010_1430 某某.pdf   (%Y%m%d + 时分)\n\n"
                "7. 命令行：\n"
                "   rename_time.exe --run 文件...   右键菜单调用\n"
                "   rename_time.exe --register/--unregister/--status\n"
                "   rename_time.exe --undo          撤销最近一批\n\n"
                "8. 配置文件位置：%APPDATA%\\RenameTime\\config.json\n"))
            box.Add(text, 1, wx.EXPAND | wx.ALL, 8)
            self.SetSizer(box)

        def load(self, cfg):
            pass

        def collect(self, cfg):
            pass

    # ----------------------------- 设置主窗口 -----------------------------

    class SettingsFrame(wx.Frame):
        def __init__(self):
            super().__init__(None, title="RenameTime — 文件日期重命名设置",
                             size=(780, 700),
                             style=wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX)
            self.cfg = load_config()
            self.icon = None
            try:
                ico = icon_path()
                if ico and os.path.exists(ico):
                    self.icon = wx.Icon(ico, wx.BITMAP_TYPE_ICO)
                    self.SetIcon(self.icon)
            except Exception:
                pass

            panel = wx.Panel(self)
            outer = wx.BoxSizer(wx.VERTICAL)

            self.nb = wx.Notebook(panel)
            self.page_basic = BasicPage(self.nb)
            self.page_adv = AdvancedPage(self.nb)
            self.page_menu = MenuPage(self.nb, self.on_menu_change)
            self.page_undo = UndoPage(self.nb)
            self.page_about = AboutPage(self.nb)
            self.nb.AddPage(self.page_basic, "基本设置")
            self.nb.AddPage(self.page_adv, "高级选项")
            self.nb.AddPage(self.page_menu, "右键菜单")
            self.nb.AddPage(self.page_undo, "撤销")
            self.nb.AddPage(self.page_about, "使用说明")
            outer.Add(self.nb, 1, wx.EXPAND | wx.ALL, 8)

            row = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_save = wx.Button(panel, label="保存设置")
            self.btn_default = wx.Button(panel, label="恢复默认设置")
            self.btn_close = wx.Button(panel, label="关闭")
            row.Add(self.btn_save, 0, wx.RIGHT, 8)
            row.Add(self.btn_default, 0, wx.RIGHT, 8)
            row.AddStretchSpacer()
            row.Add(self.btn_close, 0)
            outer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
            panel.SetSizer(outer)

            self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
            self.btn_default.Bind(wx.EVT_BUTTON, self.on_default)
            self.btn_close.Bind(wx.EVT_BUTTON, lambda e: self.Close())
            self.Bind(wx.EVT_CLOSE, self.on_close)

            # 任何控件变化都刷新示例
            self._bind_change(self.page_basic)
            self._bind_change(self.page_adv)

            # 支持把文件拖到窗口
            self.SetDropTarget(_FilesDropTarget(self))
            for page in (self.page_basic, self.page_adv, self.page_menu,
                         self.page_undo, self.page_about):
                page.SetDropTarget(_FilesDropTarget(self))

            self.load_pages(self.cfg)
            self.Centre()

        def _bind_change(self, page):
            """页面内任何控件变化都刷新效果示例。"""
            def refresh(e):
                self.page_basic.refresh_sample()
                e.Skip()

            def walk(win):
                for child in win.GetChildren():
                    yield child
                    for sub in walk(child):
                        yield sub

            for child in walk(page):
                for evt in (wx.EVT_TEXT, wx.EVT_COMBOBOX,
                            wx.EVT_RADIOBUTTON, wx.EVT_CHECKBOX):
                    child.Bind(evt, refresh)

        def load_pages(self, cfg):
            for page in (self.page_basic, self.page_adv, self.page_menu,
                         self.page_undo, self.page_about):
                page.load(cfg)
            self.page_basic.refresh_sample()

        def collect(self):
            cfg = dict(self.cfg)
            for page in (self.page_basic, self.page_adv, self.page_menu,
                         self.page_undo, self.page_about):
                page.collect(cfg)
            _validate(cfg)
            return cfg

        def on_save(self, event):
            self.cfg = self.collect()
            save_config(self.cfg)
            self.page_basic.refresh_sample()
            wx.MessageBox("设置已保存。", "提示")

        def on_default(self, event):
            self.cfg = dict(DEFAULT_CONFIG)
            self.load_pages(self.cfg)
            self.page_basic.refresh_sample()

        def on_menu_change(self):
            self.cfg = self.collect()
            save_config(self.cfg)

        def on_close(self, event):
            self.cfg = self.collect()
            save_config(self.cfg)
            event.Skip()

        def open_preview(self, paths):
            paths = normalize_paths(paths)
            if not paths:
                return
            cfg = self.collect()
            save_config(cfg)
            frame = PreviewFrame(paths, cfg, parent=self)
            frame.Show()

    class _FilesDropTarget(wx.FileDropTarget):
        def __init__(self, frame):
            super().__init__()
            self.frame = frame

        def OnDropFiles(self, x, y, filenames):
            self.frame.open_preview(filenames)
            return True

    # ----------------------------- 预览窗口 -----------------------------

    class PreviewFrame(wx.Frame):
        def __init__(self, paths, cfg, parent=None):
            super().__init__(parent, title="RenameTime — 重命名预览",
                             size=(860, 520),
                             style=wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX)
            try:
                ico = icon_path()
                if ico and os.path.exists(ico):
                    self.SetIcon(wx.Icon(ico, wx.BITMAP_TYPE_ICO))
            except Exception:
                pass

            self.cfg = cfg
            self.plans = build_plans(collect_targets(paths, cfg), cfg)

            panel = wx.Panel(self)
            outer = wx.BoxSizer(wx.VERTICAL)

            tip = wx.StaticText(panel, label="点击行可勾选/取消；只处理勾选的项。")
            tip.SetForegroundColour(wx.Colour(0x60, 0x60, 0x60))
            outer.Add(tip, 0, wx.ALL, 8)

            self.list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
            for i, (label, w) in enumerate((
                    ("√", 34), ("原文件名", 230), ("新文件名", 260), ("说明", 220))):
                self.list.InsertColumn(i, label, width=w)
            outer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

            row = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_all = wx.Button(panel, label="全选")
            self.btn_none = wx.Button(panel, label="全不选")
            self.btn_settings = wx.Button(panel, label="打开设置")
            self.btn_exec = wx.Button(panel, label="执行重命名")
            self.btn_exec.SetForegroundColour(wx.Colour(0xC0, 0x30, 0x30))
            row.Add(self.btn_all, 0, wx.RIGHT, 8)
            row.Add(self.btn_none, 0, wx.RIGHT, 8)
            row.Add(self.btn_settings, 0, wx.RIGHT, 8)
            row.AddStretchSpacer()
            row.Add(self.btn_exec, 0)
            outer.Add(row, 0, wx.EXPAND | wx.ALL, 10)
            panel.SetSizer(outer)

            self.list.Bind(wx.EVT_LEFT_DOWN, self.on_click)
            self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_activate)
            self.btn_all.Bind(wx.EVT_BUTTON, lambda e: self.set_all(True))
            self.btn_none.Bind(wx.EVT_BUTTON, lambda e: self.set_all(False))
            self.btn_settings.Bind(wx.EVT_BUTTON, self.on_settings)
            self.btn_exec.Bind(wx.EVT_BUTTON, self.on_exec)

            self.refresh_list()
            self.Centre()

        def refresh_list(self):
            self.list.DeleteAllItems()
            for i, pl in enumerate(self.plans):
                mark = "√" if (pl["status"] == "ok" and pl.get("checked")) else ""
                pos = self.list.InsertItem(i, mark)
                self.list.SetItem(pos, 1, pl["old_name"])
                self.list.SetItem(pos, 2, pl["new_name"] or "—")
                reason = pl["reason"]
                if pl["status"] == "ok" and not reason:
                    reason = "待执行"
                self.list.SetItem(pos, 3, reason)
                if pl["status"] != "ok":
                    self.list.SetItemTextColour(pos, wx.Colour(0x99, 0x99, 0x99))
                self.list.SetItemData(pos, i)
            self._update_exec_label()

        def _update_exec_label(self):
            n = sum(1 for pl in self.plans
                    if pl["status"] == "ok" and pl.get("checked"))
            self.btn_exec.SetLabel("执行重命名（%d）" % n)

        def _row_at(self, event):
            pos = event.GetPosition()
            item, flags = self.list.HitTest(pos)
            return item if flags & wx.LIST_HITTEST_ONITEM else -1

        def on_click(self, event):
            idx = self._row_at(event)
            if idx >= 0:
                self._toggle(idx)
            event.Skip()

        def on_activate(self, event):
            self._toggle(event.GetIndex())
            event.Skip()

        def _toggle(self, idx):
            data = self.list.GetItemData(idx)
            if 0 <= data < len(self.plans):
                pl = self.plans[data]
                if pl["status"] == "ok":
                    pl["checked"] = not pl.get("checked", True)
                    self.list.SetItem(idx, 0, "√" if pl["checked"] else "")
                    self._update_exec_label()

        def set_all(self, value):
            for i, pl in enumerate(self.plans):
                if pl["status"] == "ok":
                    pl["checked"] = value
            self.refresh_list()

        def on_settings(self, event):
            frame = SettingsFrame()
            frame.Show()

        def on_exec(self, event):
            n = sum(1 for pl in self.plans
                    if pl["status"] == "ok" and pl.get("checked"))
            if n == 0:
                wx.MessageBox("没有勾选任何可执行的项目。", "提示")
                return
            dlg = wx.MessageDialog(
                self, "即将重命名 %d 个项目，是否继续？\n（可在“撤销”页或结果窗口还原）" % n,
                "确认执行", wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() != wx.ID_YES:
                dlg.Destroy()
                return
            dlg.Destroy()
            stats = execute_plans(self.plans, self.cfg)
            ResultDialog(self, stats).ShowModal()
            self.refresh_list()

    # ----------------------------- 结果窗口 -----------------------------

    class ResultDialog(wx.Dialog):
        def __init__(self, parent, stats):
            super().__init__(parent, title="RenameTime — 执行结果",
                             size=(720, 460),
                             style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
            try:
                ico = icon_path()
                if ico and os.path.exists(ico):
                    self.SetIcon(wx.Icon(ico, wx.BITMAP_TYPE_ICO))
            except Exception:
                pass
            self.stats = stats

            outer = wx.BoxSizer(wx.VERTICAL)
            summary = wx.StaticText(
                self, label="成功 %d 项，跳过 %d 项，失败 %d 项。" % (
                    stats["ok"], stats["skip"], stats["error"]))
            summary.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                                    wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            outer.Add(summary, 0, wx.ALL, 10)

            self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
            lines = []
            for pl in stats["results"]:
                if pl["status"] == "done":
                    lines.append("✓ %s  →  %s" % (pl["old_name"], pl["new_name"]))
                elif pl["status"] == "error":
                    lines.append("✗ %s ：%s" % (pl["old_name"], pl.get("reason", "")))
                else:
                    lines.append("⊘ %s ：%s" % (pl["old_name"], pl.get("reason", "")))
            self.text.SetValue("\n".join(lines) if lines else "（没有项目）")
            outer.Add(self.text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

            row = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_undo = wx.Button(self, label="撤销这批重命名")
            self.btn_close = wx.Button(self, label="关闭", id=wx.ID_CLOSE)
            row.Add(self.btn_undo, 0, wx.RIGHT, 8)
            row.AddStretchSpacer()
            row.Add(self.btn_close, 0)
            outer.Add(row, 0, wx.EXPAND | wx.ALL, 10)
            self.SetSizer(outer)

            self.btn_undo.Bind(wx.EVT_BUTTON, self.on_undo)
            self.btn_close.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_OK))
            self.Centre()

        def on_undo(self, event):
            hist = History()
            if not hist.batches:
                wx.MessageBox("没有可撤销的记录。", "提示")
                return
            batch = hist.batches[0]
            ok, err = undo_batch(batch)
            if err == 0:
                hist.remove(0)
            wx.MessageBox("撤销完成：成功 %d 项，跳过 %d 项。" % (ok, err), "撤销")
            self.EndModal(wx.ID_OK)


def gui_settings():
    app = wx.App(False)
    SettingsFrame().Show()
    app.MainLoop()


def gui_run(paths):
    """右键菜单/拖拽调用。返回进程退出码。"""
    cfg = load_config()
    paths = normalize_paths(paths)
    append_launch_log("  gui_run：%d 个路径，direct_mode=%s show_result=%s" % (
        len(paths), cfg.get("direct_mode"), cfg.get("show_result")))
    if not paths:
        return 0
    if cfg.get("direct_mode"):
        plans = build_plans(collect_targets(paths, cfg), cfg)
        stats = execute_plans(plans, cfg)
        append_launch_log("  执行结果：成功 %d，跳过 %d，失败 %d" % (
            stats["ok"], stats["skip"], stats["error"]))
        if cfg.get("show_result"):
            app = wx.App(False)
            ResultDialog(None, stats).ShowModal()
        else:
            print("成功 %d，跳过 %d，失败 %d" % (stats["ok"], stats["skip"], stats["error"]))
        return 0
    app = wx.App(False)
    PreviewFrame(paths, cfg).Show()
    app.MainLoop()
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def _setup_console():
    """Windows 下让命令行输出中文不乱码：
    有控制台时按控制台代码页（如中文系统 936）输出；
    无控制台（管道/重定向/GUI 启动）时统一用 UTF-8。"""
    if os.name != "nt":
        return
    try:
        import ctypes
        import io
        cp = ctypes.windll.kernel32.GetConsoleOutputCP()
        if not cp:
            enc = "utf-8"                     # 无控制台
        elif cp == 65001:
            return                            # 控制台已是 UTF-8
        else:
            enc = "cp%d" % cp
            try:
                "测试".encode(enc)
            except Exception:
                enc = "mbcs"
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=enc,
                                      errors="replace", line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding=enc,
                                      errors="replace", line_buffering=True)
    except Exception:
        pass


def notify_no_paths():
    """没有收到任何有效路径时给出明确提示（避免“点了没反应”）。"""
    append_launch_log("  警告：没有收到任何有效路径")
    if wx is None:
        print("没有收到任何有效文件路径。")
        return
    try:
        app = wx.App(False)
        wx.MessageBox(
            "没有收到任何有效的文件路径。\n\n"
            "如果你是从资源管理器右键点击的，说明右键菜单注册已失效，\n"
            "请打开本程序 →「右键菜单」页 → 点击【注册到右键菜单】。",
            "RenameTime", wx.OK | wx.ICON_WARNING)
    except Exception:
        pass


def main(argv=None):
    _setup_console()
    append_launch_log("[%s] 启动 argv=%r" % (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), list(sys.argv)))
    parser = argparse.ArgumentParser(
        prog=APP_NAME, description="Windows 右键菜单文件日期重命名工具")
    parser.add_argument("paths", nargs="*", help="要处理的文件/文件夹路径")
    parser.add_argument("--run", action="store_true", help="按设置执行重命名（右键菜单调用）")
    parser.add_argument("--register", action="store_true", help="注册右键菜单")
    parser.add_argument("--unregister", action="store_true", help="注销右键菜单")
    parser.add_argument("--status", action="store_true", help="查看右键菜单注册状态")
    parser.add_argument("--undo", action="store_true", help="撤销最近一批重命名")
    args = parser.parse_args(argv)

    if args.register:
        ok, msgs = register_context_menu()
        print("\n".join(msgs))
        return 0 if ok else 1
    if args.unregister:
        ok, msgs = unregister_context_menu()
        print("\n".join(msgs))
        return 0 if ok else 1
    if args.status:
        st = registration_status()
        labels = {"files": "所有文件的右键菜单", "dirs": "文件夹的右键菜单",
                  "background": "文件夹空白处右键"}
        for k, label in labels.items():
            print("%s: %s" % (label, "已注册" if st.get(k) else "未注册"))
        return 0
    if args.undo:
        hist = History()
        if not hist.batches:
            print("没有可撤销的记录。")
            return 0
        batch = hist.batches[0]
        ok, err = undo_batch(batch)
        if err == 0:
            hist.remove(0)
        print("撤销完成：成功 %d 项，跳过 %d 项。" % (ok, err))
        return 0
    if args.run:
        paths = normalize_paths(args.paths)
        append_launch_log("  --run 直接收到 %d 个参数 -> %d 个路径: %r" % (
            len(args.paths), len(paths), paths))
        # 资源管理器多选时会为每个文件各启动一个进程，这里聚合成一批统一处理
        if len(paths) == 1:
            queue_paths(paths)
            if not try_become_leader():
                append_launch_log("  聚合：本进程为跟随进程，已投递队列，退出")
                return 0
            paths = collect_batch()
            append_launch_log("  聚合：本进程为批次主控，收齐 %d 个路径: %r" % (
                len(paths), paths))
        if not paths:
            notify_no_paths()
            return 0
        if wx is None:
            # 无 GUI 环境：纯引擎执行
            cfg = load_config()
            plans = build_plans(collect_targets(paths, cfg), cfg)
            stats = execute_plans(plans, cfg)
            print("成功 %d，跳过 %d，失败 %d" % (stats["ok"], stats["skip"], stats["error"]))
            return 0
        return gui_run(paths)
    if args.paths:
        # 拖到 exe 上：走预览窗口
        if wx is None:
            cfg = load_config()
            plans = build_plans(collect_targets(normalize_paths(args.paths), cfg), cfg)
            stats = execute_plans(plans, cfg)
            print("成功 %d，跳过 %d，失败 %d" % (stats["ok"], stats["skip"], stats["error"]))
            return 0
        return gui_run(normalize_paths(args.paths))

    # 默认：打开设置界面
    if wx is None:
        parser.print_help()
        return 1
    gui_settings()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        import traceback
        append_launch_log("未捕获异常：\n" + traceback.format_exc())
        raise
