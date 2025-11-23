import asyncio
import logging
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time
import re
import os

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Импорты для Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import chromedriver_autoinstaller

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
class UserStates(StatesGroup):
    COUNTRY = State()
    DEPARTURE_CITY = State()
    RESORTS = State()
    MEALS = State()
    ADULTS = State()
    CHILDREN = State()
    INFANTS = State()
    NIGHTS = State()
    HOTEL_CATEGORY = State()
    DATES = State()

# Структура для хранения параметров пользователя
@dataclass
class UserParams:
    countries: List[str] = None
    departure_city: str = None
    night_range_from: str = None
    night_range_to: str = None
    resorts: List[str] = None
    meals: List[str] = None
    tourist_group_adults: str = None
    tourist_group_kids: str = None
    tourist_group_infants: str = None
    hotel_categories: List[str] = None
    check_in_date_range_from: str = None
    check_in_date_range_to: str = None

# Словари для сопоставления названий с ID
COUNTRIES = {
    "абхазия": "1", "австрия": "3", "андорра": "4", "армения": "6",
    "бахрейн": "10", "беларусь": "11", "бельгия": "12", "болгария": "13",
    "бразилия": "16", "великобритания": "19", "венгрия": "20", "вьетнам": "22",
    "германия": "24", "греция": "26", "дания": "27", "доминикана": "28",
    "египет": "29", "израиль": "32", "индия": "33", "индонезия": "34",
    "иордания": "35", "ирландия": "36", "испания": "38", "италия": "39",
    "камбоджа": "41", "кипр": "43", "китай": "44", "коста-рика": "47",
    "куба": "48", "кыргызстан": "49", "латвия": "50", "литва": "52",
    "маврикий": "53", "малайзия": "55", "мальдивы": "56", "мальта": "57",
    "марокко": "59", "мексика": "60", "нидерланды": "65", "норвегия": "67",
    "оаэ": "68", "оман": "69", "польша": "74", "португалия": "75",
    "россия": "76", "румыния": "77", "сейшелы": "78", "сербия": "81",
    "сингапур": "82", "словакия": "83", "словения": "84", "сша": "85",
    "таиланд": "87", "танзания": "88", "тунис": "91", "турция": "92",
    "узбекистан": "94", "филиппины": "97", "финляндия": "98", "франция": "99",
    "хорватия": "101", "черногория": "104", "чехия": "105", "швейцария": "107",
    "швеция": "108", "шри-ланка": "110", "эстония": "113", "юар": "115",
    "южная корея": "116", "ямайка": "117", "япония": "118", "азербайджан": "119",
    "албания": "120", "грузия": "129", "катар": "135", "казахстан": "156",
    "гамбия": "157", "саудовская аравия": "260", "туркменистан": "293",
    "таджикистан": "294", "сан-марино": "224"
}

DEPARTURE_CITIES = {
    "абакан": "90", "архангельск": "8", "астрахань": "10", "барнаул": "12",
    "белгород": "13", "благовещенск": "15", "брянск": "18", "владивосток": "19",
    "владикавказ": "20", "волгоград": "21", "воронеж": "22", "екатеринбург": "25",
    "иркутск": "28", "казань": "29", "калининград": "30", "кемерово": "32",
    "краснодар": "36", "красноярск": "37", "курган": "38", "курск": "39",
    "липецк": "91", "магадан": "42", "магнитогорск": "43", "махачкала": "92",
    "минеральные воды": "44", "москва": "2", "мурманск": "46", "нальчик": "47",
    "нижневартовск": "48", "нижний новгород": "50", "новокузнецк": "51",
    "новороссийск": "52", "новосибирск": "53", "омск": "56", "оренбург": "57",
    "пенза": "60", "пермь": "61", "петропавловск-камчатский": "62",
    "ростов-на-дону": "63", "самара": "64", "санкт-петербург": "1", "саратов": "65",
    "симферополь": "66", "сочи": "67", "ставрополь": "93", "сургут": "68",
    "сыктывкар": "70", "тольятти": "71", "томск": "72", "тюмень": "74",
    "улан-удэ": "75", "ульяновск": "76", "уфа": "79", "хабаровск": "80",
    "ханты-мансийск": "81", "чебоксары": "83", "челябинск": "84", "чита": "85",
    "южно-сахалинск": "87", "якутск": "88"
}

