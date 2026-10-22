import textwrap
R = r"C:\Users\SSAFY\Desktop\oss-analysis\repos\gpt-researcher\gpt_researcher"
u = open(R + r"\scraper\utils.py", encoding="utf-8").read().splitlines()
ns = {}
exec("import hashlib, logging\nfrom urllib.parse import parse_qs, urlparse\n" + "\n".join(u[100:120]), ns)   # get_image_hash, utils.py:101-120
gh = ns["get_image_hash"]
print(gh("http://x.com/a/b.png?w=1") == gh("http://y.com/q/b.png?w=2"), "same filename -> same hash")
print(gh("http://x.com/i?url=http%3A%2F%2Fz%2Fq.png") == gh("http://x.com/i?url=other"), "url param differs -> differs")
print(gh("http://x.com/dir/") == gh("http://y.com/"), "empty filename collapse")
b = open(R + r"\skills\browser.py", encoding="utf-8").read().splitlines()
ns2 = {"get_image_hash": gh}; exec(textwrap.dedent("\n".join(b[85:115])), ns2)      # select_top_images, browser.py:86-115
class Res:
    def __init__(s, cur): s.cur = cur
    def get_research_images(s, top_k=10): return s.cur[:top_k]
class Self: researcher = Res([f"http://old/{i}.png" for i in range(11)])
imgs = [{"url": x, "score": sc} for x, sc in [("http://s/a.png",1),("http://s/b.png",4),("http://t/b.png",3),("http://old/10.png",5),("http://s/c.png",0),("http://s/d.png",2),("http://s/e.png",2),("http://old/3.png",9)]]
print(ns2["select_top_images"](Self, imgs, k=4))
print(ns2["select_top_images"](Self, imgs, k=10))
