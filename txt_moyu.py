# -*- coding: utf-8 -*-
"""TXT摸鱼神器

把 TXT 小说排版成桌面阅读窗口（原生窗口，不是网页）：
- 护眼配色（8 套预设 + 自定义背景/文字颜色）
- 定时休息提醒（默认每 30 分钟提示远眺放松）
- 书架：自动保存打开过的书，随时续读
- 小窗口分页阅读，支持置顶，窗口可随意缩放
- 字号、行距、字体可调
- 支持任意语言的 TXT：自动识别 UTF-8 / GBK / Big5 / Shift-JIS / EUC-KR 等编码
- 章节目录跳转、阅读进度自动保存
- Windows / macOS 通用
"""

import bisect
import json
import os
import re
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog, font as tkfont, messagebox

APP_TITLE = "TXT摸鱼神器"
APP_NAME = "TXT摸鱼神器"
STATE_FILE_NAME = "reader_state.json"

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

THEMES = (
    {
        "name": "护眼绿",
        "bg": "#CCE8CF",
        "fg": "#283C28",
        "bar": "#BEDCC2",
        "bar_fg": "#233823",
        "muted": "#5B725B",
        "accent": "#A6C9AC",
        "trough": "#B1CDB6",
        "welcome": "#3C5A3C",
        "heading": "#1E4626",
    },
    {
        "name": "暖纸黄",
        "bg": "#F5EFDD",
        "fg": "#3A3120",
        "bar": "#E8DDC3",
        "bar_fg": "#3A3120",
        "muted": "#7B6B4E",
        "accent": "#D8C7A2",
        "trough": "#DCD0B4",
        "welcome": "#6A5A38",
        "heading": "#6B4B12",
    },
    {
        "name": "夜间",
        "bg": "#1B1D20",
        "fg": "#B8BFC7",
        "bar": "#24282C",
        "bar_fg": "#D2D8DE",
        "muted": "#7E8791",
        "accent": "#343B42",
        "trough": "#2C3238",
        "welcome": "#8C96A0",
        "heading": "#DEE5EC",
    },
    {
        "name": "淡青",
        "bg": "#E1ECEC",
        "fg": "#25343A",
        "bar": "#D2E0E0",
        "bar_fg": "#25343A",
        "muted": "#5D7176",
        "accent": "#BCD2D4",
        "trough": "#C6D8DA",
        "welcome": "#3C555B",
        "heading": "#1F4A52",
    },
    {
        "name": "豆沙绿",
        "bg": "#C7EDCC",
        "fg": "#2E3B2E",
        "bar": "#B6DDBD",
        "bar_fg": "#243324",
        "muted": "#5C745C",
        "accent": "#A3CBA9",
        "trough": "#ADD3B4",
        "welcome": "#406040",
        "heading": "#20401F",
    },
    {
        "name": "雾灰",
        "bg": "#E4E4E1",
        "fg": "#3C3A36",
        "bar": "#D5D5D0",
        "bar_fg": "#3C3A36",
        "muted": "#74706A",
        "accent": "#C4C4BD",
        "trough": "#CBCBC5",
        "welcome": "#5A564F",
        "heading": "#2B2925",
    },
    {
        "name": "柔粉",
        "bg": "#F7EBE4",
        "fg": "#463633",
        "bar": "#ECDACE",
        "bar_fg": "#463633",
        "muted": "#8A736A",
        "accent": "#DEC4B2",
        "trough": "#E3CFC0",
        "welcome": "#7A5C50",
        "heading": "#5C3A2E",
    },
    {
        "name": "星蓝",
        "bg": "#16202E",
        "fg": "#A8C0DC",
        "bar": "#1F2B3C",
        "bar_fg": "#C2D4EA",
        "muted": "#64748C",
        "accent": "#2E4059",
        "trough": "#273446",
        "welcome": "#7E96B4",
        "heading": "#D2E4F8",
    },
)

# “自定义”主题的默认底色，可在设置里用取色器调整
DEFAULT_CUSTOM_BG = "#E8F0E3"
DEFAULT_CUSTOM_FG = "#30422E"

# 阅读字体候选（标注名, 系统里可能出现的字体名），只显示已安装的
FONT_CANDIDATES = (
    ("微软雅黑", ("Microsoft YaHei", "微软雅黑")),
    ("宋体", ("SimSun", "宋体")),
    ("楷体", ("KaiTi", "楷体")),
    ("等线", ("DengXian", "等线")),
    ("仿宋", ("FangSong", "仿宋")),
    ("苹方", ("PingFang SC", "苹方-简")),
    ("宋体-简", ("Songti SC",)),
    ("楷体-简", ("Kaiti SC",)),
    ("黑体-简", ("Heiti SC",)),
    ("Noto Sans CJK", ("Noto Sans SC", "Noto Sans CJK SC")),
    ("思源黑体", ("Source Han Sans SC",)),
    ("文泉驿微米黑", ("WenQuanYi Micro Hei",)),
)

# 界面字体候选（按优先级，取第一个已安装的）
UI_FONT_CANDIDATES = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "微软雅黑",
    "PingFang SC",
    "Hiragino Sans GB",
    "Noto Sans SC",
    "Source Han Sans SC",
    "WenQuanYi Micro Hei",
    "Helvetica Neue",
    "Segoe UI",
)


def pick_font(preferred, families):
    """从候选列表里挑第一个系统已安装的字体。"""
    lowered = {name.lower(): name for name in families}
    for name in preferred:
        hit = lowered.get(name.lower())
        if hit:
            return hit
    return None


def font_options_for(families):
    """按当前系统已安装的字体生成可选项。"""
    available = {name.lower(): name for name in families}
    options = []
    used = set()
    for label, names in FONT_CANDIDATES:
        for name in names:
            hit = available.get(name.lower())
            if hit and hit.lower() not in used:
                used.add(hit.lower())
                options.append((label, hit))
                break
    return options


CHAPTER_PATTERN = re.compile(
    r"^[\s\u3000]*(?:"
    r"第[0-9０-９零〇一二三四五六七八九十百千两]{1,12}[章节回卷篇集部话話]"
    r"|제\s*[0-9]{1,5}\s*[장화절]"
    r"|(?:chapter|part|book)\s+(?:\d{1,4}|[ivxlcdm]{1,8}|[a-z]+)"
    r"|序章|序言|前言|引子|楔子|后记|尾声|终章|番外|外传|正文"
    r"|prologue|epilogue|preface|foreword|afterword|interlude"
    r")[\s\u3000]*[:：、.．·\-]?[^\n]{0,60}$",
    re.IGNORECASE,
)

# 避免标点出现在行首 / 行尾，改善中文排版
NO_LINE_START = "，。、；：！？）》」』】”’…·,.;:!?)]"
NO_LINE_END = "（《「『【“‘([{"

# 宽窗口下单行最长字数，避免一行过长影响阅读
MAX_LINE_CHARS = 40

# 休息提醒间隔范围（分钟）
REST_MIN_MINUTES = 10
REST_MAX_MINUTES = 120