RESORTS_LIST = {
    "гагра": "1", "сухум": "6", "пицунда": "5", "гудаута": "2", "новый афон": "3",
    "очамчыра": "4", "цандрипш": "3899", "венa": "33", "зальцбург": "36",
    "майрхофен": "50", "зёльден": "40", "ишгль": "43", "каринтия": "44",
    "капрун": "2806", "целль-ам-зе": "2821", "андорра ла велла": "60",
    "эскальдес": "2832", "пас де ла каса": "2829", "ла массана": "3030",
    "гранд валира": "62", "ереван": "103", "джульфа": "101", "цакхадзор": "105",
    "раздан": "102", "албена": "175", "банско": "181", "боровец": "185",
    "золотые пески": "200", "несебр": "215", "солнечный берег": "241",
    "св. константин и елена": "235", "святой влас": "236", "поморие": "223",
    "елините": "199", "фантхьет": "428", "муйне": "428", "ньячанг": "417",
    "фукуок": "429", "дананг": "405", "ханой": "432", "хошимин": "434",
    "сапа": "424", "хюэ": "435", "халонг": "431", "крит": "3163", "афины": "468",
    "салоники": "529", "корфу": "497", "родос": "509", "закинф": "489",
    "кос": "498", "санторини": "530", "халкидики": "3164", "пунта кана": "571",
    "ла романа": "566", "пуэрто плата": "572", "самана": "573", "баваро": "571",
    "кабарете": "563", "шарм-эль-шейх": "598", "хургада": "597", "марса алам": "592",
    "таба": "596", "дахаб": "586", "эль гуна": "599", "сома бей": "595",
    "макади": "591", "сафага": "594", "нувейба": "593", "барселона": "747",
    "мадрид": "786", "коста брава": "770", "коста дель соль": "773",
    "коста бланка": "769", "коста дорада": "774", "майорка": "787", "тенерифе": "763",
    "ибица": "795", "льорет де мар": "782", "рим": "880", "милан": "863",
    "венеция": "842", "флоренция": "892", "неаполь": "866", "римини": "881",
    "сицилия": "868", "сардиния": "885", "капри": "851", "исачия": "867",
    "айя-напа": "919", "протарас": "926", "ларнака": "920", "лимассол": "922",
    "пафос": "2869", "полис": "925", "варадеро": "1001", "гавана": "1004",
    "кайо коко": "1011", "кайо ларго": "1012", "кайо гильермо": "1010",
    "кайо санта мария": "1014", "ольгин": "1016", "сантьяго де куба": "1020",
    "мале": "1142", "северный мале атолл": "1148", "южный мале атолл": "1152",
    "ари атолл": "1136", "баа атолл": "1137", "раа атолл": "1146", "даалу атолл": "1139",
    "лавиани атолл": "1141", "дубай": "1379", "абу даби": "1377", "шарджа": "1385",
    "аджман": "1378", "рас-эль-хайма": "1381", "фуджейра": "1384", "ум аль кувейн": "1383",
    "сочи": "3097", "адлер": "1545", "лазаревское": "1704", "хоста": "3124",
    "дагомыс": "1620", "алушта": "2202", "ялта": "2280", "симферополь": "2255",
    "евпатория": "2253", "феодосия": "2265", "судак": "2258", "керчь": "2224",
    "севастополь": "2253", "анапа": "3974", "геленджик": "1610", "туапсе": "1868",
    "паттайя": "2100", "пхукет": "4191", "самуи": "2098", "пхи-пхи": "2112",
    "краби": "2103", "чанг": "2099", "бангкок": "2084", "ча-ам": "2126",
    "хуа хин": "2125", "као лак": "2086", "джерба": "2142", "сусс": "2150",
    "хаммамет": "2155", "монастир": "2147", "махдия": "2146", "анталья": "2161",
    "кемер": "3839", "белек": "2162", "сиде": "3828", "алания": "2159",
    "мармарис": "2178", "бодрум": "2163", "кушадасы": "2177", "фетхие": "2190",
    "даламан": "2167", "измир": "2169", "стамбул": "2185", "каппадокия": "2172",
    "памуккале": "2182", "будва": "3011", "котор": "3020", "тиват": "2514",
    "петровац": "3015", "свети стефан": "3018", "бечичи": "3010", "герцег нови": "3050",
    "прага": "2535", "карловы вары": "2521", "марианские лазне": "2528",
    "коломбо": "2673", "бентота": "2652", "негомбо": "2681", "хиккадува": "2698",
    "мирисса": "2680", "унаватуна": "2695", "галле": "2658", "тринкомали": "2694",
    "нувара элия": "2683", "канди": "2668", "батуми": "2968", "тбилиси": "2976",
    "кутаиси": "2973", "боржоми": "3234", "бакуриани": "2967", "гудauri": "2970",
    "кобулети": "2972", "алматы": "3244", "астана": "3245", "актау": "3242",
    "атырау": "3246", "ташкент": "2199", "самарканд": "2198", "бухара": "2197",
    "хива": "2200"
}

MEALS_MAPPING = {
    "RO": "1", "BB": "2", "HB": "3", "FB": "4", "AI": "5", "UAI": "6", "AI(NOALC)": "7"
}

class WebDriverManager:
    """Менеджер для работы с Selenium WebDriver"""
    
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Настройка Chrome WebDriver"""
        try:
            # Автоматическая установка chromedriver
            chromedriver_autoinstaller.install()
            
            # Настройка опций Chrome
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")  # Новый headless режим
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(30)
            logger.info("Chrome WebDriver успешно запущен")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске WebDriver: {e}")
            raise
    
    def get_page_content(self, url: str) -> str:
        """Получение содержимого страницы"""
        try:
            logger.info(f"Перехожу по URL: {url}")
            self.driver.get(url)
            
            # Ждем загрузки страницы
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Получаем весь текст страницы
            page_content = self.driver.page_source
            
            logger.info(f"Успешно получено содержимое страницы, длина: {len(page_content)} символов")
            return page_content
            
        except TimeoutException:
            error_msg = "Таймаут при загрузке страницы"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Ошибка при получении содержимого страницы: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def close(self):
        """Закрытие драйвера"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver закрыт")

