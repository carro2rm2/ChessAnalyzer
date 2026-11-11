
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import queue

from chess_data import fetch_games
from analyzer import analyze_games


class ChessAnalyzer:

    def __init__(self, root):

        self.root = root

        self.root.title("ChessAnalyzer")
        self.root.geometry("850x700")
        self.root.minsize(650, 550)

        self.results = queue.Queue()

        self.build_gui()

        self.root.after(150, self.check_results)

    def build_gui(self):

        main = ttk.Frame(self.root, padding=18)
        main.pack(fill="both", expand=True)

        title = ttk.Label(
            main,
            text="ChessAnalyzer",
            font=("Segoe UI", 24, "bold")
        )

        title.pack(anchor="w")

        subtitle = ttk.Label(
            main,
            text="Chess.com Player Strength Analyzer"
        )

        subtitle.pack(anchor="w", pady=(0, 15))

        search = ttk.LabelFrame(
            main,
            text="Player Search",
            padding=12
        )

        search.pack(fill="x", pady=10)

        self.username = tk.StringVar(
            value="rmcarroll604"
        )

        self.entry = ttk.Entry(
            search,
            textvariable=self.username,
            font=("Segoe UI", 12)
        )

        self.entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 10)
        )

        self.entry.bind(
            "<Return>",
            lambda event: self.start_analysis()
        )

        self.button = ttk.Button(
            search,
            text="Analyze Player",
            command=self.start_analysis
        )

        self.button.pack(side="right")

        self.status = tk.StringVar(
            value="Enter a Chess.com username to begin."
        )

        ttk.Label(
            main,
            textvariable=self.status
        ).pack(anchor="w", pady=8)

        report_frame = ttk.LabelFrame(
            main,
            text="Analysis Report",
            padding=10
        )

        report_frame.pack(fill="both", expand=True)

        self.output = ScrolledText(
            report_frame,
            font=("Consolas", 10),
            wrap="word"
        )

        self.output.pack(fill="both", expand=True)

        self.write(
            "CHESS ANALYZER\n"
            "========================================\n\n"
            "Enter a Chess.com username and click Analyze Player.\n\n"
            "The first version analyzes rapid-game results and "
            "estimates performance strength.\n\n"
            "Stockfish move analysis will be added later."
        )

    def write(self, text):

        self.output.configure(state="normal")

        self.output.delete("1.0", "end")

        self.output.insert("1.0", text)

        self.output.configure(state="disabled")

    def start_analysis(self):

        username = self.username.get().strip()

        if not username:
            messagebox.showwarning(
                "Missing username",
                "Please enter a Chess.com username."
            )
            return

        self.button.configure(state="disabled")
        self.entry.configure(state="disabled")

        self.status.set(
            "Retrieving games from Chess.com..."
        )

        thread = threading.Thread(
            target=self.worker,
            args=(username,),
            daemon=True
        )

        thread.start()

    def worker(self, username):

        try:

            # Retrieve player information
            player_data = fetch_games(
                username,
                limit=100
            )

            # Extract the dictionary values
            actual_username = player_data["username"]
            games = player_data["games"]
            rating = player_data["current_rating"]

            # Analyze the games
            report = analyze_games(
                games,
                rating
            )

            self.results.put((
                "success",
                actual_username,
                games,
                report
            ))

        except Exception as error:

            self.results.put((
                "error",
                str(error)
            ))

    def check_results(self):

        try:

            result = self.results.get_nowait()

        except queue.Empty:

            self.root.after(
                150,
                self.check_results
            )

            return

        self.button.configure(state="normal")
        self.entry.configure(state="normal")

        if result[0] == "error":

            self.status.set("Analysis failed.")

            messagebox.showerror(
                "ChessAnalyzer",
                result[1]
            )

        else:

            _, username, games, report = result

            self.status.set(
                f"Analyzed {len(games)} rapid games: {username}"
            )

            self.display_report(username, games, report)

        self.root.after(
            150,
            self.check_results
        )

    def display_report(self, username, games, data):

        current = data["current_rating"]

        lines = [

            "CHESS ANALYZER REPORT",

            "=" * 55,

            f"Player: {username}",

            "",

            "PLAYER STRENGTH",

            "-" * 55,

            f"Current Chess.com rating: {current}",

            f"Consistency floor:       {data['floor']}",

            f"Typical performance:     {data['typical']}",

            f"Consistency ceiling:     {data['ceiling']}",

            "",

            "MAXIMUM DEMONSTRATED PERFORMANCE",

            "-" * 55,

            (
                f"Best 20-game stretch: "
                f"{data['best_sustained']['rating']}"
            ),

            (
                f"Dates: "
                f"{data['best_sustained']['start']} to "
                f"{data['best_sustained']['end']}"
            ),

            (
                f"Best 10-game stretch: "
                f"{data['best_short']['rating']}"
            ),

            (
                f"Dates: "
                f"{data['best_short']['start']} to "
                f"{data['best_short']['end']}"
            ),

            "",

            "GAME STATISTICS",

            "-" * 55,

            f"Games analyzed:       {data['total']}",

            f"Wins:                 {data['wins']}",

            f"Draws:                {data['draws']}",

            f"Losses:               {data['losses']}",

            f"Score percentage:     {data['score']}%",

            f"Average player rating: {data['average_player']}",

            f"Average opponent:     {data['average_opponent']}",

            "",

            "MOST RECENT GAMES",

            "-" * 55
        ]

        for game in reversed(games[-15:]):

            lines.append(
                f"{game['date']} | "
                f"{game['result']:4} | "
                f"{game['player_rating']:4} vs "
                f"{game['opponent_rating']:4} | "
                f"{game['opponent']}"
            )

        if data["warnings"]:

            lines.extend([
                "",
                "WARNINGS",
                "-" * 55
            ])

            for warning in data["warnings"]:
                lines.append(warning)

        lines.extend([

            "",

            "HOW TO INTERPRET THE RESULTS",

            "-" * 55,

            "Floor = 20th percentile of rolling performance.",

            "Typical = median rolling performance.",

            "Ceiling = 80th percentile of rolling performance.",

            "Maximum demonstrated performance = best sustained "
            "20-game stretch.",

            "",

            "These are statistical estimates, not official "
            "Chess.com ratings or guaranteed future potential.",

            "Stockfish analysis has not yet been incorporated."
        ])

        self.write("\n".join(lines))


if __name__ == "__main__":

    root = tk.Tk()

    app = ChessAnalyzer(root)

    root.mainloop()
