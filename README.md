# 🤖 Assistente WhatsApp per Euronics Comiso (Backend Gemini)

Backend Flask pronto per la produzione collegato a **Twilio WhatsApp API** e alimentato dai modelli **Google Gemini** (tramite il nuovo SDK unificato `google-genai`).

---

## 📋 Indice dei Contenuti
1. [Differenza tra Prototipo Browser e Backend Reale](#1-differenza-tra-prototipo-browser-e-backend-reale)
2. [Google AI Pro vs API: Verifica Privacy Dati](#2-google-ai-pro-vs-api-verifica-privacy-dati)
3. [Configurazione e Installazione Locale](#3-configurazione-e-installazione-locale)
4. [Test Locale con Twilio Sandbox e ngrok](#4-test-locale-con-twilio-sandbox-e-ngrok)
5. [Deploy Gratuito su Render.com + Trucco Anti-Sleep](#5-deploy-gratuito-su-rendercom--trucco-anti-sleep)
6. [Esecuzione dei Test Unitari](#6-esecuzione-dei-test-unitari)
7. [Prossimi Passi per il Pilota con il Negozio](#7-prossimi-passi-per-il-pilota-con-il-negozio)

---

## 1. Differenza tra Prototipo Browser e Backend Reale

- **Prototipo Browser (`agente_prenotazioni/`):**
  - Interfaccia grafica web (`index.html`) con simulazione stile WhatsApp e dashboard titolare (`admin.html`).
  - Ideale per presentare il bot dal vivo al responsabile di Euronics Comiso dal proprio PC o tablet senza configurare numeri di telefono.
- **Backend Reale (`euronics_whatsapp/` - Questa Cartella):**
  - Servizio Flask con webhook `/incoming` che gestisce veri messaggi WhatsApp inviati tramite Twilio.
  - Genera risposte ufficiali in formato **TwiML XML**.
  - Valida crittograficamente la firma di ogni richiesta tramite `X-Twilio-Signature`.
  - Mantiene la memoria della conversazione per ogni numero telefonico (`MAX_TURNS = 12`).
  - È integrato con l'SDK **Google Gemini** invece di Anthropic Claude.

---

## 2. Google AI Pro vs API: Verifica Privacy Dati

> [!IMPORTANT]
> **Attenzione alla clausola di addestramento:**
> Nel piano *gratuito* di Google AI Studio, Google si riserva il diritto di utilizzare i prompt e le risposte per il miglioramento dei propri modelli (cosa non compatibile con il GDPR per dati reali di clienti WhatsApp).
> 
> Avere un abbonamento personale a **Google One AI Premium / Google AI Pro** dà accesso all'interfaccia Gemini web, **MA l'accesso alle API tramite Google AI Studio ha una fatturazione separata**.
> 
> **Come verificare che la chiave API sia a pagamento (senza addestramento sui dati):**
> 1. Accedi a [Google AI Studio](https://aistudio.google.com/).
> 2. Vai su **Settings** > **Billing** (o *Project Billing*).
> 3. Verifica che il progetto Cloud sia collegato a un account di fatturazione attivo (*Pay-as-you-go* con carta di credito del genitore/tutore).
> 4. Con il billing attivo, il tuo tier passa da *Free Tier* a *Tier 1 (Pay-as-you-go)*: in questa modalità Google **NON** usa i dati delle API per addestrare i modelli e si applicano i termini Enterprise/Commercial privacy.

---

## 3. Configurazione e Installazione Locale

### Requisiti
- Python 3.10+
- Un account Twilio (gratuito)
- Una chiave API Gemini da [Google AI Studio](https://aistudio.google.com/)

### Installazione Dipendenze
Dalla cartella `euronics_whatsapp`:
```bash
pip install -r requirements.txt
```

### File di Configurazione `.env`
Crea una copia del file `.env.example` chiamandola `.env`:
```env
TWILIO_AUTH_TOKEN=il_tuo_auth_token_twilio
GEMINI_API_KEY=la_tua_chiave_gemini
GEMINI_MODEL=gemini-2.0-flash
SKIP_TWILIO_VALIDATION=false
PORT=5000
```

---

## 4. Test Locale con Twilio Sandbox e ngrok

### Passo 1: Sandbox WhatsApp su Twilio
1. Accedi alla console Twilio: **Messaging** > **Try it out** > **Send a WhatsApp message**.
2. Segui le istruzioni: invia il codice (es. `join <parola-codice>`) dal tuo smartphone al numero sandbox di Twilio (+1 415 523 8886).

### Passo 2: Avvia il server Flask locale
```bash
python app.py
```
Il server si avvierà su `http://localhost:5000`.

### Passo 3: Esponi la porta con ngrok
In un altro terminale:
```bash
ngrok http 5000
```
Copia l'URL HTTPS generato (es. `https://xxxx-xx-xx.ngrok-free.app`).

### Passo 4: Collega il Webhook su Twilio
1. Su Twilio Console > **Messaging** > **Settings** > **WhatsApp sandbox settings**.
2. Nel campo **"WHEN A MESSAGE COMES IN"**, inserisci:
   ```
   https://xxxx-xx-xx.ngrok-free.app/incoming
   ```
   Metodo: `HTTP POST`.
3. Clicca **Save**.
4. Manda un messaggio WhatsApp dal tuo telefono: l'assistente risponderà applicando le regole Euronics!

---

## 5. Deploy Gratuito su Render.com + Trucco Anti-Sleep

### Limite del piano Free di Render
Render.com offre 750 ore/mese gratuite per Web Service, ma spegne i server inattivi dopo 15 minuti di assenza di traffico. Il risveglio ("cold start") richiede 30-50 secondi. Twilio ha un timeout massimo di 15 secondi per i webhook: un messaggio arrivato a server addormentato andrebbe in timeout.

### Soluzione: Ping Anti-Sleep ogni 10 minuti
Render non si addormenta se riceve una richiesta HTTP almeno ogni 14 minuti. Effettuando un ping ogni 10 minuti sull'endpoint di salute `/`:
- Il server resta **sempre caldo e reattivo (<1s di risposta)**.
- Il consumo orario rimane esattamente pari al tempo naturale di 1 mese (circa 720-744 ore), restando perfettamente **dentro le 750 ore gratuite mensili**.

### Procedura di Deploy su Render:
1. Crea un repository GitHub privato (es. `euronics-whatsapp-bot`) e fai il push del contenuto di `euronics_whatsapp/`.
2. Su [Render.com](https://render.com/), crea un **New Web Service**:
   - Collega il repository GitHub.
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app` (oppure rileverà automaticamente il `Procfile`)
3. Aggiungi le **Environment Variables** su Render:
   - `TWILIO_AUTH_TOKEN`: il tuo token di Twilio
   - `GEMINI_API_KEY`: la tua chiave Google AI Studio
   - `GEMINI_MODEL`: `gemini-2.0-flash` (oppure `gemini-1.5-flash`)
   - `SKIP_TWILIO_VALIDATION`: `false`
4. Clicca **Deploy Web Service**. Render fornirà un URL pubblico (es. `https://euronics-bot.onrender.com`).
5. Aggiorna il webhook nella sandbox Twilio con:
   ```
   https://euronics-bot.onrender.com/incoming
   ```
6. **Configura il Ping Anti-Sleep:**
   - Registrati gratuitamente su [UptimeRobot](https://uptimerobot.com/) o [cron-job.org](https://cron-job.org/).
   - Crea un nuovo monitor HTTP:
     - URL: `https://euronics-bot.onrender.com/`
     - Intervallo: **ogni 10 minuti**
     - Metodo: `GET`

---

## 6. Esecuzione dei Test Unitari

Il progetto include test automatizzati per validare:
- Health check route `/`
- Rifiuto di richieste prive di firma Twilio valida (403)
- Gestione di messaggi vuoti
- Simulazione di risposta TwiML XML con risposte Gemini
- Rispetto dei vincoli API di Gemini (primo turno 'user', alternanza ruoli, fusione messaggi consecutivi)
- Gestione errori e limiti di cronologia (`MAX_TURNS`)

Per eseguire i test:
```bash
python -m unittest test_app.py
```

---

## 7. Prossimi Passi per il Pilota con il Negozio

1. **Test Interno:** Prova il bot dal tuo WhatsApp personale inviando domande tipiche (orari, finanziamento tasso zero, riparazione notebook, prezzi volantino).
2. **Presentazione al Negozio:** Mostra la demo live al gestore di Euronics Comiso usando il prototipo browser (`agente_prenotazioni/`) o la chat WhatsApp reale.
3. **Accordo Scritto Minimo:** Prima di accendere il bot su un canale aperto al pubblico:
   - Specificare che si tratta di un test pilota a tempo (es. 30 giorni) e gratuito.
   - Definire la responsabilità sui dati: chi scrive su WhatsApp accetta il trattamento per la sola gestione della richiesta.
4. **Passaggio al Numero Ufficiale del Negozio:**
   - Creazione del WhatsApp Business Account sul Meta Business Manager **intestato al negozio**.
   - Integrazione delle credenziali definitive nel backend.
