import csv, io, json, subprocess, threading, time, webbrowser
from pathlib import Path
from datetime import date, datetime, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = Path(__file__).resolve().parent
CLI = ROOT.parents[1] / 'lark-cli' / 'bin' / 'lark-cli.exe'
URL = 'https://ocnfurb8or6p.feishu.cn/wiki/SL6awFIL8iwd4dkZFCdc3uK1nZf'
STATE = {'rows': [], 'error': '正在连接飞书…', 'updated': None}
LOCK = threading.Lock()

def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values(): yield from strings(v)
    elif isinstance(x, list):
        for v in x: yield from strings(v)

def parse(text):
    rows = list(csv.reader(io.StringIO(text)))
    for h, header in enumerate(rows):
        names = [str(v).replace('\n', '').replace(' ', '').strip() for v in header]
        def col(keys):
            return next((i for i, n in enumerate(names) if n in keys), None)
        dc, ic, vc = col(['时间', '日期']), col(['抖啦咪id', '抖啦咪ID']), col(['总收益/元', '总收益', '总收益（元）'])
        if None in (dc, ic, vc): continue
        result = []
        for n, row in enumerate(rows[h+1:], h+2):
            if not any(row): continue
            row += [''] * max(0, max(dc, ic, vc)+1-len(row))
            raw, ident, val = row[dc].strip(), row[ic].strip(), row[vc].strip()
            if not raw and not ident: continue
            if not ident: raise ValueError(f'第{n}行缺少抖啦咪ID，请补全后刷新')
            try:
                if raw.replace('.', '', 1).isdigit():
                    d = date(1899,12,30)+timedelta(days=int(float(raw)))
                else:
                    parts = raw.split()[0].replace('/', '-').split('-')
                    d = date(*map(int, parts))
                money = float(val.replace(',', '').replace('¥','').replace('￥','')) if val else 0
            except Exception: raise ValueError(f'第{n}行日期或收益格式无法识别')
            result.append({'date': d.isoformat(), 'id': ident, 'value': money})
        if not result: raise ValueError('官方数据尚无有效记录')
        return result
    raise ValueError('未识别到表头：时间、总收益/元、抖啦咪id；请检查官方数据列名')

def refresh():
    try:
        p = subprocess.run([str(CLI), 'sheets', '+csv-get', '--as', 'user', '--url', URL, '--sheet-name', '官方数据', '--include-row-prefix=false', '--max-chars', '20000000'], capture_output=True, timeout=90, encoding='utf-8', errors='replace', creationflags=0x08000000)
        output = p.stdout.strip() or p.stderr.strip()
        if not output: raise ValueError(f'CLI未返回数据（退出码 {p.returncode}）。请在本机PowerShell运行 lark-cli auth status 检查登录。')
        try: payload = json.loads(output)
        except ValueError: raise ValueError('CLI调用失败：'+output[:1500])
        if p.returncode or payload.get('ok') is False:
            raise ValueError(payload.get('error', {}).get('message', '飞书读取失败，请在PowerShell确认登录'))
        if any('has_more' in str(k) and v is True for k,v in payload.items()): raise ValueError('数据读取被截断')
        candidates = sorted((s for s in strings(payload) if '抖啦咪' in s and ('\n' in s or '\r' in s)), key=len, reverse=True)
        if not candidates: raise ValueError('飞书返回格式未识别，请保留窗口并联系检查')
        rows = parse(candidates[0])
        with LOCK: STATE.update(rows=rows, error=None, updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        with LOCK: STATE['error'] = str(e)

def loop():
    while True:
        refresh(); time.sleep(60)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/data':
            with LOCK: body = json.dumps(STATE, ensure_ascii=False).encode()
            mime = 'application/json; charset=utf-8'
        elif self.path in ('/', '/index.html'):
            body = (ROOT/'index.html').read_bytes(); mime = 'text/html; charset=utf-8'
        else:
            self.send_error(404); return
        self.send_response(200); self.send_header('Content-Type', mime); self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(body)
    def log_message(self, *args): pass

if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 8766), Handler)
    threading.Thread(target=loop, daemon=True).start()
    print('报表运行中：http://127.0.0.1:8766（关闭此窗口即停止）', flush=True)
    webbrowser.open('http://127.0.0.1:8766')
    server.serve_forever()
