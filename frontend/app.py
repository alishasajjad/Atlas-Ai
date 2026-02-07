"""
Nova AI Voice Control Assistant
Main Streamlit application with modern dark theme UI.

This module is responsible ONLY for UI and high-level
orchestration. All heavy lifting (voice recognition,
text-to-speech, command handling, Groq client) lives
in the backend package.
"""

import html as html_module
import os
import sys
import time
import threading
import queue
import webbrowser

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
    # Language mode - English only
    if "language_mode" not in st.session_state:
        st.session_state.language_mode = "english"


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

    /* Chat history panel and message bubbles */
    .chat-section {
        margin-top: 1.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(124, 232, 255, 0.3);
    }
    .chat-history-container {
        max-height: 420px;
        overflow-y: auto;
        padding: 12px;
        background: rgba(10, 20, 40, 0.5);
        border-radius: 16px;
        border: 1px solid rgba(124, 232, 255, 0.25);
        margin-bottom: 12px;
    }
    .chat-msg {
        margin: 10px 0;
        padding: 12px 14px;
        border-radius: 14px;
        line-height: 1.45;
    }
    .chat-msg-user {
        background: rgba(124, 232, 255, 0.15);
        border-left: 4px solid #7ce8ff;
        margin-left: 0;
        margin-right: 24px;
    }
    .chat-msg-assistant {
        background: rgba(20, 50, 80, 0.5);
        border-left: 4px solid rgba(124, 232, 255, 0.7);
        margin-left: 24px;
        margin-right: 0;
    }
    .chat-msg-badge {
        display: inline-block;
        font-size: 0.7rem;
        padding: 2px 8px;
        border-radius: 999px;
        margin-bottom: 4px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .chat-msg-badge-voice {
        background: rgba(76, 255, 76, 0.25);
        color: #4cff4c;
    }
    .chat-msg-badge-text {
        background: rgba(255, 213, 79, 0.25);
        color: #ffd54f;
    }
    .chat-msg-time {
        font-size: 0.75rem;
        color: rgba(224, 244, 255, 0.6);
        margin-top: 4px;
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
        "ok",
        "okay",
        "confirm",
        "proceed",
        "go ahead",
        "sure",
        "yep",
    ]
    return any(p in t for p in positives)


def _is_negative_confirmation(text: str) -> bool:
    """Heuristic check if the user is saying 'no' / cancel."""
    t = text.lower()
    negatives = [
        "no",
        "cancel",
        "abort",
        "stop",
        "don't",
        "do not",
        "nope",
    ]
    return any(n in t for n in negatives)


def _execute_pending_system_action() -> str:
    """
    Execute a previously stored system action (shutdown / restart / sleep).

    Returns a human-readable status string in English.
    """
    action = st.session_state.pending_system_action
    st.session_state.pending_system_action = None

    if not action:
        return "No pending system action to execute."

    handler: CommandHandler = st.session_state.command_handler

    if action == "shutdown":
        result = handler.shutdown_system()
        return "Shutting down the system now."
    if action == "restart":
        result = handler.restart_system()
        return "Restarting the system now."
    if action == "sleep":
        result = handler.sleep_system()
        return "Putting the system to sleep now."

    return "Unknown system action. Please try again."


def handle_recognized_text(text: str, source: str = "voice") -> None:
    """
    Handle a command from either voice or text chat. Runs the same pipeline:
    pending confirmations, command handler, search, Groq fallback. All actions
    are real system-level; responses are recorded and spoken (TTS) in English.

    source: "voice" | "text" – used for chat history labeling only.
    """
    if not text or not text.strip():
        return

    text = text.strip()
    st.session_state.last_command = text
    safe_update_status("processing")

    # --- 0. Immediate voice-output controls (stop / mute / unmute) -----------
    # These commands are handled before anything else so that Nova stops
    # talking the moment you say them.
    lower_text = text.lower()
    tts = st.session_state.tts  # type: TextToSpeech or None

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
                "source": source,
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
                "source": source,
            }
        )
        st.session_state.last_response = "Voice output is back on. I’ll speak my responses again."
        safe_update_status("ready")
        if tts is not None:
            tts.speak(st.session_state.last_response)
        return

    # Add user message to conversation history (request + source for display)
    st.session_state.conversation_history.append(
        {
            "role": "user",
            "text": text,
            "timestamp": time.strftime("%H:%M:%S"),
            "source": source,
        }
    )

    response = None

    # --- 1. Handle pending confirmations for system actions ---
    if response is None and st.session_state.pending_system_action is not None:
        if _is_positive_confirmation(text):
            # Execute the stored action
            response = _execute_pending_system_action()
        elif _is_negative_confirmation(text):
            st.session_state.pending_system_action = None
            response = "System action cancelled. No changes made."
        else:
            # Ask again / clarify
            action_type = st.session_state.pending_system_action
            response = (
                f"You requested a {action_type} action. "
                "Please confirm by saying 'yes' to proceed or 'no' to cancel."
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
                    "You requested a system shutdown. "
                    "This is a critical action. Please confirm by saying 'yes' to proceed or 'no' to cancel."
                )
            elif cmd_result == "SYSTEM_RESTART_REQUEST":
                st.session_state.pending_system_action = "restart"
                response = (
                    "You requested a system restart. "
                    "Please confirm by saying 'yes' to proceed or 'no' to cancel."
                )
            elif cmd_result == "SYSTEM_SLEEP_REQUEST":
                st.session_state.pending_system_action = "sleep"
                response = (
                    "You requested to put the system to sleep. "
                    "Please confirm by saying 'yes' to proceed or 'no' to cancel."
                )
            elif cmd_result is not None:
                # Command executed successfully - provide English confirmation
                response = f"Command executed: {cmd_result}"
        except Exception as e:
            response = f"Error executing command: {str(e)}"
    
    # --- 3. Check for search commands (handle before other processing) ---
    if response is None and "search" in lower_text:
        try:
            handler: CommandHandler = st.session_state.command_handler
            if handler:
                # Let command handler process the search command
                cmd_result = handler.process_command(text)
                if cmd_result and "search" in cmd_result.lower():
                    response = cmd_result
        except Exception as e:
            response = f"Error processing search command: {str(e)}"
    
    # --- 4. If still not handled, use Groq for conversation (English only) ---
    if response is None:
        if st.session_state.groq_client is not None:
            safe_update_status("thinking")
            try:
                # Use English-only mode
                response = st.session_state.groq_client.chat_as_atlas(
                    text, language_mode="english"
                )

                # If the user asked to "write" or "generate" content,
                # also type the generated text directly into the active window.
                if any(
                    phrase in lower_text
                    for phrase in [
                        "write ",
                        "generate ",
                        "create a paragraph",
                        "create paragraph",
                        "type ",
                    ]
                ) and st.session_state.command_handler is not None:
                    try:
                        handler_for_typing: CommandHandler = st.session_state.command_handler
                        handler_for_typing.desktop.type_text_in_active_window(response)
                    except Exception as e:
                        print(f"Error while typing generated content: {e}")
            except Exception as e:
                response = f"Error communicating with AI: {str(e)}"
        else:
            response = (
                "The Groq AI client is not configured. "
                "Please set GROQ_API_KEY in the `.env` file."
            )

    # 5. Record assistant response (English only) with source for history
    st.session_state.conversation_history.append(
        {
            "role": "assistant",
            "text": response,
            "timestamp": time.strftime("%H:%M:%S"),
            "source": source,
        }
    )

    st.session_state.last_response = response
    safe_update_status("responding")

    # 6. Speak the response (verbal confirmation for both voice and text commands)
    if st.session_state.tts:
        try:
            st.session_state.tts.speak(response)
        except Exception as e:
            # Log to terminal but keep UI alive
            print(f"Error during text-to-speech: {e}")

    # 7. Return to listening or idle
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
        with st.expander("⚙️ Settings"):
            # Voice Speed
            current_rate = 140
            if "voice_rate" not in st.session_state:
                st.session_state.voice_rate = current_rate
            
            new_rate = st.slider("Voice Speed", 100, 300, st.session_state.voice_rate, step=10)
            if new_rate != st.session_state.voice_rate:
                st.session_state.voice_rate = new_rate
                if st.session_state.tts:
                    st.session_state.tts.set_rate(new_rate)

            # Voice Volume
            current_volume = 0.95
            if "voice_volume" not in st.session_state:
                st.session_state.voice_volume = current_volume
            
            new_volume = st.slider("Voice Volume", 0.0, 1.0, st.session_state.voice_volume, step=0.05)
            if new_volume != st.session_state.voice_volume:
                st.session_state.voice_volume = new_volume
                if st.session_state.tts:
                    st.session_state.tts.set_volume(new_volume)

            # AI Model
            models = ["llama-3.1-8b-instant", "llama-3.1-70b-versatile", "mixtral-8x7b-32768", "gemma-7b-it"]
            if "ai_model" not in st.session_state:
                st.session_state.ai_model = models[0]
            
            new_model = st.selectbox("AI Model", models, index=models.index(st.session_state.ai_model) if st.session_state.ai_model in models else 0)
            if new_model != st.session_state.ai_model:
                st.session_state.ai_model = new_model
                if st.session_state.groq_client:
                    st.session_state.groq_client.current_model = new_model

        st.markdown("---")
        st.header("📋 Available Commands")
        handler = st.session_state.command_handler
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
    
    # --- Voice Control section ---
    st.subheader("🎤 Voice Control")
    col_voice_1, col_voice_2 = st.columns([2, 1])
    with col_voice_1:
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
        st.subheader("💬 Response")
        st.markdown(
            f'<div class="response-box">{st.session_state.last_response or "Waiting for your command..."}</div>',
            unsafe_allow_html=True
        )
    with col_voice_2:
        st.markdown("Use **Start** in the sidebar to control Nova by voice. Same actions can be run via text chat below.")

    # --- Text Chat section: persistent history + typed commands ---
    st.markdown('<div class="chat-section">', unsafe_allow_html=True)
    st.subheader("💬 Text Chat")
    st.caption("Type a command below to run the same actions as voice (open apps, type text, save files, search, etc.). Nova will confirm verbally.")
    history = st.session_state.conversation_history
    if history:
        # Chronological log with Voice/Text badge
        buf = []
        buf.append('<div class="chat-history-container">')
        for msg in history:
            role = msg.get("role", "user")
            text = msg.get("text", "")
            ts = msg.get("timestamp", "")
            src = msg.get("source", "voice")
            esc = html_module.escape(str(text)).replace("\n", "<br/>")
            badge_class = "chat-msg-badge-voice" if src == "voice" else "chat-msg-badge-text"
            badge_label = "Voice" if src == "voice" else "Text"
            if role == "user":
                buf.append(f'<div class="chat-msg chat-msg-user"><span class="chat-msg-badge {badge_class}">{badge_label}</span><br/>{esc}<div class="chat-msg-time">{ts}</div></div>')
            else:
                buf.append(f'<div class="chat-msg chat-msg-assistant"><span class="chat-msg-badge {badge_class}">{badge_label}</span><br/>{esc}<div class="chat-msg-time">{ts}</div></div>')
        buf.append("</div>")
        st.markdown("".join(buf), unsafe_allow_html=True)
    else:
        st.info("No conversation history yet. Speak or type a command to start.")
    user_text = st.chat_input("Type a command (e.g. open Notepad and type Hello then save on Desktop as report)")
    if user_text and user_text.strip():
        initialize_components()
        handle_recognized_text(user_text.strip(), source="text")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Auto-refresh to keep polling the background queues while listening
    if st.session_state.listening:
        st.session_state.refresh_counter += 1
        time.sleep(1.5)
        st.rerun()


if __name__ == "__main__":
    main()

