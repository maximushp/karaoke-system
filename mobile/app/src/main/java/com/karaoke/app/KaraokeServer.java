package com.karaoke.app;

import android.content.Context;
import android.net.wifi.WifiManager;
import java.net.InetAddress;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import fi.iki.elonen.NanoHTTPD;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;

public class KaraokeServer extends NanoHTTPD {

    private static final String TAG = "KaraokeServer";
    public static final int PORT = 3000;

    private final Context context;
    private final OkHttpClient httpClient;
    private final List<JSONObject> fila = new ArrayList<>();

    private static final String YT_BASE = "https://www.youtube.com";
    private static final String YT_CONTEXT = "{\"client\":{\"clientName\":\"WEB\",\"clientVersion\":\"2.20231121.00.00\"}}";
    private static final MediaType JSON_TYPE = MediaType.parse("application/json; charset=utf-8");

    public KaraokeServer(Context context) {
        super(PORT);
        this.context = context;
        this.httpClient = new OkHttpClient.Builder()
                .connectTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
                .readTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
                .build();
    }

    private Response handleIp() {
        try {
            WifiManager wm = (WifiManager) context.getSystemService(Context.WIFI_SERVICE);
            int ip = wm.getConnectionInfo().getIpAddress();
            String ipStr = String.format("%d.%d.%d.%d",
                (ip & 0xff), (ip >> 8 & 0xff), (ip >> 16 & 0xff), (ip >> 24 & 0xff));
            return jsonResponse(Response.Status.OK, "{\"ip\":\"" + ipStr + "\"}");
        } catch (Exception e) {
            return jsonResponse(Response.Status.OK, "{\"ip\":\"?\"}");
        }
    }

    public void startServer() throws IOException {
        start(30000, false);
    }

    public void stopServer() {
        stop();
    }

    @Override
    public Response serve(IHTTPSession session) {
        String uri = session.getUri();
        Method method = session.getMethod();

        Log.d(TAG, method + " " + uri);

        try {
            // ── API ROUTES ──
            if (uri.equals("/api/parar") && method == Method.POST) {
                Response r = jsonResponse(Response.Status.OK, "{\"ok\":true}");
                new Thread(() -> { try { Thread.sleep(300); stopServer(); } catch (Exception ignored) {} }).start();
                return r;
            }

            if (uri.equals("/api/ip") && method == Method.GET) {
                return handleIp();
            }

            if (uri.equals("/api/busca") && method == Method.POST) {
                return handleBusca(session);
            }

            if (uri.equals("/fila")) {
                if (method == Method.GET)    return handleFilaGet();
                if (method == Method.POST)   return handleFilaPost(session);
                if (method == Method.DELETE) return handleFilaDelete();
            }

            if (uri.equals("/fila/primeira") && method == Method.DELETE) {
                return handleFilaPrimeira();
            }

            // ── PAGE ROUTES ──
            if (uri.equals("/") || uri.equals("/tv") || uri.equals("/tv.html")) {
                return serveAsset("www/tv.html", "text/html");
            }
            if (uri.equals("/controle") || uri.equals("/controle.html")) {
                return serveAsset("www/controle.html", "text/html");
            }

            // ── STATIC FILES ──
            String assetPath = "www" + uri;
            try {
                InputStream is = context.getAssets().open(assetPath);
                return newChunkedResponse(Response.Status.OK, getMimeType(uri), is);
            } catch (IOException ignored) {}

            return jsonResponse(Response.Status.NOT_FOUND, "{\"erro\":\"Not found\"}");

        } catch (Exception e) {
            Log.e(TAG, "Server error", e);
            return jsonResponse(Response.Status.INTERNAL_ERROR, "{\"erro\":\"" + e.getMessage() + "\"}");
        }
    }

    // ── FILA ────────────────────────────────────────────────────────────────

    private Response handleFilaGet() {
        synchronized (fila) {
            JSONArray arr = new JSONArray(fila);
            return jsonResponse(Response.Status.OK, arr.toString());
        }
    }

    private Response handleFilaPost(IHTTPSession session) throws Exception {
        String body = readBody(session);
        JSONObject musica = new JSONObject(body);
        if (!musica.has("id")) {
            return jsonResponse(Response.Status.BAD_REQUEST, "{\"erro\":\"Dados inválidos\"}");
        }
        synchronized (fila) {
            fila.add(musica);
        }
        return jsonResponse(Response.Status.OK, "{\"ok\":true}");
    }

    private Response handleFilaDelete() {
        synchronized (fila) {
            fila.clear();
        }
        return jsonResponse(Response.Status.OK, "{\"ok\":true}");
    }

