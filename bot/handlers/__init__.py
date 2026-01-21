from bot.handlers.start import router as start_router
from bot.handlers.worker import router as worker_router
from bot.handlers.employer import router as employer_router
from bot.handlers.admin import router as admin_router
from bot.handlers.payments import router as payments_router

__all__ = [
    'start_router',
    'worker_router',
    'employer_router',
    'admin_router',
    'payments_router',
]
