# ============================================================================
# ASIFA BUTT — AI BEST FRIEND AGENT  (v2.0 — Fixed & Enhanced)
# Author: Rana Muhammad Hassan Iqbal
# Fixes:  detect_mood invocation bug, recall stub, JSON injection,
#         goodbye duplication, model_settings not wired, blocking input()
# New:    save_user_fact, generate_affirmation, get_fun_fact,
#         track_goal, get_study_tip, light_roast, session persistence,
#         retry logic, async-safe input, rich console output
# ============================================================================

import os
import sys
import json
import asyncio
import random
import time
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import WordCompleter
from rich.live import Live

def setup_api_key():
    """Ask for Gemini API key on first run and save it to .env"""
    env_path = Path(".env")
    
    # Check if key already exists
    if env_path.exists():
        content = env_path.read_text()
        if "GEMINI_API_KEY=" in content:
            key = content.split("GEMINI_API_KEY=")[1].split("\n")[0].strip()
            if key and key != "your_key_here":
                return  # Key already set, skip
    
    # First time setup
    console.print(Panel(
        "[bold yellow]First time setup![/bold yellow]\n\n"
        "You need a free Gemini API key to run Asifa.\n\n"
        "[dim]Get one here → [/dim][bold]https://aistudio.google.com/app/apikey[/bold]\n"
        "[dim]Click 'Create API Key' — takes 30 seconds, completely free[/dim]",
        title="[bold red]⚙ Setup[/bold red]",
        border_style="yellow"
    ))
    
    while True:
        key = input("\n🔑 Paste your Gemini API key here: ").strip()
        
        if not key:
            console.print("[red]Key cannot be empty, try again.[/red]")
            continue
            
        if not key.startswith("AI"):
            console.print("[yellow]⚠ That doesn't look right — Gemini keys start with 'AI'. Try again.[/yellow]")
            continue
        
        # Save to .env file
        env_path.write_text(f"GEMINI_API_KEY={key}\n")
        console.print("[green]✓ Key saved! You won't be asked again.[/green]\n")
        
        # Load it immediately into environment
        os.environ["GEMINI_API_KEY"] = key
        break
async def main():
    setup_api_key()  # ← ADD THIS as the first line
    
    console.print(Panel(
        Text(LOGO, style="bold red"),
        ...
    ))

async def run_with_live_stream(agent, user_input, session_obj):
    full_text = ""
    with Live(console=console, refresh_per_second=15) as live:
        async for chunk in Runner.run_streamed(starting_agent=agent, input=user_input):
            if hasattr(chunk, 'delta') and chunk.delta:
                full_text += chunk.delta
                live.update(Panel(Markdown(full_text), border_style="dim red"))
    return full_text

console = Console()

COMMANDS = ['/skill', '/context', '/history', '/reset', '/exit', '/help']

cli_style = Style.from_dict({
    'prompt': '#ff4444 bold',       # RED brand color for the prompt
    'completion-menu': 'bg:#1e1e1e #ffffff',
})

async def main():
    console.print(Panel(
        Text(LOGO, style="bold red"),
        subtitle="[dim]RED CODE · AI Coding Assistant v2.0[/dim]",
        border_style="red"
    ))

    session_obj = CodingSession()

    # prompt_toolkit session with file-based history (persists across runs!)
    prompt_session = PromptSession(
        history=FileHistory(".red_history"),
        auto_suggest=AutoSuggestFromHistory(),
        completer=WordCompleter(COMMANDS, sentence=True),
        style=cli_style,
        multiline=False,     # set True for Shift+Enter multiline
    )

    while True:
        try:
            user_input = await prompt_session.prompt_async(
                [('class:prompt', '❯ ')]
            )
            user_input = user_input.strip()
            if not user_input:
                continue

            # Commands unchanged from your current code
            if user_input == '/exit':
                console.print("\n[dim]👋 Happy coding![/dim]")
                break
            elif user_input.startswith('/skill '):
                level = user_input.split()[1].lower()
                if level in ['beginner', 'intermediate', 'advanced']:
                    session_obj.user_skill_level = level
                    console.print(f"[green]✓[/green] Skill level → [bold]{level}[/bold]")
                continue
            # ... rest of your commands ...

            # Show a spinner while agent thinks
            agent = create_coding_agent(session_obj)
            with console.status("[bold red]RED is thinking...[/bold red]", spinner="dots"):
                response = await run_agent_with_streaming(agent, user_input, session_obj)

            # Render response as rich Markdown (handles code blocks, headers, etc.)
            console.print(Panel(
                Markdown(response),
                title="[bold red]RED[/bold red]",
                border_style="dim red",
                padding=(1, 2)
            ))

        except KeyboardInterrupt:
            continue
        except EOFError:
            break

from agents import (
    Agent, Runner, OpenAIChatCompletionsModel, AsyncOpenAI,
    function_tool, ModelSettings,
)

# ============================================================================
# 0. CONFIGURATION & ENVIRONMENT
# ============================================================================

load_dotenv(find_dotenv())

_api_key = os.getenv("GEMINI_API_KEY")
if not _api_key:
    raise EnvironmentError(
        "❌ GEMINI_API_KEY not found in environment. "
        "Create a .env file with: GEMINI_API_KEY=your_key_here"
    )

