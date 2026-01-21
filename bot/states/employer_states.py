"""FSM состояния для работодателя"""

from aiogram.fsm.state import State, StatesGroup


class EmployerStates(StatesGroup):
    """Состояния для создания вакансии"""
    
    waiting_for_title = State()
    waiting_for_city = State()
    waiting_for_location = State()
    waiting_for_salary = State()
    waiting_for_description = State()
    waiting_for_photo = State()


class EmployerEditStates(StatesGroup):
    """Состояния для редактирования вакансии"""
    
    selecting_vacancy = State()
    editing_title = State()
    editing_city = State()
    editing_location = State()
    editing_salary = State()
    editing_description = State()
    editing_photo = State()


class AdminBroadcastStates(StatesGroup):
    """Состояния для рассылки админа"""
    
    waiting_for_text = State()
    waiting_for_confirmation = State()


class AdminSearchStates(StatesGroup):
    """Состояния для поиска пользователя админом"""
    
    waiting_for_user_id = State()


class AdminSubscriptionStates(StatesGroup):
    """Состояния для управления подпиской админом"""
    
    waiting_for_user_id = State()
    waiting_for_days = State()
    waiting_for_vacancies_count = State()
    waiting_for_employer_id = State()
