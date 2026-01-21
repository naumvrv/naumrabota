"""FSM состояния для работника"""

from aiogram.fsm.state import State, StatesGroup


class WorkerStates(StatesGroup):
    """Состояния для создания/редактирования резюме работника"""
    
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_city = State()
    waiting_for_location = State()
    waiting_for_resume = State()
    waiting_for_photo = State()


class WorkerEditStates(StatesGroup):
    """Состояния для редактирования отдельных полей резюме"""
    
    editing_name = State()
    editing_age = State()
    editing_city = State()
    editing_location = State()
    editing_resume = State()
    editing_photo = State()
