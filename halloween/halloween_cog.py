import discord
import asyncio
from urllib.request import Request, urlopen
from typing_extensions import final
from discord.ext import commands
from datetime import date, datetime
from pytz import timezone
from bs4 import BeautifulSoup
from discord.ext import commands
from .halloween_commands import CREEPY_PASTA_COMMAND_ALIASES

class HalloweenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embeds_queue = []
        self.list_of_creepy_pastas = [
            "la-aldea-maldita-de-clash-of-clans", "la-extrana-muerte-de-kurt-kaufmann","marca-de-hielo",
            "carretera","mermaid-project","ojo-derecho","hermanastro","la-sombra-desconocida",
            "jugando-las-escondidas","el-monte-de-las-ardenas","el-dios-maldito","las-diez-horas","la-madre-descuidada",
            "la-casa-duplex", "devuelvenos-el-color","no-lo-cuentes","misu-no-potaru","ticdan","kate-kill","black-demon",
            "presencia-de-madrugada","ojos-rojos","el-capitulo-perdido-de-hora-de-aventura","rasgunos-bajo-cama",
            "el-dibujo-que-vino-del-infierno","two-heads","no-esta-en-mi-cabeza-epilogo","solo-un-sueno",
            "alguien-te-observa","ese-refrigerador-estaba-lleno-de-gusanos","la-espantosa-historia-del-rey-devandra-gandagee",
            "chicas-no-humanas"
        ]
        self.tz = timezone("US/Central")
        self.icon_footer = "https://cdn.icon-icons.com/icons2/147/PNG/256/pumpkin_evil_halloween_21550.png"
        self.base_url = "https://es.creepypasta.xyz/{}/"
        self.final_date = datetime.strptime('31/10/2021', "%d/%m/%Y").date()

    ################################################################### UTIL METHODS #############################################################  

    async def check_if_valid(context):
        """
        Util method used as decorator with the @commands.check so it only enables the use of the 
        HalloweenCog commands if:
            - The command was issued in the creepy-pastas text channel.
        Params:
            * context: Represents the context in which a command is being invoked under.
        Returns:
            * If the command is valid
        """
        accepted_channel = "creepy-privado" #"creepy-pastas"
        if context.message.channel.name != accepted_channel:
            await context.send(f"Solo se puede usar esta funcionalidad de Halloween en el canal de '{accepted_channel}'.")
            return False
        
        file = open("halloween/stories_telled.txt", "r")
        last_day = file.read()
        if last_day != "":
            last_day = int(last_day)
            if last_day >= int(datetime.now(timezone("US/Central")).strftime('%-d')):
                await context.send("Esperen a mañana por otra historia 😈")
                return False
        file.close() 
 
        return True


    def add_embed_in_queue(self, story_title, story_info):
        self.embeds_queue.append(discord.Embed(
            title=story_title,
            color=discord.Color.orange())
            .add_field(name=datetime.now(self.tz).strftime("Octubre %-d, %Y"), value=story_info, inline=False)
        )

    def fetch_story(self, story_url):
        story = {}
        creepy_story = ""
        hdr = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'none',
            'Accept-Language': 'en-US,en;q=0.8',
            'Connection': 'keep-alive'
        }
        url = self.base_url.format(story_url)
        request = Request(url, headers=hdr)
        html = urlopen(request).read()

        soup = BeautifulSoup(html,'html.parser')
        p_all = soup.find_all("p")
        h1_all = soup.find_all("h1")

        story["title"] = h1_all[0].text

        for p in p_all:
            if p.text != "Historias Espeluznantes y Miedo":
                creepy_story += p.text
                creepy_story += "\n"
        story["body"] = creepy_story
        return story

    async def arm_story(self, story_info, context):
        current = 0 # Current embed being displayed
        # queue_display_msg = ""  # Message added to field of embed object.
        self.embeds_queue = [] # We reset the embed queue if multiple calls of queue command are done.
        # characters_added = 0
        # embed_message = ""

        title = story_info["title"]
        story = story_info["body"]
        max_characters_per_embed = 1024
        story_split_for_embeds = [story[i:i+max_characters_per_embed] for i in range(0, len(story), max_characters_per_embed)]
        for text in story_split_for_embeds:
            self.add_embed_in_queue(title, text)


        # while characters_added < len(story_info["body"]):
        #     embed_message += story[characters_added]
    
        #     if len(embed_message) < max_characters_per_embed:
        #         queue_display_msg += story[characters_added]
        #         characters_added += 1

        #         if characters_added == len(story_info["body"]):
        #             self.add_embed_in_queue(title, queue_display_msg)
        #     else:  
        #         print(queue_display_msg[len(queue_display_msg)-1])
        #         if queue_display_msg[len(queue_display_msg)-1] == " ":
        #             self.add_embed_in_queue(title, queue_display_msg)
        #             queue_display_msg = ""
        #         else:
        #             i = len(queue_display_msg)
        #             we_are_not_cutting_words = False
        #             while we_are_not_cutting_words == False:
        #                 #We need to not cut words
        #                 if queue_display_msg[i] != " ":
        #                     queue_display_msg[i].pop()
        #                     i -= 1
        #                 else:
        #                     we_are_not_cutting_words = True
        #                     characters_added -= i
        #                     self.add_embed_in_queue(title, queue_display_msg)



        if len(self.embeds_queue) == 1:
            embeded_queue_item = self.embeds_queue[current]
            embeded_queue_item.set_footer(text=f"Página 1/1", icon_url=self.icon_footer)
            msg = await context.send(embed=embeded_queue_item)
            
        elif len(self.embeds_queue) > 1:
            buttons = [u"\u23EA", u"\u2B05", u"\u27A1", u"\u23E9"] # Skip to start, left, right, skip to end buttons.
            # We only need the pagination functionality if there are multiple embed queue pages.

            embeded_queue_item = self.embeds_queue[current]
            embeded_queue_item.set_footer(text=f"Página {current+1}/{len(self.embeds_queue)}", icon_url=self.icon_footer)

            msg = await context.send(embed=self.embeds_queue[current])
            for button in buttons:
                await msg.add_reaction(button)

            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", check=lambda reaction, user: user == context.author and reaction.emoji in buttons, timeout=86400.0)

                except asyncio.TimeoutError:
                    await msg.delete()
                    return print("QUEUE EMBED NATURAL TIMEOUT")

                else:
                    previous_page = current
                    if reaction.emoji == u"\u23EA": # Skip to Start
                        current = 0
                        
                    elif reaction.emoji == u"\u2B05": # Previous queue page
                        if current > 0:
                            current -= 1
                            
                    elif reaction.emoji == u"\u27A1": # Next queue page
                        if current < len(self.embeds_queue)-1:
                            current += 1

                    elif reaction.emoji == u"\u23E9": # Last queue page
                        current = len(self.embeds_queue)-1

                    for button in buttons:
                        await msg.remove_reaction(button, context.author)

                    if current != previous_page:
                        embeded_queue_item = self.embeds_queue[current]
                    
                        embeded_queue_item.set_footer(text=f"Página {current+1}/{len(self.embeds_queue)}", icon_url=self.icon_footer)
                        await msg.edit(embed=embeded_queue_item)


    ################################################################### COMMANDS METHODS #########################################################

    @commands.command(aliases=CREEPY_PASTA_COMMAND_ALIASES)
    @commands.check(check_if_valid)
    async def creepy_pasta(self, context):
        start_date = datetime.strptime(datetime.now(self.tz).strftime("%d/%m/%Y"), "%d/%m/%Y").date()
        current_day = datetime.now(self.tz).strftime('%-d')
        if start_date < self.final_date:
            remainding_days = str(31-int(current_day))
            await context.send(f"Boo! Feliz {current_day} de Octubre! Faltan {remainding_days} días para Halloween! 🎃")

            story_info = self.fetch_story(self.list_of_creepy_pastas[int(current_day)-1])
            file = open("halloween/stories_telled.txt", "w")
            file.write(current_day)
            file.close()
            await self.arm_story(story_info, context)

        elif start_date == self.final_date:
            await context.send("Muahahaha bienvenidos a Halloween, aquí está su ultima historia... 🎃")
            story_info = self.fetch_story(self.list_of_creepy_pastas[int(current_day)-1])
            file = open("halloween/stories_telled.txt", "w")
            file.write(current_day)
            file.close()
            await self.arm_story(story_info, context)



