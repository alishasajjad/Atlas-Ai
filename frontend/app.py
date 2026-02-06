"""
Nova AI Voice Control Assistant
Main Streamlit application with modern dark theme UI.

This module is responsible ONLY for UI and high-level
orchestration. All heavy lifting (voice recognition,
text-to-speech, command handling, Groq client) lives
in the backend package.
"""

import os
import sys
import time
import threading
import queue

import streamlit as st

# Ensure project root is on sys.path so we can import the backend package
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.voice_recognition import VoiceRecognizer
from backend.text_to_speech import TextToSpeech
from backend.command_handler import CommandHandler
from backend.groq_client import GroqClient


def initialize_session_state() -> None:
    """
    Initialize ALL Streamlit session_state variables used by the app.

    This MUST be called before any UI widgets or background threads are
    started, to avoid KeyError/AttributeError issues inside callbacks.
    """
    # Core backend components
    if "voice_recognizer" not in st.session_state:
        st.session_state.voice_recognizer = None
    if "tts" not in st.session_state:
        st.session_state.tts = None
    if "command_handler" not in st.session_state:
        st.session_state.command_handler = None
    if "groq_client" not in st.session_state:
        st.session_state.groq_client = None

    # Application state
    if "status" not in st.session_state:
        st.session_state.status = "Ready"  # idle state
    if "listening" not in st.session_state:
        st.session_state.listening = False
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "last_response" not in st.session_state:
        st.session_state.last_response = ""
    if "last_status" not in st.session_state:
        st.session_state.last_status = ""
    if "last_command" not in st.session_state:
        st.session_state.last_command = ""
    if "refresh_counter" not in st.session_state:
        st.session_state.refresh_counter = 0

    # Atlas-specific context and pending actions
    if "pending_system_action" not in st.session_state:
        # Example: {"type": "shutdown" | "restart" | "sleep"}
        st.session_state.pending_system_action = None
    if "atlas_context" not in st.session_state:
        # Simple dictionary we can enrich over time (last opened app/website, etc.)
        st.session_state.atlas_context = {}

    # Queues for thread-safe communication from background threads
    if "recognized_text_queue" not in st.session_state:
        st.session_state.recognized_text_queue = queue.Queue()
    if "status_queue" not in st.session_state:
        st.session_state.status_queue = queue.Queue()
    # Language mode for Atlas responses: "english" (default) or "urdu"
    if "language_mode" not in st.session_state:
        # Speak in English by default; user can switch to Urdu via voice.
        st.session_state.language_mode = "english"
    # Track whether we already auto-started listening in this session
    if "auto_started_listening" not in st.session_state:
        st.session_state.auto_started_listening = False


# Initialize session_state BEFORE anything else (buttons, threads, etc.)
initialize_session_state()


