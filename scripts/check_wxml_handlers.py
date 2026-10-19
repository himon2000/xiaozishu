"""检查 WXML 中绑定的事件处理函数是否在对应 JS 中定义。"""
import os
import re
import sys

FRONT = r"C:/QQVV/小紫薯-全/xunlongge/frontend"

EVENT_RE = re.compile(r'(?:bind|catch)([a-zA-Z]+)="([A-Za-z_$][\w$]*)"')
# 也匹配 bind:tap="xxx" 形式
EVENT_COLON_RE = re.compile(r'(?:bind|catch):([a-zA-Z]+)="([A-Za-z_$][\w$]*)"')
# 同时支持 ES6 简写「onTap() {}」与旧式「onTap: function () {}」
METHOD_RE = re.compile(
    r'^\s{2,}(?:async\s+)?([A-Za-z_$][\w$]*)\s*[(:]',
    re.M,
)

problems = []
checked = 0

for root, dirs, files in os.walk(FRONT):
    if "node_modules" in root or "__pycache__" in root:
        continue
    for f in files:
        if not f.endswith(".wxml"):
            continue
        wxml = os.path.join(root, f)
        base = wxml[:-5]
        js = base + ".js"
        if not os.path.exists(js):
            problems.append((wxml, "*", "缺少同名 JS"))
            continue
        with open(wxml, encoding="utf-8") as fp:
            tpl = fp.read()
        with open(js, encoding="utf-8") as fp:
            code = fp.read()
        handlers = set(m[1] for m in EVENT_RE.findall(tpl))
        handlers |= set(m[1] for m in EVENT_COLON_RE.findall(tpl))
        methods = set(METHOD_RE.findall(code))
        # 子组件 Component 也走同样正则；props 里的方法名可能来自 behaviors
        for h in sorted(handlers):
            checked += 1
            if h not in methods:
                problems.append((wxml, h, "JS 未定义"))

print(f"共检查 {checked} 个事件绑定")
if problems:
    print(f"发现 {len(problems)} 处问题：")
    for p in problems:
        print("  ", p[0].replace(FRONT, "frontend"), "→", p[1], p[2])
    sys.exit(1)
else:
    print("全部事件处理函数均已定义 ✅")
