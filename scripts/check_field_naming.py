"""粗筛：WXML 中使用的驼峰字段（常见于后端返回下划线字段）"""
import os
import re

FRONT = r"C:/QQVV/小紫薯-全/xunlongge/frontend"
CAMEL_RE = re.compile(r'\b(?:item|service|team|demand|provider|order|user|res|data)\.([a-z]+[A-Z][A-Za-z]*)')

SNACK_RE = re.compile(r'(currentMembers|maxMembers|coverImage|avatarUrl|createdAt|updatedAt|'
                      r'serviceCount|orderCount|ratingCount|isMine|totalPaid|providerIncome)')

hits = {}
for root, dirs, files in os.walk(FRONT):
    if "node_modules" in root:
        continue
    for f in files:
        if not f.endswith(".wxml"):
            continue
        p = os.path.join(root, f)
        with open(p, encoding="utf-8") as fp:
            txt = fp.read()
        for m in SNACK_RE.finditer(txt):
            hits.setdefault(p, set()).add(m.group(1))

if hits:
    for p, names in hits.items():
        print(p.replace(FRONT, "frontend"), "→", sorted(names))
else:
    print("未发现与后端下划线字段冲突的驼峰引用 ✅")
