#!/usr/bin/env python3
"""知识图谱构建器：从 wikilinks 提取关系，生成 graph.json + 交互式 graph.html。

用法: python3 build_graph.py [--root /path/to/wiki]
输出: _meta/graph.json + _meta/graph.html
"""
import os, re, sys, json
from collections import defaultdict

WIKI = os.environ.get("WIKI_ROOT", "/var/minis/mounts/wiki")
if "--root" in sys.argv:
    idx = sys.argv.index("--root")
    if idx + 1 < len(sys.argv):
        WIKI = sys.argv[idx + 1]

DIRS = ["entities", "concepts", "comparisons", "queries", "synthesis"]
TYPE_COLORS = {
    "entity": "#e74c3c",
    "concept": "#3498db",
    "comparison": "#2ecc71",
    "query": "#f39c12",
    "source": "#95a5a6",
    "synthesis": "#9b59b6",
}
TYPE_LABELS = {
    "entity": "实体",
    "concept": "概念",
    "comparison": "对比",
    "query": "查询",
    "source": "源摘要",
    "synthesis": "合成",
}


def strip_fm(c):
    if c.startswith("---"):
        e = c.find("\n---", 3)
        if e != -1:
            return c[e+4:]
    return c


def extract_links(body):
    raw = re.findall(r'\[\[([^\]]+)\]\]', body)
    return [l.split("|")[0].split("#")[0].strip()
            for l in raw if l.split("|")[0].split("#")[0].strip()]


def extract_summary(content):
    body = strip_fm(content)
    for line in body.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("---"):
            return line[:100]
    return ""


def main():
    print("构建知识图谱...")

    # 1. 加载所有页面
    pages = {}  # name -> {dir, type, summary, outlinks}
    for d in DIRS:
        dp = os.path.join(WIKI, d)
        if not os.path.isdir(dp):
            continue
        for f in os.listdir(dp):
            if not f.endswith(".md"):
                continue
            name = f[:-3]
            path = os.path.join(dp, f)
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            body = strip_fm(content)
            links = extract_links(body)
            summary = extract_summary(content)
            pages[name] = {"dir": d, "type": d.rstrip("s"),
                          "summary": summary, "outlinks": links}

    # 2. 计算入站链接数
    inbound = defaultdict(int)
    for name, data in pages.items():
        for link in data["outlinks"]:
            if link in pages:
                inbound[link] += 1

    # 3. 构建图数据
    nodes = []
    edges_set = set()
    for name, data in pages.items():
        in_count = inbound.get(name, 0)
        out_count = len([l for l in data["outlinks"] if l in pages])
        # 跳过没有任何连接的孤立节点（减少噪音）
        if in_count == 0 and out_count == 0:
            continue
        
        size = max(8, min(40, 8 + in_count * 3))
        color = TYPE_COLORS.get(data["type"], "#95a5a6")
        label = name[:25] + "…" if len(name) > 25 else name
        tooltip = f"<b>{name}</b><br>类型: {TYPE_LABELS.get(data['type'], data['type'])}<br>入链: {in_count} | 出链: {out_count}<br>{data['summary'][:80]}"
        
        nodes.append({
            "id": name,
            "label": label,
            "group": data["type"],
            "size": size,
            "title": tooltip,
            "color": {"background": color, "border": color},
            "font": {"size": max(10, min(16, 10 + in_count))},
        })
        
        for link in data["outlinks"]:
            if link in pages:
                edge_key = tuple(sorted([name, link]))
                if edge_key not in edges_set:
                    edges_set.add(edge_key)

    edges = [{"from": a, "to": b} for a, b in edges_set]

    # 4. 统计
    print(f"  节点: {len(nodes)}")
    print(f"  边:   {len(edges)}")
    
    # 按类型统计
    type_counts = defaultdict(int)
    for n in nodes:
        type_counts[n["group"]] += 1
    for t, c in sorted(type_counts.items()):
        print(f"    {TYPE_LABELS.get(t, t)}: {c}")

    # 5. 保存 graph.json
    graph_dir = os.path.join(WIKI, "_meta")
    os.makedirs(graph_dir, exist_ok=True)
    
    graph_data = {"nodes": nodes, "edges": edges,
                  "stats": {"total_nodes": len(nodes), "total_edges": len(edges)}}
    with open(os.path.join(graph_dir, "graph.json"), "w", encoding="utf-8") as f:
        json.dump(graph_data, f, ensure_ascii=False)
    print(f"\n  已保存: _meta/graph.json")

    # 6. 生成 graph.html（独立可交互页面）
    nodes_json = json.dumps(nodes, ensure_ascii=False)
    edges_json = json.dumps(edges, ensure_ascii=False)
    
    # 生成类型图例
    legend_items = ""
    for t, color in TYPE_COLORS.items():
        count = type_counts.get(t, 0)
        if count > 0:
            legend_items += f'<span class="legend-item"><span class="dot" style="background:{color}"></span>{TYPE_LABELS.get(t,t)} ({count})</span>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>知识图谱</title>
