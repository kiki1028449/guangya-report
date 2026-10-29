"""Read-only Feishu app API sync. No user tokens or CLI installation required."""
import csv, io, json, os, time, urllib.request, urllib.parse
from urllib.error import HTTPError
from datetime import datetime, timezone, timedelta
from pathlib import Path
from parser import parse

BASE = 'https://open.feishu.cn/open-apis/'
def call(path, token=None, body=None):
    headers = {'Content-Type':'application/json; charset=utf-8'}
    if token: headers['Authorization'] = 'Bearer '+token
    req = urllib.request.Request(BASE+path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as r: result = json.load(r)
            if result.get('code',0):
                raise RuntimeError('飞书 API 错误 '+str(result.get('code'))+'：'+str(result.get('msg')))
            return result
        except HTTPError as e:
            raw = e.read().decode('utf-8', errors='replace')
            try:
                detail = json.loads(raw)
                message = f"飞书 HTTP {e.code}；接口 {path}；错误码 {detail.get('code')}；原因 {detail.get('msg')}；详情 {json.dumps(detail.get('error', {}), ensure_ascii=False)}"
            except ValueError:
                message = f'飞书 HTTP {e.code}；接口 {path}；请检查飞书服务响应'
            if e.code < 500 and e.code != 429: raise RuntimeError(message) from None
            if attempt == 2: raise RuntimeError(message) from None
            time.sleep(2**attempt)
        except Exception:
            if attempt == 2: raise
            time.sleep(2**attempt)

def main():
    auth=call('auth/v3/tenant_access_token/internal',body={'app_id':os.environ['LARK_APP_ID'],'app_secret':os.environ['LARK_APP_SECRET']})
    token=auth['tenant_access_token']
    node=call('wiki/v2/spaces/get_node?token=SL6awFIL8iwd4dkZFCdc3uK1nZf',token)['data']['node']
    book=node['obj_token']
    info=call(f'sheets/v3/spreadsheets/{book}/sheets/query',token)['data']['sheets']
    sheet=next(s for s in info if s['title']=='官方数据')
    count=sheet['grid_properties']['row_count']
    values=[]
    for start in range(1,count+1,1000):
        region=urllib.parse.quote(f"{sheet['sheet_id']}!A{start}:M{min(start+999,count)}",safe='')
        data=call(f'sheets/v2/spreadsheets/{book}/values/{region}?valueRenderOption=ToString&dateTimeRenderOption=FormattedString',token)['data']
        values.extend(data['valueRange'].get('values',[]))
    text=io.StringIO(); csv.writer(text).writerows(values)
    rows=parse(text.getvalue())
    out=Path(__file__).parent/'site/data.json'
    payload={'rows':rows,'error':None,'updated':datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')}
    temp=out.with_suffix('.tmp');temp.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8');temp.replace(out)
    print('同步成功：',len(rows),'条记录')

if __name__=='__main__': main()
