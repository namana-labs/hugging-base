import re,html,sys
s=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
s=re.sub(r'<script.*?</script>|<style.*?</style>|<nav.*?</nav>|<footer.*?</footer>','',s,flags=re.S)
t=html.unescape(re.sub(r'<[^>]+>','\n',s))
lines=[l.strip() for l in t.split('\n') if len(l.strip())>40]
pat=sys.argv[2] if len(sys.argv)>2 else '.'
for l in lines:
    if re.search(pat,l,re.I): print('-',l[:500])
