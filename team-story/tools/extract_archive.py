"""Build the G_Robot team archive from local WeChat MHTML files.

Run from the repository root:
    python SquadotWebsite/team-story/tools/extract_archive.py

The script reads:
    所有参考资料/社团资料/公众号网页资料

And writes:
    SquadotWebsite/team-story/archive-data.js
    SquadotWebsite/team-story/assets/articles/*
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import shutil
from dataclasses import dataclass
from email import policy
from email.header import decode_header, make_header
from email.parser import BytesParser
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - developer setup guard
    raise SystemExit("Pillow is required: pip install pillow") from exc


CATEGORY_LABELS = {
    "competition": "赛事成果",
    "community": "组织传承",
    "outreach": "科普活动",
    "technical": "技术训练",
    "activity": "社团活动",
}

FOUNDER_TEAM_IMAGE_SOURCE = "./assets/articles/a20170603-20-01.webp"
FOUNDER_TEAM_IMAGE_TARGET = "./assets/articles/a20141113-09-founder.webp"

NOISE_CONTAINS = [
    "在小说阅读器",
    "去阅读",
    "沉浸阅读",
    "点击上方",
    "点击蓝字",
    "关注我们",
    "微信扫一扫",
    "二维码",
    "GRobot机器人",
    "预览时标签不可点",
    "赞赏作者",
    "赞赏后展示",
    "最低赞赏",
        "当前内容可能存在",
        "微信公众平台广告规范",
        "公众微信平台",
        "搜索「」网络结果",
    "调整当前正文文字大小",
    "暂无留言",
    "已无更多数据",
    "发消息",
    "写留言",
    "使用小程序",
    "公众号",
    "划线",
    "轻点两下",
    "对关注你的人展示",
    "确认提交投诉",
    "你可以补充投诉原因",
    "选择留言身份",
]

NOISE_EXACT = {
    "关闭",
    "更多",
    "返回",
    "确定",
    "取消",
    "允许",
    "知道了",
    "我知道了",
    "继续访问",
    "名称已清空",
    "喜欢作者",
    "其它金额",
    "作品",
    "暂无作品",
    "赞",
    "分享",
    "推荐",
    "留言",
    "收藏",
    "听过",
    "视频",
    "小程序",
    "分析",
    "¥",
    ".",
    ",",
    "，",
    "。",
    "：",
    "×",
}

FORMAL_TITLE_REPLACEMENTS = {
    "G_Robot成立一月纪念": "G_Robot 成立初期",
    "G_Robot部门介绍": "G_Robot 部门体系介绍",
    "G_Robot之G的含义知多少？": "G_Robot 名称文化与团队理念",
    "【G_Robot活动】水下机器人讲解活动圆满结束": "水下机器人原理讲解活动",
    "【G_Robot机器人科普公益活动】北师大朝阳附小站回顾": "机器人科普公益活动：北师大朝阳附小站",
    "G_Robot摇摇棒DIY制作活动回顾": "摇摇棒 DIY 制作活动",
    "G_robot社团活动回顾": "电子设计软件学习活动",
    "［比赛回顾］2014年哈尔滨机器人水下作业比赛实录": "2014 年哈尔滨水下作业比赛",
    "【单片机】充满浓浓暖意的干货课堂": "单片机基础课程",
    "快看！水下有只大龙虾！！！": "龙虾系列水下机器人训练与比赛回顾",
    "单片机——传感器精简系统构建": "单片机与传感器系统构建课程",
    "【回顾与展望】G-robot社团换届大会举行啦": "2017 年社团换届大会",
    "2017系列水下比赛—G_Robot社团再创佳绩！": "2017 年系列水下机器人赛事",
    "萌新驾到，G_Robot社团带你梦想启航！": "G_Robot 招新介绍",
    "如果科技有味道，你尝过哪种？": "社团项目与资源介绍",
    "今天，我们想对你们说": "面向新成员的团队寄语",
    "职业访谈||G_Robot带你与深度学习工程师面对面": "深度学习工程师职业访谈",
    "科技干货‖如何制作属于你的水下机器人": "水下机器人制作方法介绍",
    "华北五省之水下机器人重磅来袭！": "华北五省水下机器人展示预告",
    "活动回顾||首届科技节之水下机器人讲解": "首届科技节水下机器人讲解",
    "活动回顾‖华北五省之水下讲解圆满落幕": "华北五省水下机器人展示讲解",
    "【回顾与展望】G_Robot 社团第四届换届大会": "2018 年社团第四届换届大会",
    "震惊！2018中国机器人大赛水下机器人冠军竟然是ta!": "2018 年中国机器人大赛成果",
    "关于2018中国机器人大赛，你不知道的趣闻！": "2018 年中国机器人大赛备赛与赛场记录",
    "史上最长篇幅——直击2018中国机器人大赛比赛现场！！！": "2018 年中国机器人大赛现场纪实",
    "Amazing!没想到你是这样的破冰活动！": "2018 级新成员破冰活动",
    "活动回顾||G_Robot第五届招新工作圆满落幕！": "第五届招新活动",
    "【回顾与展望】G＿Robot社团第五届换届大会": "2019 年社团第五届换届大会",
    "2019中国机器人大赛水下机器人双冠得主在此！": "2019 年中国机器人大赛双冠成果",
    "2019中国机器人大赛回顾": "2019 年中国机器人大赛备赛与比赛回顾",
    "回顾与展望 | G_Robot社团换届大会圆满召开": "2020 年社团换届大会",
    "回顾与展望| G_Robot社团换届大会圆满召开": "2021 年社团第七届换届大会",
    "回顾与展望| G_Robot社团第八届换届大会圆满召开": "2022 年社团第八届换届大会",
    "赛事速递 | 恭喜我校G_Robot社团在2020中国机器人大赛中再创佳绩！": "2020 年中国机器人大赛成果",
    "G_robot再创佳绩 | 国际先进机器人及仿真技术大赛": "2023 年国际先进机器人及仿真技术大赛成果",
    "世界大学生水下机器人大赛活动速递": "2023 年世界大学生水下机器人大赛",
    "自动化水下机器人之旅": "自动化水下机器人技术分享",
    "G_Robot社团2025换届大会": "2025 年社团换届大会",
    "G_Robot 水下机器人暑期课程顺利开展": "2025 年水下机器人暑期课程",
    "G_Robot在中国国际海洋水下机器人大赛中载誉而归！": "2025 年中国国际海洋水下机器人大赛成果",
    "G_Robot社团参加2025中国机器人大赛（专项赛）纪实！": "2025 年中国机器人大赛专项赛参赛纪实",
    "G_Robot水下具身智能探索与 Vibe Coding 技术社团活动圆满开展": "水下具身智能与 Vibe Coding 技术活动",
    "G_Robot社团2026换届大会圆满落幕": "2026 年社团换届大会",
}

MEMORIAL_IMAGE_IDS = {
    "a20260401-11",
    "a20250802-08",
    "a20250718-05",
    "a20230816-23",
    "a20200927-29",
    "a20191108-02",
    "a20190401-22",
    "a20181113-04",
    "a20181113-32",
    "a20180926-25",
    "a20180926-28",
    "a20171123-34",
    "a20171119-33",
    "a20171108-26",
}

NO_IMAGE_TITLES = {
    # This article is a written set of advice for new members. The saved page
    # contains unrelated personal/lifestyle photos, so the public site should
    # present the text without forcing a misleading activity image.
    "今天，我们想对你们说",
    "面向新成员的团队寄语",
}

EXCLUDED_IMAGE_HASHES = {
    # Repeated app-shell screenshots, QR codes, logos, certificates, trophy close-ups,
    # decorative graphics and long poster collages should not become representative photos.
    "08a586fecd81c9326dbffa2cf950998e2d80ef03",
    "df8415b449a1dd5aacd04beca42f585437296c17",
    "72c8048fd3a3cb497d16b1e076c6901347496e29",
    "21a295e32e9cf52217775111ebebf51b0acf0762",
    "dd9cdcbf9081228322a8504beb0d43b34bf27967",
    "e0ea4e6cd8139acb2e73ef4a3e56e6dc9bc6e237",
    "096d51e41b927c4e448f649d5d5e91e979548a9d",
    "dcc4ed1165478c525ad527011da1b72be21c3077",
    "d181cafeaa6be675db0ca488879520cae14c4474",
    "4a81319a60916af3f66baf49e233ef62fc87de68",
    "ecad39e418533d4fd8eb4ce62ead485065a40c5f",
    "ee32090b18611a154d69ab1f209f46dd7f12f943",
    "aca0092c9b4c5159f566764f8e4aaa5eba2271a8",
    "c3920ea5bcc59b876ec303e974e5d1dc8698a97b",
    "cabd75b95171fdc2632de6dafd01dfa090988f03",
    "b4a8152539d9aa700009b10b3975c29238257651",
    "69bbdbf097886011a630ba27fb43da2d218a7689",
    "2c1c035a6932df2f1144dc53829d4d6dff6fec27",
    "848ab2bfdbe9d1e37626fdf83bf328450aec4144",
    "f0a0e6cc15f54bd6e1d4864e93d2320a1cd60ff6",
    "35bf107cd323f10d600cc8f323fa08832206c921",
    "4e62fcb0e0a6c9321809a50c095629fa7e081fdd",
    "bd7fb38818ec002bfed506ca2a238c575852108f",
    "0bbc5996f6a466a6d3c4986c1d338e12e02af742",
    "2b30f7aecde14607271d0a142f19f72785956b16",
    "7571cfadf9331088949fb230f07b5b1728621f21",
    "731e2b9c7afeac5c9345a693ed1ec536fe483382",
    "3d7486840f9edc4a8028abddc6973363ab587650",
    "af965d8e11431b1831574889c9b0392320d96d2b",
    "9fdab9a08e4d99a749cd830f823e60af762d4a97",
    "24695634fa95b874ea11d42fe41743c288147bf3",
    "8dff2e765bcb28ca2b8dd124f3d521fae3694cb1",
    "7dd70b734018824e3f69f60e49a7d671c0812060",
    "085e5a9f1910dc878fae780b8dbfedd501e1ded1",
    "e2ce385febaffc468d97e0b3b5be3d22159e2027",
    "9cfd257782560bb8628434dcf4191af5f851c98e",
    "1ed9b47214a8d7364bfd5b882629c509d49c827c",
    "753a1d4572c15bc3ab746752b67dbb1c8ee24c9a",
}


class WeChatContentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_content = False
        self.depth = 0
        self.text: list[str] = []
        self.images: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        if not self.in_content and tag == "div" and attr_map.get("id") == "js_content":
            self.in_content = True
            self.depth = 1
            return

        if not self.in_content:
            return

        self.depth += 1
        if tag == "img":
            self.images.append(attr_map)
        if tag in {"p", "section", "div", "li", "h1", "h2", "h3", "h4", "br"}:
            self.text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self.in_content:
            return
        if tag in {"p", "section", "div", "li", "h1", "h2", "h3", "h4"}:
            self.text.append("\n")
        self.depth -= 1
        if self.depth <= 0:
            self.in_content = False

    def handle_data(self, data: str) -> None:
        if self.in_content and data.strip():
            self.text.append(data.strip())


@dataclass
class ImagePart:
    ctype: str
    location: str
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)


def read_message(path: Path):
    return BytesParser(policy=policy.default).parsebytes(path.read_bytes())


def decode_html(msg) -> str:
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            return (part.get_payload(decode=True) or b"").decode("utf-8", "replace")
    return ""


def decode_subject(msg) -> str:
    return str(make_header(decode_header(msg.get("Subject", ""))))


def extract_title(html_text: str, fallback: str) -> str:
    match = re.search(r'<h1[^>]*id="activity-name"[^>]*>(.*?)</h1>', html_text, re.S)
    if not match:
        return fallback
    title = re.sub(r"\s+", " ", re.sub("<.*?>", "", html.unescape(match.group(1)))).strip()
    return title or fallback


def parse_publish_date(html_text: str) -> tuple[str, str]:
    match = re.search(r'publish_time"[^>]*>([^<]+)</em>', html_text)
    raw = match.group(1).strip() if match else ""
    date_match = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日(?:\s*(\d{1,2}:\d{2}))?", raw)
    if not date_match:
        return "", raw

    year, month, day, hm = date_match.groups()
    iso = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    label = f"{int(year)}年{int(month)}月{int(day)}日" + (f" {hm}" if hm else "")
    return iso, label


def clean_lines(raw_text: str, title: str) -> list[str]:
    lines: list[str] = []
    seen_short: set[str] = set()
    compact_title = title.replace(" ", "")

    for raw_line in re.split(r"[\n\r]+", raw_text):
        line = re.sub(r"\s+", " ", html.unescape(raw_line)).strip(" \u3000|")
        if not line:
            continue
        if line == title or line.replace(" ", "") == compact_title:
            continue
        if line in NOISE_EXACT:
            continue
        if len(line) <= 2 and not re.search(r"[\u4e00-\u9fffA-Za-z]", line):
            continue
        if any(noise in line for noise in NOISE_CONTAINS):
            continue
        if len(line) < 20:
            if line in seen_short:
                continue
            seen_short.add(line)
        lines.append(line)

    return lines


def classify(title: str) -> str:
    if any(key in title for key in ["换届", "招新", "萌新", "破冰", "成立一月", "部门介绍", "今天，我们想", "科技有味道"]):
        return "community"
    if any(key in title for key in ["科普", "公益", "讲解", "职业访谈", "摇摇棒", "科技节"]):
        return "outreach"
    if any(key in title for key in ["单片机", "传感器", "制作", "干货", "大龙虾", "G的含义", "自动化水下机器人", "Vibe Coding", "暑期课程"]):
        return "technical"
    if any(key in title for key in ["比赛", "大赛", "赛事", "冠军", "载誉", "佳绩", "水下作业", "华北五省"]):
        return "competition"
    return "activity"


def normalize_url(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(html.unescape(value))
    return parsed.netloc.lower() + parsed.path


def collect_image_parts(msg) -> dict[str, ImagePart]:
    parts: dict[str, ImagePart] = {}
    for part in msg.walk():
        ctype = part.get_content_type()
        if not ctype.startswith("image/"):
            continue
        location = part.get("Content-Location") or ""
        data = part.get_payload(decode=True) or b""
        key = normalize_url(location)
        if key and data:
            parts[key] = ImagePart(ctype=ctype, location=location, data=data)
    return parts


def image_dimensions(data: bytes) -> tuple[int, int]:
    try:
        with Image.open(BytesIO(data)) as image:
            return image.width, image.height
    except Exception:
        return 0, 0


def extension_for(part: ImagePart) -> str:
    if part.ctype == "image/jpeg":
        return "jpg"
    if part.ctype == "image/png":
        return "png"
    if part.ctype == "image/gif":
        return "gif"
    if part.ctype == "image/webp":
        return "webp"
    return "img"


def encode_image(image: Image.Image, ctype: str) -> bytes:
    buffer = BytesIO()
    if ctype == "image/png":
        image.save(buffer, format="PNG", optimize=True)
    elif ctype == "image/webp":
        image.save(buffer, format="WEBP", quality=88, method=6)
    else:
        image.save(buffer, format="JPEG", quality=90, optimize=True)
    return buffer.getvalue()


def trim_publication_overlay(data: bytes, ctype: str, article_id: str) -> tuple[bytes, int, int]:
    with Image.open(BytesIO(data)) as source:
        image = source.convert("RGB")
        width, height = image.size
        if width < 260 or height < 180:
            return encode_image(image, ctype), width, height

        article_year = int(article_id[1:5]) if re.match(r"a\d{8}-", article_id) else 0
        if article_year and article_year <= 2020:
            trim_bottom = min(max(round(height * 0.1), 54), 96)
        else:
            trim_bottom = min(max(round(height * 0.035), 12), 32)
        cleaned = image.crop((0, 0, width, height - trim_bottom))
        return encode_image(cleaned, ctype), cleaned.width, cleaned.height


def choose_images(article_id: str, title: str, parser_images: list[dict[str, str]], parts: dict[str, ImagePart], output_dir: Path) -> list[dict]:
    if title in NO_IMAGE_TITLES or FORMAL_TITLE_REPLACEMENTS.get(title) in NO_IMAGE_TITLES:
        return []

    candidates = []
    seen_hashes: set[str] = set()

    for index, attrs in enumerate(parser_images):
        cls = attrs.get("class", "")
        alt = attrs.get("alt", "")
        if "wx_follow_avatar" in cls or alt == "cover_image":
            continue

        url = attrs.get("src") or attrs.get("data-src") or ""
        data_url = attrs.get("data-src") or ""
        part = parts.get(normalize_url(url)) or parts.get(normalize_url(data_url))
        if not part:
            continue
        digest = hashlib.sha1(part.data).hexdigest()
        if digest in seen_hashes:
            continue
        if digest in EXCLUDED_IMAGE_HASHES:
            continue
        seen_hashes.add(digest)

        width, height = image_dimensions(part.data)
        if not width or not height:
            continue
        area = width * height
        ratio = width / height
        if part.ctype == "image/gif":
            continue
        if part.size < 8000 or width < 220 or height < 120 or area < 70000:
            continue
        if ratio > 5 or ratio < 0.3:
            continue
        if part.size > 1800 * 1024:
            continue
        score = area + part.size * 0.35
        candidates.append((score, index, part, width, height))

    selected = sorted(candidates, key=lambda item: item[0], reverse=True)[:2]
    selected = sorted(selected, key=lambda item: item[1])
    if title == "2022 年社团第八届换届大会":
        meeting_images = [item for item in selected if item[2].ctype == "image/webp"]
        selected = meeting_images[:1] or selected[:1]
    results = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for image_index, (_, _source_index, part, _width, _height) in enumerate(selected, 1):
        cleaned_data, width, height = trim_publication_overlay(part.data, part.ctype, article_id)
        filename = f"{article_id}-{image_index:02d}.{extension_for(part)}"
        (output_dir / filename).write_bytes(cleaned_data)
        results.append(
            {
                "src": f"./assets/articles/{filename}",
                "width": width,
                "height": height,
                "type": part.ctype,
                "alt": title,
            }
        )

    return results


def clean_formal_text(line: str) -> str:
    text = re.sub(r"\s+", " ", line).strip()
    text = re.sub(r"[♫♪♬♩]+", "", text)
    replacements = [
        ("Hey，guys", ""),
        ("Hey, guys", ""),
        ("So everybody ready？——Let's go", ""),
        ("So everybody ready?", ""),
        ("Let's go", ""),
        ("点击", ""),
        ("关注我们", ""),
        ("公众微信平台", "资料平台"),
        ("微信公众号", "资料平台"),
        ("公众号", "资料"),
        ("微信", "资料"),
        ("小编", "团队"),
        ("我们团队", "参赛团队"),
        ("我们的团队", "参赛团队"),
        ("我们G_Robot", "G_Robot"),
        ("我们G-robot", "G_Robot"),
        ("我们G_robot", "G_Robot"),
        ("我们社团", "社团"),
        ("我们的社团", "社团"),
        ("我们学校", "学校"),
        ("我们的学校", "学校"),
        ("我们", "团队"),
        ("成员国", "我国"),
        ("咱们", "团队"),
        ("大家", "成员"),
        ("你们", "新成员"),
        ("广大的学生朋友", "学生"),
        ("同学们", "成员"),
        ("同学担任", "同学担任"),
        ("同学", "学生"),
        ("学生担任", "同学担任"),
        ("萌新", "新成员"),
        ("小伙伴们", "成员"),
        ("小伙伴", "成员"),
        ("妹纸", "女同学"),
        ("妹子", "女同学"),
        ("男同胞", "男同学"),
        ("学长学姐", "高年级成员"),
        ("学长", "高年级成员"),
        ("学姐", "高年级成员"),
        ("高年级成员们", "高年级成员"),
        ("成员们", "成员"),
        ("队员们", "队员"),
        ("老师们", "老师"),
        ("硬软件", "软硬件"),
        ("帅气的", ""),
        ("可爱的", ""),
        ("暖暖哒", "受到鼓舞"),
        ("哒", ""),
        ("哇塞", ""),
        ("呀", ""),
        ("呦", ""),
        ("哟", ""),
        ("啦", ""),
        ("哦", ""),
        ("吧", ""),
        ("~", ""),
        ("……", "。"),
        ("...", "。"),
        ("！", "。"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    text = re.sub(r"(?<![A-Za-z])我(?![A-Za-z])", "成员", text)
    text = text.replace("成员国", "我国").replace("成员校", "我校")
    text = re.sub(r"(?:让团队|接下来|下面|首先|那么)?一起(?:来)?(?:看看|回顾|了解)[^。；]*[。；]?", "", text)
    text = re.sub(r"(?:那么|接下来|下面)?[^。；]{0,12}具体看一下[^。；]*[。；]?", "", text)
    text = re.sub(r"欢迎[^。；]*(?:参与|加入|到来)[^。；]*[。；]?", "", text)
    text = re.sub(r"下次见[。；]?", "", text)
    text = re.sub(r"大家一起加油[。；]?", "", text)
    text = re.sub(r"心里[^。；]*[。；]?", "", text)
    text = re.sub(r"[？?]{1,}", "。", text)
    text = re.sub(r"[。]{2,}", "。", text)
    text = re.sub(r"\s+([，。；：])", r"\1", text)
    text = re.sub(r"([，。；：])\s+", r"\1", text)
    return text.strip(" ，。") + ("。" if text and not text.endswith(("。", "；", "：", "）", ".")) else "")


def is_public_useful(line: str) -> bool:
    if len(line) < 12:
        return False
    if re.fullmatch(r"[0-9A-Za-z ._-]+", line):
        return False
    blocked = [
        "公众号",
        "微信",
        "二维码",
        "扫描",
        "关注",
        "点击",
        "推送",
        "接下来",
        "来看一下",
        "技术盛宴",
        "今天早上",
        "具体看一下",
        "团队来具体",
        "广大的学生朋友",
        "欢迎",
        "学弟",
        "学妹",
        "话说回来",
        "同道中人",
        "如果你",
        "搞。事。情",
        "老身",
        "美照",
        "幸福的事情",
        "志同道合",
        "全身充满力量",
        "美妙",
        "一起拼搏",
        "小编",
        "呦",
        "哇塞",
        "暖暖",
        "下次见",
        "大家一起加油",
        "无比激动",
        "面红耳赤",
        "废寝忘食",
        "要玩就玩",
        "玩点",
        "成员要感谢",
        "真的很感谢",
        "感谢",
        "感恩",
        "前程似锦",
        "岁月安好",
        "心情",
        "满怀期待",
        "期待",
        "心心念念",
        "命途多舛",
        "敌方机器人",
        "偷拍",
        "好兆头",
        "skr",
        "扫码",
        "QQ群",
        "联系人",
        "tel",
        "官网",
        "男神",
        "小礼物",
        "神奇",
        "地狱般",
        "绝唱",
        "共赴",
        "深情",
        "奋进力量",
        "无限可能",
        "老少皆宜",
        "居家必备",
        "玩得飞起",
        "群众基础",
        "团队知道",
        "成员知道",
        "社团所涉及的领域在",
        "最终发展到",
        "来具体",
        "问题来了",
        "原谅",
        "呐喊",
        "不可思议",
        "不敢奢望",
        "票赞成",
        "出乎意料是",
        "节操",
        "海绵宝宝",
        "站街",
        "Gay",
        "萌妹",
        "男同胞",
        "自费出行",
        "安慰的台词",
        "媒体进行先后报道直播",
        "多家国内媒体",
        "缺点暴露",
        "现场报道",
        "小说阅读器",
    ]
    if any(word in line for word in blocked):
        return False
    if line.endswith(("领域在。", "发展到。", "一起。", "一切准。", "报道,熟。")):
        return False
    return True


def split_formal_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[。；])\s*", text) if part.strip()]


def formal_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        if not is_public_useful(line):
            continue
        item = clean_formal_text(line)
        for sentence in split_formal_sentences(item):
            if not is_public_useful(sentence):
                continue
            if sentence not in cleaned:
                cleaned.append(sentence)
    return cleaned


def excerpt_from(lines: list[str]) -> str:
    useful = formal_lines(lines)
    if not useful:
        return "G_Robot 持续推进这一阶段的社团活动。"
    text = "".join(useful[:3])
    return text[:180] + ("..." if len(text) > 180 else "")


def formal_title(title: str) -> str:
    return FORMAL_TITLE_REPLACEMENTS.get(title, title.replace("||", "：").replace("‖", "：").replace("！", ""))


def category_role(category: str) -> str:
    return {
        "competition": "赛事成果",
        "community": "组织建设",
        "outreach": "科普交流",
        "technical": "技术训练",
        "activity": "社团活动",
    }.get(category, "社团活动")


def event_verb(title: str) -> str:
    return "举行" if title.endswith(("活动", "大会", "课程", "赛事")) else "开展"


def manual_article_copy(title: str, date_label: str) -> dict | None:
    copies = {
        "G_Robot成立一月纪念": {
            "excerpt": "G_Robot 在成立初期完成名称确立，并迅速投入水下机器人训练、赛事准备和实验室实践，形成了持续投入的团队氛围。",
            "highlights": [
                "社团成立初期围绕名称、方向和团队文化形成共识。",
                "早期成员参与水下机器人赛事训练，并将赛事复盘转化为后续改进依据。",
                "团队在水下机器人项目中取得两个亚军、一个冠军的阶段性成绩。",
                "这一节点展示了 G_Robot 的起点、成员投入和早期竞赛积累。",
            ],
            "sections": [
                {
                    "heading": "组织背景",
                    "body": "G_Robot 在成立初期完成名称确立，并逐步形成成员协作和早期发展方向。团队在成立之初即把水下机器人训练、实验室实践和赛事参与作为重要任务。",
                },
                {
                    "heading": "早期积累",
                    "body": "团队在短时间内完成了从训练到参赛的过程，并在水下机器人项目中取得两个亚军、一个冠军的阶段性成绩。相关经历也促使成员继续围绕机器改进、创新实践和赛事复盘开展工作。",
                },
                {
                    "heading": "发展意义",
                    "body": "这一节点展现了 G_Robot 从兴趣团队走向稳定社团的起步状态，也为后续社团文化、竞赛传统和成员传承奠定基础。",
                },
            ],
        },
        "G_Robot之G的含义知多少？": {
            "excerpt": "G_Robot 围绕名称中的“G”延展出起源、实践、技术探索和团队协作等理念，逐步形成社团早期文化。",
            "highlights": [
                "G_Robot 的名称文化与起源、实践和技术探索紧密相关。",
                "社团强调兴趣驱动、项目实践和团队协作。",
                "这一节点展现了社团早期价值表达和组织认同。",
            ],
            "sections": [
                {
                    "heading": "文化背景",
                    "body": "G_Robot 从名称解释切入，形成了对“G”的多重理解。团队希望以技术兴趣、实践探索和开放协作为核心建立社团文化。",
                },
                {
                    "heading": "团队理念",
                    "body": "社团将活动与起源意识、动手实践、技术探索和集体协作联系起来，不只追求单次比赛成绩，也重视成员在项目中的持续学习和共同成长。",
                },
                {
                    "heading": "发展意义",
                    "body": "这一节点展现了社团早期文化表达方式，也解释了后续招新、部门建设和成员培养方式的基础。",
                },
            ],
        },
        "如果科技有味道，你尝过哪种？": {
            "excerpt": "G_Robot 围绕项目基础与实践资源展开建设，重点发展水下机器人方向、软硬件训练、结构加工和赛事实践。",
            "highlights": [
                "社团创建于 2014 年，面向软件、硬件和工程实践能力培养。",
                "水下机器人方向使用 Raspberry Pi、网络通信、电池供电、Python 和 C++ 等技术要素。",
                "社团在水下机器人相关赛事中形成了持续参赛和获奖积累。",
            ],
            "sections": [
                {
                    "heading": "项目背景",
                    "body": "G_Robot 创建后持续建设项目方向与实践资源。社团以软件、硬件和工程实践能力培养为核心，为成员提供科技实践、项目训练和赛事准备机会。",
                },
                {
                    "heading": "技术内容",
                    "body": "水下机器人方向采用 Raspberry Pi 作为主控，通过网络传输数据，使用电池供电，并结合 Python、C++、聚丙烯结构件、数控车床和数控雕刻机等软硬件与加工条件完成设计制作。",
                },
                {
                    "heading": "发展意义",
                    "body": "这一节点集中呈现了社团早期项目资源和水下机器人技术路线，是后续竞赛成果、课程训练和项目传承的重要基础。",
                },
            ],
        },
        "萌新驾到，G_Robot社团带你梦想启航！": {
            "excerpt": "G_Robot 面向新成员介绍社团定位、实践方向和组织结构，并以水下机器人、硬件制作、软件开发和竞赛训练作为主要实践内容。",
            "highlights": [
                "G_Robot 是面向工程实践和科技创新的学生社团。",
                "社团实践内容覆盖水下机器人、硬件制作、软件开发和竞赛训练。",
                "招新介绍展示了社团面向新成员的培养路径。",
            ],
            "sections": [
                {
                    "heading": "组织背景",
                    "body": "G_Robot 面向新成员介绍社团定位。社团以学生动手实践和科技创新训练为核心，依托水下机器人项目、硬件制作、软件开发和赛事备赛形成实践平台。",
                },
                {
                    "heading": "培养方向",
                    "body": "社团围绕凝聚力、竞赛成绩、活动组织和部门分工展开建设，形成以兴趣驱动、自主学习、项目训练和成员协作为主的培养方式。",
                },
                {
                    "heading": "发展意义",
                    "body": "这一节点展现了 G_Robot 面向新成员的组织介绍方式，也体现了招新、部门建设和梯队培养的连续性。",
                },
            ],
        },
        "今天，我们想对你们说": {
            "excerpt": "指导教师和社团骨干面向新成员分享学习与实践建议，重点关注大学适应、专业学习、技术实践和社团参与。",
            "highlights": [
                "指导教师和社团骨干为新成员提供学习与实践建议。",
                "内容强调专业基础、动手能力、团队协作和持续参与。",
                "这一节点体现了社团成员培养和传承方式。",
            ],
            "sections": [
                {
                    "heading": "活动背景",
                    "body": "G_Robot 面向新加入社团的成员汇集指导教师和社团骨干的建议，内容主要围绕大学阶段的学习适应、专业基础积累和实践能力培养展开。",
                },
                {
                    "heading": "培养建议",
                    "body": "社团强调成员应重视课程学习、技术实践和团队协作，在社团项目中逐步建立工程意识、沟通能力和持续解决问题的能力。",
                },
                {
                    "heading": "发展意义",
                    "body": "这一节点体现了 G_Robot 对新成员培养和社团传承的关注，也展示了成员梯队建设的连续性。",
                },
            ],
        },
        "科技干货‖如何制作属于你的水下机器人": {
            "excerpt": "G_Robot 系统介绍水下机器人基础构成、常见部件和制作思路，涵盖水下载体、地面控制箱、推进器、密封舱、机械臂和视频传输等内容。",
            "highlights": [
                "ROV 的基本结构包括水下载体和地面控制箱。",
                "文本涉及推进器、密封舱、机械臂、框架、配重和摄像头等关键部件。",
                "这一节点为社团后续水下机器人制作训练提供了技术说明基础。",
            ],
            "sections": [
                {
                    "heading": "技术背景",
                    "body": "G_Robot 围绕水下机器人制作展开技术讲解，介绍 ROV 的基本构成和应用场景。水下机器人通常由水下载体与地面控制箱组成，通过推进、通信、视频回传和机械执行部件完成水下观察与作业。",
                },
                {
                    "heading": "结构内容",
                    "body": "讲解重点涉及推进器、密封舱、机械臂、外部框架、配重、摄像头和地面控制箱等部件，并说明水下机器人可实现前进、后退、转向、上浮、下潜和简单作业操作。",
                },
                {
                    "heading": "发展意义",
                    "body": "这一节点将社团水下机器人实践中的基础结构和制作思路转化为技术训练内容，为后续课程、训练和赛事备赛提供了入门说明。",
                },
            ],
        },
        "回顾与展望| G_Robot社团换届大会圆满召开": {
            "excerpt": "G_Robot 于 2021 年 5 月 14 日在一教 W43 举行第七届换届大会，完成上一阶段工作总结和新一届骨干交接，李一一接任社长。",
            "highlights": [
                "大会由副社长安楠主持，王扬、李越、李芳老师出席。",
                "谢晨曦总结上一阶段社团工作，回顾社团成绩和成员贡献。",
                "李一一接任社长，安楠、陈齐岳、吴晓峰任副社长。",
                "机械部、硬件部、软件部、宣传部完成负责人交接。",
            ],
            "sections": [
                {
                    "heading": "组织背景",
                    "body": "2021 年 5 月 14 日晚，G_Robot 在一教 W43 举行第七届换届大会。大会由副社长安楠主持，王扬、李越、李芳老师出席，社团成员共同参与年度交接。",
                },
                {
                    "heading": "交接与建设",
                    "body": "谢晨曦总结上一阶段社团工作。王扬老师宣布新一届任职名单：李一一任社长，安楠、陈齐岳、吴晓峰任副社长；安泽康任机械部部长，高原任硬件部部长，李昊远任软件部部长，陈开元任宣传部部长。各部门副部长包括孙乐音、甘永君、张鲜波、赵梦童、付伟、张树波、龙诗铭、王硕。",
                },
                {
                    "heading": "发展意义",
                    "body": "第七届换届大会让社团完成组织责任、部门协作和成员培养的连续交接，也为新一阶段的实验室训练、项目实践和赛事准备建立了团队基础。",
                },
            ],
        },
        "回顾与展望| G_Robot社团第八届换届大会圆满召开": {
            "excerpt": "G_Robot 于 2022 年 7 月 7 日线上举行第八届换届大会，完成第七届工作总结、赛事与创业工作交流、新一届骨干和指导教师交接，龙诗铭接任社长。",
            "highlights": [
                "20 级、21 级成员，18 级、19 级部分骨干，以及多位老师和嘉宾参加大会。",
                "李一一总结第七届社团工作，回顾社团成绩和成员贡献。",
                "赵梦童分享 MATE 比赛经历，吴晓锋汇报社团创业工作。",
                "龙诗铭接任社长，李连鹏作为新任指导教师参与后续建设。",
            ],
            "sections": [
                {
                    "heading": "组织背景",
                    "body": "2022 年 7 月 7 日上午，G_Robot 在线上举行第八届换届大会。20 级、21 级社团成员，18 级、19 级部分骨干，王扬、李越、李芳老师以及新任指导教师李连鹏老师参加大会，校团委古一老师、自动化学院副书记陈天宇老师、辅导员黄浩轩老师作为嘉宾出席。",
                },
                {
                    "heading": "交接与建设",
                    "body": "李一一总结第七届社团工作，回顾社团取得的成绩和成员贡献。赵梦童围绕 MATE 比赛准备、计划、行动、修正、实操和完赛进行分享，吴晓锋汇报龙诚智航科技有限公司的初创历程及成果。随后王扬老师宣布任职名单，龙诗铭作为新任社长发言。",
                },
                {
                    "heading": "发展意义",
                    "body": "第八届换届大会把社团工作总结、赛事经验、创业探索和指导教师交接放在同一节点中完成，体现了 G_Robot 在组织传承、工程实践和科技创新平台建设上的持续推进。",
                },
            ],
        },
        "G_Robot社团2026换届大会圆满落幕": {
            "excerpt": "G_Robot 举行 2026 年社团换届大会，完成新一届骨干交接，并围绕技术培训、项目研发、赛事备赛和新人培养规划下一阶段工作。",
            "highlights": [
                "杨文俊总结上一阶段社团工作。",
                "李越老师宣读新一届骨干名单。",
                "谢家跃接任社长，并规划技术培训、项目研发、赛事备赛和新人培养。",
            ],
            "sections": [
                {
                    "heading": "组织背景",
                    "body": "G_Robot 于 2026 年举行社团换届大会，指导老师和社团成员共同参与，围绕上一阶段工作总结、新一届骨干交接和社团发展方向展开。",
                },
                {
                    "heading": "交接与建设",
                    "body": "杨文俊总结上一阶段社团工作，李越老师宣读新一届骨干名单，谢家跃接任社长并提出任职规划。社团将继续推进技术培训、项目研发、赛事备赛和新人培养。",
                },
                {
                    "heading": "发展意义",
                    "body": "换届大会让社团经验、项目方向和组织责任完成交接，也为新一阶段的水下机器人训练与竞赛实践建立了清晰方向。",
                },
            ],
        },
        "G_Robot社团2025换届大会": {
            "excerpt": "G_Robot 举行 2025 年社团换届大会，围绕骨干交接、部门协作和新一阶段社团建设完成组织衔接。",
            "highlights": [
                "社团通过换届大会完成新一阶段骨干交接。",
                "换届工作延续了 G_Robot 的组织传承和部门协作。",
                "新一届成员将继续推进技术训练、项目实践和赛事备赛。",
            ],
            "sections": [
                {
                    "heading": "组织背景",
                    "body": "G_Robot 通过换届大会完成阶段性工作总结和新一届骨干交接。换届是社团保持组织连续性、项目传承和成员梯队建设的重要环节。",
                },
                {
                    "heading": "交接与建设",
                    "body": "新一届骨干围绕部门协作、技术训练、项目实践和赛事备赛继续推进社团工作，让水下机器人方向的经验在成员之间延续。",
                },
                {
                    "heading": "发展意义",
                    "body": "2025 年换届大会帮助社团完成责任交接，也为新一阶段的课程活动、机器人研发和竞赛准备建立组织基础。",
                },
            ],
        },
    }
    copy = copies.get(title)
    if not copy:
        return None
    display_title = formal_title(title)
    return {
        "excerpt": copy["excerpt"],
        "highlights": copy["highlights"],
        "detail": {
            "summary": f"{date_label}，{display_title}。{copy['excerpt']}",
            "sections": copy["sections"],
        },
    }


def formal_detail(title: str, date_label: str, category: str, lines: list[str], status: str) -> dict:
    useful = formal_lines(lines)
    display_title = formal_title(title)

    if status == "待补充":
        return {
            "summary": f"{date_label}，{display_title}。",
            "sections": [
                {
                    "heading": "活动概况",
                    "body": "这一节点展现了 G_Robot 在组织建设、项目实践和成员传承中的持续推进。",
                }
            ],
        }

    summary_source = useful[0] if useful else ""
    summary = f"{date_label}，{display_title}。"
    if summary_source and status != "需人工复核":
        summary += summary_source[:140]

    headings = {
        "competition": ("赛事背景", "过程与成果", "发展意义"),
        "community": ("组织背景", "交接与建设", "发展意义"),
        "outreach": ("活动背景", "活动内容", "发展意义"),
        "technical": ("训练背景", "技术内容", "发展意义"),
        "activity": ("活动背景", "活动内容", "发展意义"),
    }[category]

    if status == "需人工复核":
        first = "G_Robot 在这一节点中参与了参赛行程、赛前调试、设备准备和比赛现场报道。"
        second = "团队围绕机器人状态、工具箱、现场报到和赛前适应展开工作，为正式比赛做准备。"
        third = "这一经历体现了社团在赛事前期组织、设备保障和现场协作中的投入。"
    else:
        first = " ".join(useful[:2]) if useful else "G_Robot 在这一阶段持续开展社团活动。"
        second = " ".join(useful[2:5]) if len(useful) > 2 else "活动围绕成员训练、项目实践和团队协作展开。"
        third = " ".join(useful[5:7]) if len(useful) > 5 else "这一节点延续了社团在技术实践、成员传承和项目积累中的持续投入。"

    return {
        "summary": summary[:260],
        "sections": [
            {"heading": headings[0], "body": first[:420]},
            {"heading": headings[1], "body": second[:520]},
            {"heading": headings[2], "body": third[:420]},
        ],
    }


def polish_public_text(text: str) -> str:
    replacements = [
        ("该资料记录了", "G_Robot 展现了"),
        ("该资料记录", "G_Robot 展现"),
        ("早期资料记录了", "G_Robot 在成立初期形成了"),
        ("资料覆盖", "G_Robot 涵盖"),
        ("资料记录", "G_Robot 展现"),
        ("文章记录", "G_Robot 展现"),
        ("报道明确记录", "G_Robot 在赛事中取得"),
        ("报道记录", "G_Robot 取得"),
        ("换届文章记录", "换届大会中"),
        ("档案意义", "发展意义"),
        ("资料背景", "活动背景"),
        ("资料状态", "活动概况"),
        ("站内档案", "站内内容"),
        ("档案", "内容"),
        ("后续", "之后"),
        ("现场报道", "现场准备"),
        ("报道直播", "介绍"),
        ("媒体进行先后介绍", "媒体关注"),
        ("缺点暴露了出来", "状态仍需调整"),
        ("G_Robot 展现了", "G_Robot 展现了"),
        ("资料整理了", "G_Robot 汇集了"),
        ("资料介绍了", "G_Robot 展示了"),
        ("资料介绍", "G_Robot 展示"),
        ("资料围绕", "G_Robot 围绕"),
        ("资料重点", "G_Robot 重点"),
        ("资料将", "G_Robot 将"),
        ("资料说明", "G_Robot 展示"),
        ("资料提到", "G_Robot 在活动中体现出"),
        ("资料强调", "G_Robot 强调"),
        ("该资料", "G_Robot"),
        ("该条目", "这一节点"),
        ("条目", "内容"),
        ("本页暂以活动概况说明为主", "本页展示活动概况"),
        ("当前资料", "当前内容"),
        ("更多活动内容将持续完善。", "G_Robot 持续推进这一阶段的社团活动。"),
        ("无论是风里，还是在雨里，成员都在这里守候着你～。", "成员围绕备赛目标持续投入训练和调试。"),
        ("住宿条件棒棒。", "团队继续完成赛前适应和现场准备。"),
        ("千年老二", "连续亚军"),
        ("海军小哥哥", "现场工作人员"),
        ("爱恨纠葛", "参与经历"),
        ("脑洞", "理解和表达能力"),
        ("小鲜肉们", "新成员"),
        ("酷炫的作品", "硬件作品"),
        ("ps：第一个完成的还是女同学", "成员在活动中完成了作品"),
        ("团队暂且不表，留在最后揭晓。", ""),
        ("不得不提一句，", ""),
        ("酱油之旅", "参赛经历"),
        ("圆满结束", "顺利结束"),
        ("圆满落幕", "顺利结束"),
        ("level更高", "更深入"),
        ("建议后续对照原始文稿补完整正文。", ""),
        ("部分段落结构不完整", "内容仍在持续完善"),
        ("具体成果与过程需要结合完整记录复核", "团队将继续补充更多比赛过程"),
        ("未经核验", "尚未展示"),
        ("复核", "完善"),
        ("原始文稿", "活动内容"),
        ("早期证据", "早期基础"),
        ("属于赛事成果资料。", ""),
        ("属于组织建设资料。", ""),
        ("属于科普交流资料。", ""),
        ("属于技术训练资料。", ""),
        ("属于社团活动资料。", ""),
        ("赛事成果资料", "赛事成果"),
        ("组织建设资料", "组织建设"),
        ("科普交流资料", "科普交流"),
        ("技术训练资料", "技术训练"),
        ("社团活动资料", "社团活动"),
        ("整理于", "发生于"),
        ("记录于", "发生于"),
        ("资料", "内容"),
    ]
    result = text
    for old, new in replacements:
        result = result.replace(old, new)
    result = re.sub(r"。{2,}", "。", result)
    result = re.sub(r"，。", "。", result)
    return result


def polish_payload(value):
    if isinstance(value, str):
        return polish_public_text(value)
    if isinstance(value, list):
        return [polish_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: polish_payload(item) for key, item in value.items()}
    return value


def highlights_from(lines: list[str], category: str) -> list[str]:
    keywords = {
        "competition": ["一等奖", "二等奖", "三等奖", "冠军", "亚军", "季军", "成绩", "比赛", "大赛"],
        "community": ["社长", "副社长", "换届", "招新", "成员", "指导老师", "成立", "部门"],
        "outreach": ["活动", "讲解", "科普", "公益", "同学", "学生", "课程"],
        "technical": ["水下机器人", "单片机", "传感器", "制作", "焊接", "控制", "机械", "硬件", "软件"],
        "activity": ["活动", "社团", "成员"],
    }[category]

    candidates = [line for line in lines if len(line) >= 16 and any(key in line for key in keywords)]
    candidates.extend(line for line in lines if len(line) >= 16 and line not in candidates)

    cleaned = []
    for line in candidates:
        item = clean_formal_text(line)
        if not item or not is_public_useful(item):
            continue
        item = item[:220] + ("..." if len(item) > 220 else "")
        if item not in cleaned:
            cleaned.append(item)
        if len(cleaned) >= 4:
            break
    return cleaned


def status_for(title: str, lines: list[str]) -> str:
    if title == "G_Robot社团2025换届大会":
        return "待补充"
    if title == "G_Robot社团参加2025中国机器人大赛（专项赛）纪实！":
        return "需人工复核"
    if len([line for line in lines if len(line) > 20]) < 2:
        return "待补充"
    return "已整理"


def find_id(articles: list[dict], keyword: str) -> str:
    for article in articles:
        if keyword in article["title"] or keyword in article.get("_sourceTitle", ""):
            return article["id"]
    return ""


def find_article(articles: list[dict], keyword: str) -> dict | None:
    for article in articles:
        if keyword in article["title"] or keyword in article.get("_sourceTitle", ""):
            return article
    return None


def assign_founder_team_image(articles: list[dict], team_dir: Path) -> None:
    founder_article = find_article(articles, "G_Robot 成立初期")
    source_article = find_article(articles, "2017 年社团换届大会")
    if not founder_article or not source_article:
        return

    source_image = next((image for image in source_article.get("images", []) if image.get("src") == FOUNDER_TEAM_IMAGE_SOURCE), None)
    if not source_image:
        return

    source_path = team_dir / FOUNDER_TEAM_IMAGE_SOURCE.removeprefix("./")
    target_path = team_dir / FOUNDER_TEAM_IMAGE_TARGET.removeprefix("./")
    if source_path.exists():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target_path)
        if source_path != target_path:
            source_path.unlink()

    founder_image = {
        **source_image,
        "src": FOUNDER_TEAM_IMAGE_TARGET,
        "alt": "G_Robot 创始阶段团队合影",
    }
    founder_article["image"] = FOUNDER_TEAM_IMAGE_TARGET
    founder_article["images"] = [founder_image]

    source_article["images"] = [image for image in source_article.get("images", []) if image.get("src") != FOUNDER_TEAM_IMAGE_SOURCE]
    source_article["image"] = source_article["images"][0]["src"] if source_article["images"] else ""


def build_manual_sections(articles: list[dict]) -> tuple[list[dict], list[dict], list[dict], list[str]]:
    def fid(keyword: str) -> str:
        return find_id(articles, keyword)

    milestones = [
        {
            "year": "2014",
            "title": "成立初期即进入水下机器人竞赛",
            "body": "G_Robot 在成立初期完成名称确立和团队凝聚，成员很快投入实验室训练、水下机器人讲解和赛事准备，形成以项目实践推动成长的社团传统。",
            "articleId": fid("水下机器人原理讲解"),
            "awardArticleId": fid("成立一月"),
            "awards": ["水下机器人项目冠军 1 项", "水下机器人项目亚军 2 项"],
        },
        {
            "year": "2016",
            "title": "龙虾系列水下机器人参赛",
            "body": "G_Robot 围绕龙虾系列水下机器人开展结构、动力和操作训练，在水下作业与水下对抗任务中继续积累比赛经验。",
            "articleId": fid("大龙虾"),
            "awardArticleId": fid("大龙虾"),
            "awards": ["水下对抗赛亚军"],
        },
        {
            "year": "2017",
            "title": "国际水中机器人大赛与中国机器人大赛双线参赛",
            "body": "G_Robot 在合肥国际水中机器人大赛和中国机器人大赛之间连续备赛、调试和复盘，参赛方向覆盖水下作业与水下对抗。",
            "articleId": fid("2017系列"),
            "awardArticleId": fid("2017系列"),
            "awards": ["国际水中机器人大赛水下作业二等奖、三等奖", "国际水中机器人大赛水下对抗季军及二等奖", "中国机器人大赛水下对抗二等奖及三等奖"],
        },
        {
            "year": "2018",
            "title": "中国机器人大赛取得九项奖项",
            "body": "社团在中国机器人大赛水下机器人大项中扩大参赛规模，覆盖水下对抗、水下作业和水中巡游三个项目，并在水下对抗项目实现冠军突破。",
            "articleId": fid("震惊"),
            "awardArticleId": fid("震惊"),
            "awards": ["水下对抗项目冠军（一等奖）及二等奖 1 项", "水下作业项目二等奖 2 项、三等奖 2 项", "水中巡游项目三等奖 3 项"],
        },
        {
            "year": "2019",
            "title": "中国机器人大赛水下作业与水下对抗双冠",
            "body": "G_Robot 在中国机器人大赛中稳定发挥，水下作业项目以明显优势夺冠，水下对抗项目两支队伍会师决赛，成为社团竞赛史中的重要节点。",
            "articleId": fid("双冠"),
            "awardArticleId": fid("双冠"),
            "awards": ["水下作业项目冠军（一等奖）", "水下作业项目二等奖 2 项、三等奖 1 项", "水下对抗项目冠军（一等奖）及亚军（一等奖）"],
        },
        {
            "year": "2020",
            "title": "中国机器人大赛延续水下项目获奖",
            "body": "2020 年社团在完成组织交接的同时继续备战中国机器人大赛，在水下对抗和水下作业项目中保持稳定表现。",
            "articleId": fid("2020中国机器人大赛"),
            "awardArticleId": fid("2020中国机器人大赛"),
            "awards": ["水下对抗项目亚军（一等奖）", "水下作业项目二等奖", "水下作业项目三等奖"],
        },
        {
            "year": "2023",
            "title": "仿真技术与世界大学生水下赛事并进",
            "body": "G_Robot 同时参与国际先进机器人及仿真技术大赛、世界大学生水下机器人大赛，并围绕水下机器人设计开展技术分享。",
            "articleId": fid("国际先进机器人"),
            "awardArticleId": fid("国际先进机器人"),
            "awards": ["国际先进机器人及仿真技术大赛冠军 1 项、亚军 1 项", "国际先进机器人及仿真技术大赛一等奖 2 项、二等奖 2 项、三等奖 2 项", "世界大学生水下机器人大赛三等奖 3 项"],
        },
        {
            "year": "2025",
            "title": "中国国际海洋水下机器人大赛 ROV/AUV 赛道全部获奖",
            "body": "社团在暑期课程、机器人制作和水池训练基础上参加中国国际海洋水下机器人大赛，多支队伍在 ROV 与 AUV 赛道全部获奖。",
            "articleId": fid("中国国际海洋水下机器人大赛"),
            "awardArticleId": fid("中国国际海洋水下机器人大赛"),
            "awards": ["ROV 赛道一等奖 1 项、二等奖 2 项、三等奖 1 项", "AUV 赛道二等奖 2 项"],
        },
        {
            "year": "2026",
            "title": "水下具身智能与新一阶段社团发展",
            "body": "G_Robot 将水下具身智能、仿真训练和 Vibe Coding 纳入社团技术分享，并通过换届大会完成新一届骨干交接，为后续竞赛和项目实践延续基础。",
            "articleId": fid("Vibe Coding"),
            "awardArticleId": "",
            "awards": ["围绕水下具身智能、仿真训练和项目研发继续开展技术积累"],
        },
    ]

    awards = [
        {"year": "2014", "title": "早期水下机器人项目参赛成果", "body": "G_Robot 在成立初期便投入水下机器人赛事训练，并取得两个亚军、一个冠军的阶段性成绩。", "articleId": fid("成立一月")},
        {"year": "2016", "title": "龙虾系列水下机器人对抗赛亚军", "body": "G_Robot 使用龙虾系列水下机器人参加对抗赛，并在该项目中获得亚军。", "articleId": fid("大龙虾")},
        {"year": "2017", "title": "国际水中机器人大赛与中国机器人大赛多项奖项", "body": "G_Robot 在国际水中机器人大赛水下作业、水下对抗项目中获奖，并在中国机器人大赛水下作业、水下对抗项目中继续取得名次。", "articleId": fid("2017系列")},
        {"year": "2018", "title": "中国机器人大赛九个奖项", "body": "G_Robot 在中国机器人大赛中取得水下对抗项目冠军（一等奖）及二等奖一项，水下作业项目二等奖两项、三等奖两项，水中巡游项目三等奖三项。", "articleId": fid("震惊")},
        {"year": "2019", "title": "中国机器人大赛水下作业、水下对抗双冠", "body": "G_Robot 取得水下作业项目冠军（一等奖）、二等奖两项、三等奖一项；水下对抗项目冠军（一等奖）及亚军（一等奖）。", "articleId": fid("双冠")},
        {"year": "2020", "title": "中国机器人大赛水下对抗亚军及作业项目获奖", "body": "G_Robot 取得水下对抗项目亚军（一等奖），并在水下作业项目中获得二等奖、三等奖。", "articleId": fid("2020中国机器人大赛")},
        {"year": "2023", "title": "国际先进机器人及仿真技术大赛一冠一亚等成绩", "body": "G_Robot 六支队伍取得一个冠军、一个亚军、两个一等奖、两个二等奖和两个三等奖；同年在世界大学生水下机器人大赛中取得三个三等奖。", "articleId": fid("国际先进机器人")},
        {"year": "2025", "title": "中国国际海洋水下机器人大赛 ROV/AUV 赛道全部获奖", "body": "G_Robot 多支参赛团队全部获奖：ROV 赛道一等奖 1 项、二等奖 2 项、三等奖 1 项，AUV 赛道二等奖 2 项。", "articleId": fid("中国国际海洋水下机器人大赛")},
    ]

    teams = [
        {"period": "2014", "title": "创始阶段", "body": "何常鑫和伙伴们在 2014 年 10 月成立 G_Robot，社团早期强调兴趣、热情、自学、讨论和实验室实践。", "people": "创始成员：何常鑫等；王扬、李越等老师长期支持社团建设。", "articleId": fid("成立一月")},
        {"period": "2017", "title": "第三次换届：刘春芽接任", "body": "何常鑫、郝卫、曹冠群等早期社长完成接力后，刘春芽担任新一届社长，社团继续向稳定组织运行发展。", "people": "社长：刘春芽；副社长：邓云、王慧林。", "articleId": fid("G-robot社团换届大会")},
        {"period": "2018", "title": "第四届换届：石丛玮接任", "body": "社团结构和管理体系进一步完善，电子、机械、公关等部门完成负责人交接。", "people": "社长：石丛玮；副社长：陈治金、匡柯澜、马玉静；电子部、机械部、公关部等部门完成交接。", "articleId": fid("第四届换届")},
        {"period": "2019", "title": "第五届换届：王曜瑄接任", "body": "2019 年换届大会中，上届社长石丛玮总结 2018-2019 年工作，新任社长王曜瑄发表就职感言。", "people": "社长：王曜瑄；副社长：陈少涵；机械部、软件部、宣传部等完成交接。", "articleId": fid("第五届换届")},
        {"period": "2020", "title": "换届大会：谢晨曦接任", "body": "2020 年换届大会中，王曜瑄总结上一届工作，王扬、李越老师发言并宣读新一届成员名单。", "people": "社长：谢晨曦；副社长：赵亚楠、张轩望、马克；机械、软件、硬件部门完成交接。", "articleId": fid("圆满召开")},
        {"period": "2021", "title": "第七届换届：李一一接任", "body": "第七届换届大会在一教 W43 举行，谢晨曦总结上一阶段社团工作，李一一接任社长，社团完成新一届骨干和部门负责人交接。", "people": "社长：李一一；副社长：安楠、陈齐岳、吴晓峰；指导老师：王扬、李越、李芳。", "articleId": fid("第七届换届")},
        {"period": "2022", "title": "第八届换届：龙诗铭接任", "body": "第八届换届大会在线上举行，李一一总结第七届工作，社团同步交流 MATE 比赛经验和创业工作，龙诗铭接任社长。", "people": "社长：龙诗铭；新任指导教师：李连鹏；参会老师：王扬、李越、李芳、陈天宇、古一、黄浩轩。", "articleId": fid("第八届换届")},
        {"period": "2025", "title": "2025 年换届大会：新一届骨干接力", "body": "2025 年换届大会延续年度交接传统，社团围绕骨干接力、部门协作、技术训练和赛事备赛完成组织衔接。", "people": "新一届骨干完成交接，继续推进项目实践、课程活动和赛事准备。", "articleId": fid("2025 年社团换届")},
        {"period": "2026", "title": "换届大会：谢家跃接任", "body": "2026 年换届大会在 WLA-405 举办，杨文俊总结上一年工作，李越老师宣读名单，谢家跃规划技术培训、项目研发、赛事备赛与新人培养。", "people": "上届社长：杨文俊；社长：谢家跃；指导老师：王扬、李越。", "articleId": fid("2026换届")},
    ]

    featured = [fid("成立一月"), fid("2017系列"), fid("双冠"), fid("2020中国机器人大赛"), fid("中国国际海洋水下机器人大赛"), fid("Vibe Coding")]
    return milestones, awards, teams, [item for item in featured if item]


def build_archive(source_dir: Path, team_dir: Path) -> dict:
    output_dir = team_dir / "assets" / "articles"
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_file in output_dir.iterdir():
        if old_file.is_file() and re.fullmatch(r"a\d{8}-\d{2}(?:-\d{2}|-founder)\.(?:jpg|png|gif|webp|img)", old_file.name):
            old_file.unlink()

    articles: list[dict] = []
    seen_urls: set[str] = set()
    duplicate_sources: list[str] = []
    files = sorted(source_dir.glob("*.mhtml"))

    for path in files:
        msg = read_message(path)
        url = msg.get("Snapshot-Content-Location", "")
        if url in seen_urls:
            duplicate_sources.append(path.name)
            continue
        seen_urls.add(url)

        html_text = decode_html(msg)
        title = extract_title(html_text, decode_subject(msg) or path.stem)
        date_iso, date_label = parse_publish_date(html_text)
        if not date_iso:
            date_iso = "9999-12-31"
            date_label = msg.get("Date", "")

        parser = WeChatContentParser()
        parser.feed(html_text)
        lines = clean_lines("\n".join(parser.text), title)
        category = classify(title)
        article_id = f"a{date_iso.replace('-', '')}-{len(articles) + 1:02d}"
        display_title = formal_title(title)
        images = choose_images(article_id, display_title, parser.images, collect_image_parts(msg), output_dir)
        if display_title == "2022 年社团第八届换届大会" and len(images) > 1:
            images = [images[1], images[0], *images[2:]]
        status = status_for(title, lines)
        manual_copy = manual_article_copy(title, date_label)
        excerpt = manual_copy["excerpt"] if manual_copy else excerpt_from(lines)
        if status == "需人工复核":
            excerpt = "G_Robot 在这一节点中经历了参赛行程、赛前调试、设备准备和比赛现场适应。"

        articles.append(
            {
                "id": article_id,
                "title": display_title,
                "displayTitle": display_title,
                "_sourceTitle": title,
                "date": date_iso,
                "dateLabel": date_label,
                "year": int(date_iso[:4]) if date_iso[:4].isdigit() else None,
                "category": category,
                "categoryLabel": CATEGORY_LABELS[category],
                "excerpt": excerpt,
                "highlights": manual_copy["highlights"] if manual_copy else highlights_from(lines, category),
                "image": images[0]["src"] if images else "",
                "images": images,
                "textLineCount": len(lines),
                "imageCountInSource": len(parser.images),
                "detail": manual_copy["detail"] if manual_copy else formal_detail(title, date_label, category, lines, status),
            }
        )

    articles.sort(key=lambda article: article["date"])
    for index, article in enumerate(articles, 1):
        article["order"] = index

    assign_founder_team_image(articles, team_dir)
    milestones, awards, teams, featured_ids = build_manual_sections(articles)
    for article in articles:
        article.pop("_sourceTitle", None)
    years = [article["year"] for article in articles if article["year"]]
    payload = {
        "generatedAt": dt.date.today().isoformat(),
        "stats": {
            "recordSources": len(files),
            "uniqueArticles": len(articles),
            "duplicateFiles": len(duplicate_sources),
            "selectedImages": sum(len(article["images"]) for article in articles),
            "firstYear": min(years) if years else "",
            "lastYear": max(years) if years else "",
        },
        "categoryLabels": CATEGORY_LABELS,
        "featuredIds": featured_ids,
        "memorialImageIds": sorted(MEMORIAL_IMAGE_IDS),
        "milestones": milestones,
        "awards": awards,
        "teamTimeline": teams,
        "articles": articles,
    }
    return polish_payload(payload)


def main() -> None:
    script_path = Path(__file__).resolve()
    workspace_root = script_path.parents[3]
    team_dir = script_path.parents[1]

    parser = argparse.ArgumentParser(description="Generate the G_Robot team archive data from local WeChat MHTML files.")
    parser.add_argument("--source", type=Path, default=workspace_root / "所有参考资料" / "社团资料" / "公众号网页资料")
    parser.add_argument("--team-dir", type=Path, default=team_dir)
    args = parser.parse_args()

    if not args.source.exists():
        raise SystemExit(f"Source directory not found: {args.source}")

    payload = build_archive(args.source, args.team_dir)
    data_file = args.team_dir / "archive-data.js"
    data_file.write_text("window.teamArchive = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")

    print(f"Wrote {data_file}")
    print(f"Articles: {payload['stats']['uniqueArticles']}")
    print(f"Selected images: {payload['stats']['selectedImages']}")
    print(f"Merged duplicates: {payload['stats']['duplicateFiles']}")


if __name__ == "__main__":
    main()
