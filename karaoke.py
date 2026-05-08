import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import urllib.request
import urllib.parse
import sys
import time
import os
import logging

LOG_FILE = os.path.join(os.environ.get('TEMP', '.'), 'karaoke_app.log')
logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

import player


class KaraokeVideo:

    def __init__(self, video_id, title, channel, duration):
        self.video_id = video_id
        self.title = title
        self.channel = channel
        self.duration = duration
        self.thumbnail = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"

    @property
    def watch_url(self):
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @property
    def formatted_duration(self):
        try:
            total_seconds = int(self.duration)
            return f"{total_seconds // 60}:{total_seconds % 60:02d}"
        except (ValueError, TypeError):
            return self.duration


class YouTubeSearcher:

    def search(self, query, max_results=25):
        return self._yt(f"{query} karaoke version lyrics", max_results)

    def _yt(self, query, max_results):
        videos = []
        try:
            url = "https://www.youtube.com/youtubei/v1/search"
            payload = {
                "context": {"client": {"clientName": "WEB", "clientVersion": "2.20230101.00.00"}},
                "query": query,
                "params": "EgIQAQ%3D%3D"
            }
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode('utf-8'))
            contents = result.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get(
                "primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
            for section in contents:
                for item in section.get("itemSectionRenderer", {}).get("contents", []):
                    vr = item.get("videoRenderer")
                    if not vr:
                        continue
                    video_id = vr.get("videoId", "")
                    title = "".join(r.get("text", "") for r in vr.get("title", {}).get("runs", []))
                    channel = "".join(r.get("text", "") for r in vr.get("ownerText", {}).get("runs", []))
                    dur = vr.get("lengthText", {}).get("simpleText", "0:00")
                    parts = dur.split(":")
                    try:
                        if len(parts) == 2:
                            secs = int(parts[0]) * 60 + int(parts[1])
                        elif len(parts) == 3:
                            secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                        else:
                            secs = 0
                    except (ValueError, IndexError):
                        secs = 0
                    if video_id and title:
                        videos.append(KaraokeVideo(video_id, title, channel, secs))
                    if len(videos) >= max_results:
                        break
                if len(videos) >= max_results:
                    break
        except Exception as e:
            logging.exception("Search error")
            videos = [
                KaraokeVideo("kJQP7kiw5Fk", "Despacito - Karaoke Version", "Karaoke World", 262),
                KaraokeVideo("RgKAFK5djSk", "See You Again - Karaoke", "Sing King", 229),
                KaraokeVideo("fJ9rUzIMcZQ", "Bohemian Rhapsody - Karaoke", "Karaoke Version", 354),
                KaraokeVideo("hT_nvWreIhg", "Counting Stars - Karaoke", "Sing King", 257),
                KaraokeVideo("e-ORhEE9VVg", "Blank Space - Karaoke", "Sing King", 232),
            ]
        return videos[:max_results]


class PlaylistManager:

    def __init__(self):
        self.playlist = []
        self.current_index = -1

    def add(self, v):
        self.playlist.append(v)

    def remove(self, i):
        if 0 <= i < len(self.playlist):
            del self.playlist[i]
            if self.current_index >= len(self.playlist):
                self.current_index = len(self.playlist) - 1

    def get_next(self):
        self.current_index += 1
        if self.current_index < len(self.playlist):
            return self.current_index, self.playlist[self.current_index]
        return -1, None

    def get_prev(self):
        self.current_index -= 1
        if 0 <= self.current_index < len(self.playlist):
            return self.current_index, self.playlist[self.current_index]
        self.current_index += 1
        return -1, None

    def get_current(self):
        if 0 <= self.current_index < len(self.playlist):
            return self.current_index, self.playlist[self.current_index]
        return -1, None

    def play_at(self, i):
        if 0 <= i < len(self.playlist):
            self.current_index = i
            return self.playlist[i]
        return None

    def clear(self):
        self.playlist = []
        self.current_index = -1

    def move_up(self, i):
        if i > 0 and i < len(self.playlist):
            self.playlist[i], self.playlist[i - 1] = self.playlist[i - 1], self.playlist[i]
            if self.current_index == i:
                self.current_index -= 1
            elif self.current_index == i - 1:
                self.current_index += 1
            return True
        return False

    def move_down(self, i):
        if i < len(self.playlist) - 1:
            self.playlist[i], self.playlist[i + 1] = self.playlist[i + 1], self.playlist[i]
            if self.current_index == i:
                self.current_index += 1
            elif self.current_index == i + 1:
                self.current_index -= 1
            return True
        return False


class KaraokeApp:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sistema de Karaokê - YouTube")
        self.root.geometry("1200x700")
        self.root.minsize(900, 600)

        self.searcher = YouTubeSearcher()
        self.playlist = PlaylistManager()
        self.player_ready = False
        self.player_url = tk.StringVar(value="Player não iniciado")
        player.set_next_callback(self._play_next)

        self._style()
        self._build()

    def _style(self):
        s = ttk.Style()
        s.theme_use('clam')
        s.configure('Title.TLabel', font=('Segoe UI', 14, 'bold'))
        s.configure('S.TButton', font=('Segoe UI', 11, 'bold'))
        s.configure('PTreeview.Treeview', font=('Segoe UI', 10))
        s.configure('PTreeview.Treeview.Heading', font=('Segoe UI', 10, 'bold'))

    def _build(self):
        m = ttk.Frame(self.root, padding="10")
        m.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(m)
        top.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(top, text="Sistema de Karaokê", style='Title.TLabel').pack(side=tk.LEFT)
        ttk.Label(top, textvariable=self.player_url, font=('Segoe UI', 9),
                  foreground='#888').pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(top, text="Abrir Janela do Player", command=self._open_player,
                   style='S.TButton').pack(side=tk.RIGHT)

        sf = ttk.Frame(m)
        sf.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(sf, text="Buscar:").pack(side=tk.LEFT, padx=(0, 5))
        self.sv = tk.StringVar()
        self.se = ttk.Entry(sf, textvariable=self.sv, font=('Segoe UI', 11), width=50)
        self.se.pack(side=tk.LEFT, padx=(0, 5))
        self.se.bind('<Return>', lambda e: self._search())
        ttk.Button(sf, text="Buscar", command=self._search, style='S.TButton').pack(side=tk.LEFT)

        cf = ttk.Frame(m)
        cf.pack(fill=tk.BOTH, expand=True)
        self._results(cf)
        self._playlist(cf)

        pf = ttk.LabelFrame(m, text="Now Playing", padding="5")
        pf.pack(fill=tk.X, pady=(10, 0))
        self.np = ttk.Label(pf, text="Nenhuma musica - clique em Open Player Window", font=('Segoe UI', 12))
        self.np.pack(side=tk.LEFT, fill=tk.X, expand=True)
        b = ttk.Frame(pf)
        b.pack(side=tk.RIGHT)
        ttk.Button(b, text="Anterior", command=self._prev).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(b, text="Próxima", command=self._next).pack(side=tk.LEFT)

        self._upd_pl()

    def _results(self, parent):
        f = ttk.LabelFrame(parent, text="Resultados da Busca", padding="5")
        f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.rt = ttk.Treeview(f, columns=('title', 'channel', 'duration'), show='headings', height=15)
        self.rt.heading('title', text='Título')
        self.rt.heading('channel', text='Canal')
        self.rt.heading('duration', text='Duração')
        self.rt.column('title', width=350, minwidth=200)
        self.rt.column('channel', width=150, minwidth=100)
        self.rt.column('duration', width=70, minwidth=60)
        sc = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self.rt.yview)
        self.rt.configure(yscrollcommand=sc.set)
        self.rt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sc.pack(side=tk.RIGHT, fill=tk.Y)
        self.rt.bind('<Double-1>', lambda e: self._play_sel())
        bf = ttk.Frame(f)
        bf.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(bf, text="Adicionar à Lista", command=self._add_pl).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(bf, text="Tocar Agora", command=self._play_sel).pack(side=tk.LEFT)

    def _playlist(self, parent):
        f = ttk.LabelFrame(parent, text="Lista de Reprodução", padding="5")
        f.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.pt = ttk.Treeview(f, columns=('title', 'duration'), show='headings', height=15, style='PTreeview.Treeview')
        self.pt.heading('title', text='Título')
        self.pt.heading('duration', text='Duração')
        self.pt.column('title', width=250, minwidth=150)
        self.pt.column('duration', width=60, minwidth=50)
        sc = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self.pt.yview)
        self.pt.configure(yscrollcommand=sc.set)
        self.pt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sc.pack(side=tk.RIGHT, fill=tk.Y)
        self.pt.bind('<Double-1>', lambda e: self._play_pl_item())
        bf = ttk.Frame(f)
        bf.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(bf, text="Subir", command=self._up).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(bf, text="Descer", command=self._down).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(bf, text="Remover", command=self._rm_pl).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(bf, text="Limpar Tudo", command=self._clear_pl).pack(side=tk.LEFT)

    def _open_player(self):
        if self.player_ready:
            player.open_window()
            return

        self.root.config(cursor="wait")
        self.root.update()

        def _start():
            try:
                port, ip = player.start_server()
                self.player_ready = True
                url = f"http://{ip}:{port}"
                self.root.after(0, lambda u=url: self.player_url.set(f"URL TV: {u}"))
                self.root.after(0, lambda p=port: self.np.config(
                    text=f"Player pronto (porta {p}) - selecione uma música!"))
                self.root.after(0, lambda: self.root.config(cursor=""))
                time.sleep(0.8)
                self.root.after(0, player.open_window)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Erro", f"Falha ao abrir player: {e}"))
                self.root.after(0, lambda: self.root.config(cursor=""))

        threading.Thread(target=_start, daemon=True).start()

    def _search(self):
        q = self.sv.get().strip()
        if not q:
            return
        self.se.config(state=tk.DISABLED)
        threading.Thread(target=self._st, args=(q,), daemon=True).start()

    def _st(self, q):
        try:
            r = self.searcher.search(q)
            self.root.after(0, self._ur, r)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro", str(e)))
        finally:
            self.root.after(0, lambda: self.se.config(state=tk.NORMAL))

    def _ur(self, results):
        for i in self.rt.get_children():
            self.rt.delete(i)
        self._results_list = results
        for v in results:
            self.rt.insert('', tk.END, values=(v.title, v.channel, v.formatted_duration))
        if not results:
            messagebox.showinfo("Sem resultados", "Nenhum vídeo encontrado.")

    def _get_sel(self):
        sel = self.rt.selection()
        if not sel:
            return None
        idx = self.rt.index(sel[0])
        if hasattr(self, '_results_list') and idx < len(self._results_list):
            return self._results_list[idx]
        return None

    def _add_pl(self):
        v = self._get_sel()
        if v:
            self.playlist.add(v)
            self._upd_pl()

    def _play_sel(self):
        v = self._get_sel()
        if v:
            self.playlist.add(v)
            self._upd_pl()
            self._play(v)

    def _play_pl_item(self):
        sel = self.pt.selection()
        if not sel:
            return
        v = self.playlist.play_at(self.pt.index(sel[0]))
        if v:
            self._upd_pl()
            self._play(v)

    def _next(self):
        _, v = self.playlist.get_next()
        if v:
            self._upd_pl()
            self._play(v)
        else:
            messagebox.showinfo("Fim", "Não há mais músicas na lista de reprodução.")

    def _prev(self):
        _, v = self.playlist.get_prev()
        if v:
            self._upd_pl()
            self._play(v)

    def _play(self, video):
        self.np.config(text=f"Tocando: {video.title}")
        if not self.player_ready:
            self.np.config(text="Abra a Janela do Player primeiro!")
            return
        try:
            player.play(video.video_id, video.title)
        except Exception as e:
            self.np.config(text=f"Erro: {e}")

    def _play_next(self):
        _, v = self.playlist.get_next()
        if v:
            self.root.after(0, lambda: self._upd_pl())
            self.root.after(0, lambda vid=v: self._play(vid))
        else:
            self.root.after(0, lambda: messagebox.showinfo("Fim", "Playlist finalizada."))
            self.root.after(0, lambda: self.np.config(text="Playlist finalizada"))

    def _rm_pl(self):
        sel = self.pt.selection()
        if sel:
            self.playlist.remove(self.pt.index(sel[0]))
            self._upd_pl()

    def _up(self):
        sel = self.pt.selection()
        if sel:
            i = self.pt.index(sel[0])
            if self.playlist.move_up(i):
                self._upd_pl()
                self.pt.selection_set(i - 1)

    def _down(self):
        sel = self.pt.selection()
        if sel:
            i = self.pt.index(sel[0])
            if self.playlist.move_down(i):
                self._upd_pl()
                self.pt.selection_set(i + 1)

    def _clear_pl(self):
        self.playlist.clear()
        self._upd_pl()
        self.np.config(text="Nenhuma musica")

    def _upd_pl(self):
        for i in self.pt.get_children():
            self.pt.delete(i)
        for i, v in enumerate(self.playlist.playlist):
            tags = ('cur',) if i == self.playlist.current_index else ()
            self.pt.insert('', tk.END, values=(v.title, v.formatted_duration), tags=tags)
        self.pt.tag_configure('cur', background='#4CAF50', foreground='white')

    def run(self):
        self.root.mainloop()


def main():
    KaraokeApp().run()


if __name__ == "__main__":
    main()
