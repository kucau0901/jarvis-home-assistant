"""Names and timings shared by the integration."""

DOMAIN = "jarvis"
CONF_URL = "url"
CONF_TOKEN = "token"

# How often the batch is looked at: urgent changes go within a couple of seconds of it.
TICK_SECONDS = 2
# The watch list is asked for again when Jarvis's reply says it moved, and at least this often.
REFRESH_SECONDS = 6 * 3600
TIMEOUT_SECONDS = 15
