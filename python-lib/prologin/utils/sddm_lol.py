#!/opt/prologin/venv/bin/python

import aiohttp
import random
import asyncio
import math
import itertools
import datetime

async def fortunes(s):
    l = [" Un arbre seul ne fait pas une forêt. ", " Qui touche du rouge devient rouge, qui touche du noir devient noir. ", " Qui suit un devin apprend à le devenir. ", " Qui apporte un cadeau est toujours le bienvenu. ", " Personne ne connaît mieux le fils que son père. ", " L'oiseau choisit l'arbre sur lequel il veut se reposer, mais l'arbre ne peut choisir l'oiseau. ", " Le jeune homme qui n'a pas de barbe au menton ne peut disposer une affaire solidement. ", " La beauté et le talent conduisent à tout, et ne mènent à rien. ", " Le chemin le plus long est celui où l'on marche seul. ", " Il n'y a qu'une affaire dans la vie ; qui en a deux n'en a réellement aucune. ", " Chaque siècle le répète à l'autre : tous les faux biens produisent de vrais maux. ", " Plus on a de connaissances, moins on connaît de gens. ", " Le sage a beau voyager, il ne change pas de demeure. ", " Cultiver les sciences et ne pas aimer les hommes, c'est allumer un flambeau et fermer les yeux. ", " Les plaisirs étaient à bon marché avant que l'or fût cher. ", " L'eau ne reste point sur les montagnes, ni la vengeance sur un grand cœur. ", " Le monde est une mer, notre cœur en est le rivage. ", " Les talents sans vertu sont des esclaves sans maîtres. ", " Les plaisirs délicieux de l'innocence ne sont une chimère que pour les violents. ", " Les talents ont besoin de Mécènes, la vertu perdrait à en avoir. ", " Qui attend le superflu pour secourir les pauvres ne leur donnera jamais rien. ", " L'étude étend peu les connaissances, si elle n'ôte pas la sottise. ", " Qui brûle un tableau pour en avoir les cendres sacrifie sa conscience à son ambition. ", " Qui ne sait pas se vanter ignore l'art de parvenir. ", " Les livres parlent à l'esprit ; les amis au cœur ; le ciel à l'âme ; tout le reste aux oreilles. "]
    l = [_.strip() for _ in l]
    random.shuffle(l)
    l = itertools.cycle(l)

    i = 0

    while True:
        if i % 2 == 0:
            motd = "Bienvenue à la finale Prologin 2019 !"
        else:
            remain = datetime.datetime(2019, 6, 1, 23, 42) - datetime.datetime.now()
            remain = remain.total_seconds() // 3600
            motd = f"Aucune pression, il reste {remain:.0f} heures avant le dernier rendu…"
        i += 1

        motd = f"{motd}\n« {next(l)} »" 
        await s.send_json({'motd': motd})
        await asyncio.sleep(6)


async def scale_fun(s):
    i = 0
    while True:
        x = 2 + math.sin(i)
        await s.send_json({'eval': f'ui.scale = {x:.2f}'})
        i += .1
        await asyncio.sleep(.05)


async def final_timer(s):
    while True:
        remain = datetime.datetime(2019, 6, 1, 23, 42) - datetime.datetime.now()
        remain = remain.total_seconds()
        if remain <= 0:
            await s.send_json({'motd': "TERMINAYYYYYYY !!1!"})
            await asyncio.sleep(10)
            continue
        m = int(remain // 60)
        ss = int(remain % 60)
        motd = f"La finale est terminée dans\n\n{m:02d} minute{'s' if m > 1 else ''} et {ss:02d} seconde{'s' if ss > 1 else ''} !\n"
        await s.send_json({'motd': motd})
        await asyncio.sleep(1)


async def main():
    c = aiohttp.ClientSession()
    async with c:
        s = await c.ws_connect('ws://localhost:7766/admin')
        # await scale_fun(s)
        # await fortunes(s)
        await final_timer(s)
        



if __name__ == '__main__':
    asyncio.run(main())

