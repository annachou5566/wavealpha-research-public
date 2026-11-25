"""Bounded public integration test for historical mining data and a generic economic screen.
Not an executable trading bot, not a private WaveAlpha model. No raw data output.
"""
import csv,datetime as dt,hashlib,io,json,math,statistics,urllib.request,urllib.parse,zipfile
START=dt.date(2019,11,1); END=dt.date(2025,12,31); TRAIN=dt.date(2020,1,1)
def check(x,m):
    if not x: raise ValueError(m)
def get(url,cap=4_000_000):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'public-historical-regression/1.0'}),timeout=30) as r:
        data=r.read(cap+1)
    check(len(data)<=cap,'response exceeds cap');return data
def days(a,b): return [a+dt.timedelta(days=i) for i in range((b-a).days+1)]
def mining():
    data={}; hashes=[]
    # One request per calendar year, bounded historical intervals; no pagination into 2026.
    for year in range(2019,2026):
        a=max(START,dt.date(year,1,1)); b=min(END,dt.date(year,12,31))
        params=dict(assets='btc',metrics='DiffMean,HashRate',frequency='1d',start_time=str(a),end_time=str(b),page_size=1000)
        url='https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?'+urllib.parse.urlencode(params)
        raw=get(url); hashes.append(hashlib.sha256(raw).hexdigest()); obj=json.loads(raw)
        check(not obj.get('next_page_url'),'unexpected pagination')
        for r in obj['data']:
            d=dt.date.fromisoformat(r['time'][:10]); check(a<=d<=b and d not in data,'date boundary/duplicate')
            vals=(float(r['DiffMean']),float(r['HashRate']));check(all(math.isfinite(x) and x>0 for x in vals),'invalid metric');data[d]=vals
    check(set(data)==set(days(START,END)),'mining coverage gap')
    print(json.dumps(dict(source='Coin Metrics Community',rows=len(data),sha256_by_year=hashes,source_gate='coverage_only_no_vintage')),flush=True)
    return data
def prices():
    data={}; hashes=[]
    root='https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1d/'
    for year in range(2019,2026):
      for month in range(1,13):
        if year==2019 and month<11: continue
        name=f'BTCUSDT-1d-{year}-{month:02}.zip';raw=get(root+name);sha=hashlib.sha256(raw).hexdigest(); ck=get(root+name+'.CHECKSUM',4096).decode().split()
        check(ck[0].lower()==sha and ck[1].lstrip('*')==name,'checksum mismatch')
        hashes.append(sha)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
          check(z.namelist()==[name[:-4]+'.csv'] and z.testzip() is None,'zip invalid')
          for r in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]),encoding='utf-8-sig')):
            if r[0]=='open_time': continue
            d=dt.datetime.fromtimestamp(int(r[0])/1000,dt.timezone.utc).date();check(START<=d<=END and d not in data,'date boundary/duplicate')
            o,h,l,c=map(float,r[1:5]);check(0<l<=min(o,c)<=max(o,c)<=h,'OHLC invalid');data[d]=(o,c)
    check(set(data)==set(days(START,END)),'price coverage gap')
    print(json.dumps(dict(source='Binance Vision',rows=len(data),verified_months=len(hashes),sha256_manifest=hashlib.sha256(''.join(hashes).encode()).hexdigest())),flush=True)
    return data
def screen(m,p):
    # Predeclared: daily mining stress = log ratio of 7d mean hashrate to 30d mean,
    # difficulty growth over 14d. Both known only with 3-day conservative lag.
    # Compare against price-momentum alone on the SAME daily events. Nonoverlap per horizon.
    results=[]; paths=set()
    for metric in ('hashrate','difficulty'):
      for horizon in (1,3,7):
       for threshold in (0.02,0.05,0.10):
        for direction in (1,-1):
         obs=[];block=TRAIN
         for d in days(TRAIN,END-dt.timedelta(days=horizon)):
          if d<block:continue
          lag=d-dt.timedelta(days=3)
          if metric=='hashrate':
            short=statistics.mean(m[lag-dt.timedelta(days=i)][1] for i in range(7));long=statistics.mean(m[lag-dt.timedelta(days=i)][1] for i in range(30));x=math.log(short/long)
          else:x=math.log(m[lag][0]/m[lag-dt.timedelta(days=14)][0])
          if abs(x)<threshold:continue
          s=direction*(1 if x>0 else -1)
          mom=p[d-dt.timedelta(days=1)][1]/p[d-dt.timedelta(days=15)][1]-1
          ctrl=1 if mom>0 else -1
          ret=p[d+dt.timedelta(days=horizon)][0]/p[d][0]-1
          obs.append((d,s,s*ret,ctrl*ret,ret));block=d+dt.timedelta(days=horizon)
         fingerprint=hashlib.sha256(str([(str(x[0]),x[1]) for x in obs]).encode()).hexdigest();paths.add(fingerprint)
         n=len(obs);mean=lambda a:statistics.mean(a) if a else 0
         v=[x[2]*10000-32 for x in obs];control=[x[3]*10000-32 for x in obs]
         halves=[sum(x[2]*10000-32 for x in obs if (x[0].year<=2022)==first) for first in (True,False)]
         result=dict(metric=metric,horizon=horizon,threshold=threshold,direction=direction,n=n,net16=mean(v)+16 if n else 0,net24=mean(v)+8 if n else 0,net32=mean(v),matched_delta32=mean([a-b for a,b in zip(v,control)]),long_delta32=mean([(x[2]-x[4])*10000 for x in obs]),half1=halves[0],half2=halves[1],fingerprint=fingerprint)
         result['economic_gate']=n>=60 and result['net32']>0 and min(halves)>0 and result['matched_delta32']>0 and result['long_delta32']>0
         results.append(result)
    print(json.dumps(dict(screen='economic diagnostic only; daily open to open; no risk sizing or funding; publication vintage unknown',vectors=len(results),unique_paths=len(paths),passes=sum(r['economic_gate'] for r in results),results=results)),flush=True)
def mining_legacy():
    # Legacy public chart API only. No paid x402/API key. Annual fixed-date requests.
    data={}; hashes=[]
    for year in range(2019,2026):
        a=max(START,dt.date(year,1,1)); b=min(END,dt.date(year,12,31))
        cols=[]
        for metric in ('difficulty','hash-rate'):
            params=dict(start=str(a),timespan=str((b-a).days+1)+'days',sampled='false',format='json')
            raw=get('https://api.blockchain.info/charts/'+metric+'?'+urllib.parse.urlencode(params))
            hashes.append(hashlib.sha256(raw).hexdigest()); obj=json.loads(raw); vals={}
            for r in obj['values']:
                d=dt.datetime.fromtimestamp(r['x'],dt.timezone.utc).date()
                check(a<=d<=b and d not in vals,'unexpected chart date/duplicate')
                v=float(r['y']);check(math.isfinite(v) and v>0,'invalid chart metric');vals[d]=v
            check(set(vals)==set(days(a,b)),'daily chart coverage gap');cols.append(vals)
        for d in days(a,b):data[d]=(cols[0][d],cols[1][d])
    print(json.dumps(dict(source='Blockchain.com legacy public charts',rows=len(data),sha256_by_request=hashes,source_gate='coverage_only_no_vintage')),flush=True)
    return data

if __name__=='__main__':screen(mining_legacy(),prices())

