import os
import aiogram
from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv

from utils import calculate_calories_goal, calculate_water_goal
from clients import get_weather, get_food_info

load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')

bot = aiogram.Bot(token=API_TOKEN)
dp = aiogram.Dispatcher()

storage = {}

class Registration(StatesGroup):
    weight = State()
    height = State()
    age = State()
    active_minutes = State()
    town = State()
    calories_goal = State()
    water_consumed = State()
    calories_consumed = State()
    water_goal = State()

class Food(StatesGroup):
    food_calorias = State()
    food_quantity = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот для расчета калорий.\n"
        "Для начала работы заполни данные о себе с помощью команды /set_profile."
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Напиши мне /start, чтобы начать работу.\n"
        "Напиши мне /set_profile, чтобы зарегистрироваться или актуализировать данные.\n"
        "Напиши мне /help, чтобы получить помощь.\n"
        "Напиши мне /get_profile, чтобы получить информацию о себе."
        "Напиши мне /log_water <количество в мл>, чтобы зафиксировать количество воды, которое вы выпили."
        "Напиши мне /log_food <название продукта>, чтобы зафиксировать количество продукта, которое вы употребили."
    )

@dp.message(Command("set_profile"))
async def cmd_set_profile(message: types.Message, state: FSMContext):
    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(Registration.weight)

@dp.message(Registration.weight)
async def process_weight(message: types.Message, state: FSMContext):
    await state.update_data(weight=message.text)
    await message.answer("Введите ваш рост (в см):")
    await state.set_state(Registration.height)

@dp.message(Registration.height)
async def process_height(message: types.Message, state: FSMContext):
    await state.update_data(height=message.text)
    await message.answer("Введите ваш возраст:")
    await state.set_state(Registration.age)

@dp.message(Registration.age)
async def process_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("Сколько минут активности у вас в день?")
    await state.set_state(Registration.active_minutes)

@dp.message(Registration.active_minutes)
async def process_active_minutes(message: types.Message, state: FSMContext):
    await state.update_data(active_minutes=message.text)
    await message.answer("В каком городе вы находитесь?")
    await state.set_state(Registration.town)

@dp.message(Registration.town)
async def process_town(message: types.Message, state: FSMContext):
    await state.update_data(town=message.text)
    await message.answer("Введите вашу цель по калориям (или auto, чтобы рассчитать автоматически)")
    await state.set_state(Registration.calories_goal)

@dp.message(Registration.calories_goal)
async def process_calories_goal(message: types.Message, state: FSMContext):
    await state.update_data(calories_goal=message.text)

    data = await state.get_data()

    if message.text == "auto":
        await state.update_data(calories_goal=calculate_calories_goal(int(data['weight']), int(data['height']), int(data['age']), int(data['active_minutes'])))
    await state.update_data(water_goal=calculate_water_goal(int(data['weight']), int(data['active_minutes'])))
    await state.update_data(water_consumed=0)
    await state.update_data(calories_consumed=0)

    storage[message.from_user.id] = await state.get_data()
    await message.answer("Вы успешно зарегистрированы!")
    await state.clear()

@dp.message(Command("get_profile"))
async def cmd_get_profile(message: types.Message, state: FSMContext):
    data = storage.get(message.from_user.id)
    if not data:
        await message.answer("Профиль не найден. Пожалуйста, заполните данные с помощью /set_profile.")
        return
    temp = await get_weather(data.get('town', 'Город не указан'))
    temp = temp['main'].get('temp', 'неизвестно')
    text = (
        f"Ваш вес: {data.get('weight', 'не указано')} кг\n"
        f"Ваш рост: {data.get('height', 'не указано')} см\n"
        f"Ваш возраст: {data.get('age', 'не указано')}\n"
        f"Ваше количество активных минут в день: {data.get('active_minutes', 'не указано')}\n"
        f"Ваш город: {data.get('town', 'не указано')}, температура в вашем городе: {temp}°C\n"
        f"Ваша цель по калориям: {data.get('calories_consumed', 'не указано')}/{data.get('calories_goal', 'не указано')}\n"
        f"Ваша цель по воде: {data.get('water_consumed', 'не указано')}/{data.get('water_goal', 'не указано')}\n"
    )
    await message.answer(text)

@dp.message(Command("log_water"))
async def cmd_log_water(message: types.Message):
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Используйте формат: log_water <количество в мл>")
        return
    quantity = int(parts[1])

    storage[message.from_user.id]['water_consumed'] += quantity
    water_consumed = storage[message.from_user.id]['water_consumed']
    water_goal = storage[message.from_user.id]['water_goal']
    if water_consumed > water_goal:
        await message.answer(f"{quantity} мл воды зафиксировано - Вы выпили больше на {water_consumed - water_goal} мл, чем нужно. Пожалуйста, выпивайте меньше воды.")
        return
    elif water_consumed < water_goal:
        await message.answer(f"{quantity} мл воды зафиксировано - Осталось выпить {water_goal - water_consumed} мл воды, чтобы достичь цели.")
        return
    await message.answer(f"{quantity} мл воды зафиксировано - Вы достигли цели по воде!")

@dp.message(Command("log_food"))
async def cmd_log_food(message: types.Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("Используйте формат: log_food <название продукта>")
        return
    food_info = await get_food_info(parts[1])
    await state.update_data(food_calories=food_info['calories'])
    await message.answer(food_info['info'] + "\nВведите количество продукта в граммах:")
    await state.set_state(Food.food_quantity)

@dp.message(Food.food_quantity)
async def process_food_quantity(message: types.Message, state: FSMContext):
    food_quantity = int(message.text)
    food_info = await state.get_data()
    food_calories = food_info['food_calories']

    new_calories_consumed = food_calories * food_quantity / 100
    storage[message.from_user.id]['calories_consumed'] += new_calories_consumed

    await state.clear()
    calories_consumed = storage[message.from_user.id]['calories_consumed']
    calories_goal = storage[message.from_user.id]['calories_goal']
    if calories_consumed > calories_goal:
        await message.answer(f"Потребление зафиксировано - Вы употребили больше калорий на {calories_consumed - calories_goal} ккал. Пожалуйста, употребите меньше калорий.")
        return
    elif calories_consumed < calories_goal:
        await message.answer(f"Потребление зафиксировано - Осталось употребить {calories_goal - calories_consumed} ккал, чтобы достичь цели.")
        return
    await message.answer(f"Потребление зафиксировано - Вы достигли цели по калориям!")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
