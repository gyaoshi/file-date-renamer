# RenameTime — Add a date prefix from the Windows context menu

[简体中文](README.md) | **English** | [日本語](README.ja.md) | [Русский](README.ru.md)

Rename any file or folder to "date + original name" with one right-click:

```
report.pdf (created 2015-10-10)  →  20151010 report.pdf
```

Select one or more files/folders in Explorer, right-click → **Add date prefix**.
Files and folders can be mixed, and a multi-selection is handled as a single batch.

## Download

Grab `RenameTime.exe` from **[Releases](../../releases)** (Windows 10/11, no Python needed).
After downloading, launch it once and click "Register to context menu".

## What's new in v1.1

| Feature | Description |
|---|---|
| 🌐 **Multi-language UI** | Built-in **English / 简体中文 / 日本語 / Русский**. Switch it from the "Interface language" box at the top of the settings window — the whole UI updates immediately. The context menu text itself needs one extra click of "Register to context menu". |
| 🧹 **Clear all history** | A new "Clear all history" button on the Undo tab wipes every recorded batch (with a confirmation dialog that tells you how many batches will be removed). |
| 🔕 **Don't record history** | A new "Keep rename history (needed for undo)" checkbox. Untick it and renaming no longer writes any history (only `launch.log`), which also means you can no longer undo. Takes effect immediately — no need to press Save. |
| 🌐 **Multi-language README** | This document exists in four languages — use the switcher at the top. |

> v1.1 adds a `language` field to the config file. `verb_text` (the menu caption) now
> follows the UI language automatically when left empty.

## ⚠️ Known issues

### HTML files: the context menu misbehaves, currently unusable

Using the context menu on a `.html` file may pop up the browser's "Do you want to open
this file?" security prompt instead of renaming it. **The file is not renamed, HTML files
are currently unusable.**

| Item | Details |
|---|---|
| Symptom | A browser dialog appears instead of the rename happening |
| Scope | `.html` (`.htm` may be affected too); other file types and folders work fine |
| Current status | In the project's automated tests HTML files (including ones carrying the "from the Internet" `Zone.Identifier` mark) rename correctly; the problem still reproduces in real Explorer, so **the root cause is not fully identified and it is treated as an open bug** |
| Workarounds | ① Turn on "Show a result window after running" so you can at least see whether the program was called; ② Turn off "Run immediately" and use the preview/confirm mode; ③ Drag the HTML file onto the `RenameTime.exe` icon |

When reproducing, please attach `%APPDATA%\RenameTime\launch.log` — the program logs the
arguments it received on every invocation.

---

## 1. Installation (30 seconds)

1. Double-click `RenameTime.exe`;
2. Open the **Context menu** tab and click **Register to context menu**;
3. Done. The entry now appears when you right-click a file or folder.

> Registration writes to the per-user registry (`HKCU\Software\Classes`) — **no administrator
> rights needed**. To uninstall, click "Remove from context menu" and delete the program files.

## 2. Options

### Basic

| Option | Description |
|---|---|
| Interface language | 简体中文 / English / 日本語 / Русский — the entire UI is rebuilt instantly |
| Date source | Created / Modified / Accessed date |
| Date format | 8 built-in presets, or type your own strftime codes |
| Include time | No / Hour:minute (1430) / Hour:minute:second (14-30-05), with a configurable date-time separator |
| Separator | Between the date and the original name: space, `_`, `-`, `.` or nothing |
| Position | Date **before** the name (prefix) or **after** it (suffix, before the extension) |
| Run immediately | Rename straight away on right-click; untick to get a preview window first |
| Show result window | Show a per-item result window after running (with one-click undo) |

### Advanced

| Option | Description |
|---|---|
| Existing date prefix | **Skip** (default, prevents `20151010 20151010 report.pdf`) / Replace the old date / Add another one anyway |
| Name conflict | Auto-add `(1)`, `(2)`… when the target exists, or skip |
| Scope | Files and folders / files only / folders only |
| Recursive | When right-clicking a folder, process everything inside it too |
| Hidden files | Whether to process hidden/system files (skipped by default) |
| Sequence | Append `_001`, `_002`… after the date (digits and separator configurable) |
| Excluded extensions | e.g. `.lnk, .tmp` — matching files are left alone |

### Interface language (new in v1.1)

The "Interface language" box at the top of the settings window offers
**简体中文 / English / 日本語 / Русский**:

- the entire UI (tabs, buttons, tooltips, error messages, the preview and result windows,
  and even the sample file names shown in the date-format presets) is rebuilt instantly;
- the choice is written to the config file (`language`) immediately and kept across restarts;
- **the context menu caption needs one extra "Register to context menu" click**, because it
  lives in the registry rather than being read live;
- on first run the language is guessed from the system locale (`LANG` / `locale`),
  falling back to Simplified Chinese.

### Context menu

- Customise the menu caption (**leave it empty to follow the UI language**);
- Optionally also register on the empty space inside a folder (applies to the folder itself);
- Re-register after changing the caption or the options, and after moving the program.

### Undo (enhanced in v1.1)

- Every batch is recorded automatically (the most recent 50 batches are kept);
- Restore a whole batch from the Undo tab or the result window — names are changed back in
  reverse order;
