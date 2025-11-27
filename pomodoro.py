from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Digits
from textual.binding import Binding

class PomodoroApp(App):
    """A Textual app for a simple Pomodoro timer."""

    CSS = """
    Screen {
        align: center middle;
    }
    
    Digits {
        text-align: center;
        width: auto;
        color: #00ff00;
    }
    """

    BINDINGS = [
        Binding("1", "start_timer(25)", "25 Min"),
        Binding("2", "start_timer(10)", "10 Min"),
        Binding("3", "start_timer(5)", "5 Min"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.timer_obj = None
        self.total_seconds = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        # Initialize with 00:00 as requested
        yield Digits("00:00", id="clock")
        yield Footer()

    def action_start_timer(self, minutes: int) -> None:
        """Start a countdown for the specified number of minutes."""
        # Cancel existing timer if running
        if self.timer_obj:
            self.timer_obj.stop()

        self.total_seconds = minutes * 60
        self.update_clock_display()
        
        # set_interval returns a Timer object that we can stop later
        self.timer_obj = self.set_interval(1, self.tick)

    def tick(self) -> None:
        """Decrement the timer by one second."""
        if self.total_seconds > 0:
            self.total_seconds -= 1
            self.update_clock_display()
        else:
            # Timer finished
            if self.timer_obj:
                self.timer_obj.stop()
            self.query_one(Digits).update("00:00")
            self.bell() # System beep to notify user

    def update_clock_display(self) -> None:
        """Update the Digits widget with the current time."""
        minutes, seconds = divmod(self.total_seconds, 60)
        time_str = f"{minutes:02d}:{seconds:02d}"
        self.query_one(Digits).update(time_str)

if __name__ == "__main__":
    app = PomodoroApp()
    app.run()
