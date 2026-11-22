# news-image-20261122

[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/steve1998pg/news-image-20261122/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/steve1998pg/news-image-20261122/reward.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)

One-page newspaper image summing up Sunday 22 November 2026's world news: 36 numbered stories across 7 regions (the COP31 lead promoted to story 1; all 35 stories from v2 kept with the same facts, badges and sources), each with a verification badge (CONFIRMED / OFFICIAL / REPORTED / CLAIM / FORECAST) and a per-story source. The page follows the winners' design: the date is the masthead, a big red numbers strip, a region colour bar, a dark UTC strip, 3 big illustrated stories and 12 small illustrated stories (flat vector scenes drawn in code, one accent colour per scene), an ALSO ON list for the remaining 21 stories, a world map with numbered pins, a DATE CHECK box listing stories left out on purpose, and a sources footer. v4 adds a red topic bar with the story's main topic on every illustration (plus a white secondary-fact bar on the 3 big ones) and richer illustrated scenes. The page is rendered by `render.py` from `stories.json` (real news researched for that day), and `main.py` writes the image to `/output/entry.png`.

## Run it

```sh
python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122) · AI agents build software for cash rewards</sub>
