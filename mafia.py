import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv
from random import sample, shuffle, randint
from concurrent.futures import ThreadPoolExecutor
from model_handler import ModelHandler
from utils import try_send_html
from types import SimpleNamespace

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS"))
SHORT_NEW_TOKENS = int(os.getenv("SHORT_NEW_TOKENS"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
executor = ThreadPoolExecutor(max_workers=1)
model_handler = ModelHandler(MAX_NEW_TOKENS, SHORT_NEW_TOKENS)

NAMES = [
    "Иван", "Петр", "Алексей", "Дмитрий", "Сергей", "Михаил",
    "Андрей", "Владимир", "Артем", "Николай", "Егор", "Игорь",
    "Федор", "Глеб", "Максим", "Роман", "Григорий", "Лев"
]

PLAYER_PROMPTS = [
    "Ты обычный житель деревни, веди себя искренне и постарайся убедить других, что ты не мафия. Выскажи свою речь на голосовании.",
    "Ты мафия, старайся убедить всех, что ты обычный житель. Выскажи свою речь на голосовании, не выдавая себя и других мафий."
]

def get_next_button():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="▶️ Далее")]], resize_keyboard=True)

def get_vote_button():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🗳️ Голосование")]], resize_keyboard=True)

def remove_keyboard():
    return ReplyKeyboardRemove()

game = {}

async def send_typing(chat_id):
    try:
        while True:
            await bot.send_chat_action(chat_id, "typing")
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        pass

@dp.message(Command("start"))
async def start(message):
    game.clear()
    await try_send_html(
        message,
        "Добро пожаловать в игру 'Мафия'. Введите количество игроков (от 4 до 12):",
        reply_markup=remove_keyboard()
    )
    game['state'] = 'wait_players'

@dp.message()
async def handler(message):
    user_text = message.text.strip()
    if game.get('state') == 'wait_players':
        try:
            n_players = int(user_text)
            if 4 <= n_players <= 12:
                game['n_players'] = n_players
                await try_send_html(message, "Сколько должно быть мафий (1 или 2)?")
                game['state'] = 'wait_mafia'
            else:
                await try_send_html(message, "Введите число от 4 до 12")
        except:
            await try_send_html(message, "Пожалуйста, введите целое число.")
        return

    if game.get('state') == 'wait_mafia':
        try:
            n_mafia = int(user_text)
            if n_mafia not in (1, 2) or n_mafia >= game['n_players']:
                await try_send_html(message, "Мафий должно быть 1 или 2, и меньше чем всех игроков.")
                return
            await setup_game(message, game['n_players'], n_mafia)
        except:
            await try_send_html(message, "Пожалуйста, напишите 1 или 2.")
        return

    if user_text.lower() == "▶️ далее" and game.get('state') == 'game_day':
        await next_player_phase(message)
        return

    if user_text.lower() == "🗳️ голосование" and game.get('state') == 'game_day':
        await voting_phase(message)
        return

    if user_text.lower() == "▶️ далее" and game.get('state') == 'game_night':
        await mafia_night_phase(message)
        return

async def setup_game(message, n_players, n_mafia):
    names = sample(NAMES, n_players)
    mafia_indices = sample(range(n_players), n_mafia)
    roles = ["мафия" if i in mafia_indices else "мирный" for i in range(n_players)]
    prompts = []
    for i in range(n_players):
        if i in mafia_indices:
            mafia_names = [names[j] for j in mafia_indices if j != i]
            if mafia_names:
                info = f"Ты мафия. Другие мафии: {', '.join(mafia_names)}."
            else:
                info = "Ты мафия. Ты один в команде мафии."
            prompts.append(info + " " + PLAYER_PROMPTS[1])
        else:
            prompts.append("Ты мирный житель. " + PLAYER_PROMPTS[0])

    game.update({
        'names': names,
        'roles': roles,
        'prompts': prompts,
        'step': 0,
        'state': 'game_day',
        'alive': [True] * n_players,
        'last_killed': None
    })

    awaiting = []
    for i, (name, role, prompt) in enumerate(zip(names, roles, prompts)):
        txt = f"Игрок {name}: {prompt}"
        awaiting.append(txt)
    await try_send_html(
        message,
        "Роли розданы. Нажмите '▶️ Далее', чтобы начать день. Далее каждый игрок будет произносить свою речь.",
        reply_markup=get_next_button()
    )
    await try_send_html(
        SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
        "Запущена игра в мафию.\n" + "\n\n".join(awaiting)
    )

