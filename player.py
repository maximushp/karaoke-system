import http.server
import socketserver
import threading
import json
import urllib.parse
import urllib.request
import sys
import os
import time
import subprocess
import logging
import socket

LOG_FILE = os.path.join(os.environ.get('TEMP', '.'), 'karaoke_player.log')
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

PORT = 0
SERVER_INSTANCE = None
QUEUE = []
QUEUE_LOCK = threading.Lock()
NEXT_CALLBACK = None

def set_next_callback(fn):
    global NEXT_CALLBACK
    NEXT_CALLBACK = fn

PLAYER_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Player de Karaokê</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#1a1a2e;color:#eee;font-family:'Segoe UI',Tahoma,sans-serif;display:flex;flex-direction:column;height:100vh;overflow:hidden}
.hdr{background:linear-gradient(135deg,#16213e,#0f3460);padding:10px 20px;display:flex;align-items:center;gap:12px;box-shadow:0 2px 10px rgba(0,0,0,.3)}
.hdr h1{font-size:16px;color:#e94560;white-space:nowrap}
#np{font-size:13px;color:#aaa;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.vc{flex:1;background:#000;position:relative}
#player{width:100%;height:100%}
#wait{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:#555}
#wait .ico{font-size:72px;margin-bottom:16px}
.bar{width:100%;height:4px;background:#333;cursor:pointer}
.bar .fill{height:100%;background:#e94560;width:0%;transition:width .1s}
.td{color:#777;font-size:11px;padding:4px 16px;display:flex;justify-content:space-between;background:#0f1a30}
.ctl{background:#16213e;padding:12px 20px;display:flex;align-items:center;justify-content:center;gap:12px}
.b{background:#0f3460;color:#eee;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;transition:all .15s}
.b:hover{background:#e94560}
.b.p{background:#e94560;padding:10px 28px;font-size:14px}
.b.p:hover{background:#ff6b6b}
.vol{display:flex;align-items:center;gap:6px;color:#888;font-size:13px}
.vol input{width:80px;accent-color:#e94560}
</style>
</head>
<body>
<div class="hdr"><h1>&#9835; Player de Karaokê</h1><span id="np">Nenhuma música selecionada</span></div>
<div class="vc">
<div id="wait"><div class="ico">&#9835;</div><p>Selecione uma música no sistema</p></div>
<div id="player"></div>
</div>
<div class="bar" id="bar" onclick="seek(event)"><div class="fill" id="fill"></div></div>
<div class="td"><span id="ct">0:00</span><span id="tt">0:00</span></div>
<div class="ctl">
<button class="b p" id="pp" onclick="tp()">&#9654; Tocar</button>
<button class="b" onclick="sv()">&#9632; Parar</button>
<div class="vol">&#128266; <input type="range" min="0" max="100" value="80" onchange="player&&player.setVolume(+this.value)"></div>
</div>
<script>
var player,pi,playing=false,pendingVideo=null;
function onYouTubeIframeAPIReady(){
  player=new YT.Player('player',{height:'100%',width:'100%',
    playerVars:{autoplay:0,controls:1,modestbranding:1,rel:0,fs:1},
    events:{onReady:function(){
      document.getElementById('wait').style.display='none';
      player.setVolume(80);
      poll();
      if(pendingVideo){player.loadVideoById(pendingVideo.id);pendingVideo=null}
    },
    onStateChange:sc,
    onError:function(e){
      document.getElementById('wait').innerHTML='<div class="ico">&#9888;</div><p>Video bloqueado. Pulando...</p>';
      document.getElementById('wait').style.display='block';
      setTimeout(function(){fetch('/next')},2000);
    }}
  });
}
setTimeout(function(){
  if(!player){document.getElementById('wait').innerHTML='<div class="ico">&#9888;</div><p>Falha ao carregar API do YouTube. Verifique sua conexão.</p>'}
},5000);
function sc(e){
  var b=document.getElementById('pp');
  if(e.data==YT.PlayerState.PLAYING){b.innerHTML='&#9646;&#9646; Pausar';playing=true;sp()}
  else if(e.data==YT.PlayerState.ENDED){b.innerHTML='&#9654; Tocar';playing=false;cp();fetch('/next').then(function(){setTimeout(poll,500)})}
  else{b.innerHTML='&#9654; Tocar';playing=false;cp()}
}
function lv(id,title){
  document.getElementById('np').textContent=title||'';
  document.getElementById('wait').style.display='none';
  if(player&&player.loadVideoById){player.loadVideoById(id);pendingVideo=null}
  else{pendingVideo={id:id,title:title}}
}
function tp(){if(!player)return;playing?player.pauseVideo():player.playVideo()}
function sv(){if(!player)return;player.stopVideo();
  document.getElementById('fill').style.width='0%';
  document.getElementById('ct').textContent='0:00';
  document.getElementById('np').textContent='Parado'}
function seek(e){if(!player||!player.getDuration)return;
  var r=document.getElementById('bar').getBoundingClientRect();
  player.seekTo((e.clientX-r.left)/r.width*player.getDuration(),true)}
function sp(){cp();pi=setInterval(up,250)}
function cp(){if(pi)clearInterval(pi)}
function up(){if(!player||!player.getCurrentTime||!player.getDuration)return;
  var c=player.getCurrentTime(),t=player.getDuration();
  if(t>0){document.getElementById('fill').style.width=(c/t*100)+'%';
  document.getElementById('ct').textContent=fmt(c);document.getElementById('tt').textContent=fmt(t)}}
function fmt(s){var m=Math.floor(s/60),ss=Math.floor(s%60);return m+':'+(ss<10?'0':'')+ss}
var lv2=0;
function poll(){
  fetch('/queue?v='+lv2).then(function(r){return r.json()}).then(function(d){
    if(d.video_id&&d.version!==lv2){lv2=d.version;lv(d.video_id,d.title)}
    setTimeout(poll,500)}).catch(function(){setTimeout(poll,2000)})
}
var t=document.createElement('script');t.src="https://www.youtube.com/iframe_api";
document.getElementsByTagName('script')[0].parentNode.insertBefore(t,document.getElementsByTagName('script')[0]);
</script>
</body>
</html>"""

class _Handler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ('/', '/player.html'):
            self._ok('text/html; charset=utf-8', PLAYER_HTML.encode('utf-8'))
        elif parsed.path == '/play':
            qs = urllib.parse.parse_qs(parsed.query)
            vid = qs.get('video_id', [''])[0]
            title = qs.get('title', [''])[0]
            logging.info("Play request: video_id=%s, title=%s", vid, title)
            if vid:
                ver = int(time.time() * 1000)
                with QUEUE_LOCK:
                    QUEUE.clear()
                    QUEUE.append({'video_id': vid, 'title': title, 'version': ver})
                self._ok('application/json', json.dumps({'status': 'ok'}).encode())
            else:
                self._err(400, b'video_id required')
        elif parsed.path == '/queue':
            qs = urllib.parse.parse_qs(parsed.query)
            cv = int(qs.get('v', ['0'])[0])
            with QUEUE_LOCK:
                if QUEUE:
                    item = QUEUE[0].copy()
                    if item['version'] != cv:
                        self._ok('application/json', json.dumps(item).encode())
                    else:
                        self._ok('application/json', b'{}')
                else:
                    self._ok('application/json', b'{}')
        elif parsed.path == '/next':
            logging.info("Next requested from player")
            if NEXT_CALLBACK:
                threading.Thread(target=NEXT_CALLBACK, daemon=True).start()
            self._ok('application/json', json.dumps({'status': 'ok'}).encode())
        else:
            self.send_error(404)

    def _ok(self, ct, body):
        self.send_response(200)
        self.send_header('Content-type', ct)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(body)

    def _err(self, code, body):
        self.send_response(code)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def _find_port(start=18472):
    for p in range(start, start + 100):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", p))
            s.close()
            return p
        except OSError:
            continue
    return 0


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def start_server(port=None):
    global PORT, SERVER_INSTANCE
    PORT = port or _find_port()
    if PORT == 0:
        raise RuntimeError("No free port found")
    socketserver.TCPServer.allow_reuse_address = True
    SERVER_INSTANCE = socketserver.TCPServer(("0.0.0.0", PORT), _Handler)
    ip = get_local_ip()
    logging.info("Server started on port %d, accessible at http://%s:%d", PORT, ip, PORT)
    t = threading.Thread(target=SERVER_INSTANCE.serve_forever, daemon=True)
    t.start()
    return PORT, ip


def _launch_browser(url):
    logging.info("Opening player window: %s", url)
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                subprocess.Popen([path, f"--app={url}", "--new-window"])
                logging.info("Launched browser: %s", path)
                return True
            except Exception as e:
                logging.exception("Failed to launch %s", path)
                continue
    import webbrowser
    webbrowser.open(url)
    logging.info("Used webbrowser fallback")
    return True


def open_window():
    _launch_browser(f"http://127.0.0.1:{PORT}")


def play(video_id, title=""):
    try:
        urllib.request.urlopen(
            f"http://127.0.0.1:{PORT}/play?video_id={video_id}&title={urllib.parse.quote(title)}",
            timeout=5)
        logging.info("Play sent: %s", video_id)
    except Exception as e:
        logging.exception("Play request failed")
