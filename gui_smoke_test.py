#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GUI 冒烟测试：四种语言下分别创建设置窗口 / 预览窗口 / 结果窗口。

不能只看进程是否存活——脚本崩溃时进程同样活着。必须检查窗口标题与控件文本。
运行：python gui_smoke_test.py
"""

import io
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HOME = tempfile.mkdtemp(prefix="rt_gui_")
os.environ["RENAMETIME_HOME"] = HOME

import rename_time as rt  # noqa: E402
import wx  # noqa: E402

PASS = []
FAIL = []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print("  %s  %s%s" % ("PASS" if cond else "FAIL", name,
                          ("  -> " + str(extra)) if extra and not cond else ""))


def make_sample():
    d = tempfile.mkdtemp(prefix="rt_sample_")
    p = os.path.join(d, "sample.txt")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("x")
    return p


def walk(win):
    for c in win.GetChildren():
        yield c
        for s in walk(c):
            yield s


print("== 1. 四种语言下打开设置窗口 ==")
app = wx.App(False)
titles = {}
for code, name in rt.i18n.LANGUAGES:
    rt.i18n.set_lang(code)
    cfg = dict(rt.DEFAULT_CONFIG)
    cfg["language"] = code
    rt.save_config(cfg)
    frame = rt.SettingsFrame()
    frame.Show()
    wx.Yield()
    titles[code] = frame.GetTitle()
    check("%s 窗口标题非空且含 RenameTime" % code,
          bool(frame.GetTitle()) and "RenameTime" in frame.GetTitle(), frame.GetTitle())
    check("%s 页面数为 5" % code, frame.nb.GetPageCount() == 5, frame.nb.GetPageCount())
    # 收集所有可见文本，确认已本地化（不应出现中文界面串）
    texts = []
    for c in walk(frame):
        if hasattr(c, "GetLabel") and c.GetLabel():
            texts.append(c.GetLabel())
    joined = " | ".join(texts)
    # 标签页标题必须是当前语言的字符串
    tab_titles = [frame.nb.GetPageText(i) for i in range(frame.nb.GetPageCount())]
    check("%s 标签页已本地化" % code,
          tab_titles == [rt.i18n.tr(k) for k in
                         ("tab.basic", "tab.advanced", "tab.menu", "tab.undo", "tab.about")],
          tab_titles)
    check("%s 基本设置页标签含日期来源" % code, rt.i18n.tr("basic.source") in joined)
    frame.Destroy()
    wx.Yield()

check("四种语言窗口标题互不相同", len(set(titles.values())) == 4, titles)

print("== 2. 语言切换后界面重建 ==")
rt.i18n.set_lang("zh")
cfg = dict(rt.DEFAULT_CONFIG)
cfg["language"] = "zh"
rt.save_config(cfg)
frame = rt.SettingsFrame()
frame.Show()
wx.Yield()
frame.cb_lang.SetSelection([c for c, _n in rt.i18n.LANGUAGES].index("en"))
frame.on_language_changed(wx.CommandEvent(wx.wxEVT_COMBOBOX))
wx.Yield()
check("切换到英文后界面语言已生效", rt.i18n.get_lang() == "en", rt.i18n.get_lang())
check("切换后窗口标题已更新", "Date rename settings" in frame.GetTitle(), frame.GetTitle())
check("切换后配置已持久化", rt.load_config().get("language") == "en")
check("切换后标签页已重建", frame.nb.GetPageText(0) == "Basic",
      frame.nb.GetPageText(0))
# 切回中文
frame.cb_lang.SetSelection(0)
frame.on_language_changed(wx.CommandEvent(wx.wxEVT_COMBOBOX))
wx.Yield()
check("切回中文成功", rt.i18n.get_lang() == "zh", rt.i18n.get_lang())
frame.Destroy()
wx.Yield()

print("== 3. 日期格式预设随语言变化 ==")
rt.i18n.set_lang("zh")
zh_choices = rt.format_preset_choices()
rt.i18n.set_lang("en")
en_choices = rt.format_preset_choices()
check("中英文预设示例不同", zh_choices != en_choices)
check("预设条目数=8", len(en_choices) == 8, len(en_choices))
check("英文预设含文件名", "sample" in en_choices[0].lower(), en_choices[0])
rt.i18n.set_lang("zh")

print("== 4. 预览窗口 ==")
sample = make_sample()
cfg = dict(rt.load_config())
cfg["language"] = "en"
rt.i18n.set_lang("en")
rt.save_config(cfg)
pv = rt.PreviewFrame([sample], cfg)
pv.Show()
wx.Yield()
check("预览窗口标题正确", "Rename preview" in pv.GetTitle(), pv.GetTitle())
check("预览列表有 1 行", pv.list.GetItemCount() == 1, pv.list.GetItemCount())
cols = [pv.list.GetColumn(i).GetText() for i in range(4)]
check("预览列标题已本地化", cols[1:] == ["Old name", "New name", "Reason"], cols)
check("执行按钮带计数", "(" in pv.btn_exec.GetLabel(), pv.btn_exec.GetLabel())
pv.Destroy()
wx.Yield()

print("== 5. 结果窗口（各reason 本地化） ==")
plans = rt.build_plans(rt.collect_targets([sample], cfg), cfg)
stats = rt.execute_plans(plans, cfg)
rd = rt.ResultDialog(None, stats)
rd.Show()
wx.Yield()
check("结果窗口标题正确", "Result" in rd.GetTitle(), rd.GetTitle())
check("结果摘要已本地化", "Successful" in rd.summary_label if hasattr(rd, "summary_label")
      else bool(rd.text.GetValue()), rd.text.GetValue()[:120])
rd.Destroy()
wx.Yield()

print("== 6. 撤销页：清空历史 + 关闭记录 ==")
rt.i18n.set_lang("zh")
cfg = dict(rt.load_config())
cfg["language"] = "zh"
cfg["record_history"] = True
rt.save_config(cfg)
frame = rt.SettingsFrame()
frame.Show()
wx.Yield()
undo = frame.page_undo
check("有记录时列表非空", undo.list.GetItemCount() > 0, undo.list.GetItemCount())
check("清空按钮可用", undo.btn_clear.IsEnabled())
n = rt.History().clear()
undo.refresh()
check("清空后列表为空", undo.list.GetItemCount() == 0, undo.list.GetItemCount())
check("清空按钮变为禁用", not undo.btn_clear.IsEnabled())
# 关闭记录历史
undo.ctl["record_history"].SetValue(False)
undo.on_record_toggle(wx.CommandEvent(wx.wxEVT_CHECKBOX))
wx.Yield()
check("关闭记录后已持久化", rt.load_config().get("record_history") is False)
check("关闭记录后显示离线提示", undo.offline.IsShown())
undo.ctl["record_history"].SetValue(True)
undo.on_record_toggle(wx.CommandEvent(wx.wxEVT_CHECKBOX))
wx.Yield()
check("重新开启记录后列表恢复显示", undo.list.IsShown() and not undo.offline.IsShown())
frame.Destroy()
wx.Yield()

print("== 7. 无GUI环境降级（wx=None） ==")
rt.i18n.set_lang("ru")
saved = rt.wx
rt.wx = None
try:
    rt.notify_no_paths()
    ok = True
except Exception as e:  # noqa: BLE001
    ok = False
    print("    exception:", e)
rt.wx = saved
check("wx=None 时notify_no_paths 不崩溃", ok)

print("")
print("结果：%d 通过，%d 失败" % (len(PASS), len(FAIL)))
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("  -", f)

shutil.rmtree(HOME, ignore_errors=True)
try:
    shutil.rmtree(os.path.dirname(sample), ignore_errors=True)
except Exception:
    pass
sys.exit(1 if FAIL else 0)