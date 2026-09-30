from .antigravity import AntigravityAdapter
from .gemini import GeminiAdapter
from .claude_code import ClaudeCodeAdapter

ADAPTERS = {"antigravity": AntigravityAdapter(), "gemini": GeminiAdapter(), "claude_code": ClaudeCodeAdapter()}
