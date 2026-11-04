import importlib.util, os, sys
R = r"C:\Users\SSAFY\Desktop\oss-analysis\repos\gpt-researcher\gpt_researcher"
# 1) url_security (stdlib only) loaded from the real file
spec = importlib.util.spec_from_file_location("url_security", R + r"\utils\url_security.py")
us = importlib.util.module_from_spec(spec); sys.modules["url_security"] = us; spec.loader.exec_module(us)
def t(u, **kw):
    try: us.validate_url(u, **kw); return "OK"
    except us.UnsafeURLError as e: return "REJECT: " + str(e)[:70]
for u in ["file:///etc/passwd", "ftp://example.com/x", "/etc/passwd", "http://", "http://127.0.0.1/", "http://10.0.0.1/",
          "http://169.254.169.254/latest/meta-data", "http://[::1]/", "http://0.0.0.0/", "http://100.100.100.200/",
          "http://100.64.0.1/", "http://224.0.0.1/", "http://192.0.2.1/", "http://93.184.216.34/", "HTTP://93.184.216.34/", "  http://93.184.216.34/ ", "http://[::ffff:127.0.0.1]/", "http://no-such-host.invalid/"]:
    print(repr(u), t(u))
os.environ["ALLOW_PRIVATE_URLS"] = " TRUE "
print("allow env ' TRUE ':", t("http://127.0.0.1/"), t("file:///x"), t("http://no-such-host.invalid/"))
os.environ["ALLOW_PRIVATE_URLS"] = "false"
print("allow env 'false':", t("http://127.0.0.1/"))
os.environ["ALLOW_PRIVATE_URLS"] = "y"
print("allow env 'y':", t("http://127.0.0.1/"))
# 2) text checks: exec lines 31-106 of scraper.py verbatim
lines = open(R + r"\scraper\scraper.py", encoding="utf-8").read().splitlines()
ns = {}
exec("\n".join(lines[30:106]), ns)
b, w, p = ns["_looks_like_block_page"], ns["_looks_like_word_list"], ns["_looks_like_unextracted_pdf"]
print("block at 4990:", b("x"*4960 + "Please verify you are a human"), " beyond 5000:", b("x"*5000 + "please verify you are a human"), " upper:", b("ATTENTION REQUIRED! | CLOUDFLARE"), " curly apostrophe:", b("Making sure you\u2019re not a bot"))
print("wordlist len 199999:", w("a"*199_999), " 200000 no endings:", w("a"*200_000))
print("wordlist 200000 with 40 '.':", w("a"*199_960 + "."*40), " with 39:", w("a"*199_961 + "."*39), " with 41:", w("a"*199_959+"."*41))
print("cjk 200000 w/ 。 x100:", w("字"*199_900 + "。"*100))
print("pdf %PDF-:", p("%PDF-1.4 abc"), " one marker:", p("see the trailer"), " two:", p("xref ... trailer"), " case:", p("ENDOBJ ENDSTREAM"), " leading space %PDF:", p(" %PDF-1.4"))
