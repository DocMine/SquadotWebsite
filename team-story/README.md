# G_Robot Team Story Archive

This subsite is built from local WeChat article snapshots stored under:

`所有参考资料/社团资料/公众号网页资料`

## Structure

- `index.html` - history overview with yearly competition milestones and award details.
- `teams.html` - organization and team-generation timeline extracted from transition/recruitment articles.
- `submit.html` - source list, extraction status and contribution notes.
- `archive-data.js` - generated article data used by all pages.
- `assets/articles/` - selected images extracted from MHTML files.
- `tools/extract_archive.py` - repeatable generator for data and selected images.

## Regenerate Data

Run from the project root:

```powershell
python SquadotWebsite\team-story\tools\extract_archive.py
```

The generator:

- Parses MHTML files with Python's email parser.
- Reads WeChat title, publish time, original URL, body text and embedded images.
- Removes WeChat UI noise such as reader controls, reward panels and comment panels.
- Deduplicates repeated WeChat links.
- Selects up to two representative article images, excluding avatars, tiny decorations and duplicate images.
- Writes `archive-data.js` and `assets/articles/aYYYYMMDD-*-*.*`.

## Current Extraction Notes

- `G_Robot在中国国际海洋水下机器人大赛中载誉而归！_2026.mhtml` is a duplicate of the same WeChat link without the suffix and is not counted as a separate article.
- `G_Robot社团2025换届大会.mhtml` has title/date/image data, but its saved `js_content` is mostly WeChat shell text, so it is marked `正文待补`.
- `G_Robot社团参加2025中国机器人大赛（专项赛）纪实！.mhtml` contains readable fragments, but paragraph extraction is broken by the saved page structure, so it is marked `需人工复核`.