async def next_player_phase(message):
    names = game['names']
    prompts = game['prompts']
    roles = game['roles']
    step = game['step']
    alive = game['alive']
    total = len(names)

    while step < total and not alive[step]:
        game['step'] += 1
        step = game['step']

    if step >= total:
        await try_send_html(
            message,
            "Все игроки выступили. Напишите '🗳️ Голосование' чтобы перейти к голосованию.",
            reply_markup=get_vote_button()
        )
        return

    name = names[step]
    prompt = prompts[step]
    role = roles[step]
    aspect_prompt = f"Ты игрок {name}, твоя роль: {role}. Вот твоя информация: {prompt}\nСкажи свою речь на голосовании."
    typing_task = asyncio.create_task(send_typing(message.chat.id))
    loop = asyncio.get_event_loop()
    speech = await loop.run_in_executor(
        executor,
        model_handler.generate_short_responce,
        aspect_prompt
    )
    typing_task.cancel()

    await try_send_html(
        message,
        f"🗣 <b>{name}:</b>\n{speech}",
        reply_markup=get_next_button()
    )
    admin_report = (
        f"💡 <b>Промпт, переданный в модель:</b>\n"
        f"{aspect_prompt}\n\n"
        f"🗣 <b>{name}:</b>\n"
        f"{speech}"
    )
    await try_send_html(
        SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
        admin_report
    )
    game['step'] += 1

async def voting_phase(message):
    names = game['names']
    alive = game['alive']
    surviving_indices = [i for i, a in enumerate(alive) if a]
    shuffle(surviving_indices)
    votes = {}
    n_alive = len(surviving_indices)
    for i in surviving_indices:
        candidates = [j for j in surviving_indices if j != i]
        target = candidates[randint(0, len(candidates) - 1)]
        votes.setdefault(target, []).append(i)
    results = []
    for voted, voters in votes.items():
        voter_names = ", ".join([names[i] for i in voters])
        results.append(f"За {names[voted]} проголосовали: {voter_names}")
    most_voted = max(votes.items(), key=lambda x: len(x[1]))[0]
    game['alive'][most_voted] = False
    game['last_killed'] = most_voted
    game['step'] = 0
    await try_send_html(
        message,
        "<b>🗳️ Голоса:</b>\n" + "\n".join(results),
        reply_markup=get_next_button()
    )
    await try_send_html(
        message,
        f"<b>{names[most_voted]} выбыл из игры!</b>",
        reply_markup=get_next_button()
    )
    await try_send_html(
        SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
        "<b>🗳️ Голоса:</b>\n" + "\n".join(results) + f"\n\n<b>{names[most_voted]} выбыл из игры!</b>"
    )

    mafia_alive = sum([game['roles'][i] == 'мафия' and game['alive'][i] for i in range(len(names))])
    city_alive = sum([game['roles'][i] == 'мирный' and game['alive'][i] for i in range(len(names))])
    if mafia_alive == 0:
        await try_send_html(
            message,
            "Мирные победили! 🎉 Игра окончена.",
            reply_markup=remove_keyboard()
        )
        await try_send_html(
            SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
            "Мирные победили! 🎉 Игра окончена."
        )
        game['state'] = 'over'
        return
    elif city_alive <= mafia_alive:
        await try_send_html(
            message,
            "Мафия победила! 😈 Игра окончена.",
            reply_markup=remove_keyboard()
        )
        await try_send_html(
            SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
            "Мафия победила! 😈 Игра окончена."
        )
        game['state'] = 'over'
        return
    else:
        await try_send_html(
            message,
            "🌙 Началась ночь. Теперь мафия будет выбирать жертву. Нажмите '▶️ Далее'.",
            reply_markup=get_next_button()
        )
        await try_send_html(
            SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
            "🌙 Началась ночь. Теперь мафия будет выбирать жертву. Нажмите '▶️ Далее'."
        )
        game['state'] = 'game_night'
        game['step'] = 0

