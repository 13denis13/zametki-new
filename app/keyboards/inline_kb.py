from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Доход", callback_data="income")
    builder.button(text="➖ Расход", callback_data="expense")
    builder.button(text="📊 Отчет", callback_data="report")
    builder.button(text="📈 Отчет по категории", callback_data="report_by_category")
    builder.button(text="🗑 Очистить данные", callback_data="delete_data")
    builder.adjust(2, 1, 1, 1)
    return builder.as_markup()

def cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()

def back_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="back")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()

def confirm_delete_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить все", callback_data="confirm_delete")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2)
    return builder.as_markup()

def categories_kb(transaction_type):
    builder = InlineKeyboardBuilder()
    if transaction_type == "income":
        categories = [
            ("Зарплата", "cat_ЗП"),
            ("Подработка", "cat_Подработка"),
            ("Премия", "cat_Премия"),
            ("Другое", "cat_Другое"),
        ]
    else:  # expense
        categories = [
            ("Продукты", "cat_food"),
            ("Транспорт", "cat_transport"),
            ("Жильё", "cat_rent"),
            ("Развлечения", "cat_entertainment"),
            ("Другое", "cat_other_expense"),
        ]

    for text, callback in categories:
        builder.button(text=text, callback_data=callback)

    builder.button(text="⬅️ Назад", callback_data="back")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2)
    return builder.as_markup()

def report_category_kb(categories):
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat, callback_data=f"rep_cat_{cat}")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2)
    return builder.as_markup()

def ask_description_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data="desc_yes")
    builder.button(text="❌ Нет", callback_data="desc_no")
    builder.button(text="⬅️ Назад", callback_data="back")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2)
    return builder.as_markup()

def report_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="back")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()