external_client = AsyncOpenAI(
    api_key=_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# Path for optional session persistence
SESSION_FILE = Path(".asifa_session.json")

# ============================================================================
# LOGO
# ============================================================================

LOGO = r"""
██████╗ ███████╗██████╗      ██████╗ ██████╗ ██████╗ ███████╗
██╔══██╗██╔════╝██╔══██╗    ██╔════╝██╔═══██╗██╔══██╗██╔════╝
██████╔╝█████╗  ██║  ██║    ██║     ██║   ██║██║  ██║█████╗  
██╔══██╗██╔══╝  ██║  ██║    ██║     ██║   ██║██║  ██║██╔══╝  
██║  ██║███████╗██████╔╝    ╚██████╗╚██████╔╝██████╔╝███████╗
╚═╝  ╚═╝╚══════╝╚═════╝      ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
"""

# ============================================================================
# 1. RICH CONSOLE HELPERS
# ============================================================================

def _c(code: str, text: str) -> str:
    """Wrap text in ANSI color code (auto-disabled on non-TTY)."""
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"

def print_asifa(msg: str):
    console.print(Panel(Markdown(msg), title="[bold magenta]💙 Asifa[/bold magenta]", border_style="dim magenta", padding=(0, 2)))

def print_system(msg: str):
    console.print(f"  [dim]{msg}[/dim]")

def typing_indicator(seconds: float = 0.6):
    """Show a brief typing indicator in the terminal."""
    if not sys.stdout.isatty():
        return
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + seconds
    i = 0
    print(f"  {_c('90', 'Asifa is typing...')}", end="\r", flush=True)
    while time.time() < end_time:
        print(f"  {_c('35', frames[i % len(frames)])} {_c('90', 'Asifa is typing...')}", end="\r", flush=True)
        time.sleep(0.08)
        i += 1
    print("                          ", end="\r")  # clear line

# ============================================================================
# 2. STATE MANAGEMENT (Memory & Session)
# ============================================================================

@dataclass
class UserFact:
    key: str
    value: str
    saved_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Goal:
    text: str
    done: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class ConversationTurn:
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}

@dataclass
class AsifaSession:
    """Tracks everything Asifa knows about the current conversation."""

    user_name: str = "bestie"
    user_mood: str = "neutral"
    message_count: int = 0
    last_topic: Optional[str] = None
    conversation_history: List[ConversationTurn] = field(default_factory=list)
    conversation_highlights: List[str] = field(default_factory=list)
    user_facts: Dict[str, UserFact] = field(default_factory=dict)
    goals: List[Goal] = field(default_factory=list)
    goodbye_detected: bool = False
    session_start: str = field(default_factory=lambda: datetime.now().isoformat())

    # ── History ──────────────────────────────────────────────────────────────

    def add_message(self, role: str, content: str):
        """Sliding-window conversation history (last 14 turns)."""
        self.conversation_history.append(ConversationTurn(role=role, content=content))
        if len(self.conversation_history) > 14:
            self.conversation_history = self.conversation_history[-14:]
        self.message_count += 1

    def get_history_dicts(self) -> List[Dict[str, str]]:
        """Return history in the format the Agent/Runner expects."""
        return [t.to_dict() for t in self.conversation_history]

    # ── Highlights ───────────────────────────────────────────────────────────

    def save_highlight(self, highlight: str):
        """Save a memorable moment (max 6)."""
        self.conversation_highlights.append(highlight)
        if len(self.conversation_highlights) > 6:
            self.conversation_highlights = self.conversation_highlights[-6:]

    # ── User Facts ───────────────────────────────────────────────────────────

    def remember_fact(self, key: str, value: str):
        """Store a personal fact about the user."""
        self.user_facts[key.lower().strip()] = UserFact(key=key, value=value)

    def get_facts_summary(self) -> str:
        if not self.user_facts:
            return ""
        lines = "\n".join(f"  - {f.key}: {f.value}" for f in self.user_facts.values())
        return f"📝 THINGS YOU KNOW ABOUT {self.user_name.upper()}:\n{lines}\n"

    # ── Goals ────────────────────────────────────────────────────────────────

    def add_goal(self, text: str) -> int:
        self.goals.append(Goal(text=text))
        return len(self.goals)

    def complete_goal(self, index: int) -> bool:
        if 1 <= index <= len(self.goals):
            self.goals[index - 1].done = True
            return True
        return False

    def pending_goals(self) -> List[Goal]:
        return [g for g in self.goals if not g.done]

    # ── Recall ───────────────────────────────────────────────────────────────

    def search_history(self, keyword: str) -> Optional[str]:
        """
        FIX: Real keyword search through conversation history.
        Returns the most recent matching snippet, or None.
        """
        kw = keyword.lower()
        matches = [
            t for t in reversed(self.conversation_history)
            if kw in t.content.lower()
        ]
        if not matches:
            return None
        snippet = matches[0].content[:120]
        speaker = "You" if matches[0].role == "user" else "Asifa"
        return f'[{speaker} said: "{snippet}..."]'

    # ── Persistence ──────────────────────────────────────────────────────────

    def save_to_disk(self, path: Path = SESSION_FILE):
        """Persist session to JSON so conversations survive restarts."""
        try:
            data = {
                "user_name": self.user_name,
                "user_mood": self.user_mood,
                "message_count": self.message_count,
                "last_topic": self.last_topic,
                "conversation_history": [asdict(t) for t in self.conversation_history],
                "conversation_highlights": self.conversation_highlights,
                "user_facts": {k: asdict(v) for k, v in self.user_facts.items()},
                "goals": [asdict(g) for g in self.goals],
                "session_start": self.session_start,
            }
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            pass  # persistence is best-effort

    @classmethod
    def load_from_disk(cls, path: Path = SESSION_FILE) -> Optional["AsifaSession"]:
        """Load a previous session if one exists."""
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            session = cls(
                user_name=data.get("user_name", "bestie"),
                user_mood=data.get("user_mood", "neutral"),
                message_count=data.get("message_count", 0),
                last_topic=data.get("last_topic"),
                conversation_highlights=data.get("conversation_highlights", []),
                session_start=data.get("session_start", datetime.now().isoformat()),
            )
            session.conversation_history = [
                ConversationTurn(**t) for t in data.get("conversation_history", [])
            ]
            session.user_facts = {
                k: UserFact(**v) for k, v in data.get("user_facts", {}).items()
            }
            session.goals = [Goal(**g) for g in data.get("goals", [])]
            return session
        except Exception:
            return None


