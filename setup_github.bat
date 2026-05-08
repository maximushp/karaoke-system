@echo off
echo ============================================
echo   Configuracao para GitHub
echo ============================================
echo.
echo 1. Crie um repositorio no GitHub:
echo    - Acesse https://github.com/new
echo    - Nome sugerido: karaoke-system
echo    - NAO marque "Initialize with README"
echo.
echo 2. Depois de criar, execute estes comandos (substitua SEU_USUARIO):
echo.
echo git remote add origin https://github.com/SEU_USUARIO/karaoke-system.git
echo git branch -M main
echo git push -u origin main
echo.
echo 3. Para adicionar o EXE (Releases):
echo    - Acesse seu repo no GitHub
echo    - Clique em "Releases" > "Create new release"
echo    - Faca upload do arquivo: dist\KaraokeSystem.exe
echo    - Adicione notas sobre a versao
echo.
pause
