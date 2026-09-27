import re,html,sys,subprocess,json
UA=sys.argv[1]; ids=sys.argv[2:]
out={}
for i in ids:
    t=subprocess.run(['curl','-s','-A',UA,'--max-time','25',f'https://www.ercot.com/mp/data-products/data-product-details?id={i}'],capture_output=True,text=True).stdout
    t=re.sub(r'<script.*?</script>','',t,flags=re.S); t=re.sub(r'<style.*?</style>','',t,flags=re.S)
    txt=html.unescape(re.sub(r'<[^>]+>','\n',t)); lines=[l.strip() for l in txt.split('\n') if l.strip()]
    d={}
    try:
        k=lines.index('Data Product Details'); d['name']=lines[k+1]; d['desc']=lines[k+2][:160]
    except: d['name']='?'
    for f in ['Report Type ID','Generation Frequency','First Run Date','Channel','Display Duration','Retention Policy','Status','File Type','EMIL Last Updated Date']:
        if f in lines: d[f]=lines[lines.index(f)+1]
    out[i]=d
    print(i,'|',d.get('name'),'| RTID',d.get('Report Type ID'),'|',d.get('Generation Frequency'),'| first',d.get('First Run Date'),'| disp',d.get('Display Duration'),'|',d.get('Channel'),'|',d.get('Status'),'|',d.get('desc'))
json.dump(out,open('dp.json','a'))
