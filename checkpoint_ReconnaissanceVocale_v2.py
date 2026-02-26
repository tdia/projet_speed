import streamlit as st
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
import io
import time
import google.generativeai as genai
import os
from gtts import gTTS
import io
import base64

# ================== CONFIGURATION PAGE ==================
st.set_page_config(
    page_title="VocalCloud - Transcripteur & Traducteur",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================== CONFIGURATION GEMINI ==================
# Note: Idéalement, utilisez st.secrets ou une variable d'environnement
# Pour ce checkpoint, on utilise la clé fourni
genai.configure(api_key=GEMINI_API_KEY)
# ================== DESIGN / UI (CSS) ==================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    * { font-family: 'Outfit', sans-serif; }
    
    .main {
        background: radial-gradient(circle at top left, #1e1e2f, #121212);
        color: #e0e0e0;
    }

    .header-text {
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem;
        text-align: center;
        margin-bottom: 0.5rem;
    }

    .subtitle-text {
        text-align: center;
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    .st-emotion-cache-1r6slb0, .st-emotion-cache-12w0qpk {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px !important;
        padding: 2rem !important;
    }

    /* Amélioration des zones de texte (text_area) */
    .stTextArea textarea {
        background: rgba(255, 255, 255, 0.05) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 15px !important;
        padding: 15px !important;
        font-size: 1.15rem !important;
        line-height: 1.6 !important;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.1) !important;
        transition: border 0.3s ease;
    }
    .stTextArea textarea:focus {
        border: 1px solid #6366f1 !important;
        box-shadow: 0 0 10px rgba(99, 102, 241, 0.3) !important;
    }
    .stTextArea label {
        display: none !important; /* On cache le label standard au profit de nos markdowns avec émojis */
    }

    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
        width: 100%;
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(99, 102, 241, 0.3);
    }

    .translation-card {
        background: rgba(99, 102, 241, 0.1);
        border-left: 5px solid #6366f1;
        padding: 1.5rem;
        border-radius: 10px;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ================== LOGIC / UTILS ==================

import tempfile

def transcribe_audio_bytes(audio_bytes, language="fr-FR"):
    """Transcription utilisant l'IA Gemini (évite la dépendance FFmpeg)."""
    try:
        # Créer un fichier temporaire pour l'audio (supporte nativement MP3, WebM, etc. via Gemini)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        # Utiliser le modèle flash pour la rapidité
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # Télécharger le fichier vers l'API Gemini
        # Gemini gère automatiquement les différents formats audio
        uploaded_audio = genai.upload_file(path=tmp_path)
        
        # Prompt de transcription
        language_name = {"fr-FR": "Français", "wo-SN": "Wolof", "en-US": "Anglais", "es-ES": "Espagnol", "de-DE": "Allemand", "it-IT": "Italien"}.get(language, language)
        prompt = f"Peux-tu transcrire cet audio précisément en {language_name} ? Réponds uniquement avec le texte transcrit, sans commentaires additionnels."
        
        response = model.generate_content([uploaded_audio, prompt])
        
        # Supprimer le fichier temporaire et le fichier sur le cloud Gemini
        os.remove(tmp_path)
        # uploaded_audio.delete() # Optionnel ou via API distincte selon version
        
        return response.text.strip()
    except Exception as e:
        return f"❌ Erreur de transcription IA : {str(e)}"

def translate_text(text, target_language):
    if not text or "Erreur" in text:
        return "Aucun texte valide à traduire."
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # Le secret d'une voix parfaite: Demander à l'IA d'écrire en phonétique francophone native.
        wolof_instruction = ""
        if "Wolof" in target_language:
            wolof_instruction = """ 
            IMPORTANT : Tu dois impérativement écrire la traduction Wolof en utilisant l'alphabet phonétique Français.
            N'utilise AUCUNE lettre wolof spéciale comme ŋ, ë, ñ, x, q, c.
            - Le 'x' devient 'kh'.
            - Le 'c' devient 'thi'.
            - Le 'j' devient 'dji'.
            - Le 'u' devient 'ou'.
            - Le 'ë' devient 'eu'.
            - Le 'ñ' devient 'gn'.
            Évite la nasalisation (ex: écris 'khamé' ou 'khamme' au lieu de 'xam', 'nagne' au lieu de 'nañ').
            Ceci est crucial pour qu'un lecteur vocal français francophone ne bégaye pas et lise naturellement avec un accent sénégalais fluide sans saccades.
            """
            
        prompt = f"Traduis le texte suivant en {target_language}. {wolof_instruction}\nRéponds uniquement avec la traduction, sans commentaire ni guillemets :\n\n{text}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"❌ Erreur traduction : {str(e)}"

# ================== INTERFACE ET AUTHENTIFICATION ==================

def check_password():
    """Gère l'affichage du portail de connexion et valide l'utilisateur."""
    def password_entered():
        # Identifiants de test (Peut être relié à une base de données)
        if st.session_state["username_input"].strip().lower() == "admin" and st.session_state["password_input"] == "admin":
            st.session_state["password_correct"] = True
            st.session_state["logged_user"] = st.session_state["username_input"]
            del st.session_state["password_input"]  # Sécurité: Ne pas garder le mot de passe en mémoire
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Premier démarrage : Afficher le formulaire avec style
        st.markdown('<div style="margin-top: 10vh;"></div>', unsafe_allow_html=True)
        st.markdown('<h1 style="text-align: center; color: #4facfe;">🔒 Accès Sécurisé</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: #94a3b8; margin-bottom: 2rem;">Veuillez vous identifier pour accéder à VocalCloud AI.</p>', unsafe_allow_html=True)
        
        _, col_login, _ = st.columns([1, 1.5, 1])
        with col_login:
            with st.container(border=True):
                st.text_input("👤 Nom d'utilisateur", key="username_input")
                st.text_input("🔑 Mot de passe", type="password", key="password_input")
                st.button("Se connecter 🚀", use_container_width=True, on_click=password_entered, type="primary")
        return False
        
    elif not st.session_state["password_correct"]:
        # Erreur de connexion
        st.markdown('<div style="margin-top: 10vh;"></div>', unsafe_allow_html=True)
        st.markdown('<h1 style="text-align: center; color: #4facfe;">🔒 Accès Sécurisé</h1>', unsafe_allow_html=True)
        
        _, col_login, _ = st.columns([1, 1.5, 1])
        with col_login:
            with st.container(border=True):
                st.error("😕 Identifiant ou mot de passe incorrect.")
                st.text_input("👤 Nom d'utilisateur", key="username_input")
                st.text_input("🔑 Mot de passe", type="password", key="password_input")
                st.button("Se connecter 🚀", use_container_width=True, on_click=password_entered, type="primary")
        return False
    else:
        # Utilisateur validé
        return True

def main():
    if not check_password():
        return
        
    st.markdown('<h1 class="header-text">VocalCloud AI</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle-text">Transcription haute précision & Traduction instantanée IA</p>', unsafe_allow_html=True)

    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3293/3293811.png", width=80)
        st.title("Configuration")
        
        src_lang = st.selectbox(
            "Langue source (Audio)",
            ["fr-FR", "wo-SN", "en-US", "es-ES", "de-DE", "it-IT"],
            format_func=lambda x: {"fr-FR": "🇫🇷 Français", "wo-SN": "🇸🇳 Wolof", "en-US": "🇺🇸 Anglais", "es-ES": "🇪🇸 Espagnol", "de-DE": "🇩🇪 Allemand", "it-IT": "🇮🇹 Italien"}.get(x, x)
        )

        st.divider()
        st.subheader("Traduire en...")
        target_lang_name = st.selectbox(
            "Langue cible",
            ["Wolof", "Français", "Anglais", "Arabe", "Espagnol", "Chinois", "Allemand"]
        )
        
        st.divider()
        if st.button("➕ Nouvelle Session", use_container_width=True):
            # Conserver la connexion, mais effacer les données
            user = st.session_state.get("logged_user", "admin")
            pass_ok = st.session_state.get("password_correct", True)
            st.session_state.clear()
            st.session_state["logged_user"] = user
            st.session_state["password_correct"] = pass_ok
            st.rerun()

        if st.button("🚪 Déconnexion", use_container_width=True, type="secondary"):
            st.session_state.clear()
            st.rerun()

        st.divider()
        st.caption("Propulsé par Google Speech & Gemini AI")

    col1, col2 = st.columns([1, 1.2], gap="large")

    with col1:
        st.markdown("### 🎙️ 1. Entrée Audio")
        tab1, tab2, tab3 = st.tabs(["⚡ En direct", "🔴 Enregistrer", "📁 Charger"])
        
        audio_input = None

        with tab2:
            audio_data = mic_recorder(start_prompt="🎤 Enregistrer", stop_prompt="⏹️ Arrêter", key='recorder')
            if audio_data:
                st.audio(audio_data['bytes'])
                audio_input = audio_data['bytes']
        
        with tab3:
            up = st.file_uploader("Fichier audio", type=["wav", "mp3"])
            if up:
                st.audio(up)
                audio_input = up.read()

        with tab1:
            st.markdown("#### ⚡ Transcription & Traduction Instantanée")
            import streamlit.components.v1 as components
            
            js_target_lang = "wo" if "Wolof" in target_lang_name else "fr" if "Français" in target_lang_name else "en" if "Anglais" in target_lang_name else "ar" if "Arabe" in target_lang_name else "es"
            gtts_lang = "fr" if "Wolof" in target_lang_name else "fr" if "Français" in target_lang_name else "en" if "Anglais" in target_lang_name else "ar" if "Arabe" in target_lang_name else "es" if "Espagnol" in target_lang_name else "zh" if "Chinois" in target_lang_name else "de" if "Allemand" in target_lang_name else "en"
            
            catch_speech_js = f"""
                <style>
                    .mic-btn {{
                        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
                        color: white; border: none; width: 80px; height: 80px; border-radius: 50%;
                        cursor: pointer; font-size: 2.5em; display: flex; align-items: center; justify-content: center;
                        box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4); transition: transform 0.2s ease, box-shadow 0.2s ease;
                        margin: 0 auto;
                    }}
                    .mic-btn:hover {{
                        transform: scale(1.05); box-shadow: 0 12px 25px rgba(99, 102, 241, 0.6);
                    }}
                    .stop-btn {{
                        background: #ef4444; color: white; border: none; width: 80px; height: 80px; border-radius: 50%;
                        cursor: pointer; font-size: 2.5em; display: none; align-items: center; justify-content: center;
                        box-shadow: 0 8px 20px rgba(239, 68, 68, 0.4); margin: 0 auto;
                        animation: pulse 1.5s infinite;
                    }}
                    @keyframes pulse {{
                        0% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }}
                        70% {{ box-shadow: 0 0 0 20px rgba(239, 68, 68, 0); }}
                        100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }}
                    }}
                </style>
                <div style="background: rgba(255,255,255,0.03); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); font-family: 'Outfit', sans-serif;">
                    
                    <button id="start-btn" class="mic-btn" title="Activer le mode Live">🎤</button>
                    <button id="stop-btn" class="stop-btn" title="Arrêter la capture">⏹️</button>
                    
                    <div id="status" style="color: #4facfe; font-size: 0.9em; text-align: center; margin-top: 15px; margin-bottom: 25px; font-weight: 600;">Cliquez sur le micro au centre pour parler.</div>
                    
                    <div style="margin-bottom: 5px; color: #94a3b8; font-size: 0.8em;">Transcription :</div>
                    <div id="live-output" style="background: #ffffff; padding: 15px; border-radius: 8px; font-size: 1.1em; min-height: 50px; color: #000000; font-style: italic; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">...</div>
                    
                    <div style="margin-bottom: 5px; color: #6366f1; font-size: 0.8em;">Traduction :</div>
                    <div id="live-translation" style="background: #ffffff; padding: 15px; border-radius: 8px; font-size: 1.1em; min-height: 50px; color: #000000; font-weight: 600; line-height: 1.4; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">...</div>
                    
                    <div style="margin-top: 15px; margin-bottom: 5px; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 10px;">
                        <input type="checkbox" id="auto-speak-cb" checked style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer; accent-color: #6366f1;">
                        <label for="auto-speak-cb" style="cursor: pointer; color: #f8fafc; font-size: 0.9em; font-weight: 500;">🔊 Lire automatiquement la traduction en public</label>
                    </div>
                    
                    <button id="save-btn" style="background: #10b981; color: white; border: none; padding: 12px; border-radius: 10px; cursor: pointer; font-weight: 600; width: 100%; margin-top: 15px; transition: transform 0.2s;">💾 Enregistrer vers Résultats</button>
                </div>

                <script>
                    const output = document.getElementById('live-output');
                    const transOutput = document.getElementById('live-translation');
                    const startBtn = document.getElementById('start-btn');
                    const stopBtn = document.getElementById('stop-btn');
                    const saveBtn = document.getElementById('save-btn');
                    const status = document.getElementById('status');
                    
                    let recognition;
                    let fullFinalText = "";
                    let fullTranslationText = "";
                    let isStopped = true;
                    
                    // LECTURE VOCALE NATIVE AVEC PHONÉTIQUE
                    let audioQueue = [];
                    let isPlayingAudio = false;

                    function phonetizeWolof(text) {{
                        const isWolof = "{target_lang_name}".includes("Wolof");
                        if (!isWolof) return text;
                        // Algorithme Avancé de Phonétisation Wolof vers Français (Natif)
                        let t = text;
                        t = t.replace(/e/g, "é").replace(/E/g, "É");
                        t = t.replace(/ë/g, "eu").replace(/Ë/g, "Eu");
                        t = t.replace(/c/g, "thi").replace(/C/g, "Thi");
                        t = t.replace(/j/g, "dji").replace(/J/g, "Dji");
                        t = t.replace(/x/g, "kh").replace(/X/g, "Kh");
                        t = t.replace(/ñ/g, "gn").replace(/Ñ/g, "Gn");
                        t = t.replace(/ŋ/g, "ng").replace(/Ŋ/g, "Ng");
                        t = t.replace(/u/g, "ou").replace(/U/g, "Ou");
                        t = t.replace(/q/g, "k").replace(/Q/g, "K");
                        
                        // Garder le son "G" dur avant les voyelles (ex: ngéén ne doit pas dire njéén)
                        t = t.replace(/gé/g, "gué").replace(/Gé/g, "Gué");
                        t = t.replace(/gi/g, "gui").replace(/Gi/g, "Gui");
                        t = t.replace(/geu/g, "gueu").replace(/Geu/g, "Gueu");
                        
                        // Lettrines longues (Wa -> Oua pour éviter le V français)
                        t = t.replace(/wa/g, "oua").replace(/Wa/g, "Oua");
                        t = t.replace(/wé/g, "oué").replace(/Wé/g, "Oué");
                        t = t.replace(/wi/g, "oui").replace(/Wi/g, "Oui");
                        t = t.replace(/wo/g, "ouo").replace(/Wo/g, "Ouo");
                        t = t.replace(/wou/g, "ou").replace(/Wou/g, "Ou");

                        t = t.replace(/aa/g, "a").replace(/éé/g, "é").replace(/ii/g, "i").replace(/oo/g, "o").replace(/ouou/g, "ou");
                        
                        // Éviter la nasalisation française (ex: "Xam" -> khame au lieu de khan, "man" -> manne au lieu de ment)
                        t = t.replace(/([aeiouéoóòu])([nm])\b/gi, "$1$2e");
                        t = t.replace(/([aeiouéoóòu])([nm])(?=[bcdfghjklmnpqrstvwxz])/gi, "$1$2e");
                        
                        return t;
                    }}

                    function playNextAudio() {{
                        if (audioQueue.length === 0) {{
                            isPlayingAudio = false;
                            return;
                        }}
                        isPlayingAudio = true;
                        
                        const textToSpeak = audioQueue.shift();
                        if (!('speechSynthesis' in window)) {{
                            playNextAudio();
                            return;
                        }}

                        // Appliquer la phonétique si la langue cible est le Wolof
                        const phoneticText = phonetizeWolof(textToSpeak);
                        const utterance = new SpeechSynthesisUtterance(phoneticText);
                        
                        let langTTS = "fr-FR";
                        if ("{target_lang_name}".includes("Anglais")) langTTS = "en-US";
                        else if ("{target_lang_name}".includes("Espagnol")) langTTS = "es-ES";
                        else if ("{target_lang_name}".includes("Arabe")) langTTS = "ar-SA";
                        else if ("{target_lang_name}".includes("Chinois")) langTTS = "zh-CN";
                        else if ("{target_lang_name}".includes("Allemand")) langTTS = "de-DE";
                        
                        const voices = window.speechSynthesis.getVoices();
                        // Recherche ciblée sur des voix d'hommes
                        let bestVoice = voices.find(v => v.lang.includes(langTTS.split('-')[0]) && (v.name.includes("Male") || v.name.includes("Paul") || v.name.includes("Thomas") || v.name.includes("Henri") || v.name.includes("Guy") || v.name.includes("David") || v.name.includes("homme") || v.name.includes("Conrad")));
                        
                        if (!bestVoice) bestVoice = voices.find(v => v.lang.includes(langTTS.split('-')[0]) && v.name.includes("Google"));
                        if (!bestVoice) bestVoice = voices.find(v => v.lang.includes(langTTS.split('-')[0]));
                        
                        if (bestVoice) utterance.voice = bestVoice;
                        else utterance.lang = langTTS;
                        
                        utterance.rate = "{target_lang_name}".includes("Wolof") ? 0.75 : 0.9;
                        
                        utterance.onend = () => {{ playNextAudio(); }};
                        utterance.onerror = () => {{ playNextAudio(); }};
                        
                        window.speechSynthesis.speak(utterance);
                    }}

                    async function translateSegment(textSegment) {{
                        if (!textSegment.trim()) return;
                        try {{
                            const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={js_target_lang}&dt=t&q=${{encodeURIComponent(textSegment)}}`;
                            const response = await fetch(url);
                            const data = await response.json();
                            if (data && data[0]) {{
                                let translatedSegment = "";
                                data[0].forEach(item => {{ translatedSegment += item[0]; }});
                                
                                fullTranslationText += " " + translatedSegment;
                                transOutput.innerHTML = fullTranslationText;
                                
                                // Placer dans la file d'attente vocale (CLOUD GOOGLE PREMIUM)
                                const autoSpeakElem = document.getElementById('auto-speak-cb');
                                if (autoSpeakElem && autoSpeakElem.checked && translatedSegment.trim().length > 0) {{
                                    audioQueue.push(translatedSegment);
                                    if (!isPlayingAudio) {{
                                        playNextAudio();
                                    }}
                                }}
                            }}
                        }} catch(e) {{ console.error("Erreur Traduction:", e); }}
                    }}

                    if ('webkitSpeechRecognition' in window) {{
                        recognition = new webkitSpeechRecognition();
                        recognition.continuous = true;
                        recognition.interimResults = true;
                        recognition.lang = '{src_lang}';

                        recognition.onstart = () => {{
                            status.innerText = "L'IA vous écoute en continu... (Microphone actif)";
                            startBtn.style.display = 'none';
                            stopBtn.style.display = 'block';
                        }};

                        recognition.onresult = (event) => {{
                            let currentFinal = '';
                            let interim = '';
                            for (let i = event.resultIndex; i < event.results.length; ++i) {{
                                if (event.results[i].isFinal) {{
                                    currentFinal += event.results[i][0].transcript;
                                }} else {{
                                    interim += event.results[i][0].transcript;
                                }}
                            }}
                            
                            if (currentFinal) {{
                                fullFinalText += currentFinal;
                                translateSegment(currentFinal); // Traduire et envoyer
                            }}
                            
                            output.innerHTML = '<strong>' + fullFinalText + '</strong> <span style="color:#64748b;">' + interim + '</span>';
                        }};

                        recognition.onend = () => {{
                            if (!isStopped) {{
                                // Auto-reconnexion si coupure automatique par le navigateur (silence, etc)
                                try {{ recognition.start(); }} catch(e) {{}}
                            }} else {{
                                status.innerText = "Mode Direct arrêté.";
                                startBtn.style.display = 'block';
                                stopBtn.style.display = 'none';
                            }}
                        }};

                        startBtn.onclick = () => {{
                            isStopped = false;
                            try {{ recognition.start(); }} catch(e) {{}}
                            if ('speechSynthesis' in window) {{
                                window.speechSynthesis.cancel();
                                // Petite astuce pour débloquer l'audio synthesis sur l'iframe
                                const unlockUtterance = new SpeechSynthesisUtterance("");
                                unlockUtterance.volume = 0;
                                window.speechSynthesis.speak(unlockUtterance);
                            }}
                        }};
                        stopBtn.onclick = () => {{
                            isStopped = true;
                            recognition.stop();
                        }};
                        saveBtn.onclick = () => {{
                            if (fullFinalText.trim() === "") return;
                            status.innerText = "⏳ Enregistrement...";
                            window.parent.postMessage({{
                                type: 'streamlit:set_widget_value',
                                key: 'auto_sync',
                                value: fullFinalText + " ||| " + fullTranslationText
                            }}, '*');
                            setTimeout(() => {{ status.innerText = "✅ Placé dans les résultats !"; }}, 2000);
                        }};
                    }} else {{
                        status.innerText = "Navigateur non compatible.";
                    }}
                </script>
            """
            components.html(catch_speech_js, height=600)
            
            # Récupération automatique et fusion avec l'historique
            sync_data = st.text_input("Buffer Live (Caché)", key="auto_sync", label_visibility="collapsed")
            if sync_data and " ||| " in sync_data:
                if 'last_sync' not in st.session_state: st.session_state.last_sync = ""
                
                if sync_data != st.session_state.last_sync:
                    transcript_seg, translation_seg = sync_data.split(" ||| ", 1)
                    
                    last_t, last_tr = "", ""
                    if st.session_state.last_sync and " ||| " in st.session_state.last_sync:
                        last_t, last_tr = st.session_state.last_sync.split(" ||| ", 1)
                    
                    # Déduction de la nouveauté pour éviter les doublons sur multi-clic
                    if transcript_seg.startswith(last_t) and translation_seg.startswith(last_tr):
                        new_transcript = transcript_seg[len(last_t):]
                        new_translation = translation_seg[len(last_tr):]
                    else:
                        new_transcript = transcript_seg
                        new_translation = translation_seg
                    
                    if 'transcription' not in st.session_state: st.session_state.transcription = ""
                    if 'translation' not in st.session_state: st.session_state.translation = ""
                    
                    # Accumulation fluide sans effacer l'existant
                    st.session_state.transcription += f" {new_transcript}"
                    st.session_state.translation += f" {new_translation}"
                    
                    st.session_state.last_sync = sync_data
                    st.rerun()

            st.info("💡 Cliquez sur le bouton vert 'Enregistrer' pour déplacer votre texte vers la droite.")

        if audio_input:
            col_acc1, col_acc2 = st.columns(2)
            with col_acc1:
                if st.button("🚀 Transcrire & Traduire", use_container_width=True):
                    with st.spinner("Traitement..."):
                        new_txt = transcribe_audio_bytes(audio_input, src_lang)
                        new_trans = translate_text(new_txt, target_lang_name)
                        
                        # Accumulation sécurisée (Transcription)
                        if 'transcription' not in st.session_state or not st.session_state['transcription']:
                            st.session_state['transcription'] = new_txt
                        else:
                            st.session_state['transcription'] += f"\n\n---\n{new_txt}"
                        
                        # Accumulation sécurisée (Traduction)
                        if 'translation' not in st.session_state or not st.session_state['translation']:
                            st.session_state['translation'] = new_trans
                        else:
                            st.session_state['translation'] += f"\n\n---\n{new_trans}"
                        st.rerun()

    with col2:
        st.markdown("### 📝 2. Résultats")
        
        if 'transcription' in st.session_state and st.session_state['transcription']:
            original_text = st.text_area("📜 Historique des transcriptions", value=st.session_state['transcription'], height=250)
            st.session_state['transcription'] = original_text 

            if 'translation' in st.session_state:
                st.markdown(f"#### ✨ Traduction Globale ({target_lang_name})")
                current_translation = st.text_area(f"Texte", value=st.session_state['translation'], height=250)
                st.session_state['translation'] = current_translation
                # --------- LECTEUR AUDIO CLOUD-SAFE (GTTS MÉMOIRE) ---------
                st.markdown("---")
                
                # Mapper la langue cible vers le lecteur TTS (Google Base)
                lang_map = {
                    "Wolof": "fr",   # On lit en français la phonétique Wolof
                    "Français": "fr",
                    "Anglais": "en",
                    "Arabe": "ar",
                    "Espagnol": "es",
                    "Chinois": "zh-CN",
                    "Allemand": "de"
                }

                target_voice_lang = "fr" 
                for k, v in lang_map.items():
                    if k in target_lang_name:
                        target_voice_lang = v
                        break
                
                # Le nettoyage additionnel (les "cas désespérés" que l'IA oublierait)
                def clean_for_cloud_tts(text):
                    t = text.replace("`", "'").replace("$", "")
                    if "Wolof" in target_lang_name:
                        # Remplacement des "w" par "ou" pour éviter la prononciation "V" (Ex: "Wouyou" devient "Ou-you")
                        t = t.replace(" w", " ou").replace("W", "Ou").replace("wa", "oua").replace("wé", "oué")
                    return t
                
                safe_text = clean_for_cloud_tts(st.session_state['translation'])
                
                if st.button("🔊 Écouter (Qualité Cloud Stable)"):
                    if safe_text.strip():
                        with st.spinner("Génération de l'audio haute qualité (sans coupure)..."):
                            try:
                                # Utilisation de gTTS en BytesIO (pas de fichier local pour le web)
                                tts = gTTS(text=safe_text, lang=target_voice_lang, slow=False)
                                fp = io.BytesIO()
                                tts.write_to_fp(fp)
                                fp.seek(0)
                                
                                st.audio(fp, format='audio/mp3', autoplay=True)
                            except Exception as e:
                                st.error(f"Le moteur vocal est temporairement indisponible: {e}")
                    else:
                        st.warning("Rien à lire.")
                # (Ancien lecteur Javascript supprimé, remplacé par st.audio)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button(f"🌍 Traduire tout en {target_lang_name}", use_container_width=True):
                    with st.spinner(f"Traduction de l'historique..."):
                        translation = translate_text(original_text, target_lang_name)
                        st.session_state['translation'] = translation
                        st.rerun()

            with col_btn2:
                # Créer un contenu TXT combiné
                full_export = f"=== TRANSCRIPTION ({src_lang}) ===\n\n{original_text}"
                if 'translation' in st.session_state:
                    full_export += f"\n\n\n=== TRADUCTION ({target_lang_name}) ===\n\n{st.session_state['translation']}"
                
                st.download_button("📥 Exporter Tout (Transcription + Traduction)", full_export, "session_wolof_ai.txt", use_container_width=True)

            if st.button("🗑️ Effacer l'historique", type="secondary", use_container_width=True):
                del st.session_state['transcription']
                if 'translation' in st.session_state: del st.session_state['translation']
                st.rerun()
        else:
            st.info("Les transcriptions s'ajouteront ici progressivement.")
            st.image("https://cdni.iconscout.com/illustration/premium/thumb/empty-state-2130362-1800926.png", use_container_width=True)

if __name__ == "__main__":
    main()
