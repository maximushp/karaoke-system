const express = require("express");
const cors    = require("cors");
const path    = require("path");
const https   = require("https");

const app = express();

/* CONFIG */
app.use(cors());
app.use(express.json());

/* 🔥 SERVIR HTML (MESMA PASTA DO SERVER.JS) */
app.use(express.static(__dirname));

/* 🎵 FILA EM MEMÓRIA */
let fila = [];

/* =========================
   🔍 PROXY DE BUSCA — YouTube sem cota, sem CORS
   O browser chama /api/busca → servidor faz o fetch para o YouTube
   Node.js não tem restrição de CORS, então funciona perfeitamente.
========================= */

const YT_CTX = { client: { clientName: "WEB", clientVersion: "2.20231121.00.00" } };
const YT_HEADERS = {
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  "X-YouTube-Client-Name": "1",
  "X-YouTube-Client-Version": "2.20231121.00.00",
  "Origin": "https://www.youtube.com",
  "Referer": "https://www.youtube.com/"
};

function youtubePost(path, body) {
  return new Promise((resolve, reject) => {
    const bodyStr = JSON.stringify(body);
    const options = {
      hostname: "www.youtube.com",
      path,
      method: "POST",
      headers: { ...YT_HEADERS, "Content-Length": Buffer.byteLength(bodyStr) }
    };
    const req = https.request(options, res => {
      let data = "";
      res.on("data", chunk => data += chunk);
      res.on("end", () => {
        if (res.statusCode !== 200)
          return reject(new Error(`YouTube retornou status ${res.statusCode}`));
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error("Resposta inválida do YouTube")); }
      });
    });
    req.on("error", reject);
    req.setTimeout(10000, () => { req.destroy(); reject(new Error("Timeout")); });
    req.write(bodyStr);
    req.end();
  });
}

function extrairVideoRenderers(renderers) {
  return renderers.map(vr => {
    const id     = vr.videoId;
    const titulo = vr.title?.runs?.[0]?.text || vr.title?.simpleText || "";
    const thumb  = vr.thumbnail?.thumbnails?.slice(-1)[0]?.url
                || `https://i.ytimg.com/vi/${id}/mqdefault.jpg`;
    // channelId pode vir em três campos diferentes dependendo do contexto
    const canal  =
      vr.ownerText?.runs?.[0]?.navigationEndpoint?.browseEndpoint?.browseId ||
      vr.longBylineText?.runs?.[0]?.navigationEndpoint?.browseEndpoint?.browseId ||
      vr.shortBylineText?.runs?.[0]?.navigationEndpoint?.browseEndpoint?.browseId || "";
    return id && titulo ? { id, titulo, thumb, channelId: canal } : null;
  }).filter(Boolean);
}

/* Parser para /youtubei/v1/search (busca geral) */
function parsearSearch(data) {
  const renderers = [];
  let nextToken = null;

  if (data.contents) {
    const sections = data.contents
      ?.twoColumnSearchResultsRenderer?.primaryContents
      ?.sectionListRenderer?.contents || [];
    sections.forEach(s => {
      (s?.itemSectionRenderer?.contents || []).forEach(i => {
        if (i.videoRenderer) renderers.push(i.videoRenderer);
      });
      const tok = s?.continuationItemRenderer?.continuationEndpoint?.continuationCommand?.token;
      if (tok) nextToken = tok;
    });
  } else if (data.onResponseReceivedCommands) {
    data.onResponseReceivedCommands.forEach(cmd => {
      (cmd?.appendContinuationItemsAction?.continuationItems || []).forEach(item => {
        (item?.itemSectionRenderer?.contents || []).forEach(i => {
          if (i.videoRenderer) renderers.push(i.videoRenderer);
        });
        const tok = item?.continuationItemRenderer?.continuationEndpoint?.continuationCommand?.token;
        if (tok) nextToken = tok;
      });
    });
  }

  return { itens: extrairVideoRenderers(renderers), nextToken };
}

