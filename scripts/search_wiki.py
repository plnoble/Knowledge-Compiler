#!/usr/bin/env python3
"""BM25 全文检索引擎：为大型知识库提供相关性排序搜索。

用法: python3 search_wiki.py "查询词" [--root /path/to/wiki] [--limit N]
"""
import os, re, sys, math, json, pickle
from collections import defaultdict

WIKI = os.environ.get("WIKI_ROOT", "/var/minis/mounts/wiki")
if "--root" in sys.argv:
    idx = sys.argv.index("--root")
    if idx + 1 < len(sys.argv):
        WIKI = sys.argv[idx + 1]

LIMIT = 10
if "--limit" in sys.argv:
    idx = sys.argv.index("--limit")
    if idx + 1 < len(sys.argv):
        LIMIT = int(sys.argv[idx + 1])

DIRS = ["entities", "concepts", "comparisons", "queries", "synthesis"]
K1 = 1.5  # BM25 参数
B = 0.75  # BM25 参数
CACHE_FILE = os.path.join(WIKI, "_meta", "search_index.pkl")


def tokenize(text):
    """分词：英文按空格/连字符，中文按字符。"""
    # 移除 frontmatter
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    # 移除 wikilink 语法
    text = re.sub(r'\[\[([^\]|]+\|)?([^\]]+)\]\]', r'\2', text)
    # 移除 markdown 标记
    text = re.sub(r'[#*`>\[\](){}]', ' ', text)
    text = text.lower()
    
    tokens = []
    # 英文分词
    for word in re.findall(r'[a-z][a-z0-9_-]*', text):
        if len(word) > 1:
            tokens.append(word)
    # 中文分词（按字符 bigram）
    chinese = re.findall(r'[\u4e00-\u9fff]+', text)
    for seg in chinese:
        for i in range(len(seg) - 1):
            tokens.append(seg[i:i+2])
        if len(seg) >= 2:
            tokens.append(seg)
    return tokens


class BM25Index:
    def __init__(self):
        self.docs = {}          # doc_id -> {tokens, length, path, type, title}
        self.inverted = defaultdict(list)  # term -> [(doc_id, tf)]
        self.avg_dl = 0
        self.N = 0
    
    def add(self, doc_id, tokens, path, doc_type, title):
        self.docs[doc_id] = {
            "tokens": tokens, "length": len(tokens),
            "path": path, "type": doc_type, "title": title
        }
    
    def build(self):
        """构建倒排索引。"""
        self.N = len(self.docs)
        if self.N == 0:
            return
        
        total_dl = sum(d["length"] for d in self.docs.values())
        self.avg_dl = total_dl / self.N
        
        for doc_id, data in self.docs.items():
            tf = defaultdict(int)
            for token in data["tokens"]:
                tf[token] += 1
            for term, freq in tf.items():
                self.inverted[term].append((doc_id, freq))
    
    def search(self, query, limit=10):
        """BM25 搜索。"""
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        
        scores = defaultdict(float)
        
        for term in query_tokens:
            if term not in self.inverted:
                continue
            
            # IDF
            df = len(self.inverted[term])
            idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1)
            
            for doc_id, tf in self.inverted[term]:
                dl = self.docs[doc_id]["length"]
                # BM25 score
                score = idf * (tf * (K1 + 1)) / (tf + K1 * (1 - B + B * dl / self.avg_dl))
                scores[doc_id] += score
        
        # 排序
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        results = []
        for doc_id, score in ranked[:limit]:
            doc = self.docs[doc_id]
            results.append({
                "id": doc_id, "score": round(score, 3),
                "path": doc["path"], "type": doc["type"],
                "title": doc["title"],
            })
        return results


def build_index():
    """构建索引。"""
    index = BM25Index()
    
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
            
            tokens = tokenize(content)
            title = name
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip('"\'')
                    break
            
            index.add(name, tokens, path, d.rstrip("s"), title)
    
    index.build()
    return index


def save_cache(index, path):
    """保存索引到文件（pickle 格式，快速序列化）。"""
    import pickle
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 只保存必要数据
    slim_docs = {k: {"length": v["length"], "path": v["path"],
                     "type": v["type"], "title": v["title"]}
                 for k, v in index.docs.items()}
    data = {"N": index.N, "avg_dl": index.avg_dl,
            "docs": slim_docs, "inverted": dict(index.inverted)}
    with open(path, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_cache(path):
    """从文件加载索引。"""
    import pickle
    with open(path, "rb") as f:
        data = pickle.load(f)
    index = BM25Index()
    index.N = data["N"]
    index.avg_dl = data["avg_dl"]
    index.docs = {k: {"tokens": [], "length": v["length"], "path": v["path"],
                       "type": v["type"], "title": v["title"]}
                  for k, v in data["docs"].items()}
    index.inverted = defaultdict(list, data["inverted"])
    return index


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        print("用法: python3 search_wiki.py \"查询词\" [--limit N]")
        print("\n示例:")
        print('  python3 search_wiki.py "资产配置"')
        print('  python3 search_wiki.py "ETF 标普500"')
        print('  python3 search_wiki.py "AI agent" --limit 20')
        sys.exit(0)
    
    query = sys.argv[1]
    
    # 尝试加载缓存索引
    cache_path = os.path.join(WIKI, "_meta", "search-index.json")
    rebuild = "--rebuild" in sys.argv
    index = None
    
    if not rebuild and os.path.exists(cache_path):
        index = load_cache(cache_path)
    
    if index is None:
        print("构建索引...")
        index = build_index()
        save_cache(index, cache_path)
    else:
        print("(使用缓存索引 --rebuild 强制重建)")
    print(f"  {index.N} 个页面, {len(index.inverted)} 个词项")
    
    print(f"\n搜索: \"{query}\"")
    results = index.search(query, LIMIT)
    
    if not results:
        print("\n未找到相关结果。")
        return
    
    print(f"\n找到 {len(results)} 个结果:\n")
    for i, r in enumerate(results, 1):
        type_emoji = {"entity": "🏷️", "concept": "💡", "comparison": "⚖️",
                     "query": "🔍", "source": "📄", "synthesis": "🔬"}.get(r["type"], "📝")
        print(f"  {i}. {type_emoji} [[{r['id']}]] — 分数: {r['score']}")
        print(f"     {r['title']}")
        print(f"     {r['path']}")
        print()


if __name__ == "__main__":
    main()
