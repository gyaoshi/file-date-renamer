#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多语言模块自测：校验四种语言的词条键完全一致、占位符可用。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import i18n  # noqa: E402

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS  %s" % name)
    else:
        FAIL += 1
        print("  FAIL  %s  %s" % (name, detail))


def main():
    base = set(i18n.STRINGS["zh"].keys())
    print("== 1. 词条键对齐（以中文 %d 条为基准）==" % len(base))
    for code, _name in i18n.LANGUAGES:
        keys = set(i18n.STRINGS[code].keys())
        missing = base - keys
        extra = keys - base
        check("%s 键齐全" % code, not missing, "缺失: %s" % sorted(missing)[:8])
        check("%s 无多余键" % code, not extra, "多余: %s" % sorted(extra)[:8])

    print("== 2. 占位符一致（同一键在不同语言中的 {} 数量相同）==")
    import re
    bad = []
    for key in sorted(base):
        counts = {}
        for code, _ in i18n.LANGUAGES:
            text = i18n.STRINGS[code].get(key, "")
            counts[code] = len(re.findall(r"\{\d*\}", text))
        if len(set(counts.values())) != 1:
            bad.append((key, counts))
    check("全部 %d 个带参词条的占位符数量一致" % len(base), not bad, str(bad[:3]))

    print("== 3. 格式化与回退 ==")
    i18n.set_lang("en")
    check("英文取词", i18n.tr("btn.save") == "Save settings", i18n.tr("btn.save"))
    check("英文格式化", i18n.tr("rs.summary", 3, 1, 0) == "3 succeeded, 1 skipped, 0 failed.",
          i18n.tr("rs.summary", 3, 1, 0))
    i18n.set_lang("ru")
    check("俄语取词", i18n.tr("tab.undo") == "Отмена", i18n.tr("tab.undo"))
    check("俄语格式化", "2" in i18n.tr("undo.done", 2, 0) and "0" in i18n.tr("undo.done", 2, 0),
          i18n.tr("undo.done", 2, 0))
    i18n.set_lang("ja")
    check("日语取词", i18n.tr("btn.close") == "閉じる", i18n.tr("btn.close"))
    i18n.set_lang("zh")
    check("中文取词", i18n.tr("btn.close") == "关闭", i18n.tr("btn.close"))
    check("未知键回退为键名", i18n.tr("no.such.key") == "no.such.key")
    i18n.set_lang("xx")
    check("非法语言码回落到默认", i18n.get_lang() == i18n.DEFAULT_LANG, i18n.get_lang())
    check("语言检测可用", i18n.detect_lang() in dict(i18n.LANGUAGES),
          i18n.detect_lang())
    check("支持的语言数=4", len(i18n.LANGUAGES) == 4, str(i18n.LANGUAGES))

    print("\n结果：%d 通过，%d 失败" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())