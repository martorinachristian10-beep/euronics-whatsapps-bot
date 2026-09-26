import os
import sys

# Configura UTF-8 per supportare le emoji nella console di Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import ask_gemini, STORE_FACTS

def main():
    print("=" * 60)
    print("  SIMULATORE CHAT ASSISTENTE WHATSAPP EURONICS COMISO")
    print("=" * 60)
    print("Questo simulatore ti permette di chattare direttamente con il bot")
    print("come se fossi un cliente su WhatsApp, testando le sue risposte.")
    print("Scrivi 'esci' per terminare la conversazione.\n")
    
    sender_id = "whatsapp:+393330001122"
    
    while True:
        try:
            user_input = input("\nCliente (Tu): ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("esci", "exit", "quit"):
                print("Chiusura del simulatore. A presto!")
                break
                
            reply = ask_gemini(sender_id, user_input)
            print(f"\nAssistente Euronics: {reply}")
        except KeyboardInterrupt:
            print("\nInterrotto dall'utente.")
            break
        except Exception as e:
            print(f"\n[Errore]: {e}")

if __name__ == "__main__":
    main()