    private Response handleFilaPrimeira() {
        synchronized (fila) {
            if (!fila.isEmpty()) fila.remove(0);
        }
        return jsonResponse(Response.Status.OK, "{\"ok\":true}");
    }

    // ── BUSCA ────────────────────────────────────────────────────────────────

    private Response handleBusca(IHTTPSession session) throws Exception {
        String body = readBody(session);
        JSONObject req = new JSONObject(body);

        JSONObject ytBody = new JSONObject();
        ytBody.put("context", new JSONObject(YT_CONTEXT));

        if (req.has("continuationToken")) {
            ytBody.put("continuation", req.getString("continuationToken"));
        } else {
            String query = req.optString("query", "").trim();
            if (query.length() < 2) {
                return jsonResponse(Response.Status.BAD_REQUEST, "{\"erro\":\"Query muito curta\"}");
            }
            ytBody.put("query", query + " karaoke");
            ytBody.put("params", "EgIQAQ==");
        }

        String ytResp = youtubePost("/youtubei/v1/search?prettyPrint=false", ytBody.toString());
        JSONObject parsed = parseSearch(new JSONObject(ytResp));
        return jsonResponse(Response.Status.OK, parsed.toString());
    }

    // ── YouTube POST ─────────────────────────────────────────────────────────

    private String youtubePost(String path, String body) throws IOException {
        RequestBody rb = RequestBody.create(body, JSON_TYPE);
        Request request = new Request.Builder()
                .url(YT_BASE + path)
                .post(rb)
                .addHeader("Content-Type", "application/json")
                .addHeader("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                .addHeader("X-YouTube-Client-Name", "1")
                .addHeader("X-YouTube-Client-Version", "2.20231121.00.00")
                .addHeader("Origin", "https://www.youtube.com")
                .addHeader("Referer", "https://www.youtube.com/")
                .build();

        try (okhttp3.Response resp = httpClient.newCall(request).execute()) {
            if (!resp.isSuccessful()) throw new IOException("YouTube error: " + resp.code());
            return resp.body().string();
        }
    }

    // ── Parse YouTube ─────────────────────────────────────────────────────────

    private JSONObject parseSearch(JSONObject data) throws JSONException {
        JSONArray renderers = new JSONArray();
        String nextToken = null;

        if (data.has("contents")) {
            JSONObject col = data.optJSONObject("contents");
            if (col != null) {
                JSONObject primary = col.optJSONObject("twoColumnSearchResultsRenderer");
                if (primary != null) {
                    JSONObject pc = primary.optJSONObject("primaryContents");
                    if (pc != null) {
                        JSONObject slr = pc.optJSONObject("sectionListRenderer");
                        if (slr != null) {
                            JSONArray sections = slr.optJSONArray("contents");
                            if (sections != null) {
                                for (int i = 0; i < sections.length(); i++) {
                                    JSONObject s = sections.getJSONObject(i);
                                    JSONObject isr = s.optJSONObject("itemSectionRenderer");
                                    if (isr != null) {
                                        JSONArray contents = isr.optJSONArray("contents");
                                        if (contents != null) {
                                            for (int j = 0; j < contents.length(); j++) {
                                                JSONObject vr = contents.getJSONObject(j).optJSONObject("videoRenderer");
                                                if (vr != null) renderers.put(vr);
                                            }
                                        }
                                    }
                                    JSONObject cont = s.optJSONObject("continuationItemRenderer");
                                    if (cont != null) {
                                        JSONObject ep = cont.optJSONObject("continuationEndpoint");
                                        if (ep != null) {
                                            JSONObject cc = ep.optJSONObject("continuationCommand");
                                            if (cc != null) {
                                                String tok = cc.optString("token", "");
                                                if (!tok.isEmpty()) nextToken = tok;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } else if (data.has("onResponseReceivedCommands")) {
            JSONArray cmds = data.getJSONArray("onResponseReceivedCommands");
            for (int i = 0; i < cmds.length(); i++) {
                JSONObject cmd = cmds.getJSONObject(i);
                JSONObject action = cmd.optJSONObject("appendContinuationItemsAction");
                if (action == null) continue;
                JSONArray items = action.optJSONArray("continuationItems");
                if (items == null) continue;
                for (int j = 0; j < items.length(); j++) {
                    JSONObject item = items.getJSONObject(j);
                    JSONObject isr = item.optJSONObject("itemSectionRenderer");
                    if (isr != null) {
                        JSONArray c = isr.optJSONArray("contents");
                        if (c != null) {
                            for (int k = 0; k < c.length(); k++) {
                                JSONObject vr = c.getJSONObject(k).optJSONObject("videoRenderer");
                                if (vr != null) renderers.put(vr);
                            }
                        }
                    }
                    JSONObject cont = item.optJSONObject("continuationItemRenderer");
                    if (cont != null) {
                        JSONObject ep = cont.optJSONObject("continuationEndpoint");
                        if (ep != null) {
                            JSONObject cc = ep.optJSONObject("continuationCommand");
                            if (cc != null) {
                                String tok = cc.optString("token", "");
                                if (!tok.isEmpty()) nextToken = tok;
                            }
                        }
                    }
                }
            }
        }

        JSONArray itens = extrairVideos(renderers);
        JSONObject result = new JSONObject();
        result.put("itens", itens);
        if (nextToken != null) result.put("nextToken", nextToken);
        return result;
    }

    private JSONArray extrairVideos(JSONArray renderers) throws JSONException {
        JSONArray result = new JSONArray();
        for (int i = 0; i < renderers.length(); i++) {
            JSONObject vr = renderers.getJSONObject(i);
            String id = vr.optString("videoId", "");
            if (id.isEmpty()) continue;

            String titulo = "";
            JSONObject title = vr.optJSONObject("title");
            if (title != null) {
                JSONArray runs = title.optJSONArray("runs");
                if (runs != null && runs.length() > 0) {
                    titulo = runs.getJSONObject(0).optString("text", "");
                } else {
                    titulo = title.optString("simpleText", "");
                }
            }
            if (titulo.isEmpty()) continue;

            String thumb = "https://i.ytimg.com/vi/" + id + "/mqdefault.jpg";
            JSONObject thumbObj = vr.optJSONObject("thumbnail");
            if (thumbObj != null) {
                JSONArray thumbs = thumbObj.optJSONArray("thumbnails");
                if (thumbs != null && thumbs.length() > 0) {
                    String url = thumbs.getJSONObject(thumbs.length() - 1).optString("url", "");
                    if (!url.isEmpty()) thumb = url;
                }
            }

            JSONObject video = new JSONObject();
            video.put("id", id);
            video.put("titulo", titulo);
            video.put("thumb", thumb);
            result.put(video);
        }
        return result;
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private Response serveAsset(String path, String mime) {
        try {
            InputStream is = context.getAssets().open(path);
            byte[] bytes = readAllBytes(is);
            String mimeWithCharset = mime.contains("charset") ? mime : mime + "; charset=utf-8";
            // Serve raw bytes to avoid NanoHTTPD re-encoding the String internally
            Response r = newFixedLengthResponse(Response.Status.OK, mimeWithCharset,
                    new java.io.ByteArrayInputStream(bytes), bytes.length);
            r.addHeader("Access-Control-Allow-Origin", "*");
            return r;
        } catch (IOException e) {
            return jsonResponse(Response.Status.NOT_FOUND, "{\"erro\":\"File not found\"}");
        }
    }

    private byte[] readAllBytes(InputStream is) throws IOException {
        java.io.ByteArrayOutputStream buffer = new java.io.ByteArrayOutputStream();
        byte[] chunk = new byte[4096];
        int n;
        while ((n = is.read(chunk)) != -1) buffer.write(chunk, 0, n);
        return buffer.toByteArray();
    }

    private Response jsonResponse(Response.Status status, String json) {
        try {
            byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
            Response r = newFixedLengthResponse(status, "application/json; charset=utf-8",
                    new java.io.ByteArrayInputStream(bytes), bytes.length);
            r.addHeader("Access-Control-Allow-Origin", "*");
            return r;
        } catch (Exception e) {
            return newFixedLengthResponse(status, "application/json", json);
        }
    }

    private String readBody(IHTTPSession session) throws Exception {
        // Read raw bytes directly — avoids NanoHTTPD parseBody() ISO-8859-1 re-encoding
        int len = 0;
        String lenHeader = session.getHeaders().get("content-length");
        if (lenHeader != null && !lenHeader.isEmpty()) {
            len = Integer.parseInt(lenHeader.trim());
        }
        if (len <= 0) return "{}";
        byte[] buf = new byte[len];
        int read = 0;
        while (read < len) {
            int r = session.getInputStream().read(buf, read, len - read);
            if (r == -1) break;
            read += r;
        }
        return new String(buf, 0, read, StandardCharsets.UTF_8);
    }

    private String getMimeType(String uri) {
        if (uri.endsWith(".html")) return "text/html; charset=utf-8";
        if (uri.endsWith(".js"))   return "application/javascript; charset=utf-8";
        if (uri.endsWith(".css"))  return "text/css";
        if (uri.endsWith(".png"))  return "image/png";
        if (uri.endsWith(".jpg") || uri.endsWith(".jpeg")) return "image/jpeg";
        if (uri.endsWith(".json")) return "application/json";
        return "text/plain";
    }
}
