"""
Groq API Client Module
Handles integration with Groq API for advanced conversational AI capabilities.
"""

import os
from typing import List, Dict, Any

from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class GroqClient:
    """
    A class to handle interactions with the Groq API for conversational AI.
    """
    
    def __init__(self):
        """Initialize the Groq client with API key from environment variables."""
        api_key = os.getenv('GROQ_API_KEY')
        
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found in environment variables. "
                "Please create a .env file with your Groq API key."
            )
        
        self.client = Groq(api_key=api_key)
        self.conversation_history: List[Dict[str, str]] = []
    
    def chat(self, user_message, max_tokens=150):
        """
        Send a message to Groq API and get a response.
        
        Args:
            user_message: The user's message/query
            max_tokens: Maximum tokens in the response
            
        Returns:
            str: The AI's response
        """
        try:
            # Add user message to conversation history
            self.conversation_history.append(
                {
                    "role": "user",
                    "content": user_message,
                }
            )

            # Create chat completion (simple, generic mode – kept for backward compatibility)
            chat_completion = self.client.chat.completions.create(
                messages=self.conversation_history,
                model="llama-3.1-8b-instant",  # Fast and efficient model
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=1,
            )

            # Extract response
            assistant_message = chat_completion.choices[0].message.content

            # Add assistant response to conversation history
            self.conversation_history.append(
                {
                    "role": "assistant",
                    "content": assistant_message,
                }
            )

            # Keep conversation history manageable (last 10 exchanges)
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            return assistant_message
        
        except Exception as e:
            return f"Sorry, I encountered an error while processing your request: {str(e)}"
    
    def reset_conversation(self):
        """Reset the conversation history."""
        self.conversation_history = []

    # ------------------------------------------------------------------
    # Atlas-specific helper: bilingual, Urdu-first, boss-aware persona
    # ------------------------------------------------------------------

    def chat_as_atlas(self, user_message: str, max_tokens: int = 220, language_mode: str = "english") -> str:
        """
        Talk to the Groq model as Nova – an English-only desktop assistant.

        Nova behaviours:
        - Understands English commands
        - Replies in clear, natural English
        - Provides helpful responses for desktop automation tasks
        - Keeps a short conversation memory
        """
        try:
            # English-only system prompt
            system_prompt = (
                "You are Nova, an AI desktop automation assistant for Windows. "
                "You communicate strictly in English only. "
                "Respond concisely and helpfully. "
                "When users ask questions, provide clear English answers. "
                "Do not show JSON, code, or internal reasoning – just the final English reply."
            )

            messages: List[Dict[str, str]] = [
                {"role": "system", "content": system_prompt},
            ]

            # Include trimmed conversation history for short-term context
            history_tail: List[Dict[str, str]] = self.conversation_history[-10:]
            messages.extend(history_tail)

            messages.append(
                {
                    "role": "user",
                    "content": user_message,
                }
            )

            completion = self.client.chat.completions.create(
                messages=messages,
                model="llama-3.1-8b-instant",
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=1,
            )

            reply = completion.choices[0].message.content

            # Update our own minimal history too (so we keep context across calls)
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": reply})
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            return reply
        except Exception as e:
            return f"Error communicating with AI: {str(e)}"

