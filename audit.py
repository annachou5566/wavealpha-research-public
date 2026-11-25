"""Bounded public historical-data regression fixture."""
import argparse,calendar,csv,datetime as dt,hashlib,io,json,math,pathlib,re,urllib.request,zipfile
ROOT='https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/'
def require(ok,msg):
    if not ok: raise ValueError(msg)
def month_bounds(month):
    require(re.fullmatch(r'20(20|21|22|23|24|25)-(0[1-9]|1[0-2])',month) is not None,'Only TRAIN 2020-2025 months allowed')
    y,m=map(int,month.split('-'))
    return int(dt.datetime(y,m,1,tzinfo=dt.timezone.utc).timestamp()*1000),calendar.monthrange(y,m)[1]*1440
def get(url,cap):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'historical-data-regression/1.0'}),timeout=25) as r:
        require(r.geturl().startswith(ROOT),'Unexpected redirect')
        b=r.read(cap+1)
    require(len(b)<=cap,'Response exceeds byte cap')
    return b
def audit(month,folder,download=False):
    start,n=month_bounds(month)
    fn=f'BTCUSDT-1m-{month}.zip'
    folder=pathlib.Path(folder)
    p=folder/fn
    cp=folder/(fn+'.CHECKSUM')
    if not cp.exists() and (folder/(fn+'.CHECKSUM.bin')).exists(): cp=folder/(fn+'.CHECKSUM.bin')
    if download and (not p.exists() or not cp.exists()):
        folder.mkdir(parents=True,exist_ok=True)
        b=get(ROOT+fn,16*1024*1024); ck=get(ROOT+fn+'.CHECKSUM',4096)
    else: b=p.read_bytes(); ck=cp.read_bytes()
    match=re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?'+re.escape(fn)+r'\s*',ck.decode('ascii'))
    require(match is not None,'Unexpected checksum format or filename')
    sha=hashlib.sha256(b).hexdigest()
    require(sha==match[1].lower(),'SHA256 mismatch')
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        require(z.namelist()==[fn[:-4]+'.csv'],'Unexpected archive entries')
        require(z.getinfo(z.namelist()[0]).file_size<=40*1024*1024,'Uncompressed file too large')
        require(z.testzip() is None,'CRC failure')
        with z.open(z.namelist()[0]) as f:
            rows=csv.reader(io.TextIOWrapper(f,encoding='utf-8-sig')); count=0
            for j,row in enumerate(rows):
                if j==0 and row and row[0] in ('open_time','openTime'): continue
                require(len(row)==12,'Unexpected schema')
                t=int(row[0]); o,h,l,c,v=map(float,row[1:6])
                require(t==start+count*60000,'Gap, duplicate or out-of-order timestamp')
                require(int(row[6])==t+59999,'Close timestamp mismatch')
                require(all(math.isfinite(x) for x in (o,h,l,c,v)) and 0<l<=min(o,c)<=max(o,c)<=h and v>=0,'OHLCV invalid')
                count+=1
    require(count==n,'Incomplete month')
    if download: p.write_bytes(b); cp.write_bytes(ck)
    return {'month':month,'rows':count,'sha256':sha,'crc':'PASS','continuity':'PASS','ohlcv':'PASS'}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--month',action='append',required=True)
    ap.add_argument('--folder',default='data')
    ap.add_argument('--download',action='store_true')
    a=ap.parse_args()
    require(len(set(a.month))==len(a.month),'Duplicate month')
    require(not a.download or len(a.month)==1,'Single network fixture per invocation')
    for m in a.month: print(json.dumps(audit(m,a.folder,a.download)),flush=True)
if __name__=='__main__': main()