# Page configuration
st.set_page_config(
    page_title="Nova AI Voice Control Assistant",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# Custom CSS for a futuristic circular dashboard theme
st.markdown("""
    <style>
    .stApp {
        background: radial-gradient(circle at center, #101522 0%, #050812 55%, #020309 100%);
        color: #e0f4ff;
        font-family: "Segoe UI", system-ui, sans-serif;
    }

    /* Central circular "radar" container idea using borders and gradients */
    .main .block-container {
        max-width: 1100px;
    }

    h1, h2, h3 {
        color: #7ce8ff !important;
        font-weight: 600;
        letter-spacing: 0.05em;
    }

    /* Circular status widget */
    .status-box {
        background: radial-gradient(circle at 30% 30%, rgba(124, 232, 255, 0.2), rgba(5, 8, 18, 0.9));
        border: 2px solid rgba(124, 232, 255, 0.8);
        border-radius: 999px;
        padding: 25px;
        margin: 10px 0;
        text-align: center;
        box-shadow: 0 0 25px rgba(124, 232, 255, 0.25);
    }

    .status-listening {
        border-color: #4cff4c;
        box-shadow: 0 0 25px rgba(76, 255, 76, 0.35);
    }

    .status-processing {
        border-color: #ffd54f;
        box-shadow: 0 0 25px rgba(255, 213, 79, 0.35);
    }

    .status-responding {
        border-color: #7ce8ff;
    }

    .status-error {
        border-color: #ff5252;
        box-shadow: 0 0 25px rgba(255, 82, 82, 0.5);
    }

    /* Response panel styled as inner ring */
    .response-box {
        background: radial-gradient(circle at top, rgba(20, 40, 80, 0.9), rgba(3, 8, 20, 0.95));
        border: 1px solid rgba(124, 232, 255, 0.4);
        border-radius: 20px;
        padding: 20px;
        margin: 20px 0;
        color: #e6f7ff;
        min-height: 120px;
        box-shadow: 0 0 20px rgba(0, 200, 255, 0.25);
    }

    /* Buttons as glowing capsules */
    .stButton > button {
        background: radial-gradient(circle at 30% 0%, #7ce8ff 0%, #007acc 55%, #004f88 100%);
        color: white;
        border: none;
        border-radius: 999px;
        padding: 8px 26px;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        box-shadow: 0 0 12px rgba(0, 200, 255, 0.5);
        transition: all 0.25s ease-out;
    }

    .stButton > button:hover {
        transform: translateY(-1px) scale(1.02);
        box-shadow: 0 0 20px rgba(124, 232, 255, 0.8);
        filter: brightness(1.1);
    }

    /* Sidebar as dark radial panel */
    .css-1d391kg, .stSidebar {
        background: radial-gradient(circle at top, #111727 0%, #050813 100%) !important;
    }

    .stSidebar h2, .stSidebar h3 {
        color: #7ce8ff !important;
    }

    /* Tweak scrollbars slightly */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(124, 232, 255, 0.4);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    </style>
""", unsafe_allow_html=True)


def initialize_components() -> bool:
    """Initialize all Nova AI components."""
    try:
        if st.session_state.voice_recognizer is None:
            st.session_state.voice_recognizer = VoiceRecognizer()
        if st.session_state.tts is None:
            st.session_state.tts = TextToSpeech()
        if st.session_state.command_handler is None:
            st.session_state.command_handler = CommandHandler()
        if st.session_state.groq_client is None:
            try:
                st.session_state.groq_client = GroqClient()
            except ValueError as e:
                st.error(f"⚠️ {str(e)}")
                st.info("💡 Please create a `.env` file in the project root with: `GROQ_API_KEY=your_api_key_here`")
                return False
        return True
    except Exception as e:
        st.error(f"Error initializing components: {str(e)}")
        return False


def safe_update_status(raw_status: str) -> None:
    """
    Safely normalize and store status text in session_state.

    This function is ONLY called from the main Streamlit thread, never
    from background threads.
    """
    if "status" not in st.session_state:
        st.session_state.status = "Ready"

    if raw_status.startswith("error:"):
        new_status = f"Error: {raw_status[6:]}"
    else:
        new_status = raw_status.capitalize()

    if st.session_state.status != new_status:
        st.session_state.status = new_status
        st.session_state.last_status = new_status


def _is_positive_confirmation(text: str) -> bool:
    """Heuristic check if the user is saying 'yes' / confirmation."""
    t = text.lower()
    positives = [
        "yes",
        "haan",
        "han",
        "ji",
        "bilkul",
        "ok",
        "okay",
        "theek hai",
        "theek",
        "go ahead",
    ]
    return any(p in t for p in positives)


def _is_negative_confirmation(text: str) -> bool:
    """Heuristic check if the user is saying 'no' / cancel."""
    t = text.lower()
    negatives = [
        "no",
        "nahin",
        "nahi",
        "mat karo",
        "cancel",
        "rok do",
        "stop",
    ]
    return any(n in t for n in negatives)


def _execute_pending_system_action() -> str:
    """
    Execute a previously stored system action (shutdown / restart / sleep).

    Returns a human-readable status string (in Urdu-ish, addressed to boss).
    """
    action = st.session_state.pending_system_action
    st.session_state.pending_system_action = None

    if not action:
        return "Ji boss, abhi koi pending kaam nahin tha."

    handler: CommandHandler = st.session_state.command_handler

    if action == "shutdown":
        english_result = handler.shutdown_system()
        return "Ji boss, ab system shutdown kar raha hoon."
    if action == "restart":
        english_result = handler.restart_system()
        return "Ji boss, system ko restart kar raha hoon."
    if action == "sleep":
        english_result = handler.sleep_system()
        return "Ji boss, system ko sleep mode mein daal raha hoon."

    return "Maaf kijiye boss, mujhe samajh nahi aaya kaunsa system action tha."


def handle_recognized_text(text: str) -> None:
    """
    Handle a piece of recognized speech text in the main thread.

    Flow:
    - If there is a pending dangerous action (shutdown/restart/sleep), treat
      the next utterance as confirmation (yes/no).
    - Otherwise:
      1) Try local command handler for existing English commands
      2) If not recognized, fall back to Atlas (Groq) for Urdu-first reply
    """
    if not text:
        return

    st.session_state.last_command = text
    safe_update_status("processing")

    # --- 0. Immediate voice-output controls (stop / mute / unmute) -----------
    # These commands are handled before anything else so that Nova stops
    # talking the moment you say them.
    lower_text = text.lower()
    tts: TextToSpeech | None = st.session_state.tts

    if any(phrase in lower_text for phrase in ["stop", "chup ho jao"]):
        # Stop current speech and mute future responses until the user says
        # "speak" / "bolo". We still keep listening for further commands.
        if tts is not None:
            tts.mute()
        st.session_state.conversation_history.append(
            {
                "role": "assistant",
                "text": "Okay, I’ll stay quiet until you say 'speak' or 'bolo'.",
                "timestamp": time.strftime("%H:%M:%S"),
            }
        )
        st.session_state.last_response = "Okay, I’ll stay quiet until you say 'speak' or 'bolo'."
        safe_update_status("ready")
        return

    if any(phrase in lower_text for phrase in ["speak", "bolo"]):
        # Allow Nova to speak again.
        if tts is not None:
            tts.unmute()
        st.session_state.conversation_history.append(
            {
                "role": "assistant",
                "text": "Voice output is back on. I’ll speak my responses again.",
                "timestamp": time.strftime("%H:%M:%S"),
            }
        )
        st.session_state.last_response = "Voice output is back on. I’ll speak my responses again."
        safe_update_status("ready")
        if tts is not None:
            tts.speak(st.session_state.last_response)
        return

    # Add user message to conversation history
    st.session_state.conversation_history.append(
        {
            "role": "user",
            "text": text,
            "timestamp": time.strftime("%H:%M:%S"),
        }
    )

    # --- 0. Handle language switch commands first (English <-> Urdu) ---
    t_lower = lower_text
    if any(phrase in t_lower for phrase in ["speak in urdu", "switch to urdu", "urdu mein bolo"]):
        st.session_state.language_mode = "urdu"
        response = "Ji boss, ab main Urdu mein baat karunga."
    elif any(
        phrase in t_lower
        for phrase in ["speak in english", "switch to english", "english mein bolo"]
    ):
        st.session_state.language_mode = "english"
        response = "Yes boss, I will speak in English from now on."
    else:
        response = None

    # --- 1. Handle pending confirmations for system actions ---
    if response is None and st.session_state.pending_system_action is not None:
        if _is_positive_confirmation(text):
            # Execute the stored action
            response = _execute_pending_system_action()
        elif _is_negative_confirmation(text):
            st.session_state.pending_system_action = None
            response = "Theek hai boss, main ye action cancel kar deta hoon."
        else:
            # Ask again / clarify
            response = (
                "Boss, aapne pehle jo system ka command diya tha "
                "(shutdown / restart / sleep), uske liye please clearly "
                "bolen: 'haan' ya 'nahi'."
            )
    # --- 2. Try local command handler (time, date, apps, searches, etc.) ---
    if response is None and st.session_state.command_handler is not None:
        try:
            handler: CommandHandler = st.session_state.command_handler
            cmd_result = handler.process_command(text)

            # System actions return sentinel values so we can ask for confirmation
            if cmd_result == "SYSTEM_SHUTDOWN_REQUEST":
                st.session_state.pending_system_action = "shutdown"
                response = (
                    "Boss, kya aap waqai system shutdown karwana chahte hain? "
                    "Please bolen: 'haan' ya 'nahi'."
                )
            elif cmd_result == "SYSTEM_RESTART_REQUEST":
                st.session_state.pending_system_action = "restart"
                response = (
                    "Boss, system restart kar doon? "
                    "Agar haan to bolen 'haan', warna 'nahi'."
                )
            elif cmd_result == "SYSTEM_SLEEP_REQUEST":
                st.session_state.pending_system_action = "sleep"
                response = (
                    "Boss, system ko sleep mode mein daal doon? "
                    "Please confirm: 'haan' ya 'nahi'."
                )
            elif cmd_result is not None:
                lower_text = text.lower()
                lang = st.session_state.language_mode

                if any(word in lower_text for word in ["time", "waqt"]):
                    if lang == "urdu":
                        response = f"Ji boss, abhi ka time hai: {cmd_result}"
                    else:
                        response = f"Yes boss, the current time is: {cmd_result}"
                elif any(word in lower_text for word in ["date", "tareekh"]):
                    if lang == "urdu":
                        response = f"Ji boss, aaj ki tareekh hai: {cmd_result}"
                    else:
                        response = f"Yes boss, today’s date is: {cmd_result}"
                elif "recycle bin" in lower_text or "kooda" in lower_text or "dustbin" in lower_text:
                    response = "Ji boss, Recycle Bin khol diya hai." if lang == "urdu" else "Yes boss, I have opened the Recycle Bin."
                elif "chrome" in lower_text and "close" in lower_text:
                    response = "Ji boss, Chrome band kar diya hai." if lang == "urdu" else "Yes boss, I have closed Chrome."
                elif "notepad" in lower_text and "close" in lower_text:
                    response = "Ji boss, Notepad band kar diya hai." if lang == "urdu" else "Yes boss, I have closed Notepad."
                elif "chrome" in lower_text:
                    response = "Ji boss, Google Chrome khol diya hai." if lang == "urdu" else "Yes boss, I have opened Google Chrome."
                elif "notepad" in lower_text:
                    response = "Ji boss, Notepad khol diya hai." if lang == "urdu" else "Yes boss, I have opened Notepad."
                elif "youtube" in lower_text:
                    response = (
                        "Ji boss, YouTube par aapki command ke mutabiq search kar raha hoon."
                        if lang == "urdu"
                        else "Yes boss, I am searching on YouTube as you requested."
                    )
                elif "google" in lower_text:
                    response = (
                        "Ji boss, Google par aapka search chala diya hai."
                        if lang == "urdu"
                        else "Yes boss, I have run your search on Google."
                    )
                elif any(phrase in lower_text for phrase in ["select everything", "select all", "sab select karo"]):
                    response = (
                        "Ji boss, current window mein sab select kar diya hai."
                        if lang == "urdu"
                        else "Yes boss, I have selected everything in the current window."
                    )
                elif any(
                    phrase in lower_text
                    for phrase in ["delete this", "ye delete karo", "delete everything", "sab delete karo"]
                ):
                    response = (
                        "Ji boss, jo cheezen select theen unko delete kar diya hai."
                        if lang == "urdu"
                        else "Yes boss, I have deleted the selected items."
                    )
                elif any(
                    phrase in lower_text
                    for phrase in [
                        "chrome par",
                        "chrome pe",
                        "browser par",
                        "browser pe",
                    ]
                ):
                    response = (
                        "Ji boss, current browser window mein aapka search chala diya hai."
                        if lang == "urdu"
                        else "Yes boss, I have run your search in the current browser window."
                    )
                else:
                    # Generic acknowledgement for any other handled command
                    if lang == "urdu":
                        response = f"Ji boss, aapka command execute kar diya: {cmd_result}"
                    else:
                        response = f"Yes boss, I have executed your command: {cmd_result}"
        except Exception as e:
            response = f"Sorry boss, command chalate hue koi masla aa gaya: {e}"

    # --- 2. If not recognized, fall back to Atlas (Groq) for conversation ---
    if response is None:
        if st.session_state.groq_client is not None:
            safe_update_status("thinking")
            try:
                # Ask Atlas in the currently selected language (English default,
                # Urdu when the user has explicitly switched).
                response = st.session_state.groq_client.chat_as_atlas(
                    text, language_mode=st.session_state.language_mode
                )

                # If the user asked Atlas to "write" or "generate" content,
                # also type the generated text directly into the active window.
                if any(
                    phrase in t_lower
                    for phrase in [
                        "write ",
                        "generate ",
                        "create a paragraph",
                        "create paragraph",
                        "likho ",
                    ]
                ) and st.session_state.command_handler is not None:
                    try:
                        handler_for_typing: CommandHandler = st.session_state.command_handler
                        handler_for_typing.desktop.type_text_in_active_window(response)
                    except Exception as e:
                        print(f"Error while typing generated content: {e}")
            except Exception as e:
                lang = st.session_state.language_mode
                if lang == "urdu":
                    response = (
                        f"Maaf kijiye boss, AI se baat karte hue koi error aa gaya: {e}"
                    )
                else:
                    response = (
                        f"Sorry boss, there was an error talking to the AI: {e}"
                    )
        else:
            response = (
                "Boss, the Groq AI client is not configured yet. "
                "Please set GROQ_API_KEY in the `.env` file."
            )

    # 3. Record assistant response (always Urdu/boss-aware now)
    st.session_state.conversation_history.append(
        {
            "role": "assistant",
            "text": response,
            "timestamp": time.strftime("%H:%M:%S"),
        }
    )

    st.session_state.last_response = response
    safe_update_status("responding")

    # 4. Speak the response (non-blocking thread inside TextToSpeech)
    if st.session_state.tts:
        try:
            st.session_state.tts.speak(response)
        except Exception as e:
            # Log to terminal but keep UI alive
            print(f"Error during text-to-speech: {e}")

    # 5. Return to listening or idle
    time.sleep(0.2)
    if st.session_state.listening:
        safe_update_status("listening")
    else:
        safe_update_status("ready")


def start_listening() -> None:
    """
    Start continuous voice listening.

    This spins up a background thread that ONLY talks to a thread-safe queue,
    never to st.session_state directly. The main thread then polls that queue
    and updates the UI + state.
    """
    if not initialize_components():
        return

    if st.session_state.listening:
        return

    # Capture references outside the thread so it doesn't touch st.session_state.
    voice_recognizer: VoiceRecognizer = st.session_state.voice_recognizer
    recognized_text_queue: queue.Queue = st.session_state.recognized_text_queue
    status_queue: queue.Queue = st.session_state.status_queue

    st.session_state.listening = True
    safe_update_status("initializing")

    def on_text(recognized_text: str) -> None:
        """Callback used INSIDE the audio thread -> send text to queue."""
        try:
            recognized_text_queue.put_nowait(recognized_text)
        except Exception as e:
            # Never crash the audio thread because of queue issues
            print(f"Error while queuing recognized text: {e}")

    def on_status(raw_status: str) -> None:
        """Callback used INSIDE the audio thread -> send status to queue."""
        try:
            status_queue.put_nowait(raw_status)
        except Exception as e:
            print(f"Error while queuing status update: {e}")

    def start_recognition() -> None:
        """Background thread target: blocks inside listen_continuously."""
        try:
            voice_recognizer.listen_continuously(on_text, on_status)
        except Exception as e:
            # Report any unexpected errors back to main thread via status queue
            try:
                status_queue.put_nowait(f"error: {e}")
            except Exception:
                pass

    # Start listening in a separate thread
    thread = threading.Thread(target=start_recognition, daemon=True)
    thread.start()

    st.success("🎤 Voice listening started!")


def stop_listening() -> None:
    """Stop voice listening and cleanly shut down microphone capture."""
    if not st.session_state.listening:
        return

    st.session_state.listening = False
    if st.session_state.voice_recognizer:
        try:
            st.session_state.voice_recognizer.stop_listening()
        except Exception as e:
            print(f"Error while stopping voice recognizer: {e}")

    safe_update_status("stopped")
    st.info("🛑 Voice listening stopped.")


def _drain_queues() -> None:
    """
    Pull all pending items from the background queues and apply them.

    This function MUST be called from the main Streamlit thread.
    """
    recognized_text_queue: queue.Queue = st.session_state.recognized_text_queue
    status_queue: queue.Queue = st.session_state.status_queue

    # First apply all status updates (they are lightweight)
    try:
        while not status_queue.empty():
            raw_status = status_queue.get_nowait()
            safe_update_status(raw_status)
    except Exception as e:
        print(f"Error while draining status queue: {e}")

    # Then apply all recognized text events (may trigger Groq calls)
    try:
        while not recognized_text_queue.empty():
            text = recognized_text_queue.get_nowait()
            handle_recognized_text(text)
    except Exception as e:
        print(f"Error while draining recognized text queue: {e}")


def main() -> None:
    """Main application function (UI + high-level state)."""
    # Apply any pending updates coming from the background audio thread
    _drain_queues()

    # Ensure backend components exist so the command catalog can be shown
    initialize_components()

    # Header
    st.title("🎤 Nova AI Voice Control Assistant")
    st.markdown("---")
    
    # Sidebar for controls
    with st.sidebar:
        st.header("⚙️ Controls")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start", use_container_width=True):
                start_listening()
        
        with col2:
            if st.button("⏹️ Stop", use_container_width=True):
                stop_listening()
        
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.conversation_history = []
            st.session_state.last_response = ""
            if st.session_state.groq_client:
                st.session_state.groq_client.reset_conversation()
            st.success("History cleared!")
        
        st.markdown("---")
        st.header("📋 Available Commands")
        handler: CommandHandler | None = st.session_state.command_handler
        if handler is not None:
            catalog = handler.get_command_catalog()
            current_category = None
            for entry in catalog:
                category = entry.get("category", "Other")
                if category != current_category:
                    if current_category is not None:
                        st.markdown("---")
                    st.markdown(f"**{category}**")
                    current_category = category
                name = entry.get("name", "")
                desc = entry.get("description", "")
                st.markdown(f"- **{name}**: {desc}")
                for ex in entry.get("examples", []):
                    st.markdown(f'  - "{ex}"')
        else:
            st.info("Commands will appear here once Nova is initialized.")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Status display
        st.subheader("📊 Status")
        status_class = "status-box"
        if "listening" in st.session_state.status.lower():
            status_class += " status-listening"
        elif "processing" in st.session_state.status.lower() or "thinking" in st.session_state.status.lower():
            status_class += " status-processing"
        elif "responding" in st.session_state.status.lower():
            status_class += " status-responding"
        elif "error" in st.session_state.status.lower():
            status_class += " status-error"
        
        st.markdown(
            f'<div class="{status_class}">'
            f'<h3>{st.session_state.status}</h3>'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # Response display
        st.subheader("💬 Response")
        st.markdown(
            f'<div class="response-box">{st.session_state.last_response or "Waiting for your command..."}</div>',
            unsafe_allow_html=True
        )
    
    with col2:
        st.subheader("📝 Conversation History")
        if st.session_state.conversation_history:
            # Show last 5 conversations
            for i, msg in enumerate(st.session_state.conversation_history[-10:]):
                if msg["role"] == "user":
                    st.markdown(f"**You** ({msg['timestamp']}):")
                    st.markdown(f"*{msg['text']}*")
                else:
                    st.markdown(f"**Nova AI** ({msg['timestamp']}):")
                    st.markdown(msg['text'])
                st.markdown("---")
        else:
            st.info("No conversation history yet.")
    
    # Auto-start listening once per session so Nova reacts as soon as you talk
    if not st.session_state.listening and not st.session_state.auto_started_listening:
        start_listening()
        st.session_state.auto_started_listening = True

    # Auto-refresh to keep polling the background queues while listening
    if st.session_state.listening:
        st.session_state.refresh_counter += 1
        # Refresh every 1–2 seconds to keep status and conversation live
        time.sleep(1.5)
        st.rerun()


if __name__ == "__main__":
    main()

