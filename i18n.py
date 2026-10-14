#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RenameTime 多语言支持
=====================
四种界面语言：简体中文 / English / 日本語 / Русский

用法：
    import i18n
    i18n.set_lang("en")
    label = i18n.tr("tab.basic")

约定：
* 所有词条以 zh 为基准，键必须四种语言完全一致（由 test_i18n.py 自动校验）；
* 缺少某语言的键时自动回退到 zh，再回退到键名本身，不会崩溃；
* 占位符统一用 strftime 的 {} 位置写法，例如 tr("undo.done", 3, 0)。
"""

import os

# 语言代码 -> 界面显示名（用各自的母语显示，便于用户识别）
LANGUAGES = [
    ("zh", "简体中文"),
    ("en", "English"),
    ("ja", "日本語"),
    ("ru", "Русский"),
]
DEFAULT_LANG = "zh"

_STATE = {"lang": DEFAULT_LANG}


def available_languages():
    return list(LANGUAGES)


def is_supported(code):
    return code in dict(LANGUAGES)


def set_lang(code):
    _STATE["lang"] = code if code in dict(LANGUAGES) else DEFAULT_LANG
    return _STATE["lang"]


def get_lang():
    return _STATE["lang"]


def detect_lang():
    """根据系统语言环境猜测界面语言（找不到时回落到中文）。"""
    candidates = []
    for var in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        v = os.environ.get(var)
        if v:
            candidates.append(v.lower())
    try:
        import locale
        loc = locale.getlocale()[0]
        if loc:
            candidates.append(loc.lower())
        for loc2 in locale.getdefaultlocale():
            if loc2:
                candidates.append(str(loc2).lower())
    except Exception:
        pass
    for code in candidates:
        if "zh" in code or "chinese" in code:
            return "zh"
        if "ja" in code or "japanese" in code:
            return "ja"
        if "ru" in code or "russian" in code:
            return "ru"
        if "en" in code or "english" in code:
            return "en"
    return DEFAULT_LANG


def tr(key, *args, **kwargs):
    """取词条并做格式化；找不到时退回中文，再找不到就返回键名。"""
    lang = _STATE["lang"]
    text = STRINGS.get(lang, {}).get(key)
    if text is None:
        text = STRINGS["zh"].get(key)
    if text is None:
        text = key
    if args or kwargs:
        try:
            return text.format(*args, **kwargs)
        except (IndexError, KeyError, ValueError):
            return text
    return text


ZH = {
    # 通用
    "app.name": "RenameTime",
    "verb.default": "添加日期前缀",
    # 窗口标题
    "title.settings": "RenameTime — 文件日期重命名设置",
    "title.preview": "RenameTime — 重命名预览",
    "title.result": "RenameTime — 执行结果",
    # 标签页
    "tab.basic": "基本设置",
    "tab.advanced": "高级选项",
    "tab.menu": "右键菜单",
    "tab.undo": "撤销",
    "tab.about": "使用说明",
    # 基本设置
    "basic.source": "日期来源",
    "src.created": "创建日期",
    "src.modified": "修改日期",
    "src.accessed": "访问日期",
    "basic.format": "日期格式（选择预设，或直接输入 strftime 代码）",
    "basic.format.hint": "可用代码：%Y 年(4位)  %y 年(2位)  %m 月  %d 日  %H 时  %M 分  %S 秒  %j 年积日\n"
                        "中文可直接输入“年月日”，如：%Y年%m月%d日",
    "basic.time": "是否包含时间",
    "time.none": "不包含",
    "time.hm": "时分(1430)",
    "time.hms": "时分秒(14-30-05)",
    "basic.timesep": "日期与时间的连接符：",
    "basic.combine": "日期与文件名的组合方式",
    "basic.sep": "分隔符：",
    "basic.pos": "位置：",
    "pos.prefix": "文件名前(前缀)",
    "pos.suffix": "文件名后(后缀)",
    "basic.runmode": "右键菜单的运行方式",
    "basic.direct": "直接执行（右键点击后立即重命名，不弹预览窗口）",
    "basic.showresult": "执行后显示结果窗口（可撤销）",
    "basic.sample": "效果示例（创建于 2015-10-10 14:30:05 的文件/文件夹）",
    "basic.language": "界面语言",
    "basic.language.hint": "切换语言后界面与菜单文字立即更新；右键菜单需要重新注册一次才会生效。",
    "sample.file_name": "某某文件.pdf",
    "sample.dir_name": "项目资料",
    "basic.sample.file": "文件：{0}  →  {1}",
    "basic.sample.dir": "文件夹：{0}  →  {1}",
    # 高级选项
    "adv.existing": "原文件名已包含日期前缀时",
    "ex.skip": "跳过（推荐，避免重复添加日期）",
    "ex.replace": "替换已有日期（去掉旧日期再加新日期）",
    "ex.add": "仍然再添加一个",
    "adv.conflict": "新文件名已存在时",
    "cf.suffix": "自动加序号：某某文件 (1).pdf",
    "cf.skip": "跳过该文件",
    "adv.scope": "处理范围",
    "sc.both": "文件和文件夹都处理",
    "sc.files": "仅处理文件",
    "sc.folders": "仅处理文件夹",
    "adv.recursive": "右键文件夹时，连同里面的子文件、子文件夹一起处理",
    "adv.hidden": "包含隐藏/系统文件",
    "adv.seq": "序号",
    "adv.seq.add": "在日期后追加序号",
    "adv.seq.digits": "位数：",
    "adv.seq.sep": "连接符：",
    "adv.exclude": "排除的扩展名（不处理这些文件）",
    "adv.exclude.hint": "例如：.lnk, .tmp, .url（留空表示不排除）",
    # 右键菜单
    "menu.box": "右键菜单",
    "menu.text": "菜单显示文字：",
    "menu.bg": "同时注册到“文件夹空白处”右键（对当前文件夹生效）",
    "menu.register": "注册到右键菜单",
    "menu.unregister": "从右键菜单移除",
    "menu.status": "检查注册状态",
    "menu.info": "说明：\n"
                 "· 注册写入当前用户注册表（HKCU\\Software\\Classes），不需要管理员权限；\n"
                 "· 注册目标为本程序当前位置，移动程序后请重新注册；\n"
                 "· 多选文件/文件夹时程序会聚合成一批统一处理，只弹一次结果窗口；\n"
                 "· 修改菜单文字或界面语言后，需要重新点击【注册到右键菜单】生效；\n"
                 "· 卸载：点击【从右键菜单移除】，然后删除本程序文件即可。",
    "menu.dlg.reg": "注册右键菜单",
    "menu.dlg.unreg": "移除右键菜单",
    "menu.reg.ok": "注册成功。",
    "menu.reg.fail": "注册失败。",
    "menu.status.now": "当前状态 — {0}",
    "st.files": "文件菜单",
    "st.dirs": "文件夹菜单",
    "st.bg": "空白处菜单",
    "st.on": "已注册",
    "st.off": "未注册",
    "reg.files": "已注册：所有文件的右键菜单",
    "reg.dirs": "已注册：文件夹的右键菜单",
    "reg.bg": "已注册：文件夹空白处右键",
    "unreg.files": "已移除：所有文件的右键菜单",
    "unreg.dirs": "已移除：文件夹的右键菜单",
    "unreg.bg": "已移除：文件夹空白处右键",
    "reg.fail": "注册失败：{0}",
    # 撤销页
    "undo.col.time": "时间",
    "undo.col.count": "项目数",
    "undo.col.desc": "说明",
    "undo.btn": "撤销选中批次",
    "undo.refresh": "刷新列表",
    "undo.clear": "一键清空历史",
    "undo.hint": "提示：撤销会按相反顺序把文件名改回去；若原文件名已被占用，该项会被跳过。",
    "undo.record": "记录重命名历史（用于撤销）",
    "undo.offline": "已关闭「记录历史」，这里不会显示任何记录。",
    "undo.select": "请先选择要撤销的批次。",
    "undo.done": "撤销完成：成功 {0} 项，跳过 {1} 项。",
    "undo.clear.title": "清空历史",
    "undo.clear.ask": "确认清空全部重命名历史？\n共 {0} 批记录，清空后无法恢复。",
    "undo.clear.done": "已清空 {0} 批历史记录。",
    "undo.norecord": "没有可撤销的记录。",
    # 设置窗口
    "btn.save": "保存设置",
    "btn.default": "恢复默认设置",
    "btn.close": "关闭",
    "msg.saved": "设置已保存。",
    "msg.tip": "提示",
    # 预览窗口
    "pv.tip": "点击行可勾选/取消；只处理勾选的项。",
    "pv.col.old": "原文件名",
    "pv.col.new": "新文件名",
    "pv.col.reason": "说明",
    "pv.all": "全选",
    "pv.none": "全不选",
    "pv.settings": "打开设置",
    "pv.exec.n": "执行重命名（{0}）",
    "pv.pending": "待执行",
    "pv.nothing": "没有勾选任何可执行的项目。",
    "pv.confirm": "即将重命名 {0} 个项目，是否继续？\n（可在“撤销”页或结果窗口还原）",
    "pv.confirm.title": "确认执行",
    # 结果窗口
    "rs.summary": "成功 {0} 项，跳过 {1} 项，失败 {2} 项。",
    "rs.none": "（没有项目）",
    "rs.undo": "撤销这批重命名",
    "rs.close": "关闭",
    # 无有效路径提示
    "np.title": "RenameTime",
    "np.msg": "没有收到任何有效的文件路径。\n\n"
              "如果你是从资源管理器右键点击的，说明右键菜单注册已失效，\n"
              "请打开本程序 →「右键菜单」页 → 点击【注册到右键菜单】。",
    # 引擎原因（预览与结果窗口展示）
    "reason.not_exist": "路径不存在",
    "reason.type_scope": "按设置跳过该类型",
    "reason.hidden": "隐藏/系统项，按设置跳过",
    "reason.uncheck": "未勾选，跳过",
    "reason.ext_excluded": "扩展名在排除列表中",
    "reason.has_date": "文件名已包含日期前缀",
    "reason.read_fail": "读取日期失败：{0}",
    "reason.same_name": "名称未变化",
    "reason.target_exists": "目标已存在，按设置跳过",
    "reason.too_many_conflict": "冲突项过多，跳过",
    # 使用说明
    "about.version": "版本 {0}",
    "about.text": (
        "RenameTime 使用说明\n"
        "====================\n\n"
        "1. 注册：在“右键菜单”页点击【注册到右键菜单】。\n"
        "   之后在资源管理器中选中文件/文件夹，右键即可看到菜单项。\n\n"
        "2. 使用：选中一个或多个文件/文件夹 → 右键 → 菜单项。\n"
        "   多选时会聚合成一批统一处理；混合选择文件和文件夹也可以。\n\n"
        "3. 拖拽：把文件或文件夹拖到本窗口，可以先预览再执行。\n\n"
        "4. 语言：在“基本设置”页切换界面语言；切换后需重新注册右键菜单。\n\n"
        "5. 默认行为：文件名已包含日期前缀时会跳过，避免反复右键造成\n"
        "   “20151010 20151010 某某.pdf”；需要替换旧日期时选“替换已有日期”。\n\n"
        "6. 撤销：每次批量重命名都会记录，可在“撤销”页整批还原或一键清空；\n"
        "   不想留记录可在该页关闭“记录重命名历史”。\n\n"
        "7. 常见格式示例：\n"
        "   20151010 file.pdf        (%Y%m%d)\n"
        "   2015-10-10 file.pdf      (%Y-%m-%d)\n"
        "   20151010_1430 file.pdf   (%Y%m%d + 时分)\n\n"
        "8. 命令行：\n"
        "   rename_time.exe --run 文件...   右键菜单调用\n"
        "   rename_time.exe --register/--unregister/--status\n"
        "   rename_time.exe --undo          撤销最近一批\n\n"
        "9. 配置文件位置：%APPDATA%\\RenameTime\\config.json\n"),
}

EN = {
    "app.name": "RenameTime",
    "verb.default": "Add date prefix",
    "title.settings": "RenameTime — Date rename settings",
    "title.preview": "RenameTime — Rename preview",
    "title.result": "RenameTime — Result",
    "tab.basic": "Basic",
    "tab.advanced": "Advanced",
    "tab.menu": "Context menu",
    "tab.undo": "Undo",
    "tab.about": "Help",
    "basic.source": "Date source",
    "src.created": "Created date",
    "src.modified": "Modified date",
    "src.accessed": "Accessed date",
    "basic.format": "Date format (pick a preset, or type strftime codes)",
    "basic.format.hint": "Codes: %Y year(4)  %y year(2)  %m month  %d day  "
                         "%H hour  %M minute  %S second  %j day of year",
    "basic.time": "Include time",
    "time.none": "No",
    "time.hm": "Hour:minute (1430)",
    "time.hms": "Hour:minute:second (14-30-05)",
    "basic.timesep": "Date-time separator:",
    "basic.combine": "How the date joins the name",
    "basic.sep": "Separator:",
    "basic.pos": "Position:",
    "pos.prefix": "Before the name (prefix)",
    "pos.suffix": "After the name (suffix)",
    "basic.runmode": "Context menu behaviour",
    "basic.direct": "Run immediately (no preview window)",
    "basic.showresult": "Show a result window after running (can be undone)",
    "basic.sample": "Preview (a file/folder created at 2015-10-10 14:30:05)",
    "basic.language": "Interface language",
    "basic.language.hint": "The UI and menu text update immediately; re-register the "
                           "context menu to apply it.",
    "sample.file_name": "Sample Document.pdf",
    "sample.dir_name": "MyProject",
    "basic.sample.file": "File: {0}  →  {1}",
    "basic.sample.dir": "Folder: {0}  →  {1}",
    "adv.existing": "When the name already starts with a date",
    "ex.skip": "Skip (recommended, avoids duplicate dates)",
    "ex.replace": "Replace the existing date",
    "ex.add": "Add another one anyway",
    "adv.conflict": "When the new name already exists",
    "cf.suffix": "Add a number: Sample Document (1).pdf",
    "cf.skip": "Skip this file",
    "adv.scope": "What to process",
    "sc.both": "Both files and folders",
    "sc.files": "Files only",
    "sc.folders": "Folders only",
    "adv.recursive": "When right-clicking a folder, also process the files and "
                     "sub-folders inside it",
    "adv.hidden": "Include hidden / system files",
    "adv.seq": "Sequence number",
    "adv.seq.add": "Append a sequence number after the date",
    "adv.seq.digits": "Digits:",
    "adv.seq.sep": "Separator:",
    "adv.exclude": "Excluded extensions (these files are skipped)",
    "adv.exclude.hint": "For example: .lnk, .tmp, .url (empty means no exclusions)",
    "menu.box": "Context menu",
    "menu.text": "Menu text:",
    "menu.bg": "Also register on the folder background (applies to the current folder)",
    "menu.register": "Register context menu",
    "menu.unregister": "Remove from context menu",
    "menu.status": "Check registration",
    "menu.info": "Notes:\n"
                 "· Registration writes to the current user's registry "
                 "(HKCU\\Software\\Classes); administrator rights are not needed;\n"
                 "· It points at the current location of this program — re-register "
                 "after moving it;\n"
                 "· Multiple selected files/folders are aggregated into one batch and "
                 "show a single result window;\n"
                 "· Re-register after changing the menu text or the interface language;\n"
                 "· Uninstall: click [Remove from context menu], then delete the program "
                 "files.",
    "menu.dlg.reg": "Register context menu",
    "menu.dlg.unreg": "Remove context menu",
    "menu.reg.ok": "Registered successfully.",
    "menu.reg.fail": "Registration failed.",
    "menu.status.now": "Status — {0}",
    "st.files": "File menu",
    "st.dirs": "Folder menu",
    "st.bg": "Background menu",
    "st.on": "registered",
    "st.off": "not registered",
    "reg.files": "Registered: context menu for files",
    "reg.dirs": "Registered: context menu for folders",
    "reg.bg": "Registered: folder background menu",
    "unreg.files": "Removed: context menu for files",
    "unreg.dirs": "Removed: context menu for folders",
    "unreg.bg": "Removed: folder background menu",
    "reg.fail": "Registration failed: {0}",
    "undo.col.time": "Time",
    "undo.col.count": "Items",
    "undo.col.desc": "Description",
    "undo.btn": "Undo selected batch",
    "undo.refresh": "Refresh",
    "undo.clear": "Clear all history",
    "undo.hint": "Tip: undo restores the original names in reverse order; items whose "
                 "original name is already taken are skipped.",
    "undo.record": "Keep rename history (needed for undo)",
    "undo.offline": "History recording is off, so nothing is listed here.",
    "undo.select": "Please select a batch to undo.",
    "undo.done": "Undo finished: {0} restored, {1} skipped.",
    "undo.clear.title": "Clear history",
    "undo.clear.ask": "Clear the whole rename history?\n{0} batches will be removed; "
                      "this cannot be undone.",
    "undo.clear.done": "Cleared {0} batches.",
    "undo.norecord": "There is nothing to undo.",
    "btn.save": "Save settings",
    "btn.default": "Restore defaults",
    "btn.close": "Close",
    "msg.saved": "Settings saved.",
    "msg.tip": "Notice",
    "pv.tip": "Click a row to check or uncheck it; only checked items are processed.",
    "pv.col.old": "Old name",
    "pv.col.new": "New name",
    "pv.col.reason": "Reason",
    "pv.all": "Select all",
    "pv.none": "Clear",
    "pv.settings": "Open settings",
    "pv.exec.n": "Rename ({0})",
    "pv.pending": "Pending",
    "pv.nothing": "No item is selected.",
    "pv.confirm": "Rename {0} item(s)?\n(You can undo from the Undo tab or the result "
                  "window)",
    "pv.confirm.title": "Confirm",
    "rs.summary": "{0} succeeded, {1} skipped, {2} failed.",
    "rs.none": "(no items)",
    "rs.undo": "Undo this batch",
    "rs.close": "Close",
    "np.title": "RenameTime",
    "np.msg": "No valid file path was received.\n\n"
              "If you clicked this from Explorer's context menu, the menu entry is no "
              "longer registered.\n"
              "Open this program → the «Context menu» tab → click [Register].",
    "reason.not_exist": "Path does not exist",
    "reason.type_scope": "Skipped by the type setting",
    "reason.hidden": "Hidden / system item, skipped",
    "reason.uncheck": "Not selected, skipped",
    "reason.ext_excluded": "Extension is on the exclude list",
    "reason.has_date": "The name already starts with a date",
    "reason.read_fail": "Could not read the date: {0}",
    "reason.same_name": "Name would not change",
    "reason.target_exists": "Target already exists, skipped",
    "reason.too_many_conflict": "Too many conflicts, skipped",
    "about.version": "Version {0}",
    "about.text": (
        "RenameTime Help\n"
        "==============\n\n"
        "1. Registration: open the «Context menu» tab and click [Register context menu].\n"
        "   The entry then appears when you right-click files/folders in Explorer.\n\n"
        "2. Usage: select one or more files/folders → right-click → the menu entry.\n"
        "   A multi-selection is aggregated into one batch; mixing files and folders "
        "works too.\n\n"
        "3. Drag & drop: drop files or folders onto this window to preview before running.\n\n"
        "4. Language: switch it on the «Basic» tab; re-register the context menu "
        "afterwards.\n\n"
        "5. Default behaviour: names that already start with a date are skipped, so you "
        "never get\n   “20151010 20151010 Sample Document.pdf”. Choose “Replace the "
        "existing date”\n   on the Advanced tab if you want the date refreshed.\n\n"
        "6. Undo: every batch is recorded, and you can restore whole batches or clear "
        "the history\n   from the «Undo» tab. Turn off “Keep rename history” there to "
        "record nothing.\n\n"
        "7. Common formats:\n"
        "   20151010 file.pdf        (%Y%m%d)\n"
        "   2015-10-10 file.pdf      (%Y-%m-%d)\n"
        "   20151010_1430 file.pdf   (%Y%m%d + hour:minute)\n\n"
        "8. Command line:\n"
        "   rename_time.exe --run FILE...   invoked by the context menu\n"
        "   rename_time.exe --register/--unregister/--status\n"
        "   rename_time.exe --undo          undo the last batch\n\n"
        "9. Config file: %APPDATA%\\RenameTime\\config.json\n"),
}

JA = {
    "app.name": "RenameTime",
    "verb.default": "日付を名前に付ける",
    "title.settings": "RenameTime — 日付リネーム設定",
    "title.preview": "RenameTime — リネームのプレビュー",
    "title.result": "RenameTime — 実行結果",
    "tab.basic": "基本設定",
    "tab.advanced": "詳細設定",
    "tab.menu": "コンテキストメニュー",
    "tab.undo": "元に戻す",
    "tab.about": "使い方",
    "basic.source": "日付の参照元",
    "src.created": "作成日時",
    "src.modified": "更新日時",
    "src.accessed": "アクセス日時",
    "basic.format": "日付形式（プリセットを選ぶか、strftime コードを直接入力）",
    "basic.format.hint": "コード：%Y 年(4桁)  %y 年(2桁)  %m 月  %d 日  "
                         "%H 時  %M 分  %S 秒  %j 年内通算日",
    "basic.time": "時刻を含めるか",
    "time.none": "含めない",
    "time.hm": "時分(1430)",
    "time.hms": "時分秒(14-30-05)",
    "basic.timesep": "日付と時刻の区切り：",
    "basic.combine": "日付とファイル名の組み合わせ",
    "basic.sep": "区切り文字：",
    "basic.pos": "位置：",
    "pos.prefix": "ファイル名の前（プレフィックス）",
    "pos.suffix": "ファイル名の後（サフィックス）",
    "basic.runmode": "コンテキストメニューの動作",
    "basic.direct": "すぐに実行する（プレビュー画面を表示しない）",
    "basic.showresult": "実行後に結果画面を表示（元に戻せます）",
    "basic.sample": "効果プレビュー（2015-10-10 14:30:05 作成のファイル／フォルダー）",
    "basic.language": "表示言語",
    "basic.language.hint": "言語を切り替えると画面とメニュー文言はすぐに反映されます。"
                           "メニューには再登録が必要です。",
    "sample.file_name": "サンプル文書.pdf",
    "sample.dir_name": "プロジェクト資料",
    "basic.sample.file": "ファイル：{0}  →  {1}",
    "basic.sample.dir": "フォルダー：{0}  →  {1}",
    "adv.existing": "ファイル名の先頭がすでに日付の場合",
    "ex.skip": "スキップ（推奨。日付が重複しません）",
    "ex.replace": "既存の日付を置き換える",
    "ex.add": "このままもう 1 つ追加する",
    "adv.conflict": "新しい名前がすでに存在する場合",
    "cf.suffix": "連番を付ける：サンプル文書 (1).pdf",
    "cf.skip": "そのファイルはスキップ",
    "adv.scope": "処理対象",
    "sc.both": "ファイルとフォルダーの両方",
    "sc.files": "ファイルのみ",
    "sc.folders": "フォルダーのみ",
    "adv.recursive": "フォルダーを右クリックした際、中のファイルとサブフォルダーも処理する",
    "adv.hidden": "隠しファイル・システムファイルも含める",
    "adv.seq": "連番",
    "adv.seq.add": "日付の後に連番を付ける",
    "adv.seq.digits": "桁数：",
    "adv.seq.sep": "区切り文字：",
    "adv.exclude": "除外する拡張子（これらのファイルは処理しません）",
    "adv.exclude.hint": "例：.lnk, .tmp, .url（空欄なら除外なし）",
    "menu.box": "コンテキストメニュー",
    "menu.text": "メニューに表示する文言：",
    "menu.bg": "フォルダーの空白部分에도登録する（現在のフォルダーが対象）",
    "menu.register": "メニューに登録",
    "menu.unregister": "メニューから削除",
    "menu.status": "登録状態を確認",
    "menu.info": "説明：\n"
                 "· 登録は現在のユーザーのレジストリ（HKCU\\Software\\Classes）に書き込む"
                 "ため、管理者権限は不要です；\n"
                 "· 登録先はこのプログラムの現在の位置です。移動した場合は再登録して"
                 "ください；\n"
                 "· 複数選択した場合、プログラムがまとめて 1 回処理し、結果画面も 1 回"
                 "だけ表示します；\n"
                 "· メニュー文言や言語を変更したら、必ず【メニューに登録】を再実行して"
                 "ください；\n"
                 "· アンインストール：【メニューから削除】をクリックしてからプログラム"
                 "ファイルを削除します。",
    "menu.dlg.reg": "メニューへの登録",
    "menu.dlg.unreg": "メニューからの削除",
    "menu.reg.ok": "登録しました。",
    "menu.reg.fail": "登録に失敗しました。",
    "menu.status.now": "現在の状態 — {0}",
    "st.files": "ファイルメニュー",
    "st.dirs": "フォルダーメニュー",
    "st.bg": "空白部分メニュー",
    "st.on": "登録済み",
    "st.off": "未登録",
    "reg.files": "登録しました：ファイルのコンテキストメニュー",
    "reg.dirs": "登録しました：フォルダーのコンテキストメニュー",
    "reg.bg": "登録しました：フォルダーの空白部分メニュー",
    "unreg.files": "削除しました：ファイルのコンテキストメニュー",
    "unreg.dirs": "削除しました：フォルダーのコンテキストメニュー",
    "unreg.bg": "削除しました：フォルダーの空白部分メニュー",
    "reg.fail": "登録に失敗しました：{0}",
    "undo.col.time": "日時",
    "undo.col.count": "件数",
    "undo.col.desc": "内容",
    "undo.btn": "選択した一括を元に戻す",
    "undo.refresh": "一覧を更新",
    "undo.clear": "履歴をすべて消去",
    "undo.hint": "ヒント：元に戻すは逆順に元のファイル名へ戻します。元の名前が既に使われて"
                 "いる項目はスキップされます。",
    "undo.record": "リネーム履歴を記録する（元に戻すため）",
    "undo.offline": "履歴記録がオフのため、ここには何も表示されません。",
    "undo.select": "元に戻す一括を選択してください。",
    "undo.done": "元に戻しました：成功 {0} 件、スキップ {1} 件。",
    "undo.clear.title": "履歴を消去",
    "undo.clear.ask": "リネーム履歴をすべて消去しますか？\n{0} 件の記録が削除されます。"
                      "元に戻せません。",
    "undo.clear.done": "{0} 件の履歴を消去しました。",
    "undo.norecord": "元に戻せる記録がありません。",
    "btn.save": "設定を保存",
    "btn.default": "既定値に戻す",
    "btn.close": "閉じる",
    "msg.saved": "設定を保存しました。",
    "msg.tip": "お知らせ",
    "pv.tip": "行をクリックするとチェック／解除できます。チェックされた項目だけを処理します。",
    "pv.col.old": "元のファイル名",
    "pv.col.new": "新しいファイル名",
    "pv.col.reason": "説明",
    "pv.all": "すべて選択",
    "pv.none": "選択を解除",
    "pv.settings": "設定を開く",
    "pv.exec.n": "リネームを実行（{0}）",
    "pv.pending": "待機中",
    "pv.nothing": "実行対象の項目が選択されていません。",
    "pv.confirm": "{0} 件の項目をリネームします。続行しますか？\n"
                  "（「元に戻す」タブまたは結果画面から取り消せます）",
    "pv.confirm.title": "実行の確認",
    "rs.summary": "成功 {0} 件、スキップ {1} 件、失敗 {2} 件。",
    "rs.none": "（項目なし）",
    "rs.undo": "この一括を元に戻す",
    "rs.close": "閉じる",
    "np.title": "RenameTime",
    "np.msg": "有効なファイルパスを受け取りませんでした。\n\n"
              "エクスプローラーのコンテキストメニューから実行した場合、"
              "登録が失われている可能性があります。\n"
              "このプログラムを開き【コンテキストメニュー】タブで"
              "【メニューに登録】をクリックしてください。",
    "reason.not_exist": "パスが存在しません",
    "reason.type_scope": "設定によりこの種別は対象外です",
    "reason.hidden": "隠しファイル／システムファイルのためスキップ",
    "reason.uncheck": "未選択のためスキップ",
    "reason.ext_excluded": "除外リストにある拡張子です",
    "reason.has_date": "ファイル名の先頭に日付が既にあります",
    "reason.read_fail": "日付を読み取れませんでした：{0}",
    "reason.same_name": "名前は変更されません",
    "reason.target_exists": "対象が既に存在するためスキップ",
    "reason.too_many_conflict": "競合が多すぎるためスキップ",
    "about.version": "バージョン {0}",
    "about.text": (
        "RenameTime の使い方\n"
        "====================\n\n"
        "1. 登録：【コンテキストメニュー】タブで【メニューに登録】をクリックします。\n"
        "   以後、エクスプローラーでファイル／フォルダーを右クリックするとメニュー項目が"
        "表示されます。\n\n"
        "2. 使用：ファイル／フォルダーを選択 → 右クリック → メニュー項目。\n"
        "   複数選択はまとめて 1 回処理されます。ファイルとフォルダーの混在も可比です。\n\n"
        "3. ドラッグ＆ドロップ：このウィンドウにファイルをドロップすると、"
        "プレビューしてから実行できます。\n\n"
        "4. 言語：【基本設定】タブで切り替えます。切替後はメニューの再登録が必要です。\n\n"
        "5. 既定の動作：ファイル名の先頭に日付が既にある場合はスキップするため、"
        "「20151010 20151010 サンプル文書.pdf」\n   のように重複しません。"
        "日付を最新にしたい場合は【詳細設定】で「既存の日付を置き換える」"
        "を選んでください。\n\n"
        "6. 元に戻す：実行履歴は毎回記録されます。【元に戻す】タブで一括で戻すか、"
        "履歴をすべて消去できます。\n"
        "   記録を残したくない場合は同タブの【リネーム履歴を記録する】をオフにします。\n\n"
        "7. よく使う形式：\n"
        "   20151010 file.pdf        (%Y%m%d)\n"
        "   2015-10-10 file.pdf      (%Y-%m-%d)\n"
        "   20151010_1430 file.pdf   (%Y%m%d + 時分)\n\n"
        "8. コマンドライン：\n"
        "   rename_time.exe --run FILE...   メニューから呼び出し\n"
        "   rename_time.exe --register/--unregister/--status\n"
        "   rename_time.exe --undo          直前の一括を元に戻す\n\n"
        "9. 設定ファイル：%APPDATA%\\RenameTime\\config.json\n"),
}

RU = {
    "app.name": "RenameTime",
    "verb.default": "Добавить префикс даты",
    "title.settings": "RenameTime — Настройки переименования по дате",
    "title.preview": "RenameTime — Предпросмотр переименования",
    "title.result": "RenameTime — Результат",
    "tab.basic": "Основные",
    "tab.advanced": "Дополнительно",
    "tab.menu": "Контекстное меню",
    "tab.undo": "Отмена",
    "tab.about": "Справка",
    "basic.source": "Источник даты",
    "src.created": "Дата создания",
    "src.modified": "Дата изменения",
    "src.accessed": "Дата обращения",
    "basic.format": "Формат даты (выберите вариант или введите код strftime)",
    "basic.format.hint": "Коды: %Y год(4)  %y год(2)  %m месяц  %d день  "
                         "%H час  %M минута  %S секунда  %j день в году",
    "basic.time": "Включить время",
    "time.none": "Нет",
    "time.hm": "Часы:минуты (1430)",
    "time.hms": "Часы:минуты:секунды (14-30-05)",
    "basic.timesep": "Разделитель даты и времени:",
    "basic.combine": "Как дата соединяется с именем",
    "basic.sep": "Разделитель:",
    "basic.pos": "Позиция:",
    "pos.prefix": "Перед именем (префикс)",
    "pos.suffix": "После имени (суффикс)",
    "basic.runmode": "Поведение контекстного меню",
    "basic.direct": "Выполнять сразу (без окна предпросмотра)",
    "basic.showresult": "Показывать окно результата (можно отменить)",
    "basic.sample": "Пример (файл/папка созданы 2015-10-10 14:30:05)",
    "basic.language": "Язык интерфейса",
    "basic.language.hint": "Интерфейс и текст меню обновляются сразу; для меню нужна "
                           "повторная регистрация.",
    "sample.file_name": "Образец документа.pdf",
    "sample.dir_name": "Мой проект",
    "basic.sample.file": "Файл: {0}  →  {1}",
    "basic.sample.dir": "Папка: {0}  →  {1}",
    "adv.existing": "Если имя уже начинается с даты",
    "ex.skip": "Пропустить (рекомендуется — без повторов)",
    "ex.replace": "Заменить существующую дату",
    "ex.add": "Всё равно добавить ещё одну",
    "adv.conflict": "Если новое имя уже существует",
    "cf.suffix": "Добавить номер: Образец документа (1).pdf",
    "cf.skip": "Пропустить этот файл",
    "adv.scope": "Что обрабатывать",
    "sc.both": "Файлы и папки",
    "sc.files": "Только файлы",
    "sc.folders": "Только папки",
    "adv.recursive": "При щелчке правой кнопкой по папке обрабатывать также вложенные "
                     "файлы и подпапки",
    "adv.hidden": "Включать скрытые и системные файлы",
    "adv.seq": "Порядковый номер",
    "adv.seq.add": "Добавлять номер после даты",
    "adv.seq.digits": "Цифр:",
    "adv.seq.sep": "Разделитель:",
    "adv.exclude": "Исключённые расширения (эти файлы пропускаются)",
    "adv.exclude.hint": "Например: .lnk, .tmp, .url (пусто — ничего не исключать)",
    "menu.box": "Контекстное меню",
    "menu.text": "Текст пункта меню:",
    "menu.bg": "Также регистрировать в меню фона папки (для текущей папки)",
    "menu.register": "Зарегистрировать в меню",
    "menu.unregister": "Убрать из меню",
    "menu.status": "Проверить регистрацию",
    "menu.info": "Примечания:\n"
                 "· Регистрация пишет в реестр текущего пользователя "
                 "(HKCU\\Software\\Classes); права администратора не нужны;\n"
                 "· Регистрация указывает на текущее расположение программы — после "
                 "перемещения регистрируйте заново;\n"
                 "· Несколько выбранных файлов/папок объединяются в одну партию, "
                 "окно результата показывается одно;\n"
                 "· После смены текста меню или языка нужно снова нажать "
                 "«Зарегистрировать в меню»;\n"
                 "· Удаление: нажмите «Убрать из меню», затем удалите файлы программы.",
    "menu.dlg.reg": "Регистрация в меню",
    "menu.dlg.unreg": "Удаление из меню",
    "menu.reg.ok": "Регистрация выполнена.",
    "menu.reg.fail": "Ошибка регистрации.",
    "menu.status.now": "Состояние — {0}",
    "st.files": "Меню файлов",
    "st.dirs": "Меню папок",
    "st.bg": "Меню фона",
    "st.on": "зарегистрировано",
    "st.off": "не зарегистрировано",
    "reg.files": "Зарегистрировано: меню для файлов",
    "reg.dirs": "Зарегистрировано: меню для папок",
    "reg.bg": "Зарегистрировано: меню фона папки",
    "unreg.files": "Удалено: меню для файлов",
    "unreg.dirs": "Удалено: меню для папок",
    "unreg.bg": "Удалено: меню фона папки",
    "reg.fail": "Не удалось зарегистрировать: {0}",
    "undo.col.time": "Время",
    "undo.col.count": "Элементов",
    "undo.col.desc": "Описание",
    "undo.btn": "Отменить выбранную партию",
    "undo.refresh": "Обновить",
    "undo.clear": "Очистить всю историю",
    "undo.hint": "Подсказка: отмена возвращает исходные имена в обратном порядке; "
                 "элементы, чьё исходное имя занято, пропускаются.",
    "undo.record": "Сохранять историю переименований (для отмены)",
    "undo.offline": "Запись истории отключена, поэтому здесь ничего нет.",
    "undo.select": "Сначала выберите партию для отмены.",
    "undo.done": "Отмена завершена: восстановлено {0}, пропущено {1}.",
    "undo.clear.title": "Очистить историю",
    "undo.clear.ask": "Очистить всю историю переименований?\nБудет удалено партий: "
                      "{0}. Отменить это нельзя.",
    "undo.clear.done": "Удалено партий: {0}.",
    "undo.norecord": "Отменять нечего.",
    "btn.save": "Сохранить настройки",
    "btn.default": "Сбросить настройки",
    "btn.close": "Закрыть",
    "msg.saved": "Настройки сохранены.",
    "msg.tip": "Уведомление",
    "pv.tip": "Щёлкните по строке, чтобы отметить или снять отметку; обрабатываются "
              "только отмеченные элементы.",
    "pv.col.old": "Старое имя",
    "pv.col.new": "Новое имя",
    "pv.col.reason": "Причина",
    "pv.all": "Выбрать все",
    "pv.none": "Снять все",
    "pv.settings": "Настройки",
    "pv.exec.n": "Переименовать ({0})",
    "pv.pending": "Ожидание",
    "pv.nothing": "Не выбрано ни одного элемента.",
    "pv.confirm": "Переименовать элементов: {0}. Продолжить?\n(Отменить можно на вкладке "
                  "«Отмена» или в окне результата)",
    "pv.confirm.title": "Подтверждение",
    "rs.summary": "Успешно: {0}, пропущено: {1}, ошибок: {2}.",
    "rs.none": "(нет элементов)",
    "rs.undo": "Отменить эту партию",
    "rs.close": "Закрыть",
    "np.title": "RenameTime",
    "np.msg": "Не получено ни одного корректного пути к файлу.\n\n"
              "Если вы запустили программу из контекстного меню проводника, пункт меню "
              "больше не зарегистрирован.\n"
              "Откройте программу → вкладка «Контекстное меню» → нажмите "
              "«Зарегистрировать в меню».",
    "reason.not_exist": "Путь не существует",
    "reason.type_scope": "Пропущено по настройке типа",
    "reason.hidden": "Скрытый или системный элемент — пропущено",
    "reason.uncheck": "Не выбрано — пропущено",
    "reason.ext_excluded": "Расширение в списке исключений",
    "reason.has_date": "Имя уже начинается с даты",
    "reason.read_fail": "Не удалось прочитать дату: {0}",
    "reason.same_name": "Имя не изменится",
    "reason.target_exists": "Целевое имя уже существует — пропущено",
    "reason.too_many_conflict": "Слишком много конфликтов — пропущено",
    "about.version": "Версия {0}",
    "about.text": (
        "RenameTime — справка\n"
        "====================\n\n"
        "1. Регистрация: откройте вкладку «Контекстное меню» и нажмите "
        "«Зарегистрировать в меню».\n"
        "   После этого пункт появляется при щелчке правой кнопкой по файлам и папкам.\n\n"
        "2. Использование: выберите файлы/папки → правая кнопка → пункт меню.\n"
        "   Несколько выбранных элементов обрабатываются одной партией; можно смешивать "
        "файлы и папки.\n\n"
        "3. Перетаскивание: перетащите файлы или папки в это окно, чтобы сначала "
        "посмотреть предпросмотр.\n\n"
        "4. Язык: переключается на вкладке «Основные»; после этого меню нужно "
        "зарегистрировать заново.\n\n"
        "5. Поведение по умолчанию: имена, уже начинающиеся с даты, пропускаются, поэтому "
        "не будет\n   «20151010 20151010 Образец документа.pdf». Чтобы обновить дату, "
        "выберите\n   «Заменить существующую дату» на вкладке «Дополнительно».\n\n"
        "6. Отмена: каждая партия записывается; на вкладке «Отмена» можно вернуть всё "
        "парией\n   или очистить историю целиком. Чтобы ничего не записывать, "
        "отключите\n   «Сохранять историю переименований».\n\n"
        "7. Частые форматы:\n"
        "   20151010 file.pdf        (%Y%m%d)\n"
        "   2015-10-10 file.pdf      (%Y-%m-%d)\n"
        "   20151010_1430 file.pdf   (%Y%m%d + часы:минуты)\n\n"
        "8. Командная строка:\n"
        "   rename_time.exe --run ФАЙЛ...   вызов из контекстного меню\n"
        "   rename_time.exe --register/--unregister/--status\n"
        "   rename_time.exe --undo          отменить последнюю партию\n\n"
        "9. Файл настроек: %APPDATA%\\RenameTime\\config.json\n"),
}

STRINGS = {"zh": ZH, "en": EN, "ja": JA, "ru": RU}