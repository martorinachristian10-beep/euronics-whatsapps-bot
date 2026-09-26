import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Imposta ambiente fittizio per i test prima dell'import
os.environ["TWILIO_AUTH_TOKEN"] = "test_auth_token_12345"
os.environ["GEMINI_API_KEY"] = "test_gemini_key_abcde"
os.environ["GEMINI_MODEL"] = "gemini-2.0-flash"
os.environ["SKIP_TWILIO_VALIDATION"] = "false"

# Importa l'app e le funzioni
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as bot_app
from app import (
    _format_conversation_history_for_gemini,
    app,
    ask_gemini,
    conversations,
    webhook_url,
)


class TestEuronicsWhatsAppBot(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        conversations.clear()

    def test_health_check(self):
        """Verifica che l'endpoint di salute risponda 200 con messaggio corretto per i ping anti-sleep."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Assistente Euronics Comiso: online.", response.get_data(as_text=True))

    def test_incoming_forbidden_without_signature(self):
        """Verifica che una richiesta senza firma Twilio valida sia bloccata con 403 Forbidden."""
        response = self.client.post("/incoming", data={"From": "whatsapp:+393331112233", "Body": "Ciao"})
        self.assertEqual(response.status_code, 403)

    def test_incoming_empty_body(self):
        """Verifica il comportamento con messaggio privo di testo."""
        with patch.object(bot_app.validator, "validate", return_value=True):
            response = self.client.post(
                "/incoming",
                data={"From": "whatsapp:+393331112233", "Body": "   "},
                headers={"X-Twilio-Signature": "dummy_sig"}
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("<Response>", response.get_data(as_text=True))
            self.assertIn("Non ho ricevuto testo nel messaggio", response.get_data(as_text=True))

    def test_incoming_valid_message_with_gemini(self):
        """Verifica il flusso completo di ricezione e risposta TwiML."""
        with (
            patch.object(bot_app.validator, "validate", return_value=True),
            patch("app.ask_gemini", return_value="Ciao! Siamo aperti dalle 9 alle 13.") as mock_ask,
        ):
            response = self.client.post(
                "/incoming",
                data={"From": "whatsapp:+393331112233", "Body": "A che ora aprite?"},
                headers={"X-Twilio-Signature": "dummy_sig"}
            )
            self.assertEqual(response.status_code, 200)
            mock_ask.assert_called_once_with("whatsapp:+393331112233", "A che ora aprite?")
            xml_data = response.get_data(as_text=True)
            self.assertIn("<Response>", xml_data)
            self.assertIn("Ciao! Siamo aperti dalle 9 alle 13.", xml_data)

    def test_incoming_skip_twilio_validation(self):
        """Verifica che con SKIP_TWILIO_VALIDATION=True le chiamate locali bypassino la firma."""
        with patch("app.SKIP_TWILIO_VALIDATION", True), patch("app.ask_gemini", return_value="Test bypass ok"):
            response = self.client.post(
                "/incoming",
                data={"From": "whatsapp:+393331112233", "Body": "Test"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("Test bypass ok", response.get_data(as_text=True))

    def test_format_conversation_history_constraints(self):
        """
        Verifica che la cronologia per Gemini rispetti sempre le regole API:
        1. Primo turno DEVE essere 'user'
        2. I turni devono alternarsi user / model
        3. Turni consecutivi dello stesso ruolo vengono unificati
        4. Ultimo turno DEVE essere 'user'
        """
        raw_history = [
            {"role": "assistant", "content": "Messaggio rimosso perché all'inizio"},
            {"role": "user", "content": "Ciao"},
            {"role": "user", "content": "Volevo sapere gli orari"},
            {"role": "assistant", "content": "Aperti 9-13 e 16:30-20:30"},
            {"role": "user", "content": "Grazie"},
        ]
        formatted = _format_conversation_history_for_gemini(raw_history)
        self.assertEqual(len(formatted), 3)
        self.assertEqual(formatted[0]["role"], "user")
        self.assertEqual(formatted[0]["parts"], ["Ciao", "Volevo sapere gli orari"])
        self.assertEqual(formatted[1]["role"], "model")
        self.assertEqual(formatted[1]["parts"], ["Aperti 9-13 e 16:30-20:30"])
        self.assertEqual(formatted[2]["role"], "user")
        self.assertEqual(formatted[2]["parts"], ["Grazie"])

    def test_format_conversation_history_prunes_trailing_assistant(self):
        """Verifica che i messaggi finali con ruolo 'assistant' vengano rimossi perché Gemini richiede 'user' alla fine."""
        raw_history = [
            {"role": "user", "content": "Ciao"},
            {"role": "assistant", "content": "Salve!"},
            {"role": "assistant", "content": "Come posso aiutarti?"},
        ]
        formatted = _format_conversation_history_for_gemini(raw_history)
        self.assertEqual(len(formatted), 1)
        self.assertEqual(formatted[0]["role"], "user")
        self.assertEqual(formatted[0]["parts"], ["Ciao"])

    def test_format_conversation_history_filters_empty_content(self):
        """Verifica che contenuti vuoti o solo spazi vengano scartati."""
        raw_history = [
            {"role": "user", "content": "   "},
            {"role": "user", "content": "Messaggio valido"},
            {"role": "assistant", "content": ""},
        ]
        formatted = _format_conversation_history_for_gemini(raw_history)
        self.assertEqual(len(formatted), 1)
        self.assertEqual(formatted[0]["role"], "user")
        self.assertEqual(formatted[0]["parts"], ["Messaggio valido"])

    def test_ask_gemini_google_genai_backend_success(self):
        """Verifica la generazione corretta tramite SDK google-genai."""
        sender = "whatsapp:+393339991122"
        with patch("app._GEMINI_BACKEND", "google-genai"), patch.object(bot_app, "gemini_client") as mock_client:
            mock_res = MagicMock()
            mock_res.text = "Siamo aperti dal lunedì al sabato."
            mock_client.models.generate_content.return_value = mock_res

            reply = ask_gemini(sender, "Quando aprite?")
            self.assertEqual(reply, "Siamo aperti dal lunedì al sabato.")
            self.assertEqual(len(conversations[sender]), 2)
            self.assertEqual(conversations[sender][0]["role"], "user")
            self.assertEqual(conversations[sender][1]["role"], "assistant")

    def test_ask_gemini_google_generativeai_backend_success(self):
        """Verifica la generazione corretta tramite SDK legacy google-generativeai."""
        sender = "whatsapp:+393339992233"
        mock_genai_legacy = MagicMock()
        mock_model_instance = MagicMock()
        mock_res = MagicMock()
        mock_res.text = "Consegne disponibili a domicilio."
        mock_model_instance.generate_content.return_value = mock_res
        mock_genai_legacy.GenerativeModel.return_value = mock_model_instance

        with patch("app._GEMINI_BACKEND", "google-generativeai"), patch(
            "app.genai_legacy", mock_genai_legacy, create=True
        ):
            reply = ask_gemini(sender, "Fate consegne?")
            self.assertEqual(reply, "Consegne disponibili a domicilio.")
            mock_genai_legacy.configure.assert_called_once_with(api_key=os.environ["GEMINI_API_KEY"])

    def test_ask_gemini_safety_block_handling(self):
        """Verifica il recupero sicuro quando response.text genera eccezione (es. safety filter)."""
        sender = "whatsapp:+393339993344"
        with patch("app._GEMINI_BACKEND", "google-genai"), patch.object(bot_app, "gemini_client") as mock_client:
            mock_res = MagicMock()
            # Simula ValueError quando si accede a response.text su contenuto bloccato
            type(mock_res).text = unittest.mock.PropertyMock(side_effect=ValueError("Blocked by safety"))
            # Simula presenza di parti nel candidato
            mock_part = MagicMock()
            mock_part.text = "Risposta recuperata dalle parti."
            mock_cand = MagicMock()
            mock_cand.content.parts = [mock_part]
            mock_res.candidates = [mock_cand]
            mock_client.models.generate_content.return_value = mock_res

            reply = ask_gemini(sender, "Test safety")
            self.assertEqual(reply, "Risposta recuperata dalle parti.")

    def test_ask_gemini_empty_response_fallback(self):
        """Verifica il fallback se la risposta dell'AI è completamente vuota."""
        sender = "whatsapp:+393339994455"
        with patch("app._GEMINI_BACKEND", "google-genai"), patch.object(bot_app, "gemini_client") as mock_client:
            mock_res = MagicMock()
            mock_res.text = ""
            mock_res.candidates = []
            mock_client.models.generate_content.return_value = mock_res

            reply = ask_gemini(sender, "Messaggio con risposta vuota")
            self.assertIn("Scusa, non sono riuscito a rispondere", reply)
            self.assertIn("+39 0932 723173", reply)

    def test_ask_gemini_error_handling(self):
        """Verifica che in caso di eccezione non gestita dell'API venga restituito il messaggio di problema tecnico."""
        sender = "whatsapp:+393339998877"
        with patch("app._GEMINI_BACKEND", "google-genai"), patch.object(bot_app, "gemini_client") as mock_client:
            mock_client.models.generate_content.side_effect = Exception("API rate limit o errore di rete")
            reply = ask_gemini(sender, "Avete la PS5?")
            self.assertEqual(reply, "Al momento ho un problema tecnico. Riprova tra poco o chiama il negozio.")
            self.assertEqual(len(conversations[sender]), 2)
            self.assertEqual(conversations[sender][0]["role"], "user")
            self.assertEqual(conversations[sender][1]["role"], "assistant")

    def test_history_max_turns_truncation(self):
        """Verifica che la cronologia non superi MAX_TURNS (12)."""
        sender = "whatsapp:+393330000000"
        with patch("app._GEMINI_BACKEND", "google-genai"), patch.object(bot_app, "gemini_client") as mock_client:
            mock_res = MagicMock()
            mock_res.text = "Risposta simulata"
            mock_client.models.generate_content.return_value = mock_res

            # Invia 10 messaggi (20 turni tra user e assistant)
            for i in range(10):
                ask_gemini(sender, f"Messaggio {i}")

            # La cronologia deve essere limitata a MAX_TURNS (12)
            self.assertLessEqual(len(conversations[sender]), bot_app.MAX_TURNS)

    def test_webhook_url_reverse_proxy_multi_proto(self):
        """Verifica che webhook_url parsi correttamente intestazioni composite da proxy come Render e ngrok."""
        with app.test_request_context(
            "/incoming",
            base_url="http://127.0.0.1:5000",
            headers={
                "X-Forwarded-Proto": "https, http",
                "X-Forwarded-Host": "euronics-bot.onrender.com, internal-router"
            }
        ):
            url = webhook_url()
            self.assertEqual(url, "https://euronics-bot.onrender.com/incoming")

    def test_webhook_url_preserves_query_string(self):
        """Verifica che webhook_url conservi la query string necessaria alla validazione Twilio."""
        with app.test_request_context(
            "/incoming?channel=whatsapp&store=comiso",
            base_url="https://euronics-bot.onrender.com",
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "euronics-bot.onrender.com"
            }
        ):
            url = webhook_url()
            self.assertEqual(url, "https://euronics-bot.onrender.com/incoming?channel=whatsapp&store=comiso")

    def test_incoming_valid_signature_real_hmac(self):
        """Verifica che una richiesta con firma HMAC-SHA1 Twilio reale calcolata venga validata con successo."""
        from twilio.request_validator import RequestValidator
        auth_token = os.environ["TWILIO_AUTH_TOKEN"]
        real_validator = RequestValidator(auth_token)
        url = "http://localhost/incoming"
        params = {"From": "whatsapp:+393331112233", "Body": "A che ora chiudete?"}
        signature = real_validator.compute_signature(url, params)

        with patch("app.ask_gemini", return_value="Chiudiamo alle 20:30."):
            response = self.client.post(
                "/incoming",
                data=params,
                headers={"X-Twilio-Signature": signature}
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("Chiudiamo alle 20:30.", response.get_data(as_text=True))

    def test_incoming_trailing_slash(self):
        """Verifica che /incoming/ (con trailing slash) non restituisca 308 redirect ma risponda 200."""
        with patch("app.SKIP_TWILIO_VALIDATION", True), patch("app.ask_gemini", return_value="Test trailing slash ok"):
            response = self.client.post(
                "/incoming/",
                data={"From": "whatsapp:+393331112233", "Body": "Test"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("Test trailing slash ok", response.get_data(as_text=True))

    def test_ask_gemini_missing_api_key(self):
        """Verifica che in assenza di API key venga restituito il messaggio di problema tecnico."""
        sender = "whatsapp:+393339995566"
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}, clear=False):
            reply = ask_gemini(sender, "Avete offerte?")
            self.assertEqual(reply, "Al momento ho un problema tecnico. Riprova tra poco o chiama il negozio.")

    def test_ask_gemini_no_backend_installed(self):
        """Verifica la gestione del caso in cui nessun backend Gemini sia disponibile."""
        sender = "whatsapp:+393339996677"
        with patch("app._GEMINI_BACKEND", None):
            reply = ask_gemini(sender, "Avete PC?")
            self.assertEqual(reply, "Al momento ho un problema tecnico. Riprova tra poco o chiama il negozio.")

    def test_resolve_backend_environment_override(self):
        """Verifica che la variabile d'ambiente GEMINI_BACKEND consenta di selezionare il backend."""
        from app import _resolve_backend
        with patch("app.genai", MagicMock()), patch("app.genai_legacy", MagicMock()):
            with patch.dict(os.environ, {"GEMINI_BACKEND": "google-generativeai"}):
                self.assertEqual(_resolve_backend(), "google-generativeai")
            with patch.dict(os.environ, {"GEMINI_BACKEND": "google-genai"}):
                self.assertEqual(_resolve_backend(), "google-genai")

    def test_ask_gemini_response_length_truncation(self):
        """Verifica che risposte troppo lunghe (>1550 car) vengano troncate per rispettare il limite WhatsApp di 1600."""
        sender = "whatsapp:+393339997788"
        with patch("app._GEMINI_BACKEND", "google-genai"), patch.object(bot_app, "gemini_client") as mock_client:
            mock_res = MagicMock()
            mock_res.text = "A" * 2000
            mock_client.models.generate_content.return_value = mock_res

            reply = ask_gemini(sender, "Dammi un testo lunghissimo")
            self.assertLessEqual(len(reply), 1600)
            self.assertTrue(reply.endswith("..."))


if __name__ == "__main__":
    unittest.main()
