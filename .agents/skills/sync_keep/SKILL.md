---
name: Keep Syncer
description: 縲桑eep繧貞酔譛溘＠縺ｦ縲阪′繝医Μ繧ｬ繝ｼ縺ｨ縺ｪ繧翫；oogle Keep 縺ｮ ob-* 繝ｩ繝吶Ν縺ｮ繝｡繝｢繧・Daily/Inbox/ 縺ｫ譖ｸ縺榊・縺吶ょｮ御ｺ・ｾ後↓ process_daily 繧ｹ繧ｭ繝ｫ縺ｧ謨ｴ蠖｢縺ｧ縺阪ｋ縲・---

# Keep Syncer Skill

## 繝医Μ繧ｬ繝ｼ譚｡莉ｶ
- **縲桑eep繧貞酔譛溘＠縺ｦ縲・*・哦oogle Keep 縺ｮ繝｡繝｢繧・Daily/Inbox/ 縺ｫ譖ｸ縺榊・縺・- **縲桑eep繧貞酔譛溘＠縺ｦ縺九ｉ謨ｴ蠖｢縺励※縲・*・壼酔譛・竊・Inbox謨ｴ蠖｢ 繧帝｣邯壼ｮ溯｡後☆繧・
---

## 繝輔か繝ｫ繝讒区・

```
.agents/scripts/
  sync_keep.py            竊・繝｡繧､繝ｳ蜷梧悄繧ｹ繧ｯ繝ｪ繝励ヨ
  sync_keep_setup.py      竊・蛻晏屓繧ｻ繝・ヨ繧｢繝・・逕ｨ・医ヨ繝ｼ繧ｯ繝ｳ蜿門ｾ暦ｼ・
Daily/Inbox/              竊・蜷梧悄邨先棡縺ｮ蜃ｺ蜉帛・
  YYYY-MM-DD-ideas.md
  YYYY-MM-DD-tasks.md
  YYYY-MM-DD-memo.md

C:\Users\111r9\.keep_token  竊・隱崎ｨｼ繝医・繧ｯ繝ｳ・・ault螟悶・git邂｡逅・､厄ｼ・```

---

## 螳溯｡梧焔鬆・
### 1. 繧ｻ繝・ヨ繧｢繝・・遒ｺ隱・
`C:\Users\111r9\.keep_token` 縺悟ｭ伜惠縺吶ｋ縺狗｢ｺ隱阪☆繧九・
蟄伜惠縺励↑縺・ｴ蜷医・莉･荳九ｒ莨昴∴縺ｦ邨ゆｺ・ｼ・> 縲後そ繝・ヨ繧｢繝・・縺悟ｿ・ｦ√〒縺吶ゆｻ･荳九・謇矩・ｒ螳溯｡後＠縺ｦ縺上□縺輔＞・・> 1. pip install gkeepapi
> 2. python ".agents/scripts/sync_keep_setup.py"縲・
### 2. 繧ｹ繧ｯ繝ｪ繝励ヨ螳溯｡・
莉･荳九・繧ｳ繝槭Φ繝峨ｒ Bash 繝・・繝ｫ縺ｧ螳溯｡後☆繧具ｼ・
```bash
python ".agents/scripts/sync_keep.py"
```