<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #1a1a2e; color: #eee; }}
#header {{ padding: 12px 20px; background: #16213e; display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }}
#header h1 {{ font-size: 18px; color: #e94560; }}
.stats {{ font-size: 13px; color: #aaa; }}
.legend {{ display: flex; gap: 12px; flex-wrap: wrap; }}
.legend-item {{ display: flex; align-items: center; gap: 4px; font-size: 12px; color: #ccc; cursor: pointer; }}
.legend-item:hover {{ color: #fff; }}
.dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
#controls {{ padding: 8px 20px; background: #0f3460; display: flex; gap: 10px; align-items: center; }}
#controls input {{ padding: 6px 12px; border: 1px solid #333; border-radius: 4px; background: #1a1a2e; color: #eee; width: 250px; }}
#controls button {{ padding: 6px 14px; border: none; border-radius: 4px; background: #e94560; color: #fff; cursor: pointer; font-size: 13px; }}
#controls button:hover {{ background: #c73e54; }}
#controls select {{ padding: 6px; border: 1px solid #333; border-radius: 4px; background: #1a1a2e; color: #eee; }}
#graph {{ width: 100%; height: calc(100vh - 100px); }}
#info {{ position: fixed; bottom: 20px; right: 20px; background: #16213e; padding: 12px 16px; border-radius: 8px; font-size: 13px; max-width: 300px; display: none; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }}
#info h3 {{ color: #e94560; margin-bottom: 6px; }}
</style>
</head>
<body>
<div id="header">
  <h1>🧠 知识图谱</h1>
  <span class="stats">{len(nodes)} 节点 · {len(edges)} 连接</span>
  <div class="legend">{legend_items}</div>
</div>
<div id="controls">
  <input type="text" id="search" placeholder="搜索节点..." />
  <select id="filter">
    <option value="">全部类型</option>
    {"".join(f'<option value="{t}">{TYPE_LABELS.get(t,t)}</option>' for t in TYPE_COLORS if type_counts.get(t,0)>0)}
  </select>
  <button onclick="resetView()">重置视图</button>
  <button onclick="togglePhysics()">物理引擎</button>
</div>
<div id="graph"></div>
<div id="info"><h3 id="info-title"></h3><p id="info-body"></p></div>

<script>
var allNodes = {nodes_json};
var allEdges = {edges_json};

var nodes = new vis.DataSet(allNodes);
var edges = new vis.DataSet(allEdges);

var container = document.getElementById('graph');
var data = {{ nodes: nodes, edges: edges }};
var options = {{
  physics: {{
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {{ gravitationalConstant: -30, springLength: 120, springConstant: 0.04 }},
    stabilization: {{ iterations: 100 }}
  }},
  edges: {{
    color: {{ color: '#444', highlight: '#e94560', hover: '#888' }},
    width: 0.8,
    smooth: {{ type: 'continuous' }}
  }},
  nodes: {{
    shape: 'dot',
    borderWidth: 1,
    shadow: false,
    font: {{ color: '#eee', face: 'sans-serif' }}
  }},
  interaction: {{
    hover: true,
    tooltipDelay: 100,
    zoomView: true,
    dragView: true
  }},
  layout: {{ improvedLayout: true }}
}};

var network = new vis.Network(container, data, options);

// 点击节点显示详情
network.on('click', function(params) {{
  if (params.nodes.length > 0) {{
    var nodeId = params.nodes[0];
    var node = nodes.get(nodeId);
    document.getElementById('info-title').textContent = node.id;
    document.getElementById('info-body').innerHTML = node.title.replace(/\\n/g, '<br>').replace(/<[^>]*>/g, '');
    document.getElementById('info').style.display = 'block';
  }} else {{
    document.getElementById('info').style.display = 'none';
  }}
}});

// 搜索
document.getElementById('search').addEventListener('input', function(e) {{
  var q = e.target.value.toLowerCase();
  if (!q) {{ nodes.update(allNodes.map(n => ({{...n, hidden: false}}))); return; }}
  nodes.update(allNodes.map(n => ({{...n, hidden: !n.id.toLowerCase().includes(q)}})));
}});

// 过滤
document.getElementById('filter').addEventListener('change', function(e) {{
  var t = e.target.value;
  if (!t) {{ nodes.update(allNodes.map(n => ({{...n, hidden: false}}))); return; }}
  nodes.update(allNodes.map(n => ({{...n, hidden: n.group !== t}})));
}});

// 重置视图
function resetView() {{
  network.fit({{ animation: true }});
  nodes.update(allNodes.map(n => ({{...n, hidden: false}})));
  document.getElementById('search').value = '';
  document.getElementById('filter').value = '';
}}

// 物理引擎切换
var physicsOn = true;
function togglePhysics() {{
  physicsOn = !physicsOn;
  network.setOptions({{ physics: {{ enabled: physicsOn }} }});
}}
</script>
</body>
</html>"""

    html_path = os.path.join(graph_dir, "graph.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  已保存: _meta/graph.html")
    print(f"\n完成! 在浏览器中打开 graph.html 查看图谱。")


if __name__ == "__main__":
    main()
