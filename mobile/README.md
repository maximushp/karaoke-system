# 🎤 Karaokê App — Android APK

Projeto Android com servidor HTTP embutido (NanoHTTPD) + WebView.
Não precisa de Node.js no celular — tudo roda dentro do APK!

---

## 🏗️ Como compilar (Android Studio)

### Pré-requisitos
- Android Studio Hedgehog (2023.1) ou mais novo
- Android SDK 34
- JDK 11 ou 17

### Passos

1. **Abra o projeto no Android Studio**
   - File → Open → selecione esta pasta `KaraokeApp/`

2. **Aguarde o Gradle sincronizar** (baixa as dependências automaticamente)

3. **Compile e instale**
   - Clique em ▶️ Run, ou
   - Build → Build Bundle(s)/APK(s) → Build APK(s)
   - O APK fica em: `app/build/outputs/apk/debug/app-debug.apk`

---

## 📱 Como usar o app

### Modo TV (MainActivity)
- Abre automaticamente em tela cheia **paisagem**
- Exibe a fila de músicas e o player YouTube
- Servidor HTTP sobe na porta **3000**
- Botão rosa (FAB) no canto → abre o Controle no mesmo aparelho

### Modo Controle (ControleActivity)
- Busca músicas no YouTube
- Adiciona à fila
- Pode ser acessado de **qualquer celular na mesma rede Wi-Fi**

### Acesso pelo celular (rede local)
1. Descubra o IP do Android TV/celular principal:
   - Configurações → Wi-Fi → detalhes da rede → IP address
2. No celular dos convidados, abra o navegador e acesse:
   - `http://192.168.X.X:3000/controle`

---

## 🏗️ Estrutura do projeto

```
KaraokeApp/
├── app/
│   ├── src/main/
│   │   ├── java/com/karaoke/app/
│   │   │   ├── MainActivity.java       ← Tela TV (landscape, fullscreen)
│   │   │   ├── ControleActivity.java   ← Tela controle (portrait)
│   │   │   └── KaraokeServer.java      ← Servidor HTTP (NanoHTTPD)
│   │   ├── assets/www/
│   │   │   ├── tv.html                 ← Interface da TV
│   │   │   ├── controle.html           ← Interface do controle
│   │   │   └── server.js               ← (referência, não usado no APK)
│   │   ├── res/layout/
│   │   │   ├── activity_main.xml
│   │   │   └── activity_controle.xml
│   │   └── AndroidManifest.xml
│   └── build.gradle
└── build.gradle
```

## 📦 Dependências
- **NanoHTTPD 2.3.1** — servidor HTTP leve
- **OkHttp 4.12** — proxy para busca no YouTube
- **Material Components** — botão flutuante (FAB)

---

## 🔧 Compilar via linha de comando

```bash
# Com Android SDK configurado no PATH:
./gradlew assembleDebug

# APK gerado em:
# app/build/outputs/apk/debug/app-debug.apk
```

---

## 💡 Dica: Instalar APK via ADB

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```
