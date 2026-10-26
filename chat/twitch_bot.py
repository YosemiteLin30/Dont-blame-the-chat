"""TwitchIO (v2) bot: forwards chat lines to the game bridge."""


def handle_message(bridge, author, content):
    """Shared by the live bot and tests: queue a chat line as a game command."""
    return bridge.submit_text("twitch", author, content)


def make_bot(token, channel, bridge):
    from twitchio.ext import commands

    class ChatBot(commands.Bot):
        def __init__(self):
            super().__init__(token=token, prefix="!", initial_channels=[channel])

        async def event_ready(self):
            print(f"Twitch: connected as {self.nick}, listening to #{channel}")

        async def event_message(self, message):
            if message.echo or message.author is None:
                return
            handle_message(bridge, message.author.name, message.content)

    return ChatBot()
