import time
import re
from datetime import datetime
import feedparser
from bs4 import BeautifulSoup
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Container
from textual.widgets import Header, Footer, Static, Label
from textual.reactive import reactive
from textual.binding import Binding

class RSSReaderApp(App):
    """
    A Textual app to cycle through RSS feed stories.
    Features: 
    - Auto-advance (10s)
    - Auto-refresh feeds (1hr)
    - Clean text (First paragraph only, flattened)
    """

    CSS = """
    Screen {
        align: center middle;
    }
    
    #main-container {
        width: 80%;
        height: 90%;
        border: solid green;
        padding: 1 2;
        background: $surface;
    }

    #title {
        width: 100%;
        height: auto;
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        padding-bottom: 1;
        border-bottom: solid $primary-background;
    }

    #meta {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    #body {
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("right", "next_story", "Next"),
        Binding("space", "next_story", "Next"),
        Binding("left", "prev_story", "Previous"),
        Binding("r", "refresh_feeds", "Force Refresh"),
    ]

    # State
    stories = []
    current_index = reactive(0)
    auto_timer = None 

    def __init__(self, feed_file="feeds.txt"):
        super().__init__()
        self.feed_file = feed_file

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            yield Static("Loading feeds...", id="title")
            yield Label("", id="meta")
            with VerticalScroll():
                yield Static("", id="body")
        yield Footer()

    def on_mount(self) -> None:
        """Start the app, load feeds, and set timers."""
        # 1. Initial Load
        self.refresh_feeds()
        
        # 2. Set Auto-Advance Timer (Cycles story every 10 seconds)
        self.auto_timer = self.set_interval(10.0, self.action_next_story)

        # 3. Set Feed Refresh Timer (Reloads RSS every 1 hour / 3600 seconds)
        self.set_interval(3600.0, self.refresh_feeds)

    def refresh_feeds(self):
        """Wrapper to run the blocking load_feeds method in a thread."""
        self.notify("Refreshing RSS feeds...")
        self.run_worker(self.load_feeds, exclusive=True, thread=True)

    def load_feeds(self):
        """Reads feeds.txt, parses RSS, cleans data, and sorts by date."""
        try:
            with open(self.feed_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.call_from_thread(self.query_one("#title", Static).update, "Error: feeds.txt not found")
            return

        all_entries = []
        for url in urls:
            try:
                # Use feedparser (blocking I/O)
                parsed = feedparser.parse(url)
                for entry in parsed.entries:
                    # Get raw content (summary or content)
                    raw_content = entry.get('content', [{'value': entry.get('summary', '')}])[0]['value']
                    
                    # Apply the strict "First Paragraph + Flatten" cleaning
                    clean_text = self.clean_html(raw_content)
                    
                    # Handle Date
                    pub_date = entry.get('published_parsed') or entry.get('updated_parsed')
                    if pub_date:
                        dt_object = datetime.fromtimestamp(time.mktime(pub_date))
                    else:
                        dt_object = datetime.now()

                    all_entries.append({
                        'title': entry.get('title', 'No Title'),
                        'date': dt_object,
                        'source': parsed.feed.get('title', url),
                        'body': clean_text
                    })
            except Exception:
                continue # Skip broken feeds

        # Sort and Store
        if all_entries:
            self.stories = sorted(all_entries, key=lambda x: x['date'], reverse=True)
            # Reset index to 0 so we don't crash if the list length changed
            self.current_index = 0
            self.call_from_thread(self.update_display)
        else:
            self.call_from_thread(self.query_one("#title", Static).update, "No stories found.")

    def clean_html(self, html_content):
        """
        1. Extract FIRST paragraph (<p>) only.
        2. Remove all hard returns/formatting within that paragraph.
        """
        if not html_content:
            return "No content available."

        soup = BeautifulSoup(html_content, "lxml")
        
        # 1. Grab first <p> or fallback to all text
        first_p = soup.find('p')
        if first_p:
            raw_text = first_p.get_text()
        else:
            raw_text = soup.get_text()

        # 2. Flatten: Replace newlines/tabs/spaces with single space
        flat_text = re.sub(r'\s+', ' ', raw_text).strip()
        
        return flat_text

    def update_display(self):
        """Updates widgets based on current_index."""
        if not self.stories:
            return

        # Safety check for index bounds
        if self.current_index >= len(self.stories):
            self.current_index = 0

        story = self.stories[self.current_index]
        date_str = story['date'].strftime("%Y-%m-%d %H:%M")
        
        self.query_one("#title", Static).update(story['title'])
        self.query_one("#meta", Label).update(f"{story['source']} | {date_str}")
        self.query_one("#body", Static).update(story['body'])
        
        self.query_one(VerticalScroll).scroll_home(animate=False)

    def action_next_story(self):
        """Next story + reset idle timer."""
        if self.stories:
            self.current_index = (self.current_index + 1) % len(self.stories)
            self.update_display()
            if self.auto_timer:
                self.auto_timer.reset()

    def action_prev_story(self):
        """Prev story + reset idle timer."""
        if self.stories:
            self.current_index = (self.current_index - 1) % len(self.stories)
            self.update_display()
            if self.auto_timer:
                self.auto_timer.reset()

if __name__ == "__main__":
    app = RSSReaderApp()
    app.run()