菴懈･ｭ繝・ぅ繝ｬ繧ｯ繝医Μ・啻c:/Users/111r9/OneDrive/繝峨く繝･繝｡繝ｳ繝・Obsidian Vault/obsidian/`

### 3. 螳溯｡檎ｵ先棡縺ｮ遒ｺ隱・
- `蜷梧悄螳御ｺ・ YYYY-MM-DD-ideas.md (X莉ｶ), ...` 縺ｨ陦ｨ遉ｺ縺輔ｌ繧後・謌仙粥
- 繧ｨ繝ｩ繝ｼ縺悟・縺溷ｴ蜷医・譌･譛ｬ隱槭〒繝ｦ繝ｼ繧ｶ繝ｼ縺ｫ莨昴∴縲∝ｯｾ蜃ｦ豕輔ｒ譯亥・縺吶ｋ

**繧医￥縺ゅｋ繧ｨ繝ｩ繝ｼ縺ｨ蟇ｾ蜃ｦ・・*

| 繧ｨ繝ｩ繝ｼ | 蜴溷屏 | 蟇ｾ蜃ｦ |
|---|---|---|
| `繝医・繧ｯ繝ｳ繝輔ぃ繧､繝ｫ縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ` | 繧ｻ繝・ヨ繧｢繝・・譛ｪ螳滓命 | `sync_keep_setup.py` 繧貞ｮ溯｡・|
| `謗･邯壹↓螟ｱ謨励＠縺ｾ縺励◆` | 繝医・繧ｯ繝ｳ譛滄剞蛻・ｌ | `sync_keep_setup.py` 繧貞・螳溯｡・|
| `ModuleNotFoundError: gkeepapi` | 繝ｩ繧､繝悶Λ繝ｪ譛ｪ繧､繝ｳ繧ｹ繝医・繝ｫ | `pip install gkeepapi` 繧貞ｮ溯｡・|

### 4. 邨先棡蝣ｱ蜻・
譖ｸ縺榊・縺輔ｌ縺溘ヵ繧｡繧､繝ｫ縺ｮ莉ｶ謨ｰ繧堤ｰ｡貎斐↓蝣ｱ蜻翫☆繧九・
萓具ｼ壹後い繧､繝・い4莉ｶ縲√ち繧ｹ繧ｯ2莉ｶ縲√Γ繝｢1莉ｶ繧・Daily/Inbox/ 縺ｫ譖ｸ縺榊・縺励∪縺励◆縲・
### 5. 蠕檎ｶ壼・逅・・譯亥・

縲栗nbox繧呈紛蠖｢縺励※縲阪→邯壹￠繧九％縺ｨ縺ｧ process_daily 繧ｹ繧ｭ繝ｫ繧貞他縺ｳ蜃ｺ縺帙ｋ縺薙→繧呈｡亥・縺吶ｋ縲・
繝ｦ繝ｼ繧ｶ繝ｼ縺後梧紛蠖｢縺励※縲阪→險縺｣縺溘ｉ process_daily 繧ｹ繧ｭ繝ｫ縺ｮ謇矩・↓遘ｻ繧九・
---

## 遖∵ｭ｢莠矩・
- `Source/` 驟堺ｸ九・繝輔ぃ繧､繝ｫ縺ｯ邱ｨ髮・・遘ｻ蜍輔・蜑企勁縺吶∋縺ｦ遖∵ｭ｢
- `.keep_token` 縺ｮ荳ｭ霄ｫ繧偵メ繝｣繝・ヨ縺ｫ陦ｨ遉ｺ縺励↑縺・ｼ医そ繧ｭ繝･繝ｪ繝・ぅ・・- 縺吶∋縺ｦ縺ｮ霑皮ｭ斐・繝弱・繝医・**譌･譛ｬ隱・*縺ｧ陦後≧

---

## 蛻晏屓繧ｻ繝・ヨ繧｢繝・・謇矩・
蛻晏屓縺ｮ縺ｿ莉･荳九ｒ螳溯｡後☆繧九％縺ｨ・・
**繧ｹ繝・ャ繝・・哦oogle繧｢繝励Μ繝代せ繝ｯ繝ｼ繝峨・蜿門ｾ暦ｼ・谿ｵ髫手ｪ崎ｨｼ繧剃ｽｿ逕ｨ縺励※縺・ｋ蝣ｴ蜷茨ｼ・*

1. `https://myaccount.google.com/apppasswords` 繧帝幕縺・2. 繧｢繝励Μ蜷阪ｒ莉ｻ諢上〒蜈･蜉帙＠縺ｦ菴懈・
3. 陦ｨ遉ｺ縺輔ｌ縺・6譁・ｭ励・繝代せ繝ｯ繝ｼ繝峨ｒ繝｡繝｢縺吶ｋ

**繧ｹ繝・ャ繝・・喩keepapi 縺ｮ繧､繝ｳ繧ｹ繝医・繝ｫ**

```bash
pip install gkeepapi
```

**繧ｹ繝・ャ繝・・壹ヨ繝ｼ繧ｯ繝ｳ蜿門ｾ・*

```bash
python ".agents/scripts/sync_keep_setup.py"
```

繝｡繝ｼ繝ｫ繧｢繝峨Ξ繧ｹ縺ｨ繧｢繝励Μ繝代せ繝ｯ繝ｼ繝峨ｒ蜈･蜉帙☆繧九→ `C:\Users\111r9\.keep_token` 縺檎函謌舌＆繧後ｋ縲・
---

## 蜈ｨ菴薙ヵ繝ｭ繝ｼ

```
繧ｹ繝槭・髻ｳ螢ｰ蜈･蜉・    竊・Google Keep・・b-ideas / ob-tasks / ob-memo 繝ｩ繝吶Ν・・    竊・縲桑eep繧貞酔譛溘＠縺ｦ縲搾ｼ医％縺ｮ繧ｹ繧ｭ繝ｫ・・    竊・sync_keep.py 螳溯｡・竊・Daily/Inbox/YYYY-MM-DD-*.md 逕滓・
    竊・縲栗nbox繧呈紛蠖｢縺励※縲搾ｼ・rocess_daily 繧ｹ繧ｭ繝ｫ・・    竊・Daily/Ideas繝ｻTasks繝ｻMemo 縺ｫ霑ｽ險倥！nbox 蜑企勁
```

---

## 文字化け時の前処理（2026-03-07追記）

Keep連携後に `Daily/Inbox` の本文が文字化けしている場合は、同期直後に次を実行する。

```bash
python ".agents/scripts/repair_keep_mojibake.py" --apply
```

その後に `process_daily` を実行する。