def _mix_color(color_a, color_b, ratio):
    """按比例把 color_b 混入 color_a，用于给自定义主题推导辅助色。"""
    try:
        a = [int(color_a[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(color_b[i:i + 2], 16) for i in (1, 3, 5)]
    except (ValueError, IndexError):
        return color_a
    return "#%02X%02X%02X" % tuple(int(round(x + (y - x) * ratio)) for x, y in zip(a, b))


def _valid_hex(color):
    if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
        return False
    try:
        int(color[1:], 16)
    except ValueError:
        return False
    return True


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def state_dir():
    """状态文件目录：macOS 放进 Application Support，其他平台放程序同目录。"""
    if IS_MAC:
        base = os.path.join(
            os.path.expanduser("~/Library/Application Support"), APP_NAME
        )
        try:
            os.makedirs(base, exist_ok=True)
            return base
        except OSError:
            return os.path.expanduser("~/")
    return app_dir()


STATE_PATH = os.path.join(state_dir(), STATE_FILE_NAME)


def enable_dpi_awareness():
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# 常用汉字：用于判断解码结果像不像正常中文，乱码通常由生僻字组成
COMMON_CJK = set(
    "的一是了我不人在他有这个上们来到时大地为子中你说生国年着就那和要她出也得里"
    "后自以会家可下而过天去能对小多然于心学么之都好看起发当没成只如事把还用第样"
    "道想作种开美总从无情己面最女但现前些所同日手又行意动方期它头经长儿回位分爱"
    "老因很给名法间斯知世什两次使身者被高已亲其进此话常与活正感见明问力理尔点文"
    "几定本公特做外孩相西果走将月十实向声车全信重三机工物气每并别真打太新比才便"
    "夫再书部水像眼等体却加电主界门利海受听表德少克代员许先口由死安写性马光白或"
    "住难望教命花结乐色更拉东神记处让母父应直字场平报友关放至张认接告入笑内英军"
    "候民岁往何度山觉路带万男边风解叫任金快原吃妈变通师立象数四失满战远格士音轻"
    "目条呢病始达深完今提求清王化空业思切怎非找片罗钱吗语元喜曾离飞科言干流欢约"
    "各即指合反题必该论交终林请医晚制球决传画保读运及则房早院量苦火布品近坐产答"
    "星精视五连司巴奇管类未朋且婚台夜青北队久乎越观落尽形影红爸百令周吧识步希亚"
    "术留市半热送兴造谈容极随演收首根讲整式取照办强石古华拿计您装似足双妻尼转诉"
    "米称丽客南领节衣站黑刻统断福城故历惊脸选包紧争另建维绝树系伤示愿持千史谁准"
    "联妇纪基买志静阿诗独复痛消社算义竟确酒需单治卡幸兰念举仅钟怕共毛句息功官待"
    "究跟穿室易游程号居考突皮哪费倒价图具刚脑永歌响商礼细专黄块脚味灵改据般破引"
    "食仍存众注笔甚某沉血备习校默务土微娘须试怀料调广苏显赛查密议底列富梦错座参"
    "八除跑亮假印设线温虽掉京初养香停际致阳纸李纳验助激够严证帝饭忘趣支春集丈木"
    "研班普导顿睡展跳获艺六波察群皇段急庭创区奥器谢弟店否害草排背止组州朝封睛板"
    "角况曲馆育忙质河续哥呼若推境遇雨标姐充围案伦护冷警贝著雪索剧船险烟依斗值帮"
    "汉慢佛肯闻唱沙局伯族低玩资屋击速顾泪洲团圣旁堂兵七露园牛哭旅街劳型烈姑陈莫"
    "鱼异抱宝权鲁简态级票怪寻杀律胜份汽右洋范床舞秘午登楼贵吸责例追较职属渐左录"
    "丝牙党继托赶章智冲叶胡吉卖坚喝肉遗救修松临藏担戏善卫药悲敢靠伊村戴词森耳差"
    "短祖云规窗散迷油旧适乡架恩投弹铁博雷府压超负勒杂醒洗采毫嘴毕九冰既状乱景席"
    "珍童顶派素脱农疑练野按犯拍征坏骨余承置臂彩灯巨琴免环姆暗换技翻束增忍餐洛塞"
    "缺忆判欧层付阵玛批岛项狗休懂武革良恶恋委拥娜妙探呀营退摇弄桌熟诺宣银势奖宫"
    "忽套康供优课鸟喊降夏困刘罪亡鞋健模败伴守挥鲜财孤枪禁恐伙杰迹妹籍讯灭输隔"
)


def readability_score(text):
    """估算解码结果是否是正常文本，用于在多种编码间择优。"""
    sample = text[:4000]
    if not sample:
        return 0.0
    good = 0
    bad = 0
    cjk = 0
    cjk_common = 0
    kana = 0
    hangul = 0
    for ch in sample:
        o = ord(ch)
        if o in (9, 10, 13) or 32 <= o < 127:
            good += 1
        elif 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:      # 中日韩汉字
            good += 1
            cjk += 1
            if ch in COMMON_CJK:
                cjk_common += 1
        elif 0x3040 <= o <= 0x30FF:                              # 假名
            good += 1
            kana += 1
        elif 0xAC00 <= o <= 0xD7AF:                              # 韩文
            good += 1
            hangul += 1
        elif 0x0370 <= o <= 0x04FF:                              # 希腊/西里尔字母
            good += 1
        elif 0x00C0 <= o <= 0x024F:                              # 带音标的拉丁字母
            good += 1
        elif 0xFF00 <= o <= 0xFFEF or 0x2000 <= o <= 0x206F:     # 全角与通用标点
            good += 1
        elif o < 32 or o == 0x7F:                                # 控制字符
            bad += 1

    count = len(sample)
    score = (good - bad * 2) / count * 0.65
    score += 0.35 * (cjk_common / cjk) if cjk else 0.35
    if kana / count > 0.03:
        score += 0.15
    if hangul / count > 0.03:
        score += 0.15
    return score


def decode_txt(raw):
    """尽量正确地解码 TXT 文本，兼容中日韩、俄文等常见编码。"""
    if raw.startswith(b"\xff\xfe\x00\x00") or raw.startswith(b"\x00\x00\xfe\xff"):
        return raw.decode("utf-32")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")

    best = None
    for encoding in ("utf-8", "gb18030", "big5", "shift_jis", "euc-kr", "cp1251"):
        try:
            text = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        score = readability_score(text)
        if encoding == "utf-8":
            score += 0.03
        if best is None or score > best[0]:
            best = (score, text)
    if best is None or best[0] <= 0:
        return raw.decode("utf-8", errors="replace")
    return best[1]


def normalize_text(raw):
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\ufeff", "").replace("\u200b", "").replace("\u00a0", " ")

    result = []
    blank_run = 0
    for line in text.split("\n"):
        line = line.rstrip()
        if not line.strip():
            blank_run += 1
            if blank_run <= 1:
                result.append("")
            continue
        blank_run = 0
        result.append(line)
    while result and result[0] == "":
        result.pop(0)
    while result and result[-1] == "":
        result.pop()
    return "\n".join(result)


def find_chapters(text):
    chapters = []
    offset = 0
    for line in text.split("\n"):
        title = line.strip(" \u3000")
        if title and len(title) <= 80 and CHAPTER_PATTERN.match(line):
            chapters.append((offset, title))
        offset += len(line) + 1
    return chapters


class NovelReader:
    def __init__(self, root, initial_file=None):
        self.root = root
        self.state = self._load_state()
        if self.state.get("layout_version") != 2:
            # 旧版默认窗口偏大，升级后改用更紧凑的默认尺寸
            self.state["geometry"] = None
        self.ui_scale = self._dpi_scale()

        self.theme_index = self._state_int("theme", 0, 0, len(THEMES))
        self.font_size = self._state_int("font_size", 14, 10, 28)
        self.line_spacing = self._state_float("line_spacing", 1.7, 1.2, 2.4)

        # 按当前系统实际安装的字体选择界面字体与阅读字体，兼容 Windows / macOS / Linux
        families = set(tkfont.families(root))
        self.ui_family = pick_font(UI_FONT_CANDIDATES, families) or "TkDefaultFont"
        self.font_options = font_options_for(families)
        default_family = self.font_options[0][1] if self.font_options else "TkDefaultFont"
        saved_family = str(self.state.get("font_family") or "")
        self.font_family = saved_family if saved_family in families else default_family
        self.always_on_top = bool(self.state.get("always_on_top", False))
        self.rest_remind = bool(self.state.get("rest_remind", True))
        self.rest_minutes = self._state_int(
            "rest_minutes", 30, REST_MIN_MINUTES, REST_MAX_MINUTES
        )
        self.custom_bg = str(self.state.get("custom_bg") or DEFAULT_CUSTOM_BG)
        self.custom_fg = str(self.state.get("custom_fg") or DEFAULT_CUSTOM_FG)
        if not _valid_hex(self.custom_bg):
            self.custom_bg = DEFAULT_CUSTOM_BG
        if not _valid_hex(self.custom_fg):
            self.custom_fg = DEFAULT_CUSTOM_FG

        saved_files = self.state.get("files")
        self.files = saved_files if isinstance(saved_files, dict) else {}
        saved_shelf = self.state.get("shelf")
        self.shelf = [p for p in saved_shelf if isinstance(p, str)] if isinstance(saved_shelf, list) else []
        self.last_file = str(self.state.get("last_file") or "")

        self.text = ""
        self.lines = []
        self.line_offsets = []
        self.book_path = None
        self.book_title = ""
        self.page = 0
        self.page_starts = [0]
        self.lpp = 1
        self.chapters = []
        self.heading_lines = set()
        self.side_margin = 24
        self.content_top = 20
        self.line_height = 30
        self.text_width = 300
        self.theme = self._theme_list()[self.theme_index]
        self._width_cache = {}
        self._slider_guard = False
        self._reflow_job = None
        self._save_job = None
        self._titlebar_job = None
        self._welcome_job = None
        self._startup_job = None
        self._rest_job = None
        self._settings_win = None
        self._shelf_win = None
        self._settings_widgets = {}

        self.reader_font = tkfont.Font(root=root, family=self.font_family, size=self.font_size)
        self.heading_font = tkfont.Font(
            root=root, family=self.font_family, size=self.font_size, weight="bold"
        )
        self.ui_font = tkfont.Font(root=root, family=self.ui_family, size=10)
        self.welcome_font = tkfont.Font(root=root, family=self.ui_family, size=19, weight="bold")

        self._build_ui()
        self._setup_bindings()
        self._apply_theme()
        self._restore_window()
        self._update_pin_button()
        self._sync_ui()

        if initial_file and os.path.isfile(initial_file):
            self._startup_job = self.root.after(120, lambda: self._load_file(initial_file))
        elif self.last_file:
            self._startup_job = self.root.after(120, self._maybe_load_last)
        else:
            self._welcome_job = self.root.after(50, self._draw_welcome)

    # ------------------------------------------------------------------ 状态
    def _dpi_scale(self):
        try:
            scaling = float(self.root.tk.call("tk", "scaling"))
            return max(1.0, min(2.2, scaling / (96.0 / 72.0)))
        except Exception:
            return 1.0

    def _px(self, value):
        return int(round(value * self.ui_scale))

    def _load_state(self):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _state_int(self, key, default, low, high):
        try:
            value = int(self.state.get(key, default))
        except (TypeError, ValueError):
            value = default
        return max(low, min(high, value))

    def _state_float(self, key, default, low, high):
        try:
            value = float(self.state.get(key, default))
        except (TypeError, ValueError):
            value = default
        return max(low, min(high, value))

    def _norm_path(self, path):
        return os.path.normcase(os.path.abspath(path))

    def _make_custom_theme(self):
        bg, fg = self.custom_bg, self.custom_fg
        return {
            "name": "自定义",
            "bg": bg,
            "fg": fg,
            "bar": _mix_color(bg, fg, 0.08),
            "bar_fg": fg,
            "muted": _mix_color(bg, fg, 0.45),
            "accent": _mix_color(bg, fg, 0.16),
            "trough": _mix_color(bg, fg, 0.12),
            "welcome": fg,
            "heading": fg,
        }

    def _theme_list(self):
        return list(THEMES) + [self._make_custom_theme()]

    def _cancel_job(self, attribute):
        job = getattr(self, attribute, None)
        if job:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        setattr(self, attribute, None)

    def _schedule_save(self, delay=1500):
        self._cancel_job("_save_job")
        self._save_job = self.root.after(delay, self._on_save_timer)

    def _on_save_timer(self):
        self._save_job = None
        self._save_now()

    def _save_now(self):
        try:
            data = {
                "theme": self.theme_index,
                "font_size": self.font_size,
                "line_spacing": round(self.line_spacing, 2),
                "font_family": self.font_family,
                "always_on_top": self.always_on_top,
                "rest_remind": self.rest_remind,
                "rest_minutes": self.rest_minutes,
                "custom_bg": self.custom_bg,
                "custom_fg": self.custom_fg,
                "shelf": self.shelf,
                "layout_version": 2,
                "files": self.files,
            }
            if self.book_path and self.text:
                self.files[self._norm_path(self.book_path)] = self._progress_ratio()
                data["last_file"] = self.book_path
            elif self.last_file:
                data["last_file"] = self.last_file
            if self.root.winfo_width() > 100:
                data["geometry"] = self.root.geometry()

            tmp = STATE_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, STATE_PATH)
        except Exception:
            pass

    # ------------------------------------------------------------------ 界面
    def _button(self, parent, text, command, padx=4):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bd=0,
            relief="flat",
            highlightthickness=0,
            padx=self._px(padx),
            pady=self._px(4),
            font=self.ui_font,
            takefocus=0,
            cursor="hand2",
        )

    def _build_ui(self):
        self.root.title(APP_TITLE)

        self.toolbar = tk.Frame(self.root, bd=0)
        self.toolbar.pack(side="top", fill="x")

        self.btn_open = self._button(self.toolbar, "打开", self._open_dialog)
        self.btn_shelf = self._button(self.toolbar, "书架", self._show_shelf)
        self.btn_toc = self._button(self.toolbar, "目录", self._show_toc)
        self.btn_font_down = self._button(self.toolbar, "A−", lambda: self._change_font(-1), padx=5)
        self.btn_font_up = self._button(self.toolbar, "A＋", lambda: self._change_font(1), padx=5)
        self.btn_theme = self._button(self.toolbar, self.theme["name"], self._cycle_theme)
        self.btn_settings = self._button(self.toolbar, "设置", self._open_settings)
        self.btn_pin = self._button(self.toolbar, "置顶", self._toggle_topmost)

        self.btn_open.pack(side="left", padx=(self._px(8), 0))
        self.btn_shelf.pack(side="left", padx=(self._px(3), 0))
        self.btn_toc.pack(side="left", padx=(self._px(3), 0))
        self.btn_font_down.pack(side="left", padx=(self._px(4), 0))
        self.btn_font_up.pack(side="left", padx=(self._px(4), 0))
        self.btn_theme.pack(side="left", padx=(self._px(4), 0))
        self.btn_settings.pack(side="left", padx=(self._px(4), 0))
        self.btn_pin.pack(side="right", padx=(self._px(6), self._px(8)))

        # 窗口很窄时，整条工具栏收进一个菜单按钮，保证任何尺寸下都能操作
        self.btn_menu = self._button(self.toolbar, "≡", self._show_toolbar_menu)
        self._toolbar_fixed = (
            (self.btn_open, "left", (self._px(8), 0)),
            (self.btn_shelf, "left", (self._px(3), 0)),
            (self.btn_toc, "left", (self._px(3), 0)),
            (self.btn_font_down, "left", (self._px(4), 0)),
            (self.btn_font_up, "left", (self._px(4), 0)),
            (self.btn_theme, "left", (self._px(4), 0)),
            (self.btn_settings, "left", (self._px(4), 0)),
            (self.btn_pin, "right", (self._px(6), self._px(8))),
        )
        self._toolbar_compact = False
        self._build_toolbar_menu()

        self.canvas = tk.Canvas(self.root, highlightthickness=0, bd=0, takefocus=0)

        self.footer = tk.Frame(self.root, bd=0)
        self.footer.pack(side="bottom", fill="x")

        self.progress = tk.Scale(
            self.footer,
            from_=1,
            to=1,
            orient="horizontal",
            showvalue=0,
            resolution=1,
            sliderlength=self._px(18),
            width=self._px(8),
            bd=0,
            highlightthickness=0,
            takefocus=0,
            command=self._on_slider,
        )
        self.progress.pack(fill="x", padx=self._px(10), pady=(self._px(5), 0))

        self.nav = tk.Frame(self.footer, bd=0)
        self.nav.pack(fill="x", padx=self._px(10), pady=(self._px(1), self._px(5)))

        self.btn_prev = self._button(self.nav, "‹ 上一页", lambda: self._turn(-1), padx=5)
        self.btn_next = self._button(self.nav, "下一页 ›", lambda: self._turn(1), padx=5)
        self.status_label = tk.Label(self.nav, text="未打开文件", font=self.ui_font, anchor="center")

        self.btn_prev.pack(side="left")
        self.btn_next.pack(side="right")
        self.status_label.pack(side="left", fill="x", expand=True, padx=self._px(4))

        # 画布最后打包，窗口变小时优先保证工具栏与底栏完整显示
        self.canvas.pack(side="top", fill="both", expand=True)

        self._all_buttons = (
            self.btn_open,
            self.btn_shelf,
            self.btn_toc,
            self.btn_font_down,
            self.btn_font_up,
            self.btn_theme,
            self.btn_settings,
            self.btn_pin,
            self.btn_menu,
            self.btn_prev,
            self.btn_next,
        )

    def _build_toolbar_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0, font=self.ui_font)
        self.menu.add_command(label="打开…", command=self._open_dialog)
        self.menu.add_command(label="书架", command=self._show_shelf)
        self.menu.add_command(label="目录", command=self._show_toc)
        self.menu.add_separator()
        self.menu.add_command(label="字号增大", command=lambda: self._change_font(1))
        self.menu.add_command(label="字号减小", command=lambda: self._change_font(-1))
        self.menu.add_command(label="切换主题", command=self._cycle_theme)
        self.menu.add_command(label="阅读设置…", command=self._open_settings)
        self.menu.add_separator()
        self._pin_var = tk.BooleanVar(value=self.always_on_top)
        self.menu.add_checkbutton(label="窗口置顶", variable=self._pin_var, command=self._toggle_topmost)

    def _show_toolbar_menu(self):
        self._pin_var.set(self.always_on_top)
        try:
            self.menu.tk_popup(
                self.btn_menu.winfo_rootx(),
                self.btn_menu.winfo_rooty() + self.btn_menu.winfo_height(),
            )
        finally:
            self.menu.grab_release()

    def _adapt_toolbar(self, event=None):
        """窗口变窄时把工具栏收进菜单，保证任意尺寸都能正常操作。"""
        if event is not None and event.widget is not self.root:
            return
        width = self.root.winfo_width()
        if width <= 1:
            return
        compact = width < self._px(400)
        if compact == self._toolbar_compact:
            return
        self._toolbar_compact = compact
        for btn, _side, _padx in self._toolbar_fixed:
            btn.pack_forget()
        if compact:
            self.btn_menu.pack(side="left", padx=(self._px(8), 0))
            self.btn_pin.pack(side="right", padx=(self._px(6), self._px(8)))
            self.btn_prev.configure(text="‹")
            self.btn_next.configure(text="›")
        else:
            self.btn_menu.pack_forget()
            for btn, side, padx in self._toolbar_fixed:
                btn.pack(side=side, padx=padx)
            self.btn_prev.configure(text="‹ 上一页")
            self.btn_next.configure(text="下一页 ›")
        self._sync_ui()

    def _setup_bindings(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Configure>", self._adapt_toolbar)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.root.bind("<MouseWheel>", self._on_wheel)
        self.root.bind("<Button-4>", lambda e: self._key_turn(-1))
        self.root.bind("<Button-5>", lambda e: self._key_turn(1))

        self.root.bind("<space>", lambda e: self._key_turn(1))
        self.root.bind("<Shift-space>", lambda e: self._key_turn(-1))
        self.root.bind("<Right>", lambda e: self._key_turn(1))
        self.root.bind("<Down>", lambda e: self._key_turn(1))
        self.root.bind("<Next>", lambda e: self._key_turn(1))
        self.root.bind("<Left>", lambda e: self._key_turn(-1))
        self.root.bind("<Up>", lambda e: self._key_turn(-1))
        self.root.bind("<Prior>", lambda e: self._key_turn(-1))
        self.root.bind("<Home>", lambda e: self._key_jump(0))
        self.root.bind("<End>", lambda e: self._key_jump(10 ** 9))
        self.root.bind("<Control-o>", lambda e: self._open_dialog())
        self.root.bind("<Control-plus>", lambda e: self._change_font(1))
        self.root.bind("<Control-equal>", lambda e: self._change_font(1))
        self.root.bind("<Control-minus>", lambda e: self._change_font(-1))
        if IS_MAC:
            # macOS 用 Command 键，和系统习惯保持一致
            self.root.bind("<Command-o>", lambda e: self._open_dialog())
            self.root.bind("<Command-plus>", lambda e: self._change_font(1))
            self.root.bind("<Command-equal>", lambda e: self._change_font(1))
            self.root.bind("<Command-minus>", lambda e: self._change_font(-1))

    # ------------------------------------------------------------------ 主题
    def _apply_theme(self):
        theme = self._theme_list()[self.theme_index]
        self.theme = theme

        reopen_settings = self._settings_win is not None
        if reopen_settings:
            self._close_settings()

        self.root.configure(bg=theme["bg"])
        self.toolbar.configure(bg=theme["bar"])
        self.footer.configure(bg=theme["bar"])
        self.nav.configure(bg=theme["bar"])
        self.canvas.configure(bg=theme["bg"])

        for btn in self._all_buttons:
            btn.configure(
                bg=theme["bar"],
                fg=theme["bar_fg"],
                activebackground=theme["accent"],
                activeforeground=theme["fg"],
                disabledforeground=theme["muted"],
            )
        self.status_label.configure(bg=theme["bar"], fg=theme["muted"])
        self.menu.configure(
            bg=theme["bar"],
            fg=theme["bar_fg"],
            activebackground=theme["accent"],
            activeforeground=theme["fg"],
            bd=0,
        )
        self.btn_theme.configure(text=theme["name"])
        self.progress.configure(
            bg=theme["bar"],
            fg=theme["fg"],
            troughcolor=theme["trough"],
            activebackground=theme["accent"],
            highlightbackground=theme["bar"],
            highlightcolor=theme["bar"],
        )

        self._update_pin_button()
        if self.text:
            self._render()
        else:
            self._draw_welcome()
        self._schedule_titlebar()
        if reopen_settings:
            self._open_settings()

    def _schedule_titlebar(self):
        if self._titlebar_job:
            try:
                self.root.after_cancel(self._titlebar_job)
            except Exception:
                pass
        self._titlebar_job = self.root.after(10, self._update_root_titlebar)

    def _update_root_titlebar(self):
        self._titlebar_job = None
        self._set_window_titlebar(self.root)

    def _update_pin_button(self):
        theme = self.theme
        self.btn_pin.configure(
            bg=theme["accent"] if self.always_on_top else theme["bar"],
            fg=theme["fg"] if self.always_on_top else theme["bar_fg"],
        )
        try:
            self._pin_var.set(self.always_on_top)
        except Exception:
            pass

    def _cycle_theme(self):
        self.theme_index = (self.theme_index + 1) % len(self._theme_list())
        self._apply_theme()
        self._schedule_save()

    def _pick_custom_color(self, which):
        initial = self.custom_bg if which == "bg" else self.custom_fg
        parent = self._settings_win if self._settings_win is not None else self.root
        try:
            _rgb, color = colorchooser.askcolor(initialcolor=initial, parent=parent, title="选择颜色")
        except Exception:
            return
        if not color:
            return
        color = color.upper()
        if which == "bg":
            self.custom_bg = color
        else:
            self.custom_fg = color
        self.theme_index = len(THEMES)  # 切到自定义主题
        self._apply_theme()
        self._schedule_save()

    # ------------------------------------------------------------------ 休息提醒
    def _reset_rest_timer(self):
        self._cancel_job("_rest_job")
        self.canvas.delete("rest_toast")
        if self.rest_remind and self.text:
            self._rest_job = self.root.after(self.rest_minutes * 60000, self._show_rest_toast)

    def _show_rest_toast(self):
        self._rest_job = None
        if not self.text:
            return
        self.canvas.delete("rest_toast")
        width = max(self.canvas.winfo_width(), 200)
        message = "已连续阅读 %d 分钟，看看远处或闭目休息一下眼睛" % self.rest_minutes
        text_item = self.canvas.create_text(
            width // 2,
            self._px(42),
            text=message,
            font=self.ui_font,
            fill=self.theme["fg"],
            tags="rest_toast",
        )
        bbox = self.canvas.bbox(text_item)
        if bbox:
            pad = self._px(14)
            bg_item = self.canvas.create_rectangle(
                bbox[0] - pad,
                bbox[1] - pad,
                bbox[2] + pad,
                bbox[3] + pad,
                fill=self.theme["accent"],
                outline=self.theme["muted"],
                tags="rest_toast",
            )
            self.canvas.tag_raise(text_item, bg_item)
        # 提示显示 10 秒后自动消失，并重新开始计时
        self._rest_job = self.root.after(10000, self._hide_rest_toast)

    def _hide_rest_toast(self):
        self._rest_job = None
        self.canvas.delete("rest_toast")
        self._reset_rest_timer()

    def _toggle_topmost(self):
        self.always_on_top = not self.always_on_top
        try:
            self.root.attributes("-topmost", self.always_on_top)
        except Exception:
            pass
        self._update_pin_button()
        self._schedule_save()

    @staticmethod
    def _colorref(hex_color):
        try:
            red = int(hex_color[1:3], 16)
            green = int(hex_color[3:5], 16)
            blue = int(hex_color[5:7], 16)
            return (blue << 16) | (green << 8) | red
        except Exception:
            return 0

    @staticmethod
    def _is_dark(hex_color):
        try:
            red = int(hex_color[1:3], 16)
            green = int(hex_color[3:5], 16)
            blue = int(hex_color[5:7], 16)
        except (ValueError, IndexError):
            return False
        return (0.299 * red + 0.587 * green + 0.114 * blue) < 128

    def _set_window_titlebar(self, win):
        """让标题栏跟随阅读主题（Windows 10/11），夜间模式减少刺眼白条。"""
        if sys.platform != "win32":
            return
        try:
            if not win.winfo_exists():
                return
            import ctypes

            hwnd = win.winfo_id()
            parent = ctypes.windll.user32.GetParent(hwnd)
            if parent:
                hwnd = parent
            theme = self.theme
            dark = 1 if self._is_dark(theme["bg"]) else 0
            value = ctypes.c_int(dark)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
            )
            for attribute, color in ((35, theme["bar"]), (36, theme["bar_fg"])):
                value = ctypes.c_int(self._colorref(color))
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
                )
        except Exception:
            pass

    # ------------------------------------------------------------------ 加载
    def _open_dialog(self):
        initial_dir = os.path.dirname(self.book_path) if self.book_path else os.path.expanduser("~")
        path = filedialog.askopenfilename(
            parent=self.root,
            title="选择 TXT 小说",
            initialdir=initial_dir,
            filetypes=(("文本文件", "*.txt"), ("所有文件", "*.*")),
        )
        if path:
            self._load_file(path)

    def _maybe_load_last(self):
        if self.last_file and os.path.isfile(self.last_file):
            self._load_file(self.last_file, silent=True)
        else:
            self.status_label.configure(text="未打开文件")
            self._draw_welcome()

    # ------------------------------------------------------------------ 书架
    def _remember_book(self, path):
        path = os.path.abspath(path)
        norm = self._norm_path(path)
        self.shelf = [p for p in self.shelf if self._norm_path(p) != norm]
        self.shelf.insert(0, path)
        del self.shelf[60:]

    def _close_shelf(self):
        if self._shelf_win is not None:
            try:
                self._shelf_win.destroy()
            except Exception:
                pass
        self._shelf_win = None

    def _show_shelf(self):
        if self._shelf_win is not None:
            try:
                self._shelf_win.lift()
                self._shelf_win.focus_set()
                return
            except Exception:
                self._shelf_win = None

        theme = self.theme
        win = tk.Toplevel(self.root)
        win.title("书架")
        win.transient(self.root)
        win.configure(bg=theme["bg"])
        win.geometry("%dx%d" % (self._px(380), self._px(450)))
        win.minsize(self._px(320), self._px(300))
        self._shelf_win = win

        frame = tk.Frame(win, bg=theme["bg"], padx=self._px(10), pady=self._px(10))
        frame.pack(fill="both", expand=True)

        tip = tk.Label(
            frame,
            text="打开过的书会自动保存在这里，并记住阅读进度",
            bg=theme["bg"],
            fg=theme["muted"],
            font=self.ui_font,
            anchor="w",
        )
        tip.pack(fill="x", pady=(0, self._px(6)))

        list_frame = tk.Frame(frame, bg=theme["bg"])
        list_frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        listbox = tk.Listbox(
            list_frame,
            bd=0,
            highlightthickness=0,
            font=self.ui_font,
            bg=theme["bg"],
            fg=theme["fg"],
            selectbackground=theme["accent"],
            selectforeground=theme["fg"],
            activestyle="none",
            exportselection=False,
            yscrollcommand=scrollbar.set,
        )
        scrollbar.configure(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        entries = []

        def refresh():
            listbox.delete(0, "end")
            entries.clear()
            for path in self.shelf:
                title = os.path.splitext(os.path.basename(path))[0]
                ratio = self.files.get(self._norm_path(path), 0.0)
                try:
                    percent = max(0, min(100, int(round(float(ratio) * 100))))
                except (TypeError, ValueError):
                    percent = 0
                exists = os.path.isfile(path)
                shown = "%s%s    %d%%" % (title, "" if exists else "（文件缺失）", percent)
                listbox.insert("end", shown)
                entries.append(path)
            if not entries:
                listbox.insert("end", "（书架还是空的，打开一本书就会自动保存到这里）")
                return
            if self.book_path:
                norm = self._norm_path(self.book_path)
                for index, path in enumerate(entries):
                    if self._norm_path(path) == norm:
                        listbox.selection_set(index)
                        listbox.see(index)
                        break

        def selected_path():
            selection = listbox.curselection()
            if not selection:
                return None
            index = selection[0]
            if index >= len(entries):
                return None
            return entries[index]

        def open_selected(_event=None):
            path = selected_path()
            if not path:
                return
            if not os.path.isfile(path):
                messagebox.showwarning("文件不存在", "这本书的文件已被移动或删除：\n%s" % path, parent=win)
                return
            if self._load_file(path):
                self._close_shelf()
                self._schedule_save()

        def add_file():
            initial_dir = os.path.dirname(self.book_path) if self.book_path else os.path.expanduser("~")
            path = filedialog.askopenfilename(
                parent=win,
                title="保存书到书架",
                initialdir=initial_dir,
                filetypes=(("文本文件", "*.txt"), ("所有文件", "*.*")),
            )
            if not path:
                return
            if self._load_file(path):
                refresh()
                self._schedule_save()

        def remove_selected():
            path = selected_path()
            if not path:
                return
            title = os.path.splitext(os.path.basename(path))[0]
            if not messagebox.askyesno("移出书架", "要把《%s》从书架中移出吗？" % title, parent=win):
                return
            norm = self._norm_path(path)
            self.shelf = [p for p in self.shelf if self._norm_path(p) != norm]
            refresh()
            self._schedule_save()

        buttons = tk.Frame(frame, bg=theme["bg"])
        buttons.pack(fill="x", pady=(self._px(8), 0))

        btn_style = dict(
            bd=0,
            relief="flat",
            highlightthickness=0,
            bg=theme["bar"],
            fg=theme["bar_fg"],
            activebackground=theme["accent"],
            activeforeground=theme["fg"],
            font=self.ui_font,
            padx=self._px(10),
            pady=self._px(4),
            cursor="hand2",
        )

        close_btn = tk.Button(buttons, text="关闭", command=self._close_shelf, **btn_style)
        close_btn.pack(side="right")
        remove_btn = tk.Button(buttons, text="移出书架", command=remove_selected, **btn_style)
        remove_btn.pack(side="right", padx=(0, self._px(6)))
        add_btn = tk.Button(buttons, text="添加文件…", command=add_file, **btn_style)
        add_btn.pack(side="right", padx=(0, self._px(6)))
        open_btn = tk.Button(buttons, text="打开所选", command=open_selected, **btn_style)
        open_btn.pack(side="left")

        listbox.bind("<Double-Button-1>", open_selected)
        listbox.bind("<Return>", open_selected)
        listbox.bind("<Delete>", lambda e: remove_selected())
        win.bind("<Escape>", lambda e: self._close_shelf())
        win.protocol("WM_DELETE_WINDOW", self._close_shelf)

        refresh()
        listbox.focus_set()
        win.update_idletasks()
        self._set_window_titlebar(win)

    def _load_file(self, path, silent=False):
        path = os.path.abspath(path)
        self._save_now()
        try:
            with open(path, "rb") as f:
                raw = f.read()
            decoded = decode_txt(raw)
        except Exception as exc:
            if not silent:
                messagebox.showerror("打开失败", "无法读取这个文件：\n%s\n\n%s" % (path, exc), parent=self.root)
            return False

        text = normalize_text(decoded)
        if not text.strip():
            if not silent:
                messagebox.showwarning("文件为空", "这个 TXT 文件中没有可显示的文字。", parent=self.root)
            return False

        self.book_path = path
        self.book_title = os.path.splitext(os.path.basename(path))[0]
        self.text = text
        self.chapters = find_chapters(text)
        self._width_cache.clear()
        self._remember_book(path)
        self.root.title("%s - %s" % (self.book_title, APP_TITLE))
        self.status_label.configure(text="正在排版…")
        self.root.update_idletasks()

        ratio = self.files.get(self._norm_path(path), 0.0)
        try:
            ratio = float(ratio)
        except (TypeError, ValueError):
            ratio = 0.0
        anchor = int(max(0.0, min(1.0, ratio)) * len(text))
        self._reflow(anchor)
        self._reset_rest_timer()
        self._schedule_save()
        return True

    # ------------------------------------------------------------------ 排版
    def _wrap_text(self, max_width):
        font = self.reader_font
        cache = self._width_cache
        lines = []
        offsets = []
        pos = 0

        for para in self.text.split("\n"):
            if not para:
                lines.append("")
                offsets.append(pos)
                pos += 1
                continue

            n = len(para)
            i = 0
            while i < n:
                used = 0
                j = i
                last_space = -1
                while j < n:
                    ch = para[j]
                    cw = cache.get(ch)
                    if cw is None:
                        cw = font.measure(ch)
                        cache[ch] = cw
                    if j > i and used + cw > max_width:
                        break
                    used += cw
                    if ch == " ":
                        last_space = j
                    j += 1

                if j < n and last_space > i and (j - last_space) <= 24:
                    j = last_space + 1
                if j < n and para[j] in NO_LINE_START:
                    j += 1
                while j > i and para[j - 1] in NO_LINE_END:
                    j -= 1
                if j <= i:
                    j = i + 1

                lines.append(para[i:j].rstrip())
                offsets.append(pos + i)
                i = j
            pos += n + 1

        return lines, offsets

    def _total_pages(self):
        return max(1, len(self.page_starts))

    def _build_page_starts(self, line_count):
        """分页：每章标题另起一页，避免紧接上一章结尾。"""
        if line_count <= 0:
            return [0]
        starts = [0]
        index = 0
        while index < line_count:
            limit = min(line_count, index + self.lpp)
            cut = limit
            for candidate in range(index + 1, limit):
                if candidate in self.heading_lines:
                    cut = candidate
                    break
            if cut <= index:
                cut = limit
            if cut >= line_count:
                break
            starts.append(cut)
            index = cut

        # 去掉只含空行的页（会把标题前的空行单独挤成一页），并入上一页
        cleaned = [starts[0]]
        for i in range(1, len(starts)):
            page_start = starts[i]
            page_end = starts[i + 1] if i + 1 < len(starts) else line_count
            if all(not self.lines[j].strip() for j in range(page_start, page_end)):
                continue
            cleaned.append(page_start)
        return cleaned

    def _page_for_line(self, line_index):
        if not self.page_starts:
            return 0
        return max(0, min(len(self.page_starts) - 1, bisect.bisect_right(self.page_starts, line_index) - 1))

    def _current_offset(self):
        if not self.line_offsets:
            return 0
        line_index = self.page_starts[min(self.page, len(self.page_starts) - 1)]
        line_index = min(len(self.line_offsets) - 1, line_index)
        return self.line_offsets[line_index]

    def _heading_line_indices(self):
        if not self.chapters or not self.line_offsets:
            return set()
        result = set()
        for offset, _ in self.chapters:
            index = bisect.bisect_right(self.line_offsets, offset) - 1
            if 0 <= index < len(self.line_offsets):
                result.add(index)
        return result

    def _reflow(self, anchor_offset=None):
        if not self.text:
            self._draw_welcome()
            return

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width < 80 or height < 80:
            return

        linespace = self.reader_font.metrics("linespace")
        char_width = self.reader_font.measure("国")
        self.line_height = max(linespace, int(round(char_width * self.line_spacing)))
        self.side_margin = max(16, min(42, int(width * 0.075)))
        top_margin = max(12, int(height * 0.035))
        usable_height = height - top_margin * 2
        self.lpp = max(1, usable_height // self.line_height)

        text_width = width - self.side_margin * 2
        if text_width < 40:
            text_width = max(40, width - 16)
            self.side_margin = 8
        max_text_width = int(char_width * MAX_LINE_CHARS)
        if text_width > max_text_width:
            text_width = max_text_width
            self.side_margin = max(8, (width - text_width) // 2)
        self.text_width = text_width

        if anchor_offset is None:
            anchor_offset = self._current_offset() if self.lines else 0
        anchor_offset = max(0, min(len(self.text), int(anchor_offset)))

        self.lines, self.line_offsets = self._wrap_text(text_width)
        self.heading_lines = self._heading_line_indices()
        self.page_starts = self._build_page_starts(len(self.lines))

        total = self._total_pages()
        if self.line_offsets:
            index = bisect.bisect_right(self.line_offsets, anchor_offset) - 1
            index = max(0, min(len(self.line_offsets) - 1, index))
        else:
            index = 0
        self.page = max(0, min(total - 1, self._page_for_line(index)))

        block_height = self.lpp * self.line_height
        self.content_top = top_margin + max(0, (usable_height - block_height) // 2)

        self._render()
        self._sync_ui()

    def _schedule_reflow(self, delay=180):
        if self._reflow_job:
            try:
                self.root.after_cancel(self._reflow_job)
            except Exception:
                pass
        self._reflow_job = self.root.after(delay, self._do_reflow)

    def _do_reflow(self):
        self._reflow_job = None
        if self.text:
            self._reflow(self._current_offset())

    def _on_canvas_configure(self, event):
        if not self.text:
            self._draw_welcome()
            return
        self._schedule_reflow(200)

    # ------------------------------------------------------------------ 绘制
    def _render(self):
        self.canvas.delete("all")
        if not self.text:
            self._draw_welcome()
            return

        if not self.page_starts:
            self.page_starts = [0]
        page = min(self.page, len(self.page_starts) - 1)
        start = self.page_starts[page]
        end = self.page_starts[page + 1] if page + 1 < len(self.page_starts) else len(self.lines)
        theme = self.theme
        for i, line in enumerate(self.lines[start:end]):
            if not line:
                continue
            line_index = start + i
            heading = line_index in self.heading_lines
            font = self.reader_font
            fill = theme["fg"]
            if heading:
                fill = theme["heading"]
                if self.heading_font.measure(line) <= self.text_width:
                    font = self.heading_font
            self.canvas.create_text(
                self.side_margin,
                self.content_top + i * self.line_height,
                text=line,
                anchor="nw",
                font=font,
                fill=fill,
            )

    def _draw_welcome(self):
        if self.text:
            return
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width < 120 or height < 80:
            return

        theme = self.theme
        cx = width // 2
        text_width = max(160, width - self._px(40))
        title_h = self.welcome_font.metrics("linespace")
        sub_h = self.ui_font.metrics("linespace")

        if height >= self._px(300):
            hint = (
                "点击左上角「打开」载入 .txt 小说，或从「书架」继续上次的书\n\n"
                "空格 / → 下一页　　← 上一页\n点击左/右侧空白也可翻页\n\n"
                "字号、行距与护眼配色可在「设置」中调整\n"
                "打开的书会自动存入书架，进度自动保存"
            )
            show_title = show_sub = show_line = True
        elif height >= self._px(200):
            hint = (
                "点击「打开」载入 .txt 小说\n"
                "空格 / ← → 翻页，点击两侧空白也可翻页\n"
                "「≡」菜单里有书架、目录、主题与设置"
            )
            show_title = True
            show_sub = show_line = False
        else:
            hint = "点击「≡」打开 .txt"
            show_title = show_sub = show_line = False

        hint_id = self.canvas.create_text(
            cx,
            -2000,
            text=hint,
            font=self.ui_font,
            fill=theme["muted"],
            justify="center",
            anchor="n",
            width=text_width,
        )
        bbox = self.canvas.bbox(hint_id)
        hint_h = (bbox[3] - bbox[1]) if bbox else sub_h * 3

        gap = self._px(12)
        total = hint_h
        if show_title:
            total += title_h + gap
        if show_sub:
            total += sub_h + self._px(6)
        if show_line:
            total += self._px(18)
        y = max(self._px(6), (height - total) // 2)

        if show_title:
            self.canvas.create_text(
                cx, y, text=APP_NAME, font=self.welcome_font, fill=theme["welcome"], anchor="n"
            )
            y += title_h + gap
        if show_sub:
            self.canvas.create_text(
                cx, y, text="桌面沉浸阅读 · 护眼配色", font=self.ui_font, fill=theme["muted"], anchor="n"
            )
            y += sub_h + self._px(6)
        if show_line:
            self.canvas.create_line(cx - 36, y, cx + 36, y, fill=theme["accent"], width=2)
            y += self._px(18)
        self.canvas.coords(hint_id, cx, y)

    # ------------------------------------------------------------------ 翻页
    def _sync_ui(self):
        has_text = bool(self.text)
        total = self._total_pages() if has_text else 1
        self._slider_guard = True
        try:
            self.progress.configure(to=max(1, total), state="normal" if has_text and total > 1 else "disabled")
            self.progress.set(1 if not has_text else self.page + 1)
        finally:
            self._slider_guard = False

        if not has_text:
            self.status_label.configure(text="未打开文件")
        elif self._toolbar_compact:
            self.status_label.configure(text="%d / %d" % (self.page + 1, total))
        else:
            percent = 0 if total <= 1 else int(round(self.page / (total - 1) * 100))
            self.status_label.configure(text="第 %d / %d 页 · %d%%" % (self.page + 1, total, percent))

    def _turn(self, step):
        if not self.text:
            return
        new_page = self.page + step
        total = self._total_pages()
        if new_page < 0 or new_page >= total or new_page == self.page:
            return
        self.page = new_page
        self._render()
        self._sync_ui()
        self._schedule_save()

    def _goto_page(self, page):
        if not self.text:
            return
        total = self._total_pages()
        page = max(0, min(total - 1, int(page)))
        if page == self.page:
            return
        self.page = page
        self._render()
        self._sync_ui()
        self._schedule_save()

    def _key_turn(self, step):
        self._turn(step)
        return "break"

    def _key_jump(self, page):
        self._goto_page(page)
        return "break"

    def _on_slider(self, value):
        if self._slider_guard or not self.text:
            return
        try:
            page = int(float(value)) - 1
        except ValueError:
            return
        if page != self.page:
            self._goto_page(page)

    def _on_canvas_click(self, event):
        self.canvas.focus_set()
        if not self.text:
            return "break"
        width = self.canvas.winfo_width()
        if width <= 0:
            return "break"
        if event.x < width * 0.28:
            self._turn(-1)
        elif event.x > width * 0.72:
            self._turn(1)
        return "break"

    def _on_wheel(self, event):
        if not self.text:
            return "break"
        delta = event.delta
        if IS_MAC:
            # macOS 的滚轮 delta 是细粒度的小数，累积到阈值再翻页，避免一次滚动翻好几页
            self._wheel_accum = getattr(self, "_wheel_accum", 0.0) + delta
            if abs(self._wheel_accum) < 1:
                return "break"
            direction = self._wheel_accum
            self._wheel_accum = 0.0
        else:
            direction = delta
        if direction > 0:
            self._turn(-1)
        elif direction < 0:
            self._turn(1)
        return "break"

    # ------------------------------------------------------------------ 设置
    def _change_font(self, delta):
        new_size = max(10, min(28, self.font_size + delta))
        if new_size == self.font_size:
            return
        self.font_size = new_size
        self.reader_font.configure(size=new_size)
        self.heading_font.configure(size=new_size)
        self._width_cache.clear()
        self._schedule_reflow()
        self._schedule_save()
        if self._settings_win is not None and "font_size" in self._settings_widgets:
            try:
                self._settings_widgets["font_size"].set(new_size)
            except Exception:
                pass

    def _open_settings(self):
        if self._settings_win is not None:
            try:
                self._settings_win.lift()
                self._settings_win.focus_set()
                return
            except Exception:
                self._settings_win = None

        theme = self.theme
        win = tk.Toplevel(self.root)
        win.title("阅读设置")
        win.transient(self.root)
        win.resizable(False, False)
        win.configure(bg=theme["bg"])
        self._settings_win = win
        self._settings_widgets = {}

        body = tk.Frame(win, bg=theme["bg"], padx=self._px(14), pady=self._px(12))
        body.pack(fill="both", expand=True)

        def add_label(row, text):
            label = tk.Label(row, text=text, bg=theme["bg"], fg=theme["fg"], font=self.ui_font, anchor="w")
            label.pack(side="left", padx=(0, self._px(8)))
            return label

        # 字号
        row_font = tk.Frame(body, bg=theme["bg"])
        row_font.pack(fill="x", pady=(0, self._px(6)))
        add_label(row_font, "字号")
        font_scale = tk.Scale(
            row_font,
            from_=10,
            to=28,
            resolution=1,
            orient="horizontal",
            length=self._px(190),
            showvalue=1,
            bd=0,
            highlightthickness=0,
            bg=theme["bar"],
            fg=theme["bar_fg"],
            troughcolor=theme["trough"],
            activebackground=theme["accent"],
            font=self.ui_font,
        )
        font_scale.set(self.font_size)
        font_scale.configure(command=self._on_font_scale)
        font_scale.pack(side="left")
        self._settings_widgets["font_size"] = font_scale

        # 行距
        row_space = tk.Frame(body, bg=theme["bg"])
        row_space.pack(fill="x", pady=(0, self._px(6)))
        add_label(row_space, "行距")
        space_scale = tk.Scale(
            row_space,
            from_=1.2,
            to=2.4,
            resolution=0.1,
            orient="horizontal",
            length=self._px(150),
            showvalue=0,
            bd=0,
            highlightthickness=0,
            bg=theme["bar"],
            fg=theme["bar_fg"],
            troughcolor=theme["trough"],
            activebackground=theme["accent"],
            font=self.ui_font,
        )
        space_scale.set(self.line_spacing)
        space_scale.configure(command=self._on_space_scale)
        space_scale.pack(side="left")
        space_value = tk.Label(
            row_space, text="%.1f" % self.line_spacing, bg=theme["bg"], fg=theme["muted"], font=self.ui_font, width=3
        )
        space_value.pack(side="left", padx=(self._px(4), 0))
        self._settings_widgets["line_spacing"] = space_scale
        self._settings_widgets["line_spacing_value"] = space_value

        # 字体
        row_family = tk.Frame(body, bg=theme["bg"])
        row_family.pack(fill="x", pady=(0, self._px(8)))
        add_label(row_family, "字体")
        labels = [label for label, family in self.font_options] or [self._font_label()]
        current = self._font_label()
        family_var = tk.StringVar(value=current)
        option = tk.OptionMenu(row_family, family_var, *labels, command=self._on_family_change)
        option.configure(
            bg=theme["bar"],
            fg=theme["bar_fg"],
            activebackground=theme["accent"],
            activeforeground=theme["fg"],
            bd=0,
            highlightthickness=0,
            font=self.ui_font,
            width=8,
        )
        option["menu"].configure(
            bg=theme["bg"], fg=theme["fg"], activebackground=theme["accent"], activeforeground=theme["fg"], font=self.ui_font
        )
        option.pack(side="left")
        self._settings_widgets["family_var"] = family_var

        # 置顶
        pin_var = tk.BooleanVar(value=self.always_on_top)
        pin_check = tk.Checkbutton(
            body,
            text="窗口置顶（可边看边做别的事）",
            variable=pin_var,
            command=lambda: self._toggle_topmost(),
            bg=theme["bg"],
            fg=theme["fg"],
            activebackground=theme["bg"],
            activeforeground=theme["fg"],
            selectcolor=theme["bar"],
            bd=0,
            highlightthickness=0,
            font=self.ui_font,
            anchor="w",
        )
        pin_check.pack(fill="x", pady=(0, self._px(10)))
        self._settings_widgets["pin_var"] = pin_var

        # 休息提醒
        rest_var = tk.BooleanVar(value=self.rest_remind)
        rest_check = tk.Checkbutton(
            body,
            text="定时提醒休息眼睛",
            variable=rest_var,
            command=lambda: self._toggle_rest_remind(rest_var.get()),
            bg=theme["bg"],
            fg=theme["fg"],
            activebackground=theme["bg"],
            activeforeground=theme["fg"],
            selectcolor=theme["bar"],
            bd=0,
            highlightthickness=0,
            font=self.ui_font,
            anchor="w",
        )
        rest_check.pack(fill="x", pady=(0, self._px(6)))
        self._settings_widgets["rest_var"] = rest_var

        row_rest = tk.Frame(body, bg=theme["bg"])
        row_rest.pack(fill="x", pady=(0, self._px(10)))
        add_label(row_rest, "间隔")
        rest_scale = tk.Scale(
            row_rest,
            from_=REST_MIN_MINUTES,
            to=REST_MAX_MINUTES,
            resolution=5,
            orient="horizontal",
            length=self._px(140),
            showvalue=0,
            bd=0,
            highlightthickness=0,
            bg=theme["bar"],
            fg=theme["bar_fg"],
            troughcolor=theme["trough"],
            activebackground=theme["accent"],
            font=self.ui_font,
        )
        rest_scale.set(self.rest_minutes)
        rest_scale.configure(command=self._on_rest_scale)
        rest_scale.pack(side="left")
        rest_value = tk.Label(
            row_rest,
            text="%d 分钟" % self.rest_minutes,
            bg=theme["bg"],
            fg=theme["muted"],
            font=self.ui_font,
        )
        rest_value.pack(side="left", padx=(self._px(6), 0))
        self._settings_widgets["rest_minutes"] = rest_scale
        self._settings_widgets["rest_minutes_value"] = rest_value

        # 自定义配色
        row_color = tk.Frame(body, bg=theme["bg"])
        row_color.pack(fill="x", pady=(0, self._px(10)))
        add_label(row_color, "配色")
        for text, which in (("背景色…", "bg"), ("文字色…", "fg")):
            btn = tk.Button(
                row_color,
                text=text,
                command=lambda w=which: self._pick_custom_color(w),
                bd=0,
                relief="flat",
                highlightthickness=0,
                bg=theme["bar"],
                fg=theme["bar_fg"],
                activebackground=theme["accent"],
                activeforeground=theme["fg"],
                font=self.ui_font,
                padx=self._px(10),
                pady=self._px(2),
                cursor="hand2",
            )
            btn.pack(side="left", padx=(0, self._px(6)))
        swatch_bg = tk.Label(row_color, text="  ", bg=self.custom_bg, bd=1, relief="solid", width=2)
        swatch_bg.pack(side="left", padx=(0, self._px(4)))
        swatch_fg = tk.Label(row_color, text="  ", bg=self.custom_fg, bd=1, relief="solid", width=2)
        swatch_fg.pack(side="left")
        self._settings_widgets["swatch_bg"] = swatch_bg
        self._settings_widgets["swatch_fg"] = swatch_fg

        hint = tk.Label(
            body,
            text="所有调整立即生效；自定义配色会记住你的选择",
            bg=theme["bg"],
            fg=theme["muted"],
            font=self.ui_font,
        )
        hint.pack(fill="x", pady=(0, self._px(8)))

        close_btn = tk.Button(
            body,
            text="关闭",
            command=self._close_settings,
            bd=0,
            relief="flat",
            highlightthickness=0,
            bg=theme["bar"],
            fg=theme["bar_fg"],
            activebackground=theme["accent"],
            activeforeground=theme["fg"],
            font=self.ui_font,
            padx=self._px(16),
            pady=self._px(4),
            cursor="hand2",
        )
        close_btn.pack()

        win.protocol("WM_DELETE_WINDOW", self._close_settings)
        win.update_idletasks()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - w) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - h) // 2)
        win.geometry("+%d+%d" % (max(0, x), max(0, y)))
        win.update_idletasks()
        self._set_window_titlebar(win)

    def _close_settings(self):
        if self._settings_win is not None:
            try:
                self._settings_win.destroy()
            except Exception:
                pass
        self._settings_win = None
        self._settings_widgets = {}
        try:
            self.root.focus_set()
        except Exception:
            pass

    def _font_label(self):
        for label, family in self.font_options:
            if family == self.font_family:
                return label
        return self.font_options[0][0] if self.font_options else "默认"

    def _toggle_rest_remind(self, enabled):
        self.rest_remind = bool(enabled)
        self._reset_rest_timer()
        self._schedule_save()

    def _on_rest_scale(self, value):
        try:
            minutes = int(float(value))
        except (TypeError, ValueError):
            return
        self.rest_minutes = max(REST_MIN_MINUTES, min(REST_MAX_MINUTES, minutes))
        label = self._settings_widgets.get("rest_minutes_value")
        if label is not None:
            try:
                label.configure(text="%d 分钟" % self.rest_minutes)
            except Exception:
                pass
        self._reset_rest_timer()
        self._schedule_save()

    def _on_font_scale(self, value):
        try:
            size = int(round(float(value)))
        except ValueError:
            return
        if size == self.font_size:
            return
        self.font_size = size
        self.reader_font.configure(size=size)
        self.heading_font.configure(size=size)
        self._width_cache.clear()
        self._schedule_reflow(140)
        self._schedule_save()

    def _on_space_scale(self, value):
        try:
            spacing = round(float(value), 1)
        except ValueError:
            return
        if "line_spacing_value" in self._settings_widgets:
            try:
                self._settings_widgets["line_spacing_value"].configure(text="%.1f" % spacing)
            except Exception:
                pass
        if abs(spacing - self.line_spacing) < 0.05:
            return
        self.line_spacing = spacing
        self._schedule_reflow(140)
        self._schedule_save()

    def _on_family_change(self, label):
        if not self.font_options:
            return
        family = self.font_options[0][1]
        for option_label, option_family in self.font_options:
            if option_label == label:
                family = option_family
                break
        if family == self.font_family:
            return
        self.font_family = family
        self.reader_font.configure(family=family)
        self.heading_font.configure(family=family)
        self._width_cache.clear()
        self._schedule_reflow(140)
        self._schedule_save()

    # ------------------------------------------------------------------ 目录
    def _show_toc(self):
        if not self.text:
            messagebox.showinfo("目录", "请先打开一个 TXT 小说。", parent=self.root)
            return
        if not self.chapters:
            messagebox.showinfo(
                "目录",
                "这本书里没有检测到「第X章」这类章节标题。\n可以直接拖动底部的进度条跳转。",
                parent=self.root,
            )
            return

        theme = self.theme
        win = tk.Toplevel(self.root)
        win.title("目录 - %s" % self.book_title)
        win.transient(self.root)
        win.configure(bg=theme["bg"])
        win.geometry("%dx%d" % (self._px(360), self._px(460)))
        win.minsize(self._px(300), self._px(320))

        frame = tk.Frame(win, bg=theme["bg"], padx=self._px(10), pady=self._px(10))
        frame.pack(fill="both", expand=True)

        list_frame = tk.Frame(frame, bg=theme["bg"])
        list_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        listbox = tk.Listbox(
            list_frame,
            bd=0,
            highlightthickness=0,
            font=self.ui_font,
            bg=theme["bg"],
            fg=theme["fg"],
            selectbackground=theme["accent"],
            selectforeground=theme["fg"],
            activestyle="none",
            exportselection=False,
            yscrollcommand=scrollbar.set,
        )
        scrollbar.configure(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        for _, title in self.chapters:
            shown = title if len(title) <= 40 else title[:39] + "…"
            listbox.insert("end", shown)

        offsets = [offset for offset, _ in self.chapters]
        current = max(0, bisect.bisect_right(offsets, self._current_offset()) - 1)
        listbox.selection_set(current)
        listbox.see(current)

        buttons = tk.Frame(frame, bg=theme["bg"])
        buttons.pack(fill="x", pady=(self._px(8), 0))

        def jump():
            selected = listbox.curselection()
            if not selected:
                return
            offset = self.chapters[selected[0]][0]
            self._jump_to_offset(offset)
            win.destroy()

        jump_btn = tk.Button(
            buttons,
            text="跳转",
            command=jump,
            bd=0,
            relief="flat",
            highlightthickness=0,
            bg=theme["bar"],
            fg=theme["bar_fg"],
            activebackground=theme["accent"],
            activeforeground=theme["fg"],
            font=self.ui_font,
            padx=self._px(14),
            pady=self._px(4),
            cursor="hand2",
        )
        cancel_btn = tk.Button(
            buttons,
            text="取消",
            command=win.destroy,
            bd=0,
            relief="flat",
            highlightthickness=0,
            bg=theme["bar"],
            fg=theme["bar_fg"],
            activebackground=theme["accent"],
            activeforeground=theme["fg"],
            font=self.ui_font,
            padx=self._px(14),
            pady=self._px(4),
            cursor="hand2",
        )
        jump_btn.pack(side="right")
        cancel_btn.pack(side="right", padx=(0, self._px(8)))

        listbox.bind("<Double-Button-1>", lambda e: jump())
        listbox.bind("<Return>", lambda e: jump())
        listbox.bind("<Escape>", lambda e: win.destroy())
        win.bind("<Escape>", lambda e: win.destroy())
        listbox.focus_set()
        try:
            win.grab_set()
        except Exception:
            pass
        win.update_idletasks()
        self._set_window_titlebar(win)

    def _jump_to_offset(self, offset):
        if not self.line_offsets:
            return
        index = bisect.bisect_right(self.line_offsets, offset) - 1
        index = max(0, min(len(self.line_offsets) - 1, index))
        self._goto_page(self._page_for_line(index))

    # ------------------------------------------------------------------ 窗口
    def _restore_window(self):
        min_w, min_h = self._px(220), self._px(160)
        self.root.minsize(min_w, min_h)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        geometry = self.state.get("geometry")
        restored = False
        if isinstance(geometry, str):
            match = re.match(r"^(\d{3,5})x(\d{3,5})([+-]\d{1,5})([+-]\d{1,5})$", geometry)
            if match:
                width, height, x, y = (int(match.group(i)) for i in range(1, 5))
                width = min(width, screen_w)
                height = min(height, screen_h)
                if width >= min_w and height >= min_h and 0 <= x < screen_w and 0 <= y < screen_h:
                    # 防止窗口整体跑到屏幕外
                    x = min(x, max(0, screen_w - width))
                    y = min(y, max(0, screen_h - height))
                    self.root.geometry("%dx%d+%d+%d" % (width, height, x, y))
                    restored = True
        if not restored:
            default_w = min(self._px(400), int(screen_w * 0.92))
            default_h = min(self._px(540), int(screen_h * 0.9))
            self.root.geometry("%dx%d" % (default_w, default_h))

        if self.always_on_top:
            try:
                self.root.attributes("-topmost", True)
            except Exception:
                pass

    def _progress_ratio(self):
        if not self.text:
            return 0.0
        return max(0.0, min(1.0, self._current_offset() / max(1, len(self.text))))

    def _on_close(self):
        for attribute in ("_save_job", "_reflow_job", "_titlebar_job", "_welcome_job", "_startup_job", "_rest_job"):
            self._cancel_job(attribute)
        self._save_now()
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    initial_file = None
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        initial_file = sys.argv[1]
    NovelReader(root, initial_file)
    if IS_MAC:
        try:
            root.lift()
            root.focus_force()
        except Exception:
            pass
    root.mainloop()


if __name__ == "__main__":
    main()
