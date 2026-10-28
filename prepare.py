from pathlib import Path
p = Path(__file__).parent / 'site/index.html'
s = p.read_text(encoding='utf-8').replace('每 60 秒同步', '每小时定时同步')
s = s.replace("fetch('/api/data')", "fetch('./data.json?t='+Date.now(),{cache:'no-store'})")
s = s.replace('本地服务未连接，请运行启动报表.cmd；当前显示内容可能已过期。', '数据暂时无法加载，请稍后刷新；首次发布请先完成飞书同步配置。')
s = s.replace('setInterval(load,10000)', 'setInterval(load,300000)')
p.write_text(s, encoding='utf-8')