- Items whose original name is already taken are skipped and reported;
- **Clear all history** — wipes every batch, after asking for confirmation and telling you
  how many batches will go;
- **Keep rename history (needed for undo)** — untick it and renaming stops writing history
  immediately (so undo becomes unavailable); the buttons grey out when there is nothing to
  undo, and a hint under the checkbox tells you the current state.

## 3. Common formats

| Desired result | Setting |
|---|---|
| `20151010 report.pdf` | `%Y%m%d` + space |
| `2015-10-10 report.pdf` | `%Y-%m-%d` |
| `2015_10_10 report.pdf` | `%Y_%m_%d` + `_` |
| `20151010_1430 report.pdf` | `%Y%m%d` + hour:minute |
| `2015-10-10 14-30-05 report.pdf` | `%Y-%m-%d` + hour:minute:second |

Useful strftime codes: `%Y` year (4 digits), `%y` year (2 digits), `%m` month, `%d` day,
`%H` hour, `%M` minute, `%S` second, `%j` day of year. Literal text (including Chinese
年月日) can be typed in as-is.

## 4. Command line

```bat
RenameTime.exe                  open the settings window
RenameTime.exe --run FILE...    run with the current settings (used by the context menu)
RenameTime.exe --register       register the context menu
RenameTime.exe --unregister     remove the context menu
RenameTime.exe --status         show the registration status
RenameTime.exe --undo           undo the most recent batch
```

Dropping files/folders onto `RenameTime.exe` opens the preview window.

## 5. FAQ

**Q: The language switched but the context menu still shows the old caption.**
A: The caption lives in the registry and is not refreshed live. Go to the "Context menu" tab
and click "Register to context menu" once more.

**Q: Can I pin the menu caption to one language regardless of the UI language?**
A: Yes — type your own text into "Menu caption". Leaving it empty means "follow the UI language".

**Q: Nothing happens when I right-click / I can't see the menu.**
A: Launch the exe → "Context menu" → "Check registration status". If you moved the program,
register again. Every invocation is logged to `%APPDATA%\RenameTime\launch.log`, which shows
exactly what the system passed in and where it stopped — send that file if you need help.

**Q: If I select many files, will I get many windows?**
A: No. Explorer's mechanism for legacy (static registry) context menu entries is to **start
one process per selected file**, and the command line can only pass `%1`. This program uses a
"queue + leader process" design to merge those processes into **one batch**: the first process
becomes the leader, waits about one second for the others to hand over their paths, runs
everything at once and shows a single result window while the rest exit silently. The side
effect is that a process is started per file, so **selecting dozens of files takes a few
seconds** (the exe has to unpack and start each time). That is normal.

**Q: Why is the menu entry at the very top?**
A: To avoid confusion with the built-in "Open" entry (clicking that by mistake would open the
file in its default program — an HTML file would launch the browser). Our entry is pinned to
the top with `Position=Top`.

**Q: Do dates pile up if I right-click repeatedly?**
A: Not by default. Files whose name already starts with a date are skipped; to overwrite an old
date, choose "Replace existing date" under Advanced.

**Q: I made a mistake.**
A: Click "Undo this batch" in the result window, or pick the batch on the Undo tab.

**Q: The file is in use / being edited.**
A: The rename fails for that item and the result window lists it with the reason; other files
are unaffected.

**Q: Very long paths (over 260 characters).**
A: The program calls the `\\?\` long-path API internally, so those work fine.

## 6. Files

| File | Description |
|---|---|
| `rename_time.py` | Full source (Python + wxPython) |
| `i18n.py` | i18n string tables (129 entries × 4 languages) |
| `RenameTime.exe` | Prebuilt program (see [Releases](../../releases)) |
| `test_i18n.py` | i18n module self-test (key alignment, placeholders, fallback — 19 assertions) |
| `test_engine.py` | Rename engine self-test (26 assertions) |
| `cli_smoke_test.py` | End-to-end exe command-line test (9 assertions) |
| `shellexec_probe.py` | Real context-menu invocation check via ShellExecuteW + multi-process merging (7 assertions) |
| `gui_smoke_test.py` | GUI smoke test (four languages, live language switch, undo page — 39 assertions) |
| `make_icon.py` | Icon generator |
| `app_icon.ico` | Program icon |

Running from source (Python 3.8+ and wxPython required):

```bat
pip install wxPython
python rename_time.py            :: settings window
python rename_time.py --register :: register the context menu (points to pythonw + script)
```

Building the exe yourself (`pip install pyinstaller`):

```bat
python make_icon.py
python -m PyInstaller --onefile --windowed --name RenameTime --icon app_icon.ico rename_time.py
```

> `i18n.py` is picked up automatically by PyInstaller as a dependency.

Running all tests:

```bat
python test_i18n.py
python test_engine.py
python gui_smoke_test.py     :: requires wxPython
python cli_smoke_test.py     :: requires the built exe
python shellexec_probe.py    :: requires the context menu to be registered
```

Settings and undo history live in `%APPDATA%\RenameTime\`
(config.json / history.json / launch.log / rename_time.log).