async def mafia_night_phase(message):
    names = game['names']
    roles = game['roles']
    alive = game['alive']
    mafia_indices = [i for i, role in enumerate(roles) if role == "мафия" and alive[i]]
    peaceful_indices = [i for i, role in enumerate(roles) if role == "мирный" and alive[i]]
    all_alive_indices = [i for i, status in enumerate(alive) if status]

    victims_votes = []
    for mafia_id in mafia_indices:
        visible_names = [names[j] for j in all_alive_indices if j != mafia_id]
        aspect_prompt = (
            f"Ты {names[mafia_id]}, мафия.\n"
            f"Из живых игроков: {', '.join(visible_names)}.\n"
            "Согласуйтесь мысленно с другими мафиями и выберите только ОДНОГО игрока, которого мафии решают убить ночью. "
            "Напиши только ИМЯ того, кого вы решили убить."
        )
        typing_task = asyncio.create_task(send_typing(message.chat.id))
        loop = asyncio.get_event_loop()
        llm_answer = await loop.run_in_executor(
            executor,
            model_handler.generate_short_responce,
            aspect_prompt
        )
        typing_task.cancel()
        victim_name = None
        for n in visible_names:
            if n in llm_answer:
                victim_name = n
                break
        if not victim_name:
            victim_name = visible_names[randint(0, len(visible_names)-1)]
        victims_votes.append(victim_name)
        admin_report = (
            f"💡 <b>Промпт, переданный в модель:</b>\n"
            f"{aspect_prompt}\n\n"
            f"🦹‍♂️ <b>{names[mafia_id]} (мафия) выбрал:</b> {llm_answer}"
        )
        await try_send_html(
            SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
            admin_report
        )
    final_victim = max(set(victims_votes), key = victims_votes.count)
    victim_index = names.index(final_victim)
    game['alive'][victim_index] = False
    game['last_killed'] = victim_index
    mafia_alive = sum([game['roles'][i] == 'мафия' and game['alive'][i] for i in range(len(names))])
    city_alive = sum([game['roles'][i] == 'мирный' and game['alive'][i] for i in range(len(names))])
    await try_send_html(
        message,
        f"🌑 Ночью был убит игрок {final_victim}!",
        reply_markup=get_next_button()
    )
    await try_send_html(
        SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
        f"🌑 Ночью был убит игрок {final_victim}!"
    )
    if mafia_alive == 0:
        await try_send_html(
            message,
            "Мирные победили! 🎉 Игра окончена.",
            reply_markup=remove_keyboard()
        )
        await try_send_html(
            SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
            "Мирные победили! 🎉 Игра окончена."
        )
        game['state'] = 'over'
        return
    elif city_alive <= mafia_alive:
        await try_send_html(
            message,
            "Мафия победила! 😈 Игра окончена.",
            reply_markup=remove_keyboard()
        )
        await try_send_html(
            SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
            "Мафия победила! 😈 Игра окончена."
        )
        game['state'] = 'over'
        return
    else:
        game['state'] = 'game_day'
        game['step'] = 0
        await try_send_html(
            message,
            "☀️ Наступает утро. Игроки снова могут выступить. Нажмите '▶️ Далее'.",
            reply_markup=get_next_button()
        )
        await try_send_html(
            SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
            "☀️ Наступает утро. Игроки снова могут выступить. Нажмите '▶️ Далее'."
        )

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
