#!/usr/bin/env python

import json
import logging
import re

import cloudscraper
import discord
import yaml


logger = logging.getLogger("relayer")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="relayer.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)


site_regexes = {
    "fur_affinity": r"(furaffinity\.net/view/(\d+))",
    "weasyl": r"(weasyl\.com/~\w+/submissions/(\d+))"
}


def read_config():
    with open('relayer.yml') as cfg:
        return yaml.full_load(cfg)


class SiteBase:
    def __init__(self):
        self.url = None
        self.headers = None
        self.author = True
        self.author_name = None
        self.author_icon = None
        self.image = None
        self.image_url = None


class FurAffinity(SiteBase):
    def __init__(self, site_id):
        super().__init__()
        self.url = f"https://bawk.space/fapi/submission/{site_id}"

    def gather_info(self, data):
        self.author_name = data["author"]
        self.author_icon = data["avatar"]
        self.image = data["title"]
        self.image_url = data["image_url"]


class Weasyl(SiteBase):
    def __init__(self, site_id):
        super().__init__()
        self.url = f"https://www.weasyl.com/api/submissions/{site_id}/view"
        self.headers = {'X-Weasyl-API-Key': relayer_config["weasyl_api_key"]}

    def gather_info(self, data):
        self.author_name = data["owner"]
        self.author_icon = data["owner_media"]["avatar"][0]["url"]
        self.image = data["title"]
        self.image_url = data["media"]["submission"][0]["links"]["cover"][0]["url"]


class RelayerClient(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)
        self.scraper = cloudscraper.create_scraper()

    @staticmethod
    def log_details(message, content):
        logger.info(
            f"{message.author.name}#{message.author.discriminator}@"
            f"{message.guild.name}:{message.channel.name}: {content}"
        )

    async def on_ready(self):
        logger.info(f"Logged in as {self.user}")

    async def on_message(self, message):
        # Bot should not reply to itself
        if message.author == client.user:
            return

        for name, regex in site_regexes.items():
            site_class = ''.join(w.capitalize() for w in name.split('_'))
            comp_regex = re.compile(regex)
            links = comp_regex.findall(message.content)
            logger.debug(links)

            for link, site_id in links:
                site = globals()[site_class](site_id)

                # If no response, just skip
                if not (resp := self.scraper.get(site.url, headers=site.headers)):
                    continue

                data = json.loads(resp.text)
                site.gather_info(data)
                self.log_details(message, site.image_url)

                embed = discord.Embed(title=site.image)
                embed.set_image(url=site.image_url)

                if site.author:
                    embed.set_author(
                        name=site.author_name,
                        icon_url=site.author_icon
                    )

                await message.channel.send(embed=embed)


relayer_config = read_config()
client = RelayerClient()
client.run(relayer_config["discord_token"])
