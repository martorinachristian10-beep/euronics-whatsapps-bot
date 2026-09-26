@echo off
title Tunnel Pubblico Gratuito (Cloudflare - Nessuna registrazione)
echo ===================================================================
echo   TUNNEL PUBBLICO HTTPS PER WEBHOOK WHATSAPP (CLOUDFLARE)
echo ===================================================================
echo.
echo Avvio del tunnel verso la porta 5000...
echo.
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:5000
pause