/* Parser para /youtubei/v1/browse com query (busca dentro do canal) */
function parsearBrowse(data) {
  const renderers = [];
  let nextToken = null;

  if (data.onResponseReceivedActions) {
    // Paginação do browse
    data.onResponseReceivedActions.forEach(action => {
      (action?.appendContinuationItemsAction?.continuationItems || []).forEach(item => {
        (item?.itemSectionRenderer?.contents || []).forEach(i => {
          if (i.videoRenderer) renderers.push(i.videoRenderer);
        });
        const tok = item?.continuationItemRenderer?.continuationEndpoint?.continuationCommand?.token;
        if (tok) nextToken = tok;
      });
    });
  } else {
    // Primeira página do browse
    const tabs = data.contents?.twoColumnBrowseResultsRenderer?.tabs || [];
    const tab = tabs.find(t => t.tabRenderer?.selected)?.tabRenderer;
    const sections = tab?.content?.sectionListRenderer?.contents || [];
    sections.forEach(s => {
      (s?.itemSectionRenderer?.contents || []).forEach(i => {
        if (i.videoRenderer) renderers.push(i.videoRenderer);
      });
      const tok = s?.continuationItemRenderer?.continuationEndpoint?.continuationCommand?.token;
      if (tok) nextToken = tok;
    });
  }

  return { itens: extrairVideoRenderers(renderers), nextToken };
}

/* ── ROTA: busca GERAL no YouTube ── */
app.post("/api/busca", async (req, res) => {
  const { query, continuationToken } = req.body;
  try {
    let body;
    if (continuationToken) {
      body = { context: YT_CTX, continuation: continuationToken };
    } else {
      if (!query || query.trim().length < 2)
        return res.status(400).json({ erro: "Query muito curta" });
      body = { context: YT_CTX, query: query.trim() + " karaoke", params: "EgIQAQ==" };
    }
    const data = await youtubePost("/youtubei/v1/search?prettyPrint=false", body);
    res.json(parsearSearch(data));
  } catch (e) {
    console.error("Erro /api/busca:", e.message);
    res.status(500).json({ erro: e.message });
  }
});

/* ── ROTA: busca DENTRO DO CANAL (browse) ── */
app.post("/api/busca-canal", async (req, res) => {
  const { query, channelId, continuationToken } = req.body;
  try {
    let body;
    if (continuationToken) {
      body = { context: YT_CTX, continuation: continuationToken };
    } else {
      if (!query || query.trim().length < 2)
        return res.status(400).json({ erro: "Query muito curta" });
      if (!channelId)
        return res.status(400).json({ erro: "channelId obrigatório" });
      // params = EgZzZWFyY2g= é o protobuf para "tab=search" no browse do canal
      body = { context: YT_CTX, browseId: channelId, query: query.trim(), params: "EgZzZWFyY2g=" };
    }
    const data = await youtubePost("/youtubei/v1/browse?prettyPrint=false", body);
    res.json(parsearBrowse(data));
  } catch (e) {
    console.error("Erro /api/busca-canal:", e.message);
    res.status(500).json({ erro: e.message });
  }
});

/* =========================
   📡 ROTAS DA FILA
========================= */

app.get("/fila", (req, res) => res.json(fila));

app.post("/fila", (req, res) => {
  const musica = req.body;
  if (!musica || !musica.id) return res.status(400).json({ erro: "Dados inválidos" });
  fila.push(musica);
  res.json({ ok: true });
});

app.delete("/fila/primeira", (req, res) => {
  fila.shift();
  res.json({ ok: true });
});

app.delete("/fila", (req, res) => {
  fila = [];
  res.json({ ok: true });
});

/* =========================
   🌐 ROTAS DE PÁGINA
========================= */

app.get("/tv",       (req, res) => res.sendFile(path.join(__dirname, "tv.html")));
app.get("/controle", (req, res) => res.sendFile(path.join(__dirname, "controle.html")));

/* =========================
   🚀 START SERVIDOR
========================= */

app.listen(3000, "0.0.0.0", () => {
  console.log("🔥 Servidor rodando!");
  console.log("📺 TV:       http://localhost:3000/tv");
  console.log("📱 Controle: http://localhost:3000/controle");
});
