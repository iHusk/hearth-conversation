"""Constants for the Hearth Conversation integration."""

DOMAIN = "hearth_conversation"

CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_AGENT_ID = "agent_id"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SYSTEM_PROMPT = "system_prompt"
CONF_TIMEOUT = "timeout"
CONF_MAX_HISTORY = "max_history"

DEFAULT_BASE_URL = "https://clawd.hayeshousehold.com"
DEFAULT_AGENT_ID = "main"
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_HISTORY = 10
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful voice assistant. Keep responses brief and natural — "
    "they will be spoken aloud. Avoid markdown, bullet points, or formatting. "
    "Use short sentences."
)

ERROR_UNREACHABLE = "I can't reach my brain right now. Try again in a moment."
ERROR_AUTH = "I'm having trouble authenticating. Check my settings."
ERROR_TIMEOUT = "That took too long. Try asking again."
ERROR_UNKNOWN = "Something went wrong on my end. Try again."
