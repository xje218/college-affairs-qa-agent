# -*- coding: utf-8 -*-
"""发布到 GitHub：建仓库 -> 上传全部文件 -> 启用 Pages。令牌仅从环境变量 GH_TOKEN 读取。"""
import os, sys, json, base64, urllib.request, urllib.error
from urllib.parse import quote

TOKEN = os.environ.get("GH_TOKEN")
if not TOKEN:
    print("ERROR: 未提供 GH_TOKEN 环境变量"); sys.exit(1)

OWNER = "xje218"
REPO = "college-affairs-qa-agent"
BASE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.github.com"

def req(method, url, body=None, accept="application/vnd.github+json"):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + TOKEN)
    r.add_header("Accept", accept)
    r.add_header("User-Agent", "workbuddy-publish")
    if data is not None:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

# 1) 建仓库（已存在则忽略）
st, txt = req("POST", API + "/user/repos", {
    "name": REPO, "private": False, "auto_init": True,
    "description": "学院事务咨询智能体（单人版）· 确定性检索式问答，覆盖补考/缓考/重修/成绩复核、奖助学金、宿舍与教室报修。",
    "homepage": "https://%s.github.io/%s/" % (OWNER, REPO)
})
print("create repo:", st, ("OK" if st in (200,201,422) else txt[:200]))
if st == 422:
    print("（仓库已存在，继续上传）")

# 2) 收集要上传的文件
upload_paths = []
for root, dirs, files in os.walk(BASE):
    # 跳过无关目录
    if ".git" in root: continue
    for f in files:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, BASE).replace("\\", "/")
        # 不传脚本自身与运行产物（避免噪声；kb.json/index 等核心已包含）
        upload_paths.append(rel)

# 3) 逐文件上传（PUT，更新已有文件需带 sha）
def get_sha(rel):
    st, txt = req("GET", API + "/repos/%s/%s/contents/%s" % (OWNER, REPO, quote(rel, safe="/")))
    if st == 200:
        try: return json.loads(txt)["sha"]
        except Exception: return None
    return None

ok = 0
for rel in sorted(upload_paths):
    full = os.path.join(BASE, rel)
    with open(full, "rb") as fh:
        content = base64.b64encode(fh.read()).decode("ascii")
    body = {"message": "add " + rel, "content": content, "branch": "main"}
    sha = get_sha(rel)
    if sha:
        body["sha"] = sha
    st, txt = req("PUT", API + "/repos/%s/%s/contents/%s" % (OWNER, REPO, quote(rel, safe="/")), body)
    if st in (200, 201):
        ok += 1
    else:
        print("UPLOAD FAIL", st, rel, txt[:160])
print("uploaded files: %d / %d" % (ok, len(upload_paths)))

# 4) 启用 GitHub Pages
st, txt = req("POST", API + "/repos/%s/%s/pages" % (OWNER, REPO), {
    "source": {"branch": "main", "path": "/"}
})
print("enable pages:", st, (txt[:200] if st not in (201,200) else "OK"))

print("REPO_URL=https://github.com/%s/%s" % (OWNER, REPO))
print("PAGES_URL=https://%s.github.io/%s/" % (OWNER, REPO))
