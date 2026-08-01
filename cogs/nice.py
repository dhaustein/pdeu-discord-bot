"""Replies 'hello world' when a trigger phrase appears as a standalone word."""

import logging
from random import choice

import discord

from bot import PDEUBot

from .base import MessageWatcherCog

logger = logging.getLogger(__name__)

NICE_LIST = ["nice", "nice.", "nice!"]


class NiceCog(MessageWatcherCog):
    """Replies when a trigger phrase appears as a standalone word."""

    async def handle(self, message: discord.Message) -> None:
        if message.content == "I for one welcome our AI overlords.":
            logger.debug(f"Welcome phrase matched in message: {message.id}")
            await message.channel.send(f"Very well, you will be killed last, {message.author}")

        if message.content.lower() in NICE_LIST and message.author.id in ["444270573434961932", "238924573213589505"]:  # Patropolis
            logger.debug(f"Nice matched in message: {message.id}")
            await message.channel.send(reply_to_patropolis())


def reply_to_patropolis() -> str:
    replies = [
        "Good craic!",
        "That's grand.",
        "What a great bunch of lads!",
        "I'm pooping in the embassy.",
        "Tiocfaidh ár lá!",
        "Noice!",
        "This will help my lactic acid.",
        "Grand.",
        "That's pretty rock and roll.",
        "nice",
        "I am so warm right now.",
        "God I love girls.",
        "ugh",
        "I have an itchy bum.",
        "I just had an awesome poop, lads!",
        "Boli me kurac.",
        "[F1 trivia]",
        "...and don't call me paddy!",
        "That was a solid 6 on the Bristol scale.",
        "I too have a Japanese waifu",
        "SweepyB",
        "I love getting blasted.",
        "This is good vibes",
        "fuckin class",
        "Right on, brother.",
        "that was pretty mad, I enjoyed it",
        "you're a good lad",
        "I eat fish and chips on the bus.",
        "I just want to stick my 3.5mm somewhere",
        "I'd wank to Elusive",
        "who let this many weebs in here",
        "Bon craic!",
        "C'est grandiose.",
        "Quelle belle bande de gars!",
        "Je fais caca à l'ambassade.",
        "Le Tiocfaidh ár lá!",
        "l'Noice!",
        "Cela aidera mon acide lactique.",
        "Grandiose.",
        "C'est plutôt rock and roll.",
        "joli!",
        "J'ai tellement chaud en ce moment.",
        "Dieu j'aime les filles.",
        "pouah...",
        "J'ai des fesses qui piquent.",
        "Je viens d'avoir une merde géniale, gars!",
        "Boli me le kurac.",
        "[Trivia de F1]",
        "... et ne m'appelle pas « paddy! »",
        "C'était un solide 6 sur l'échelle de Bristol.",
        "Moi aussi j'ai un waifu japonais",
        "l'SviaupiB",
        "J'adore me faire exploser.",
        "Ce sont de bonnes vibrations",
        "putain de classe",
        "Tout de suite, frère.",
        "c'était assez fou, j'ai bien aimé",
        "tu es un bon garçon",
        "Je mange du poisson-frites dans le bus.",
        "Je veux juste coller mon 3,5 mm quelque part",
        "Je me branlerais à monsieur Elusíve",
        "qui a laissé autant de weebs ici",
        "Craic mhaith!",
        "Tá sé sin go breá.",
        "Nach maith an bhuíon buachaillí iad!",
        "Tá mé ag cacú san ambasáid.",
        "Ar dóigh! ",
        "Cabhróidh sé seo le m'aigéad lachtach.",
        "Go breá.",
        "Tá sé sin go leor 'rock and roll'.",
        "A Dhia, is aoibhinn liom cailíní.",
        "Tá mo thóin ag tochas.",
        "Rinne mé cac iontach díreach anois, a bhuachaillí!",
        "Is cuma sa diabhal liom. ",
        "[Eolas fánach F1]",
        "...agus ná glaor Páidí orm!",
        "Bhí sé sin ina 6 dhaingean ar scála Bristol.",
        "Is aoibhinn liom a bheith gafa ar an ól.",
        "Sár-aicmeach!",
        "Sin é, a dheartháir!",
        "bhí sé sin go leor mire, thaitin sé liom",
        "is maith an buachaill thú",
        "Ithim iasc agus sceallóga ar an mbus.",
        "Níl uaim ach mo 3.5mm a shá isteach áit éigin",
        "Bhuailfinn ceann do Elusive",
        "cé a lig an oiread sin 'weebs' isteach anseo",
    ]

    return choice(replies)


async def setup(bot: PDEUBot) -> None:
    await bot.add_cog(NiceCog(bot, bot.watch_channel_id))
    logger.info("Loaded cog %s", __name__)
