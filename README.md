# Sistema de Karaokê YouTube

Um sistema de karaokê completo que usa vídeos do YouTube, com interface gráfica amigável e suporte a rede local para controle via TV.

## 🎤 Funcionalidades

- **Busca Inteligente**: Pesquise músicas no YouTube com foco em versões karaokê
- **Player Integrado**: Reprodução via YouTube IFrame API com controles personalizados
- **Playlist Automática**: Ao terminar uma música, a próxima inicia automaticamente
- **Pulão Inteligente**: Vídeos bloqueados pelo YouTube são pulados automaticamente
- **Acesso via Rede**: Use a URL exibida para abrir o player em uma TV ou dispositivo na mesma rede
- **Gerenciamento de Playlist**: Adicione, remova, reorganize e toque músicas facilmente
- **Interface em Português**: Totalmente traduzido para PT-BR

## 📦 Download

Baixe a última versão do executável (`KaraokeSystem.exe`) na seção [Releases](../../releases) ou na pasta `dist` deste repositório.

## 🚀 Como Usar

### Opção 1: Executável (Recomendado)

1. Baixe o `KaraokeSystem.exe`
2. Se o Windows bloquear por segurança:
   - Clique com botão direito → **Propriedades** → Marque **Desbloquear**
   - Ou adicione uma exclusão no Windows Defender

### Opção 2: Script Python (Sem bloqueio)

1. Certifique-se de ter Python 3.10+ instalado
2. Clone este repositório:
   ```bash
   git clone https://github.com/seu-usuario/karaoke_system.git
   cd karaoke_system
   ```
3. Crie e ative um ambiente virtual:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
4. Execute o programa:
   ```bash
   python karaoke.py
   ```
   Ou use o arquivo `run.bat` (basta dar duplo-clique)

## 🎮 Guia Rápido

1. **Abrir o Player**: Clique em "Abrir Janela do Player"
   - O programa mostrará a URL para acesso via rede (ex: `http://192.168.1.50:18472`)
   - Use esta URL na TV ou outro dispositivo na mesma rede

2. **Buscar Músicas**: Digite o nome da música e clique em "Buscar"

3. **Montar Playlist**:
   - Clique em "Adicionar à Lista" para adicionar à playlist
   - Ou "Tocar Agora" para tocar imediatamente

4. **Controles**:
   - Use os botões "Anterior" e "Próxima" no painel principal
   - No player, use Play/Pause e Barra de Progresso
   - Ajuste o volume no player

5. **Gerenciar Playlist**:
   - Selecione um item e use "Subir/Descer" para reordenar
   - "Remover" para excluir um item
   - "Limpar Tudo" para esvaziar a lista

## 🔧 Requisitos (Para execução via Python)

- Python 3.10 ou superior
- Sem dependências externas (apenas bibliotecas padrão)

## 📝 Logs

O programa gera logs para diagnóstico em:
- `%TEMP%\karaoke_player.log` (servidor e player)
- `%TEMP%\karaoke_app.log` (interface principal)

## ⚠️ Solução de Problemas

**O player não carrega:**
- Verifique sua conexão com a internet
- Certifique-se de que o YouTube não está bloqueado por firewall/ad blocker

**Vídeos bloqueados:**
- O sistema pula automaticamente vídeos com embedding desativado
- Tente outra versão da mesma música

**Erro de segurança no Windows:**
- Use o `run.bat` para executar via Python (sem bloqueio)
- Ou desbloqueie o EXE nas propriedades

## 📃 Versão Atual

- ✅ Player funcionando com YouTube IFrame API
- ✅ Tradução completa para Português
- ✅ Playlist com auto-play
- ✅ Metadados para evitar bloqueio do Windows
- ✅ Tratamento de erros e vídeos bloqueados

## 🤝 Contribuição

Sinta-se à vontade para abrir issues ou pull requests!

## 📄 Licença

Este projeto está sob a licença MIT.