class TravelataBot:
    def __init__(self, token: str):
        self.token = token
        self.bot = Bot(token=token)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.router = Router()
        self.user_params = {}
        self.monitoring_users = {}
        self.web_driver_manager = WebDriverManager()
        self.last_request_time = {}
        self.request_delay = 2  # секунды между запросами
        
        # Регистрация обработчиков
        self.setup_handlers()
        self.dp.include_router(self.router)
    
    async def rate_limit(self, user_id: int):
        """Ограничение частоты запросов"""
        current_time = time.time()
        if user_id in self.last_request_time:
            time_passed = current_time - self.last_request_time[user_id]
            if time_passed < self.request_delay:
                await asyncio.sleep(self.request_delay - time_passed)
        self.last_request_time[user_id] = current_time
    
    def escape_markdown(self, text: str) -> str:
        """Экранирование специальных символов Markdown"""
        escape_chars = r'\_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    
    def _create_search_summary(self, params: UserParams) -> str:
        """Создание сводки параметров поиска"""
        summary = ""
        
        if params.countries:
            country_names = [name for name, id in COUNTRIES.items() if id in params.countries]
            summary += f"• 🌍 Страна: {', '.join(country_names)}\n"
        
        if params.departure_city:
            city_name = [name for name, id in DEPARTURE_CITIES.items() if id == params.departure_city]
            summary += f"• 🛫 Вылет из: {city_name[0] if city_name else params.departure_city}\n"
        
        if params.resorts:
            resort_names = [name for name, id in RESORTS_LIST.items() if id in params.resorts]
            summary += f"• 🏖 Курорты: {', '.join(resort_names) if resort_names else 'Любые'}\n"
        
        if params.tourist_group_adults:
            summary += f"• 👨‍👩‍👧‍👦 Взрослые: {params.tourist_group_adults}\n"
        
        if params.tourist_group_kids and params.tourist_group_kids != "0":
            summary += f"• 👶 Дети: {params.tourist_group_kids}\n"
        
        if params.tourist_group_infants and params.tourist_group_infants != "0":
            summary += f"• 🍼 Младенцы: {params.tourist_group_infants}\n"
        
        if params.night_range_from and params.night_range_to:
            summary += f"• 🗓 Ночи: {params.night_range_from}-{params.night_range_to}\n"
        
        if params.hotel_categories:
            summary += f"• ⭐ Категории отелей: {', '.join(params.hotel_categories)}*\n"
        
        if params.check_in_date_range_from and params.check_in_date_range_to:
            summary += f"• 📅 Даты: {params.check_in_date_range_from} - {params.check_in_date_range_to}\n"
        
        return summary
    
    def safe_send_message(self, chat_id: int, text: str, **kwargs):
        """Безопасная отправка сообщения с обработкой ошибок форматирования"""
        try:
            # Пытаемся отправить с Markdown
            return self.bot.send_message(chat_id, text, parse_mode="Markdown", **kwargs)
        except Exception as e:
            if "can't parse entities" in str(e):
                # Если ошибка форматирования, отправляем без разметки
                logger.warning(f"Markdown ошибка, отправляю без форматирования: {e}")
                # Убираем Markdown символы
                clean_text = re.sub(r'[*_`\[\]()~>#+\-=|{}.!]', '', text)
                return self.bot.send_message(chat_id, clean_text, **kwargs)
            else:
                raise
    
    def parse_json_to_hotels_list(self, json_text: str) -> Tuple[str, bool]:
        """Преобразование JSON текста в список отелей"""
        try:
            # Пытаемся найти JSON в тексте страницы
            start_idx = json_text.find('{')
            end_idx = json_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                return "❌ Не удалось найти данные на странице. Попробуйте позже.", False
            
            json_str = json_text[start_idx:end_idx]
            data = json.loads(json_str)
            
            if not data.get('success') or 'data' not in data:
                return "❌ Ошибка получения данных от системы поиска", False
            
            tours = data['data']
            if not tours:
                return "📭 По вашему запросу туров не найдено.\n\nПопробуйте изменить параметры поиска:", True
            
            # Группировка по отелям (убираем дубликаты по hotelId)
            hotels = {}
            for tour in tours:
                hotel_id = tour['hotelId']
                hotel_name = tour['hotelName']
                
                if hotel_id not in hotels:
                    hotels[hotel_id] = {
                        'name': hotel_name,
                        'category': tour['hotelCategoryName'],
                        'rating': float(tour['hotelRating']),
                        'prices': [],
                        'min_nights': float('inf'),
                        'max_nights': 0,
                        'checkin_dates': set(),
                        'tour_urls': [],
                        'meal_types': set()
                    }
                
                # Добавляем данные, избегая полных дубликатов
                hotels[hotel_id]['prices'].append(tour['price'])
                hotels[hotel_id]['min_nights'] = min(hotels[hotel_id]['min_nights'], tour['nights'])
                hotels[hotel_id]['max_nights'] = max(hotels[hotel_id]['max_nights'], tour['nights'])
                hotels[hotel_id]['checkin_dates'].add(tour['checkinDate'])
                hotels[hotel_id]['meal_types'].add(tour['mealId'])
                
                # Сохраняем URL самого дешевого тура для этого отеля
                if not hotels[hotel_id]['tour_urls'] or tour['price'] == min(hotels[hotel_id]['prices']):
                    hotels[hotel_id]['tour_urls'].append(tour['tourPageUrl'])
            
            # Сортировка отелей по минимальной цене
            sorted_hotels = sorted(
                hotels.values(),
                key=lambda x: min(x['prices'])
            )
            
            # Формирование списка отелей БЕЗ Markdown форматирования
            message = "🎯 РЕЗУЛЬТАТЫ ПОИСКА\n"
            message += "══════════════════════════════\n"
            message += f"🏨 Найдено отелей: {len(hotels)}\n"
            message += f"📊 Всего туров: {len(tours)}\n"
            message += "══════════════════════════════\n\n"
            
            for i, hotel in enumerate(sorted_hotels[:15], 1):  # Показываем топ-15 отелей
                min_price = min(hotel['prices'])
                max_price = max(hotel['prices'])
                
                # Форматирование ночей
                nights_info = f"{hotel['min_nights']}"
                if hotel['min_nights'] != hotel['max_nights']:
                    nights_info = f"{hotel['min_nights']}-{hotel['max_nights']}"
                
                # Форматирование дат
                dates = sorted(hotel['checkin_dates'])[:3]  # Первые 3 даты
                dates_str = ", ".join(dates)
                if len(hotel['checkin_dates']) > 3:
                    dates_str += f" (+{len(hotel['checkin_dates']) - 3})"
                
                # Ссылка на отель (берем первый URL)
                hotel_link = hotel['tour_urls'][0] if hotel['tour_urls'] else "#"
                
                message += f"{i}. {hotel['name']}\n"
                message += f"   🏷 Категория: {hotel['category']}\n"
                message += f"   ⭐ Рейтинг: {hotel['rating']}\n"
                message += f"   💰 Цена: от {min_price:,} руб."
                if min_price != max_price:
                    message += f" до {max_price:,} руб."
                message += f"\n"
                message += f"   🗓 Ночи: {nights_info}\n"
                message += f"   📅 Даты заезда: {dates_str}\n"
                message += f"   🔗 Ссылка: {hotel_link}\n"
                
                # Разделитель между отелями
                if i < min(15, len(sorted_hotels)):
                    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            if len(sorted_hotels) > 15:
                message += f"\n... и еще {len(sorted_hotels) - 15} отелей"
            
            # Добавляем статистику
            total_hotels = len(hotels)
            avg_rating = sum(h['rating'] for h in hotels.values()) / total_hotels
            min_price_overall = min(min(h['prices']) for h in hotels.values())
            
            message += f"\n\n📈 СТАТИСТИКА ПОИСКА:\n"
            message += f"• Самый дешевый отель: {min_price_overall:,} руб.\n"
            message += f"• Средний рейтинг отелей: ⭐{avg_rating:.2f}\n"
            message += f"• Всего вариантов: {len(tours)} туров\n"
            
            return message, True
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {e}")
            return "❌ Ошибка: Неверный формат данных от сервера", False
        except Exception as e:
            logger.error(f"Ошибка при парсинге туров: {e}")
            return f"❌ Ошибка при обработке данных: {str(e)}", False

    async def start(self, message: Message, state: FSMContext) -> None:
        """Обработчик команды /start"""
        await self.rate_limit(message.from_user.id)
        user_id = message.from_user.id
        self.user_params[user_id] = UserParams()
        await state.clear()
        
        keyboard = [
            [InlineKeyboardButton(text="🎯 Настроить параметры", callback_data="set_params")],
            [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await message.answer(
            "✨ Добро пожаловать в Travelata Parser!\n\n"
            "Я помогу найти самые выгодные туры по вашим параметрам 🤑\n"
            "Начнем с настройки параметров поиска:",
            reply_markup=reply_markup
        )

    async def help_command(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Показать справку"""
        await callback.answer()
        
        help_text = (
            "📖 Помощь по использованию бота:\n\n"
            "1. Настройка параметров - поэтапная настройка всех критериев поиска\n"
            "2. Поиск туров - автоматический поиск по вашим параметрам\n"
            "3. Мониторинг - отслеживание изменений цен и новых предложений\n\n"
            "Доступные команды:\n"
            "/start - начать работу\n"
            "/help - показать эту справку\n\n"
            "💡 Совет: Для точного поиска указывайте конкретные параметры"
        )
        
        keyboard = [
            [InlineKeyboardButton(text="🎯 Начать настройку", callback_data="set_params")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(help_text, reply_markup=reply_markup)

    async def set_params(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Начало установки параметров"""
        await callback.answer()
        await self.rate_limit(callback.from_user.id)
        
        keyboard = [
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "🌍 Шаг 1/10: Выбор страны\n\n"
            "Напишите название страны в именительном падеже:\n"
            "Пример: Турция или Египет\n\n"
            "💡 Совет: Указывайте одну страну для точного поиска",
            reply_markup=reply_markup
        )
        await state.set_state(UserStates.COUNTRY)

    async def get_country(self, message: Message, state: FSMContext) -> None:
        """Получение страны от пользователя"""
        await self.rate_limit(message.from_user.id)
        user_id = message.from_user.id
        country_input = message.text.strip().lower()
        
        if country_input in COUNTRIES:
            country_id = COUNTRIES[country_input]
            self.user_params[user_id].countries = [country_id]
            
            keyboard = [
                [InlineKeyboardButton(text="◀️ Назад", callback_data="set_params")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await message.answer(f"✅ Страна выбрана: {message.text}")
            await message.answer(
                "🛫 Шаг 2/10: Город вылета\n\n"
                "Напишите город вылета в именительном падеже:\n"
                "Пример: Москва или Санкт-Петербург",
                reply_markup=reply_markup
            )
            await state.set_state(UserStates.DEPARTURE_CITY)
        else:
            # Поиск похожих вариантов
            suggestions = [name for name in COUNTRIES.keys() if country_input in name][:3]
            suggestions_text = "\n".join(f"• {suggestion}" for suggestion in suggestions) if suggestions else "не найдено"
            
            await message.answer(
                f"❌ Страна не найдена\n\n"
                f"Проверьте правильность написания.\n"
                f"Возможные варианты:\n{suggestions_text}\n\n"
                f"Попробуйте еще раз или введите 'отмена' для выхода"
            )
            await state.set_state(UserStates.COUNTRY)

    async def get_departure_city(self, message: Message, state: FSMContext) -> None:
        """Получение города вылета"""
        await self.rate_limit(message.from_user.id)
        user_id = message.from_user.id
        city_input = message.text.strip().lower()
        
        if city_input in DEPARTURE_CITIES:
            city_id = DEPARTURE_CITIES[city_input]
            self.user_params[user_id].departure_city = city_id
            
            keyboard = [
                [InlineKeyboardButton(text="◀️ Назад", callback_data="set_params")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await message.answer(f"✅ Город вылета: {message.text}")
            await message.answer(
                "🏖 Шаг 3/10: Выбор курортов\n\n"
                "Напишите города/курорты через пробел:\n"
                "Пример: Анталья Кемер Сиде\n\n"
                "Если курорты не важны, напишите нет",
                reply_markup=reply_markup
            )
            await state.set_state(UserStates.RESORTS)
        else:
            suggestions = [name for name in DEPARTURE_CITIES.keys() if city_input in name][:3]
            suggestions_text = "\n".join(f"• {suggestion}" for suggestion in suggestions) if suggestions else "не найдено"
            
            await message.answer(
                f"❌ Город не найден\n\n"
                f"Возможные варианты:\n{suggestions_text}\n\n"
                f"Попробуйте еще раз:"
            )
            await state.set_state(UserStates.DEPARTURE_CITY)

    async def get_resorts(self, message: Message, state: FSMContext) -> None:
        """Получение курортов"""
        await self.rate_limit(message.from_user.id)
        user_id = message.from_user.id
        resorts_input = message.text.strip().lower()
        
        if resorts_input in ["нет", "нету", "не важно"]:
            self.user_params[user_id].resorts = []
            resorts_text = "Не указаны"
        else:
            resorts_list = resorts_input.split()
            valid_resorts = []
            invalid_resorts = []
            
            for resort in resorts_list:
                if resort in RESORTS_LIST:
                    valid_resorts.append(RESORTS_LIST[resort])
                else:
                    invalid_resorts.append(resort)
            
            if valid_resorts:
                self.user_params[user_id].resorts = valid_resorts
                resorts_text = ", ".join(resorts_list)
                
                if invalid_resorts:
                    await message.answer(f"⚠️ Не найдены курорты: {', '.join(invalid_resorts)}")
            else:
                await message.answer(
                    "❌ Курорты не найдены\n\n"
                    "Проверьте правильность написания и попробуйте еще раз:"
                )
                await state.set_state(UserStates.RESORTS)
                return
        
        keyboard = [
            [InlineKeyboardButton(text="◀️ Назад", callback_data="set_params")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await message.answer(f"✅ Курорты: {resorts_text}")
        await message.answer(
            "🍽 Шаг 4/10: Тип питания\n\n"
            "Доступные варианты:\n"
            "• RO - без питания\n"
            "• BB - завтраки\n" 
            "• HB - завтрак + ужин\n"
            "• FB - полный пансион\n"
            "• AI - всё включено\n"
            "• UAI - ультра всё включено\n"
            "• AI(NOALC) - всё включено без алкоголя\n\n"
            "Введите коды через пробел или не нужно",
            reply_markup=reply_markup
        )
        await state.set_state(UserStates.MEALS)

    async def get_meals(self, message: Message, state: FSMContext) -> None:
        """Получение типов питания"""
        await self.rate_limit(message.from_user.id)
        user_id = message.from_user.id
        meals_input = message.text.strip().upper()
        
        if meals_input in ["НЕ НУЖНО", "НЕТУ", "НЕТ", "ЛЮБОЙ"]:
            self.user_params[user_id].meals = []
            meals_text = "Любой"
        else:
            meals_list = meals_input.split()
            valid_meals = []
            invalid_meals = []
            
            for meal in meals_list:
                if meal in MEALS_MAPPING:
                    valid_meals.append(MEALS_MAPPING[meal])
                else:
                    invalid_meals.append(meal)
            
            if valid_meals:
                self.user_params[user_id].meals = valid_meals
                meals_text = ", ".join(meals_list)
                
                if invalid_meals:
                    await message.answer(f"⚠️ Неизвестные типы питания: {', '.join(invalid_meals)}")
            else:
                await message.answer(
                    "❌ Типы питания не распознаны\n\n"
                    "Проверьте правильность кодов и попробуйте еще раз:"
                )
                await state.set_state(UserStates.MEALS)
                return
        
        keyboard = [
            [InlineKeyboardButton(text="◀️ Назад", callback_data="set_params")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await message.answer(f"✅ Питание: {meals_text}")
        await message.answer(
            "👨‍👩‍👧‍👦 Шаг 5/10: Количество туристов\n\n"
            "Напишите, сколько будет взрослых людей:",
            reply_markup=reply_markup
        )
        await state.set_state(UserStates.ADULTS)

    async def get_adults(self, message: Message, state: FSMContext) -> None:
        """Получение количества взрослых"""
        await self.rate_limit(message.from_user.id)
        user_id = message.from_user.id
        adults_input = message.text.strip()
        
        if adults_input.isdigit() and int(adults_input) > 0:
            self.user_params[user_id].tourist_group_adults = adults_input
            
            keyboard = [
                [InlineKeyboardButton(text="◀️ Назад", callback_data="set_params")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await message.answer(f"✅ Взрослые: {adults_input}")
            await message.answer(
                "👶 Шаг 6/10: Дети\n\n"
                "Напишите количество детей:\n"
                "Пример: 2 или 0 если детей нет",
                reply_markup=reply_markup
            )
            await state.set_state(UserStates.CHILDREN)
        else:
            await message.answer(
                "❌ Неверный формат\n\n"
                "Введите число больше 0:"
            )
            await state.set_state(UserStates.ADULTS)

    async def get_children(self, message: Message, state: FSMContext) -> None:
        """Получение количества детей"""
        await self.rate_limit(message.from_user.id)
        user_id = message.from_user.id
        children_input = message.text.strip().lower()
        
        if children_input.isdigit():
            self.user_params[user_id].tourist_group_kids = children_input
            children_text = children_input
        elif children_input in ["0", "нет", "нету"]:
            self.user_params[user_id].tourist_group_kids = "0"
            children_text = "0"
        else:
            await message.answer(
                "❌ Неверный формат\n\n"
                "Введите число или 'нет':"
            )
            await state.set_state(UserStates.CHILDREN)
            return
        
        keyboard = [
            [InlineKeyboardButton(text="◀️ Назад", callback_data="set_params")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await message.answer(f"✅ Дети: {children_text}")
        await message.answer(
            "🍼 Шаг 7/10: Младенцы\n\n"
            "Напишите количество младенцев (до 2 лет):\n"
            "Пример: 1 или 0 если младенцев нет",
            reply_markup=reply_markup
        )
        await state.set_state(UserStates.INFANTS)

    async def get_infants(self, message: Message, state: FSMContext) -> None:
        """Получение количества младенцев"""
        await self.rate_limit(message.from_user.id)
        user_id = message.from_user.id
        infants_input = message.text.strip()
        
        if infants_input.isdigit():
            self.user_params[user_id].tourist_group_infants = infants_input
            
            keyboard = [
                [InlineKeyboardButton(text="◀️ Назад", callback_data="set_params")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await message.answer(f"✅ Младенцы: {infants_input}")
            await message.answer(
                "🗓 Шаг 8/10: Продолжительность тура\n\n"
                "Напишите минимальное и максимальное количество ночей:\n"
                "Пример: 7 14 - от 7 до 14 ночей",
                reply_markup=reply_markup
            )
            await state.set_state(UserStates.NIGHTS)
        else:
            await message.answer(
                "❌ Неверный формат\n\n"
                "Введите число:"
            )
            await state.set_state(UserStates.INFANTS)

    async def get_nights(self, message: Message, state: FSMContext) -> None:
        """Получение диапазона ночей"""
        await self.rate_limit(message.from_user.id)
        user_id = message.from_user.id
        nights_input = message.text.strip().split()
        
        if len(nights_input) == 2 and nights_input[0].isdigit() and nights_input[1].isdigit():
            self.user_params[user_id].night_range_from = nights_input[0]
            self.user_params[user_id].night_range_to = nights_input[1]
            
            keyboard = [
                [InlineKeyboardButton(text="◀️ Назад", callback_data="set_params")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await message.answer(f"✅ Ночи: от {nights_input[0]} до {nights_input[1]}")
            await message.answer(
                "⭐ Шаг 9/10: Категория отеля\n\n"
                "Напишите звездность отелей через пробел:\n"
                "Пример: 3 4 5 - отели 3*, 4* и 5*",
                reply_markup=reply_markup
            )
            await state.set_state(UserStates.HOTEL_CATEGORY)
        else:
            await message.answer(
                "❌ Неверный формат\n\n"
                "Введите два числа через пробел:\n"
                "Пример: 7 14"
            )
            await state.set_state(UserStates.NIGHTS)

    async def get_hotel_category(self, message: Message, state: FSMContext) -> None:
        """Получение категорий отеля"""
        await self.rate_limit(message.from_user.id)
        user_id = message.from_user.id
        categories_input = message.text.strip().split()
        
        valid_categories = []
        invalid_categories = []
        
        for category in categories_input:
            if category.isdigit() and 1 <= int(category) <= 5:
                valid_categories.append(category)
            else:
                invalid_categories.append(category)
        
        if valid_categories:
            self.user_params[user_id].hotel_categories = valid_categories
            
            keyboard = [
                [InlineKeyboardButton(text="◀️ Назад", callback_data="set_params")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await message.answer(f"✅ Категории отелей: {', '.join(valid_categories)}*")
            
            if invalid_categories:
                await message.answer(f"⚠️ Игнорированы: {', '.join(invalid_categories)} (допустимы значения 1-5)")
            
            await message.answer(
                "📅 Шаг 10/10: Даты заезда\n\n"
                "Введите начальную и конечную даты в формате:\n"
                "Пример: 2025-06-01 2025-06-15\n\n"
                "Где:\n"
                "• 2025-06-01 - дата заезда\n"
                "• 2025-06-15 - дата выезда",
                reply_markup=reply_markup
            )
            await state.set_state(UserStates.DATES)
        else:
            await message.answer(
                "❌ Неверные категории\n\n"
                "Введите числа от 1 до 5 через пробел:\n"
                "Пример: 3 4 5"
            )
            await state.set_state(UserStates.HOTEL_CATEGORY)

    async def get_dates(self, message: Message, state: FSMContext) -> None:
        """Получение дат заселения"""
        await self.rate_limit(message.from_user.id)
        user_id = message.from_user.id
        dates_input = message.text.strip().split()
        
        if len(dates_input) == 2:
            try:
                date_from = datetime.strptime(dates_input[0], "%Y-%m-%d")
                date_to = datetime.strptime(dates_input[1], "%Y-%m-%d")
                
                if date_from <= date_to:
                    self.user_params[user_id].check_in_date_range_from = dates_input[0]
                    self.user_params[user_id].check_in_date_range_to = dates_input[1]
                    
                    # Показываем сводку параметров
                    params = self.user_params[user_id]
                    summary = self._create_search_summary(params)
                    
                    keyboard = [
                        [InlineKeyboardButton(text="🚀 Начать поиск", callback_data="start_search")],
                        [InlineKeyboardButton(text="⚙️ Изменить параметры", callback_data="set_params")]
                    ]
                    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                    
                    await message.answer(
                        f"✅ Параметры настроены!\n\n"
                        f"{summary}\n"
                        f"Готовы начать поиск?",
                        reply_markup=reply_markup
                    )
                    await state.clear()
                else:
                    await message.answer(
                        "❌ Дата начала должна быть раньше даты окончания\n\n"
                        "Попробуйте снова:"
                    )
                    await state.set_state(UserStates.DATES)
            except ValueError:
                await message.answer(
                    "❌ Неверный формат даты\n\n"
                    "Используйте формат ГГГГ-ММ-ДД:\n"
                    "Пример: 2025-06-01 2025-06-15"
                )
                await state.set_state(UserStates.DATES)
        else:
            await message.answer(
                "❌ Неверный формат\n\n"
                "Введите две даты через пробел:\n"
                "Пример: 2025-06-01 2025-06-15"
            )
            await state.set_state(UserStates.DATES)

    async def start_search(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Начало поиска туров"""
        await callback.answer()
        await self.rate_limit(callback.from_user.id)
        
        user_id = callback.from_user.id
        
        if user_id not in self.user_params or not self.user_params[user_id]:
            await callback.message.edit_text("❌ Параметры поиска не найдены. Начните с настройки.")
            await self.set_params(callback, state)
            return
        
        await callback.message.edit_text("🔍 Анализирую ваши предпочтения...")
        
        # Показываем сводку параметров
        params = self.user_params[user_id]
        summary = self._create_search_summary(params)
        await callback.message.answer(f"📋 Параметры поиска:\n{summary}")
        
        # Создание URL для API запроса
        url = "https://api-gateway.travelata.ru/statistic/cheapestTours"
        
        # Построение параметров запроса
        query_params = []
        
        if params.countries:
            for country in params.countries:
                query_params.append(f"countries[]={country}")
        
        if params.departure_city:
            query_params.append(f"departureCity={params.departure_city}")
        
        if params.night_range_from:
            query_params.append(f"nightRange[from]={params.night_range_from}")
        
        if params.night_range_to:
            query_params.append(f"nightRange[to]={params.night_range_to}")
        
        if params.resorts:
            for resort in params.resorts:
                query_params.append(f"resorts[]={resort}")
        
        if params.meals:
            for meal in params.meals:
                query_params.append(f"meals[]={meal}")
        
        if params.tourist_group_adults:
            query_params.append(f"touristGroup[adults]={params.tourist_group_adults}")
        
        if params.tourist_group_kids:
            query_params.append(f"touristGroup[kids]={params.tourist_group_kids}")
        
        if params.tourist_group_infants:
            query_params.append(f"touristGroup[infants]={params.tourist_group_infants}")
        
        if params.hotel_categories:
            for category in params.hotel_categories:
                query_params.append(f"hotelCategories[]={category}")
        
        if params.check_in_date_range_from:
            query_params.append(f"checkInDateRange[from]={params.check_in_date_range_from}")
        
        if params.check_in_date_range_to:
            query_params.append(f"checkInDateRange[to]={params.check_in_date_range_to}")
        
        full_url = f"{url}?{'&'.join(query_params)}"
        
        await callback.message.answer("🌐 Формирую запрос к системе поиска...")
        
        # ВСЕГДА используем браузер для получения данных
        await self.get_data_via_browser(full_url, callback.message.chat.id, user_id)

    async def get_data_via_browser(self, url: str, chat_id: int, user_id: int) -> None:
        """Получение данных через браузер и преобразование в список отелей"""
        try:
            await self.bot.send_message(chat_id, "🔄 Подключаюсь к системе поиска...")
            
            # Получаем содержимое страницы через Selenium
            page_content = self.web_driver_manager.get_page_content(url)
            
            if "Ошибка" in page_content or "Таймаут" in page_content:
                await self.bot.send_message(chat_id, f"❌ {page_content}")
                return
            
            # Преобразуем содержимое страницы в список отелей
            hotels_message, has_tours = self.parse_json_to_hotels_list(page_content)
            
            if not has_tours:
                # Если туров нет, показываем сообщение и НЕ запускаем мониторинг
                keyboard = [
                    [InlineKeyboardButton(text="⚙️ Изменить параметры", callback_data="set_params")],
                    [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="start_search")]
                ]
                reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                
                await self.bot.send_message(chat_id, "✅ Поиск завершен")
                await self.bot.send_message(
                    chat_id, 
                    hotels_message, 
                    reply_markup=reply_markup
                )
                return
            
            # Только если есть туры - показываем кнопку мониторинга
            keyboard = [
                [InlineKeyboardButton(text="🔍 Включить мониторинг", callback_data="start_monitoring")],
                [InlineKeyboardButton(text="⚙️ Новый поиск", callback_data="set_params")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await self.bot.send_message(chat_id, "✅ Поиск завершен успешно!")
            
            # Отправляем список отелей (разбиваем на части если нужно)
            if len(hotels_message) > 4000:
                parts = [hotels_message[i:i+4000] for i in range(0, len(hotels_message), 4000)]
                for part in parts:
                    await self.bot.send_message(chat_id, part)
            else:
                await self.bot.send_message(chat_id, hotels_message)
            
            await self.bot.send_message(
                chat_id, 
                "📊 Что дальше?\n\n"
                "• 🔍 Мониторинг - отслеживать изменения цен\n"
                "• ⚙️ Новый поиск - изменить параметры", 
                reply_markup=reply_markup
            )
            
            # Сохраняем данные для возможного запуска мониторинга
            self.monitoring_users[user_id] = {
                'url': url,
                'current_content': page_content,
                'chat_id': chat_id,
                'hotels_snapshot': self._create_hotels_snapshot_from_content(page_content),
                'has_tours': has_tours
            }
            
        except Exception as e:
            error_msg = f"❌ Ошибка при получении данных: {str(e)}"
            await self.bot.send_message(chat_id, error_msg)
            logger.error(error_msg)

    async def start_monitoring(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Запуск мониторинга после подтверждения"""
        await callback.answer()
        await self.rate_limit(callback.from_user.id)
        
        user_id = callback.from_user.id
        
        if user_id not in self.monitoring_users:
            await callback.message.edit_text("❌ Данные для мониторинга не найдены. Выполните поиск сначала.")
            return
        
        monitoring_data = self.monitoring_users[user_id]
        
        if not monitoring_data.get('has_tours', False):
            await callback.message.edit_text("❌ Мониторинг недоступен - туры не найдены.")
            return
        
        keyboard = [
            [InlineKeyboardButton(text="⏹ Остановить мониторинг", callback_data="stop_monitoring")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "🔍 Мониторинг активирован!\n\n"
            "Я буду проверять изменения каждые 10 минут:\n"
            "• 📈 Изменения цен\n"
            "• 🆕 Новые туры\n"
            "• 🏨 Новые отели\n\n"
            "Вы получите уведомление о любых изменениях.",
            reply_markup=reply_markup
        )
        
        # Запускаем мониторинг
        asyncio.create_task(self.monitor_tours(user_id))

    def _create_hotels_snapshot_from_content(self, page_content: str):
        """Создание снимка текущего состояния отелей из содержимого страницы"""
        try:
            start_idx = page_content.find('{')
            end_idx = page_content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                return {}
            
            json_str = page_content[start_idx:end_idx]
            data = json.loads(json_str)
            
            if not data.get('success') or 'data' not in data:
                return {}
            
            tours = data['data']
            if not tours:
                return {}
            
            hotels = {}
            for tour in tours:
                hotel_id = tour['hotelId']
                if hotel_id not in hotels:
                    hotels[hotel_id] = {
                        'name': tour['hotelName'],
                        'min_price': tour['price'],
                        'prices': [tour['price']],
                        'tours_count': 1
                    }
                else:
                    hotels[hotel_id]['prices'].append(tour['price'])
                    hotels[hotel_id]['min_price'] = min(hotels[hotel_id]['min_price'], tour['price'])
                    hotels[hotel_id]['tours_count'] += 1
            
            return hotels
        except:
            return {}

    async def monitor_tours(self, user_id: int) -> None:
        """Умный мониторинг изменений в турах через браузер - каждые 10 минут"""
        delay = 600  # начальная задержка 10 минут
        max_delay = 3600  # максимальная задержка 1 час
        
        while user_id in self.monitoring_users:
            try:
                await asyncio.sleep(delay)
                
                if user_id not in self.monitoring_users:
                    break
                
                monitoring_data = self.monitoring_users[user_id]
                url = monitoring_data['url']
                old_snapshot = monitoring_data['hotels_snapshot']
                chat_id = monitoring_data['chat_id']
                
                await self.bot.send_message(
                    chat_id, 
                    f"🔍 Проверка обновлений\n⏰ {datetime.now().strftime('%H:%M')}"
                )
                
                # Получаем новые данные через браузер
                new_content = self.web_driver_manager.get_page_content(url)
                
                if "Ошибка" in new_content or "Таймаут" in new_content:
                    await self.bot.send_message(chat_id, f"❌ Ошибка при мониторинге: {new_content}")
                    continue
                
                new_snapshot = self._create_hotels_snapshot_from_content(new_content)
                
                # Проверяем, есть ли вообще туры в новых данных
                if not new_snapshot:
                    await self.bot.send_message(
                        chat_id, 
                        "📭 Туры больше не найдены\n\nМониторинг остановлен."
                    )
                    if user_id in self.monitoring_users:
                        del self.monitoring_users[user_id]
                    break
                
                changes = self._compare_hotels_snapshots(old_snapshot, new_snapshot)
                
                if changes:
                    message = "📊 Обнаружены изменения:\n\n"
                    for change in changes:
                        message += f"{change}\n\n"
                    
                    # Добавляем разделитель
                    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    
                    await self.bot.send_message(chat_id=chat_id, text=message)
                    
                    # Обновляем снимок
                    self.monitoring_users[user_id]['hotels_snapshot'] = new_snapshot
                    self.monitoring_users[user_id]['current_content'] = new_content
                    
                    # Сбрасываем задержку при изменениях
                    delay = 600
                else:
                    await self.bot.send_message(
                        chat_id=chat_id, 
                        text=f"ℹ️ Изменений не обнаружено\nСледующая проверка через {delay//60} мин."
                    )
                    
                    # Увеличиваем задержку если нет изменений
                    delay = min(delay * 1.5, max_delay)
                        
            except Exception as e:
                error_message = f"❌ Ошибка при мониторинге: {str(e)}"
                if user_id in self.monitoring_users:
                    await self.bot.send_message(
                        chat_id=self.monitoring_users[user_id]['chat_id'], 
                        text=error_message
                    )
                logger.error(f"Ошибка при мониторинге: {e}")
                continue

    def _compare_hotels_snapshots(self, old_snapshot, new_snapshot):
        """Сравнение двух снимков отелей и выявление изменений"""
        changes = []
        
        # Проверяем изменения цен в существующих отелях
        for hotel_id, old_info in old_snapshot.items():
            if hotel_id in new_snapshot:
                new_info = new_snapshot[hotel_id]
                old_min_price = old_info['min_price']
                new_min_price = new_info['min_price']
                
                # Изменение цены более чем на 10%
                price_change_percent = ((new_min_price - old_min_price) / old_min_price) * 100
                
                if price_change_percent < -10:  # Цена понизилась более чем на 10%
                    changes.append(f"💰 Понижение цены\n🏨 {old_info['name']}\n📉 Было: {old_min_price:,} руб.\n📊 Стало: {new_min_price:,} руб.\n📈 Изменение: ▼{abs(price_change_percent):.1f}%")
                
                elif price_change_percent > 10:  # Цена повысилась более чем на 10%
                    changes.append(f"💸 Повышение цены\n🏨 {old_info['name']}\n📈 Было: {old_min_price:,} руб.\n📊 Стало: {new_min_price:,} руб.\n📈 Изменение: ▲{price_change_percent:.1f}%")
                
                # Изменение количества туров
                old_count = old_info['tours_count']
                new_count = new_info['tours_count']
                if new_count > old_count:
                    changes.append(f"🆕 Добавлены туры\n🏨 {old_info['name']}\n✅ Добавлено: +{new_count - old_count}\n📊 Всего: {new_count} туров")
                elif new_count < old_count:
                    changes.append(f"❌ Удалены туры\n🏨 {old_info['name']}\n❌ Удалено: -{old_count - new_count}\n📊 Осталось: {new_count} туров")
        
        # Новые отели
        new_hotels = set(new_snapshot.keys()) - set(old_snapshot.keys())
        for hotel_id in new_hotels:
            hotel_info = new_snapshot[hotel_id]
            changes.append(f"🏨 Новый отель\n🎯 {hotel_info['name']}\n💰 Цена от: {hotel_info['min_price']:,} руб.\n📊 Туров: {hotel_info['tours_count']}")
        
        # Исчезнувшие отели
        disappeared_hotels = set(old_snapshot.keys()) - set(new_snapshot.keys())
        for hotel_id in disappeared_hotels:
            hotel_info = old_snapshot[hotel_id]
            changes.append(f"🚫 Отель удален\n🎯 {hotel_info['name']}\n📊 Было туров: {hotel_info['tours_count']}")
        
        return changes

    async def stop_monitoring(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Остановка мониторинга"""
        await callback.answer()
        await self.rate_limit(callback.from_user.id)
        
        user_id = callback.from_user.id
        
        if user_id in self.monitoring_users:
            del self.monitoring_users[user_id]
        
        keyboard = [
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="set_params")],
            [InlineKeyboardButton(text="🔄 Продолжить поиск", callback_data="start_search")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "⏹ Мониторинг остановлен\n\nВыберите действие:",
            reply_markup=reply_markup
        )

    async def back_to_start(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Возврат к началу"""
        await callback.answer()
        await state.clear()
        
        keyboard = [
            [InlineKeyboardButton(text="🎯 Настроить параметры", callback_data="set_params")],
            [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "✨ Главное меню\n\nВыберите действие:",
            reply_markup=reply_markup
        )

    def setup_handlers(self) -> None:
        """Настройка обработчиков"""
        
        # Обработчик команды /start
        self.router.message.register(self.start, Command("start"))
        
        # Обработчики callback запросов
        self.router.callback_query.register(self.set_params, F.data == "set_params")
        self.router.callback_query.register(self.help_command, F.data == "help")
        self.router.callback_query.register(self.start_search, F.data == "start_search")
        self.router.callback_query.register(self.start_monitoring, F.data == "start_monitoring")
        self.router.callback_query.register(self.stop_monitoring, F.data == "stop_monitoring")
        self.router.callback_query.register(self.back_to_start, F.data == "back_to_start")
        
        # Обработчики состояний
        self.router.message.register(self.get_country, UserStates.COUNTRY)
        self.router.message.register(self.get_departure_city, UserStates.DEPARTURE_CITY)
        self.router.message.register(self.get_resorts, UserStates.RESORTS)
        self.router.message.register(self.get_meals, UserStates.MEALS)
        self.router.message.register(self.get_adults, UserStates.ADULTS)
        self.router.message.register(self.get_children, UserStates.CHILDREN)
        self.router.message.register(self.get_infants, UserStates.INFANTS)
        self.router.message.register(self.get_nights, UserStates.NIGHTS)
        self.router.message.register(self.get_hotel_category, UserStates.HOTEL_CATEGORY)
        self.router.message.register(self.get_dates, UserStates.DATES)

    async def run(self):
        """Запуск бота"""
        try:
            await self.dp.start_polling(self.bot)
        finally:
            # Закрываем WebDriver при завершении работы
            self.web_driver_manager.close()

async def main():
    """Основная функция"""
    # Используем переменную окружения для токена
    BOT_TOKEN = "8315207560:AAGmeIyfKGEhy2cQPQvaj4zyY_l3PPn-K7k"
    
    # Создание и запуск бота
    bot = TravelataBot(BOT_TOKEN)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())