#test_connection.py
#utils/gmail_client.py içinde test_gmail_connection() adlı async fonksiyon var.


from aiogram.filters import Command
from aiogram.types import Message
from handlers.email_handlers import router  # veya kendi router'ını kullan

@router.message(Command("testgmail"), admin_filter)
async def test_gmail_cmd(message: Message):
    result = await test_gmail_connection()
    await message.answer(result)
