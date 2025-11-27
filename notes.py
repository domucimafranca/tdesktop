import os
import asyncio
import re # Added regex import, although not strictly needed for this simple parsing
from textual.app import App, ComposeResult
from textual.widgets import TextArea, Footer, Header, Input, Label
from textual.screen import ModalScreen
from textual.containers import Grid
from textual.binding import Binding
import google.generativeai as genai
import simplenote

# --- Configuration ---
# Initialize Google AI
# Ensure your GOOGLE_API_KEY environment variable is set
try:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
except Exception:
    print("Warning: GOOGLE_API_KEY environment variable not found. AI features disabled.")

# Initialize Simplenote
# Ensure SIMPLENOTE_USER and SIMPLENOTE_PASSWORD environment variables are set
sn_user = os.environ.get("SIMPLENOTE_USER")
sn_pass = os.environ.get("SIMPLENOTE_PASSWORD")
try:
    sn_client = simplenote.Simplenote(sn_user, sn_pass)
except Exception:
    print("Warning: Simplenote credentials not found. Saving features may fail.")


class AskAIModal(ModalScreen[str]):
    """A modal screen to ask a question to the AI."""

    CSS = """
    AskAIModal {
        align: center middle;
    }
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 11;
        border: heavy $primary;
        background: $surface;
    }
    #question_input {
        column-span: 2;
        width: 100%;
    }
    Label {
        column-span: 2;
        content-align: center middle;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            yield Label("Ask Google AI:")
            yield Input(placeholder="Type your prompt here...", id="question_input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class NoteApp(App):
    """A Textual app for taking notes with AI and Simplenote integration."""

    CSS = """
    TextArea {
        height: 100%; 
        border: heavy $accent;
    }
    """

    BINDINGS = [
        Binding("ctrl+n", "new_note", "New Note"),
        Binding("ctrl+s", "save_note", "Save Note"),
        Binding("ctrl+g", "ask_ai", "Ask AI"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield TextArea(id="editor")
        yield Footer()

    def action_new_note(self) -> None:
        """Clears text area immediately."""
        editor = self.query_one(TextArea)
        editor.text = ""
        self.notify("Editor cleared for new note.")

    def action_save_note(self) -> None:
        """Trigger manual save."""
        editor = self.query_one(TextArea)
        content = editor.text.strip()
        
        if not content:
            self.notify("Cannot save empty note.", severity="error")
            return

        self.save_to_simplenote(content)

    def save_to_simplenote(self, content: str) -> None:
        """Parses content and sends to Simplenote, skipping the first three lines."""
        
        lines = content.splitlines()
        
        if not lines:
            return

        # 1. Extract Title (First Line)
        title = lines[0].strip()

        # 2. Extract Tags (Second Line, if in parens)
        tags = []
        if len(lines) > 1:
            second_line = lines[1].strip()
            if second_line.startswith("(") and second_line.endswith(")"):
                # Remove parens and split by comma
                tag_str = second_line[1:-1]
                tags = [t.strip() for t in tag_str.split(",") if t.strip()]

        # 3. Construct Note Body (Fourth line onwards)
        # Note: We skip lines 0 (title), 1 (tags), and 2 (assumed empty line)
        if len(lines) >= 4:
            note_body = "\n".join(lines[3:])
        else:
            note_body = "" # If note is too short, the body is empty

        if not note_body.strip():
            self.notify("Note body is empty after skipping title/tags.", severity="warning")
            return
            
        # Simplenote uses the first line of the 'content' field as the title, 
        # but we prepend the extracted title and ensure the body follows.
        final_simplenote_content = f"{title}\n{note_body}"


        note_data = {
            "content": final_simplenote_content,
            "tags": tags,
        }

        # 4. API Call (Run in worker to prevent UI freeze)
        self.run_worker(self._async_save(note_data, title), exclusive=True)

    async def _async_save(self, note_data, title_log):
        """Worker function for saving."""
        try:
            # Simplenote client is synchronous, so use asyncio.to_thread
            result, status = await asyncio.to_thread(sn_client.add_note, note_data)
            if status == 0:
                self.notify(f"Saved: '{title_log}'")
            else:
                self.notify(f"Error saving note. Status: {status}", severity="error")
        except Exception as e:
            self.notify(f"API Error: {str(e)}", severity="error")

    def action_ask_ai(self) -> None:
        """Opens the modal to ask AI."""
        self.push_screen(AskAIModal(), self.handle_ai_response)

    def handle_ai_response(self, prompt: str) -> None:
        """Callback when modal is submitted."""
        if not prompt:
            return
        
        self.notify("Consulting Google AI...")
        self.run_worker(self._async_ai_query(prompt), exclusive=True)

    async def _async_ai_query(self, prompt: str):
        """Worker function for AI generation."""
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = await asyncio.to_thread(model.generate_content, prompt)
            
            editor = self.query_one(TextArea)
            
            # Append the reply to the existing text
            append_text = f"\n\n--- AI Reply ({prompt}) ---\n{response.text}\n"
            editor.insert(append_text) 
            
            self.notify("AI response added.")
            
        except Exception as e:
            self.notify(f"AI Error: {str(e)}", severity="error")

if __name__ == "__main__":
    app = NoteApp()
    app.run()