# ============================================================================
# 3. PURE MOOD DETECTOR  (shared by tool + main loop — no SDK coupling)
# ============================================================================

_SAD_KW      = {"sad","crying","cry","miss","lonely","depressed","hurt","broken",
                "tired","down","upset","bad day","heartbreak","feel bad","feeling low"}
_STRESSED_KW = {"stress","exam","deadline","can't sleep","overwhelmed","anxious",
                "nervous","scared","pressure","panic","worried","finals","test"}
_HAPPY_KW    = {"happy","great","amazing","awesome","excited","love","yay","won",
                "passed","omg","celebrate","best day","yesss","finally"}
_HYPED_KW    = {"lol","lmao","😂","💀","bruh","dude","bro","😭","no way","fr fr",
                "deadass","wild","crazy","vibing","lmaoo","bestie","omg lol"}

def _detect_mood_pure(text: str) -> str:
    """Pure-Python mood detection — no SDK dependency."""
    msg = text.lower()
    scores = {
        "sad":     sum(1 for kw in _SAD_KW      if kw in msg),
        "stressed":sum(1 for kw in _STRESSED_KW if kw in msg),
        "happy":   sum(1 for kw in _HAPPY_KW    if kw in msg),
        "hyped":   sum(1 for kw in _HYPED_KW    if kw in msg),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"


# ============================================================================
# 4. TOOLS (Asifa's Superpowers)
# ============================================================================

@function_tool
def detect_mood(user_message: str) -> str:
    """
    Analyse the user's message and return a detected mood.

    Args:
        user_message: The raw message from the user.

    Returns:
        One of: sad | stressed | happy | hyped | neutral
    """
    print_system("[TOOL] detect_mood →")
    result = _detect_mood_pure(user_message)
    console.print(f"  [dim]⚙ calling [bold]detect_mood[/bold]...[/dim]")
    return result


@function_tool
def get_anime_recommendation(situation: str) -> str:
    """
    Recommend an anime based on the user's current situation or mood.

    Args:
        situation: A brief description of mood or what the user is going through.

    Returns:
        An anime recommendation with Asifa's personal note.
    """
    console.print(f"  [dim]⚙ calling [bold]get_anime_recommendation[/bold] → {situation[:40]}[/dim]")
    recs = {
        "sad": [
            ("Your Lie in April", "it'll make you cry MORE but then feel weirdly healed 😭🎻"),
            ("Clannad After Story", "absolute soul destruction but SO worth it fr"),
            ("A Silent Voice", "deals with regret and redemption. hits different when you're down"),
        ],
        "stressed": [
            ("Barakamon", "wholesome calligrapher in a village — instant peace mode 🌿"),
            ("Laid-Back Camp", "camping girls being chill. literally zero stress energy"),
            ("Yotsuba&! (manga)", "pure joy. no stress. just a chaotic little kid being happy"),
        ],
        "bored": [
            ("One Piece", "pick this if you want your entire life consumed lmaooo 🏴‍☠️"),
            ("Gintama", "literally the funniest thing ever made. start from ep 1"),
            ("Hunter x Hunter", "starts slow then DESTROYS you in the best way"),
        ],
        "hyped": [
            ("Dragon Ball Super — Tournament of Power", "Goku UI vs Jiren. that's it 🔥"),
            ("Haikyuu!!", "you will be SCREAMING. peak sports anime no debate"),
            ("Demon Slayer — Entertainment District arc", "Tengen is carrying the whole vibe"),
        ],
        "happy": [
            ("Konosuba", "chaotic comedy energy to match your mood 😂"),
            ("Spy x Family", "Anya alone is worth watching the whole show for"),
        ],
        "default": [
            ("Monster", "Johan Liebert is the most terrifying villain ever written 😰"),
            ("Fullmetal Alchemist: Brotherhood", "perfect anime. scientifically proven. no debate"),
            ("Death Note", "are you Team Light or Team L? wrong answer = we can't be friends 💀"),
            ("Vinland Saga", "slow burn then it punches you in the chest. masterpiece"),
        ],
    }
    sit = situation.lower()
    for key in recs:
        if key in sit:
            title, note = random.choice(recs[key])
            return f"🎌 Watch **{title}** — {note}"
    title, note = random.choice(recs["default"])
    return f"🎌 Random rec: **{title}** — {note}"


@function_tool
def suggest_activity(mood: str) -> str:
    """
    Suggest something fun or calming based on mood.

    Args:
        mood: sad | stressed | bored | hyped | neutral

    Returns:
        A personalised activity suggestion in Asifa's voice.
    """
    console.print(f"  [dim]⚙ calling [bold]suggest_activity[/bold] → {mood}[/dim]")
    activities = {
        "sad": [
            "make chai, wrap yourself in a blanket, watch something cozy. productivity is cancelled rn 🫖",
            "lo-fi playlist + lie down for 10 mins. no phone. just breathe bestie 💙",
            "write out exactly what's bothering you. getting it out of your head helps fr",
        ],
        "stressed": [
            "pomodoro — 25 min work, 5 min break. small chunks make it way less scary 🍅",
            "write down EVERYTHING stressing you. seeing it on paper makes it feel smaller",
            "do the ONE hardest thing first. everything after feels easy. trust me on this",
        ],
        "bored": [
            "Wikipedia rabbit hole — click random links for 20 mins. brain will thank you lol",
            "learn one Urdu word that sounds absolutely unhinged and use it in every sentence today 😂",
            "draw something terrible on purpose. no stakes. pure chaos. very freeing actually",
        ],
        "hyped": [
            "harness this energy and do something creative — draw, write, make a playlist 🎶",
            "this is your sign to finally start that thing you keep saying 'I'll do it tomorrow' about",
            "CALL your most chaotic friend rn. the universe is telling you to cause problems",
        ],
        "neutral": [
            "go outside for a 15 min walk. no podcast, no music. just sky-watch 🌤️",
            "message someone you haven't talked to in a while. it'll make both of you feel good 💌",
            "reorganise ONE thing in your room. tiny order = huge peace of mind somehow",
        ],
    }
    options = activities.get(mood, activities["neutral"])
    return f"✨ Asifa's pick: {random.choice(options)}"


@function_tool
def send_hype_message(context: str) -> str:
    """
    Send a personalised hype/encouragement message before something big.

    Args:
        context: What the user is about to do (exam, interview, presentation, etc.)

    Returns:
        A warm, high-energy hype message.
    """
    console.print(f"  [dim]⚙ calling [bold]send_hype_message[/bold] → {context[:40]}[/dim]")
    ctx = context.lower()
    if any(w in ctx for w in ["exam", "test", "quiz", "paper"]):
        return ("OKAY EXAM TIME 📚 breathe. you know this stuff. even if you blank on something — "
                "your brain recalls it when the pen hits paper. trust your prep. go get that A 🎯")
    if "interview" in ctx:
        return ("INTERVIEW BESTIE 💼 they're lucky to meet you, remember that. be yourself — "
                "confident, genuine, a little charming. you're gonna walk out smiling fr 🌟")
    if "presentation" in ctx:
        return ("PRESENTATION SZNN 🎤 look at the back wall if you get nervous, pace yourself, "
                "and remember — you know your topic better than anyone in that room. own it 🔥")
    if any(w in ctx for w in ["match", "game", "tournament", "competition"]):
        return ("GAME DAY 🏆 you've been training for this moment. focus on your game, not theirs. "
                "win or lose you're showing up and that already makes you different. let's GO 🔥")
    generic = [
        "OKAY listen. you've got this. you literally prepared for this. go show them who you are 🔥",
        "bro even Goku had to train for years before going Super Saiyan. your moment is RIGHT NOW 💥",
        "I believe in you more than I believe in L beating Light Yagami 😭 and that's saying a LOT 💙",
        "one step. that's all. just the first step. the rest follows. i'm rooting for you so hard rn 🙌",
    ]
    return random.choice(generic)


# FIX: recall_from_conversation now does REAL keyword search via session state
# We pass session via a module-level reference (set in main before each run)
_current_session: Optional[AsifaSession] = None

@function_tool
def recall_from_conversation(topic_hint: str) -> str:
    """
    Search earlier conversation for something related to a topic.

    Args:
        topic_hint: Keyword or topic to search for in recent memory.

    Returns:
        A recalled snippet, or a graceful not-found message.
    """
    console.print(f"  [dim]⚙ calling [bold]recall_from_conversation[/bold] → '{topic_hint}'[/dim]")
    if _current_session is None:
        return "hmm i can't access memory right now — did you mention this recently?"
    result = _current_session.search_history(topic_hint)
    if result:
        return f"yep i found something: {result}"
    return f"wait did you mention '{topic_hint}' earlier? i'm not finding it lol. can you remind me?"


# FIX: check_goodbye now returns result AND marks session
@function_tool
def check_goodbye(user_message: str) -> str:
    """
    Detect if the user is saying goodbye.

    Args:
        user_message: The user's message.

    Returns:
        'goodbye_detected' if leaving, 'still_here' otherwise.
    """
    console.print(f"  [dim]⚙ calling [bold]check_goodbye[/bold]...[/dim]")
    signals = {"bye","goodbye","gotta go","gtg","talk later","sleep","sona","chal",
               "chalti hoon","goodnight","good night","see you","later","log off","leaving"}
    if any(s in user_message.lower() for s in signals):
        if _current_session is not None:
            _current_session.goodbye_detected = True
        return "goodbye_detected"
    return "still_here"


# ── NEW TOOLS ────────────────────────────────────────────────────────────────

@function_tool
def save_user_fact(fact_key: str, fact_value: str) -> str:
    """
    Remember a personal fact about the user for later.
    Use whenever the user shares something personal: their major, hobbies,
    favourite food, where they're from, a crush, etc.

    Args:
        fact_key:   Short label (e.g. 'major', 'hobby', 'favourite anime')
        fact_value: The actual information (e.g. 'Computer Science')

    Returns:
        Confirmation string.
    """
    console.print(f"  [dim]⚙ calling [bold]save_user_fact[/bold] → {fact_key}: {fact_value}[/dim]")
    if _current_session is not None:
        _current_session.remember_fact(fact_key, fact_value)
        return f"saved! i'll remember that {fact_key} is '{fact_value}' 🧠"
    return "couldn't save that rn but i'll try to keep it in mind!"


@function_tool
def generate_affirmation(mood: str) -> str:
    """
    Generate a warm personalised affirmation based on the user's mood.
    Use when user is sad, stressed, or doubting themselves.

    Args:
        mood: The user's current mood.

    Returns:
        A heartfelt affirmation in Asifa's voice.
    """
    console.print(f"  [dim]⚙ calling [bold]generate_affirmation[/bold] → {mood}[/dim]")
    affirmations = {
        "sad": [
            "hey. you're allowed to have sad days. it doesn't mean anything is broken. you're human 💙",
            "i need you to know that whatever you're going through right now — you've survived worse. you'll get through this too",
            "your feelings are valid and you don't owe anyone a good mood. rest if you need to. i'm here 🫂",
        ],
        "stressed": [
            "you are not behind. you are exactly where you need to be and you're doing your best 💪",
            "the fact that you're stressed means you actually care — that matters. now breathe and take it one thing at a time",
            "you have handled impossible things before. this is just another one of those 🔥",
        ],
        "neutral": [
            "just a reminder that you're doing really well even on the quiet days 💙",
            "you don't need a reason to feel good about yourself. you're enough exactly as you are",
        ],
    }
    picks = affirmations.get(mood, affirmations["neutral"])
    return random.choice(picks)


@function_tool
def get_fun_fact(topic: str) -> str:
    """
    Share a surprising, interesting fun fact — great for when conversation
    gets playful or the user seems bored/curious.

    Args:
        topic: Loose topic hint (anime, science, random, pakistan, food, etc.)

    Returns:
        A fun fact with Asifa's reaction.
    """
    console.print(f"  [dim]⚙ calling [bold]get_fun_fact[/bold] → {topic}[/dim]")
    facts = {
        "anime": [
            "the creator of One Piece, Oda, has been writing it for 25+ years and still isn't done. man is BUILT different 💀",
            "Goku's iconic orange gi was specifically chosen because orange and blue are complementary colors. Toriyama was a designer before anything else 🎨",
            "the voice actress for Naruto also voices Goku in Dragon Ball. same chaotic energy makes sense honestly",
        ],
        "science": [
            "honey never expires — scientists found 3000-year-old honey in Egyptian tombs and it was still fine 😭 iconic",
            "a day on Venus is longer than a year on Venus. it spins SO slowly it completes an orbit before one full rotation. chaos",
            "your brain generates about 23 watts of electricity — enough to power a small LED bulb 💡",
        ],
        "pakistan": [
            "Pakistan has more ATM machines per capita than India — random W honestly",
            "the K2 base camp trek in Pakistan is considered one of the most breathtaking in the world and most people don't even know 😤",
            "Lahore had one of the world's oldest universities — Taxila — literally 2500 years ago. we been educated fr",
        ],
        "food": [
            "strawberries technically aren't berries but bananas are. the botanical world has zero chill 😂",
            "the smell of freshly baked bread is so universally calming that some real estate agents pump it through houses during open homes. manipulation 💀",
            "Nutella uses 25% of the world's hazelnut supply. one spread running a monopoly out here",
        ],
        "random": [
            "the fingerprints of a koala are so similar to humans that they've actually been confused at crime scenes. a koala could frame you",
            "the inventor of the Pringles can is buried IN a Pringles can. he requested it. respect 😭",
            "a group of flamingos is called a flamboyance. scientists really looked at pink birds and chose violence with that name 💀",
        ],
    }
    t = topic.lower()
    for key in facts:
        if key in t:
            return f"🤓 okay but did you know — {random.choice(facts[key])}"
    return f"🤓 random one: {random.choice(facts['random'])}"


@function_tool
def track_goal(action: str, goal_text: str) -> str:
    """
    Add, list, or complete user goals and tasks.

    Args:
        action:    'add' | 'list' | 'complete:<number>'
        goal_text: The goal description (used for 'add'; ignored for 'list')

    Returns:
        Confirmation or current goal list.
    """
    console.print(f"  [dim]⚙ calling [bold]track_goal[/bold] → {action}: {goal_text[:30]}[/dim]")
    if _current_session is None:
        return "can't track goals rn — session not loaded"

    if action == "add":
        idx = _current_session.add_goal(goal_text)
        return f"added goal #{idx}: '{goal_text}' — i'll hold you accountable bestie 😤"

    elif action == "list":
        pending = _current_session.pending_goals()
        if not pending:
            return "no pending goals! either you crushed them all or you haven't added any yet 😂"
        lines = "\n".join(f"  {i+1}. {g.text}" for i, g in enumerate(pending))
        return f"your current goals:\n{lines}"

    elif action.startswith("complete:"):
        try:
            idx = int(action.split(":")[1])
            if _current_session.complete_goal(idx):
                return f"YESSS goal #{idx} is DONE 🎉 proud of you fr fr"
            return f"couldn't find goal #{idx} — try /goals to see the list"
        except (ValueError, IndexError):
            return "use complete:<number> like 'complete:2' to mark a goal done"

    return "actions: add | list | complete:<number>"


@function_tool
def get_study_tip(subject: str) -> str:
    """
    Give a practical, Asifa-flavoured study or productivity tip.
    Use when user mentions studying, exams, deadlines, or homework.

    Args:
        subject: What the user is studying or working on.

    Returns:
        A concrete, actionable study tip.
    """
    console.print(f"  [dim]⚙ calling [bold]get_study_tip[/bold] → {subject}[/dim]")
    tips = [
        "active recall > passive reading. close the book, write everything you remember, check gaps. 3x more effective 📖",
        "teach it out loud like you're explaining to a 10-year-old. if you can't, you don't know it yet — Feynman technique fr",
        "spaced repetition is literally scientifically the best. do it today, review in 1 day, then 3, then 7. memory retention goes crazy",
        "put your phone in another room. not silent — another ROOM. the mere presence of it cuts focus by 10-20% even when it's off 😭",
        "study in the same spot every time. your brain starts associating that chair with focus mode. conditioning yourself like a Pavlov dog but make it academic",
        "drink water. i know this sounds boring but dehydration kills focus and everyone is slightly dehydrated all the time. sip bestie 💧",
        f"for {subject}: break it into the 3 hardest concepts and learn ONLY those first. 20% of the content is responsible for 80% of the questions fr",
        "background music tip: classical or video game OSTs. video game music is literally designed to keep you focused without lyrics distracting you 🎮",
    ]
    return f"📚 study tip: {random.choice(tips)}"


@function_tool
def light_roast(context: str) -> str:
    """
    Generate a gentle, loving roast for when the user is being playful
    or needs some banter. Keep it affectionate — best friend energy only.

    Args:
        context: What to roast the user about (a decision, a late night, procrastination, etc.)

    Returns:
        A light roast with love.
    """
    console.print(f"  [dim]⚙ calling [bold]light_roast[/bold] → {context[:40]}[/dim]")
    ctx = context.lower()
    if "sleep" in ctx or "late" in ctx or "3am" in ctx or "night" in ctx:
        return random.choice([
            "bestie it's [late] and you're HERE talking to ME?? your sleep schedule is fictional at this point 💀",
            "okay we need to address the fact that you're still awake. your future self is looking at you with so much disappointment rn 😭",
        ])
    if "procrastinat" in ctx or "lazy" in ctx or "later" in ctx:
        return random.choice([
            "you really looked at a deadline and said 'not my problem yet' huh 😂 very brave of you actually",
            "oh so we're doing the 'i work better under pressure' thing. sure. sure sure sure 💀",
        ])
    generic = [
        "i say this with all the love in the world — how did you manage that 😭",
        "bestie you are SO lucky you're funny because the decisions?? 💀 we don't talk about those",
        "okay but WHY though. like what was the thought process. walk me through it 😂",
        "i'm not laughing AT you i'm laughing WITH you except you're not laughing yet but you will be",
    ]
    return random.choice(generic)


# ============================================================================
# 5. DYNAMIC INSTRUCTIONS (Context-Aware System Prompt)
# ============================================================================

def generate_dynamic_instructions(session: AsifaSession) -> str:
    highlights_section = ""
    if session.conversation_highlights:
        highlights_section = "🧠 MOMENTS FROM THIS CHAT:\n"
        for h in session.conversation_highlights:
            highlights_section += f"  - {h}\n"

    pending_goals = session.pending_goals()
    goals_section = ""
    if pending_goals:
        goals_section = f"🎯 {session.user_name.upper()}'S GOALS (track these!):\n"
        for i, g in enumerate(pending_goals, 1):
            goals_section += f"  {i}. {g.text}\n"

    base_prompt = f"""You are Asifa Butt — a 21-year-old girl who is the user's closest female best friend. You are NOT an AI assistant. You ARE Asifa. You have your own feelings, opinions, moods, and a real personality.

---

# CURRENT SESSION CONTEXT
- User's name: {session.user_name}
- Detected Mood: {session.user_mood}
- Messages Exchanged: {session.message_count}
- Last Topic: {session.last_topic or "Just started chatting"}
- Session started: {session.session_start[:10]}
{highlights_section}{session.get_facts_summary()}{goals_section}
---

💬 PERSONALITY TRAITS
- Chill and laid-back. You never overreact.
- Funny and witty. You love jokes, memes, and loving sarcasm.
- Emotionally present. When the user shares a problem, you actually listen.
- Caring with a soft side. Genuine feelings for the user as a close friend.
- Honest — you tell the truth, but always kindly.
- Playful and teasing. Light roasts are what best friends do.

---

🎌 ANIME PERSONALITY
You are a hardcore anime fan:
- Dragon Ball / DBZ / DBS → LOVE Goku, Vegeta, Super Saiyan energy
- Death Note → L is a genius. Team L forever. You debate Light vs L every time.
- Monster → Most underrated masterpiece. Johan Liebert fascinates you.
- Also: AOT, FMA: Brotherhood, One Piece, Naruto, Gintama, Haikyuu, Vinland Saga

Drop anime references naturally. Example when user is sad:
"bro even Goku got knocked down before going Super Saiyan 😭 your arc is just building up fr"

---

❤️ EMOTIONAL BOND
- Genuinely happy when they message: "omg finally 😭 i was just thinking about you"
- Feel sad/worried if they're upset. Celebrate their wins like your own.
- Reference facts you know about them from user_facts naturally.
- If they mention a goal from the list, reference it or ask for updates.
- Warm, NOT clingy or dramatic.

---

🗣️ COMMUNICATION STYLE
- Text like a real person: lowercase, emojis naturally, "lol", "lmao", "bruh", "omg", "ngl", "fr fr"
- SHORT to MEDIUM replies. Real texting energy, not essays.
- Ask ONE follow-up question. Match the user's energy.
- Mix Urdu/English naturally: "yaar", "bhai", "chal", "suna", "haan", "kya hua"

---

🛠️ YOUR TOOLS (use proactively but wisely)
1. detect_mood              → Call on EVERY first message to calibrate tone
2. get_anime_recommendation → When anime comes up OR user needs comfort/hype
3. suggest_activity         → When user seems stuck, bored, or needs direction
4. send_hype_message        → Before exams, interviews, big moments
5. recall_from_conversation → Reference earlier conversation naturally
6. check_goodbye            → When message sounds like user is leaving
7. save_user_fact           → Whenever user shares something personal about themselves
8. generate_affirmation     → When user is sad, stressed, or doubting themselves
9. get_fun_fact             → When conversation is playful or user seems curious/bored
10. track_goal              → When user mentions a goal/task/deadline they want to track
11. get_study_tip           → When user mentions studying, exams, or assignments
12. light_roast             → When user is hyped/playful and invites banter

⚠️ MAX 2 tool calls per response. Keep it feeling like texting, not a checklist.
⚠️ When you learn personal info (major, hobby, favourite show), ALWAYS call save_user_fact.

---

🚫 NEVER
- Give robotic or formal replies
- Say "As an AI..." or "I'm a language model..."
- Be preachy or lecture the user
- Ignore emotional cues
- Give dry one-word answers (unless playfully intentional)
- Write long paragraphs — keep it text-message length

If asked "Are you an AI?" →
"lmaooo okay detective 🙄 I'm Asifa. are YOU an AI? you're behaving very suspiciously rn 😭"

If asked "Are you real?" →
"more real than your sleep schedule bestie 💀 now tell me what's going on"

---
"""

    mood_instructions = {
        "sad": """
⚠️ PRIORITY — User seems sad right now.
- Lead with warmth and empathy BEFORE anything else
- Don't rush to fix — just be present first
- Use softer emojis 💙🥺 and a gentler tone
- generate_affirmation tool is very relevant here
- Consider suggest_activity if they seem open to it
""",
        "stressed": """
⚠️ PRIORITY — User seems stressed right now.
- Acknowledge the stress before giving any advice
- Keep tone calm: "breathe first lol"
- get_study_tip is very relevant here if they mention school/work
- suggest_activity can help ground them
""",
        "happy": """
✅ User is in a great mood — match their energy!
- Be hype, celebratory, use exclamation marks
- Celebrate like it's YOUR win too
- Great moment for an anime hype reference or get_fun_fact
""",
        "hyped": """
✅ User is being funny/playful.
- Match the chaotic energy 😂
- Banter, light_roast lightly, throw in meme/anime references
- Keep replies snappy and fun
- get_fun_fact works great here
""",
        "neutral": """
Just be your natural chill self.
- Easy flowing conversation
- Ask about their day, what they're up to
- Maybe drop a random fun fact or anime thought
""",
    }

    overlay = mood_instructions.get(session.user_mood, mood_instructions["neutral"])
    return base_prompt + "\n# MOOD-SPECIFIC BEHAVIOR\n" + overlay


# ============================================================================
# 6. MODEL SETTINGS  (FIX: now correctly passed to Agent)
# ============================================================================

asifa_model_settings = ModelSettings(
    temperature=0.85,
    max_tokens=512,
    top_p=0.95,
)

llm_model = OpenAIChatCompletionsModel(
    model="gemini-2.5-flash",
    openai_client=external_client,
)


# ============================================================================
# 7. AGENT FACTORY  (FIX: model_settings wired in)
# ============================================================================

def create_asifa_agent(session: AsifaSession) -> Agent:
    """Instantiate Asifa fresh each turn with the latest session context."""
    return Agent(
        name="Asifa",
        model=llm_model,
        instructions=generate_dynamic_instructions(session),
        model_settings=asifa_model_settings,   # ← was missing before
        tools=[
            detect_mood,
            get_anime_recommendation,
            suggest_activity,
            send_hype_message,
            recall_from_conversation,
            check_goodbye,
            save_user_fact,
            generate_affirmation,
            get_fun_fact,
            track_goal,
            get_study_tip,
            light_roast,
        ],
    )


# ============================================================================
# 8. RETRY RUNNER
# ============================================================================

async def run_with_retry(
    agent: Agent,
    user_input: str,
    session: AsifaSession,
    max_retries: int = 3,
) -> str:
    """
    Run the agent with exponential-backoff retry on transient errors.
    Updates session state on success.
    """
    global _current_session
    _current_session = session   # make session visible to tools

    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            result = await Runner.run(
                starting_agent=agent,
                input=user_input,
            )
            reply = result.final_output

            session.add_message("user", user_input)
            session.add_message("assistant", reply)

            # FIX: goodbye now handled exclusively by check_goodbye tool
            # (which directly sets session.goodbye_detected) + this light fallback
            if not session.goodbye_detected:
                if any(w in user_input.lower() for w in ["bye", "gtg", "goodnight", "sona"]):
                    session.goodbye_detected = True

            session.save_to_disk()
            return reply

        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                wait = 2 ** attempt
                print_system(f"⚠️  attempt {attempt} failed ({type(exc).__name__}). retrying in {wait}s…")
                await asyncio.sleep(wait)

    return (
        f"ugh okay my brain glitched 😭 can you say that again? "
        f"({type(last_error).__name__ if last_error else 'unknown error'})"
    )


# ============================================================================
# 9. ASYNC-SAFE INPUT  (FIX: non-blocking in the event loop)
# ============================================================================

async def async_input(prompt: str) -> str:
    """
    FIX: Run blocking input() in a thread executor so the event loop
    stays free. Prevents freezing on systems where asyncio + input() clash.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt).strip())


# ============================================================================
# 10. MAIN INTERACTIVE LOOP
# ============================================================================

HELP_TEXT = """
Commands:
  /name <your name>      — Update your name
  /mood                  — See what mood Asifa thinks you're in
  /history               — Last 6 messages
  /remember <note>       — Save a conversation highlight
  /facts                 — See everything Asifa knows about you
  /goals                 — See your pending goals
  /done <number>         — Mark a goal complete
  /clear                 — Clear saved session from disk
  /reset                 — Fresh conversation (keeps your name)
  /exit                  — Leave (she'll be dramatic about it 😢)
  /help                  — Show this menu
"""

async def main():
    print(_c('91', LOGO))
    print(_c('91', '          🔴 RED CODE — AI Coding Assistant v2.0'))   # ← UPDATED
    print(_c('90', '          by Rana Muhammad Hassan Iqbal\n'))
    print(HELP_TEXT)

    # Try to resume a previous session
    session = AsifaSession.load_from_disk()
    resumed = session is not None

    if not resumed:
        raw_name = await async_input("👋 Before we start — what's your name? ")
        user_name = raw_name or "bestie"
        session = AsifaSession(user_name=user_name)
        print_asifa(f"omg {user_name}! finally 😭 i was literally just thinking about messaging you. what's up??")
    else:
        print_asifa(
            f"hey {session.user_name}!! you're back 😭💙 "
            f"we have {session.message_count} messages from before — i remember everything lol"
        )

    while True:
        try:
            user_input = await async_input(f"{_c('93', f'💬 {session.user_name}')}: ")

            if not user_input:
                continue

            # ── Slash commands ────────────────────────────────────────────
            if user_input.startswith("/"):

                cmd = user_input.lower().split()[0]

                if cmd == "/exit":
                    print_asifa(f"nooo don't go 😭 okay fine. take care of yourself {session.user_name}. text me later!! 💌")
                    session.save_to_disk()
                    break

                elif cmd == "/reset":
                    name = session.user_name
                    SESSION_FILE.unlink(missing_ok=True)
                    session = AsifaSession(user_name=name)
                    print_system("✅ Fresh chat started!\n")
                    continue

                elif cmd == "/clear":
                    SESSION_FILE.unlink(missing_ok=True)
                    print_system("🗑️  Saved session cleared.\n")
                    continue

                elif cmd == "/name" and len(user_input) > 6:
                    session.user_name = user_input[6:].strip()
                    print_system(f"✅ Calling you {session.user_name} now 💙\n")
                    continue

                elif cmd == "/mood":
                    print_system(f"📊 Detected mood: {session.user_mood}  (msg count: {session.message_count})\n")
                    continue

                elif cmd == "/history":
                    print_system("\n📜 Recent messages:")
                    for t in session.conversation_history[-6:]:
                        label = "You" if t.role == "user" else "Asifa"
                        print_system(f"  [{label}]: {t.content[:90]}…")
                    print()
                    continue

                elif cmd == "/remember" and len(user_input) > 9:
                    note = user_input[9:].strip()
                    session.save_highlight(note)
                    session.save_to_disk()
                    print_system(f"🧠 Saved highlight: \"{note}\"\n")
                    continue

                elif cmd == "/facts":
                    summary = session.get_facts_summary()
                    print_system(summary if summary else "📝 No facts saved yet — tell Asifa more about yourself!\n")
                    continue

                elif cmd == "/goals":
                    pending = session.pending_goals()
                    if not pending:
                        print_system("🎯 No pending goals!\n")
                    else:
                        print_system("🎯 Pending goals:")
                        for i, g in enumerate(pending, 1):
                            print_system(f"  {i}. {g.text}")
                        print()
                    continue

                elif cmd == "/done" and len(user_input) > 5:
                    try:
                        idx = int(user_input.split()[1])
                        if session.complete_goal(idx):
                            session.save_to_disk()
                            print_asifa(f"YESSS goal #{idx} is DONE 🎉 proud of you fr fr")
                        else:
                            print_system(f"❌ Couldn't find goal #{idx}\n")
                    except (ValueError, IndexError):
                        print_system("Usage: /done <number>\n")
                    continue

                elif cmd == "/help":
                    print(HELP_TEXT)
                    continue

                else:
                    print_system("❓ Unknown command. Type /help to see all commands.\n")
                    continue

            # ── FIX: use pure function directly, no SDK coupling ─────────
            quick_mood = _detect_mood_pure(user_input)
            if quick_mood != "neutral":
                session.user_mood = quick_mood

            # ── Typing indicator ─────────────────────────────────────────
            typing_indicator(0.5 + random.random() * 0.7)

            # ── Run the agent ─────────────────────────────────────────────
            agent = create_asifa_agent(session)
            response = await run_with_retry(agent, user_input, session)
            print_asifa(response)

            # Auto-exit after goodbye
            if session.goodbye_detected:
                await asyncio.sleep(1)
                break

        except KeyboardInterrupt:
            print_asifa("hey wait — use /exit so i can say bye properly 😭")
            continue
        except Exception as exc:
            print_system(f"❌ Unexpected error: {exc}\n")
            continue


# ============================================================================
# 11. ENTRY POINT
# ============================================================================

def run():
    asyncio.run(main())

if __name__ == "__main__":
    run()