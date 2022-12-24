from typing import Union
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
import sqlite3 as sql
from telegram.ext import ConversationHandler, ContextTypes

from telegram.ext import (
    filters,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
)
"""
Builds AMI-study-bot.

Requires:
    - `./bot_config.toml`: file with bot configuration
"""

### External Modules
import logging
from pathlib import Path

"""
Module used to work with bot's configurations.
"""

# module for working w/ toml files
import logging
import toml


class BotConfig:
    """
    Class representing configuration of a bot.

    #### Attributes:

        token (:obj:`str`): Token of the bot.
    """

    def __init__(self, token: str):
        self.token: str = token

    @classmethod
    def from_file(cls, config_file_path: str):
        """
        Create an instance of BotConfig using a filepath.

        Filepath should point to a valid `bot_config.toml` file.

        #### Arguments:

            config_file_path (:obj:`str`): Path to the config file.

        """

        # open file w/ bot config
        try:
            with open(
                config_file_path,  # current file path + name
                "r",  # read-only config
            ) as config_file:
                # load the toml config object
                config_toml = toml.load(config_file)

                # load the token and throw an exception if cannot
                try:
                    token: str = config_toml["bot"]["token"]
                except Exception:  # failed to get token from toml
                    raise AttributeError(
                        f'Config file "{config_file_path}" does not have token properly defined.'
                    )

                # return new bot config instance
                logging.debug(f'Loaded bot config from "{config_file_path}".')
                return cls(token)
        except:  # failed to open the file
            raise OSError(
                f'Couldn\'t open the bot config file at "{config_file_path}".'
            )


async def check_ans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    user_id = update.message.from_user.id
    user_nickname = update.message.from_user.username
    task_number = context.user_data["task_number"]
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    query_db.execute(
        f"""SELECT * FROM All_Tasks WHERE ID = "{task_number}";""")
    res = query_db.fetchone()
    ans = res[2]
    group_id = res[4]

    query_db.execute(
        f"""SELECT * FROM Students WHERE ID = "{user_id}";""")
    res = query_db.fetchone()
    attempts = res[4] + 1
    query_db.execute(
        f"""UPDATE Students set ALL_ATTEMPTS = {attempts} WHERE ID = "{user_id}";""")

    if ans == message:
        query_db.execute(
            f"""SELECT * FROM Students WHERE ID = "{user_id}";""")
        res = query_db.fetchone()
        success_solve = res[3] + 1
        query_db.execute(
            f"""UPDATE Students set SUCCESS_SOLVE = {success_solve} WHERE ID = "{user_id}";""")

        query_db.execute(
            f"""SELECT * FROM Groups WHERE GROUP_ID = "{group_id}";""")
        res_group = query_db.fetchone()
        new_res = res_group[2]
        if new_res == None:
            new_res = ""
        new_res = new_res + " " + str(user_nickname) + "_" + str(task_number)

        query_db.execute(
            f"""UPDATE Groups set RESULTS = "{new_res}" WHERE GROUP_ID = "{group_id}";""")

        await context.bot.send_message(
            text=f"Правильно!",
            chat_id=update.message.chat_id)

        keyboard = [
            [
                InlineKeyboardButton("Ещё", callback_data="Новая задача"),
                InlineKeyboardButton("Выйти", callback_data="Выйти к списку команд"),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        conn.commit()
        conn.close()
        return 'choose_next_when_correct'
    else:
        await context.bot.send_message(
            text=f"Неправильно :(",
            chat_id=update.message.chat_id)

        keyboard = [
            [
                InlineKeyboardButton("Решение", callback_data="Посмотреть решение"),
                InlineKeyboardButton("Ещё", callback_data="Новая задача"),
                InlineKeyboardButton("Выйти", callback_data="Выйти к списку команд"),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        conn.commit()
        conn.close()
        return 'choose_next_when_incorrect'


async def choose_next_step_correct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[int, str]:
    query = update.callback_query
    if query.data == "Новая задача":
        context.user_data["text_group"] = False
        context.user_data["query_group"] = True
        return await send_task_message(update, context)
    elif query.data == "Выйти к списку команд":
        context.user_data.clear()
        await bot_help(update, context)
        return ConversationHandler.END


async def choose_next_step_incorrect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[int, str, None]:
    query = update.callback_query
    if query.data == "Посмотреть решение":
        return await show_ans(update, context)
    elif query.data == "Новая задача":
        context.user_data["text_group"] = False
        context.user_data["query_group"] = True
        return await send_task_message(update, context)
    elif query.data == "Выйти к списку команд":
        context.user_data.clear()
        await bot_help(update, context)
        return ConversationHandler.END


async def show_ans(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    task_number = context.user_data["task_number"]
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    query_db.execute(
        f"""SELECT * FROM All_Tasks WHERE ID = "{task_number}" ORDER BY RANDOM() LIMIT 1;""")
    res = query_db.fetchone()

    answer = res[2]
    solution = res[3]
    if type(answer) != str:
        await context.bot.send_photo(photo=answer, chat_id=update.callback_query.message.chat_id)
        answer = 'Изображение выше'
    if type(solution) != str:
        await context.bot.send_photo(photo=solution, chat_id=update.callback_query.message.chat_id)
        solution = 'Изображение выше'
    ans = 'Правильный ответ: ' + answer + '\nРешение: ' + solution
    await context.bot.send_message(
        text=ans,
        chat_id=update.callback_query.message.chat_id)

    keyboard = [
        [
            InlineKeyboardButton("Ещё", callback_data="Новая задача"),
            InlineKeyboardButton("Выйти", callback_data="Выйти к списку команд"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text("Что дальше?", reply_markup=reply_markup)
    return 'choose_next_when_incorrect'

def check_teacher(user_id):
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    query_db.execute(
        f"""SELECT * FROM Teachers WHERE ID = "{user_id}";""")
    res = query_db.fetchone()
    if res is None or len(res) == 0:
        return 'not_correct'
    return 'correct'


def check_student(user_id):
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    query_db.execute(
        f"""SELECT * FROM Students WHERE ID = "{user_id}";""")
    res = query_db.fetchone()
    if res is None or len(res) == 0:
        return 'not_correct'
    return 'correct'


async def delete_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_id = update.message.from_user.id
    correct_person = check_teacher(user_id)
    if correct_person != "correct":
        await context.bot.sendMessage(text="Эта функция доступна только преподавателю.",
                                      chat_id=update.message.chat_id)
        keyboard = [
            [
                InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return "what_to_do"
    context.user_data["chat_id"] = update.message.chat_id
    return await delete_group_start_state(update, context)


async def delete_group_start_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await context.bot.send_message(
        text="Выберите коллекцию, которую хотите удалить. Для этого напишите ниже название коллекции:",
        chat_id=context.user_data["chat_id"], reply_markup=ForceReply()
    )
    return 'specify_group'


async def specify_group_dg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    user_id = update.message.from_user.id
    query_db.execute(f"""SELECT * FROM Groups WHERE GROUP_ID = "{update.message.text}";""")
    res = query_db.fetchone()
    conn.commit()
    conn.close()

    keyboard = [
        [
            InlineKeyboardButton("Продолжить", callback_data="Продолжить"),
            InlineKeyboardButton("Выйти", callback_data="Выйти к списку команд")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if res is None:
        await context.bot.send_message(
            text=f"Такой коллекции не существует, пожалуйста, попробуйте другое название.",
            chat_id=context.user_data["chat_id"])

        await context.bot.send_message(
            text="Что дальше?",
            chat_id=context.user_data["chat_id"],
            reply_markup=reply_markup
        )
        return 'show_next_steps'

    if res[1] == user_id:
        context.user_data["group_id"] = update.message.text

        conn = sql.connect('study_bot.db')
        query_db = conn.cursor()
        query_db.execute(
            f"""SELECT * FROM All_Tasks WHERE GROUP_ID = "{context.user_data["group_id"]}";""")
        res = query_db.fetchall()
        conn.commit()
        conn.close()

        if len(res) > 0:
            context.user_data["tasks"] = res
            return await show_warning_tasks_in_group(update, context)
        else:
            await delete_group_from_db(update, context)

            await context.bot.send_message(
                text="Что дальше?",
                chat_id=context.user_data["chat_id"],
                reply_markup=reply_markup
            )
            return 'show_next_steps'
    else:
        await context.bot.send_message(
            text=f"Вы не создавали эту коллекцию, поэтому не можете её удалить :(",
            chat_id=context.user_data["chat_id"])

        await context.bot.send_message(
            text="Что дальше?",
            chat_id=context.user_data["chat_id"],
            reply_markup=reply_markup
        )
        return 'show_next_steps'


async def show_warning_tasks_in_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await context.bot.send_message(
        text="Внимание! В коллекции, которую вы хотите удалить, есть задачи:",
        chat_id=context.user_data["chat_id"]
    )
    tasks = []
    for i in range(len(context.user_data["tasks"])):
        task = context.user_data["tasks"][i][1]
        if type(task) != str:
            await context.bot.send_photo(photo=task, chat_id=context.user_data["chat_id"])
            task = 'Изображение выше'
        ans = str(i + 1) + '. ' + task + '\n'
        tasks.append(context.user_data["tasks"][i][0])
        await context.bot.send_message(
            text=f"{ans}",
            chat_id=context.user_data["chat_id"])

    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data="Да"),
            InlineKeyboardButton("Нет", callback_data="Нет")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        text="Вы действительно хотите удалить её?",
        chat_id=context.user_data["chat_id"],
        reply_markup=reply_markup
    )

    context.user_data["tasks"] = tasks
    return 'confirm_deletion'


async def confirm_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[str, int]:
    keyboard = [
        [
            InlineKeyboardButton("Продолжить", callback_data="Продолжить"),
            InlineKeyboardButton("Выйти", callback_data="Выйти к списку команд")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query.data == 'Да':
        await delete_group_from_db(update, context)

    await context.bot.send_message(
        text="Что дальше?",
        chat_id=context.user_data["chat_id"],
        reply_markup=reply_markup
    )
    return 'show_next_steps'


async def delete_group_from_db(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    if "tasks" in context.user_data:
        for task in context.user_data["tasks"]:
            query_db.execute(f"""DELETE FROM All_Tasks WHERE ID = "{task}";""")
    query_db.execute(f"""DELETE FROM Groups WHERE GROUP_ID = "{context.user_data["group_id"]}";""")
    conn.commit()
    conn.close()

    await context.bot.send_message(
        text="Коллекция была успешно удалена.",
        chat_id=context.user_data["chat_id"]
    )


async def show_next_steps_dg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[str, int]:
    if update.callback_query.data == 'Продолжить':
        return await delete_group_start_state(update, context)
    elif update.callback_query.data == 'Выйти к списку команд':
        context.user_data.clear()
        await bot_help(update, context)
        return ConversationHandler.END


async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_id = update.message.from_user.id
    correct_person = check_teacher(user_id)
    if correct_person != "correct":
        await context.bot.sendMessage(text="Эта функция доступна только преподавателю.",
                                      chat_id=update.message.chat_id)
        keyboard = [
            [
                InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return "what_to_do"
    context.user_data["chat_id"] = update.message.chat_id
    await context.bot.send_message(
        text="Выберите коллекцию, из которой хотите удалить задачи. Для этого напишите ниже название коллекции:",
        chat_id=context.user_data["chat_id"], reply_markup=ForceReply()
    )
    return 'specify_group'


async def specify_group_dt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[str, int]:
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    user_id = update.message.from_user.id
    query_db.execute(f"""SELECT * FROM Groups WHERE GROUP_ID = "{update.message.text}";""")
    res = query_db.fetchone()
    conn.commit()
    conn.close()
    if res is None:
        await context.bot.send_message(
            text=f"Такой коллекции не существует, пожалуйста, введите команду еще раз.",
            chat_id=context.user_data["chat_id"])
        context.user_data.clear()
        await bot_help(update, context)
        return ConversationHandler.END
    if res[1] == user_id:
        context.user_data["group_id"] = update.message.text
        return await show_tasks_in_group(update, context)
    else:
        await context.bot.send_message(
            text=f"Вы не создавали эту коллекцию, поэтому удалить в ней ничего не можете :(",
            chat_id=context.user_data["chat_id"])
        context.user_data.clear()
        await bot_help(update, context)
        return ConversationHandler.END


async def specify_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await context.bot.send_message(text="Укажите номер задачи, который хотите удалить.",
                                   chat_id=context.user_data["chat_id"], reply_markup=ForceReply())
    return 'delete_task_from_db'


async def delete_task_by_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    all_tasks = context.user_data["tasks"]
    num_task = update.message.text

    keyboard = [
        [
            InlineKeyboardButton("Продолжить", callback_data="Продолжить"),
            InlineKeyboardButton("Выйти", callback_data="Выйти к списку команд")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if num_task not in all_tasks.keys():
        await context.bot.send_message(text="Вы ввели несуществующий номер задачи. Возможно задача была удалена ранее. Повторите попытку.",
                                       chat_id=context.user_data["chat_id"], reply_markup=reply_markup)
    else:
        conn = sql.connect('study_bot.db')
        query_db = conn.cursor()
        query_db.execute(f"""DELETE FROM All_Tasks WHERE ID = "{all_tasks[num_task]}";""")
        conn.commit()
        conn.close()
        await context.bot.send_message(text=f"Задача {num_task} была успешно удалена!",
                                       chat_id=context.user_data["chat_id"])
        await context.bot.send_message(text="Что дальше?",
                                       chat_id=context.user_data["chat_id"],
                                       reply_markup=reply_markup)
    return 'show_next_steps'


async def show_next_steps_dt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[str, int]:
    if update.callback_query.data == 'Продолжить':
        return await show_tasks_in_group(update, context)
    elif update.callback_query.data == 'Выйти к списку команд':
        context.user_data.clear()
        await bot_help(update, context)
        return ConversationHandler.END


async def show_tasks_in_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[str, int]:
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    query_db.execute(
        f"""SELECT * FROM All_Tasks WHERE GROUP_ID = "{context.user_data["group_id"]}";""")
    res = query_db.fetchall()
    conn.commit()
    conn.close()
    if res is None or len(res) == 0:
        await context.bot.send_message(
            text=f"Эта коллекция пуста. Для добавления новых задач воспользуйтесь командой /add.",
            chat_id=context.user_data["chat_id"])
        context.user_data.clear()
        await bot_help(update, context)
        return ConversationHandler.END
    from_numbers_to_tasks = dict()
    for i in range(len(res)):
        task = res[i][1]
        if type(task) != str:
            await context.bot.send_photo(photo=task, chat_id=context.user_data["chat_id"])
            task = 'Изображение выше'
        ans = str(i + 1) + '. ' + task + '\n'
        from_numbers_to_tasks[str(i + 1)] = res[i][0]
        await context.bot.send_message(
            text=f"{ans}",
            chat_id=context.user_data["chat_id"])
    context.user_data["tasks"] = from_numbers_to_tasks
    return await specify_task(update, context)

async def edit_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_id = update.message.from_user.id
    correct_person = check_teacher(user_id)
    if correct_person != "correct":
        await context.bot.sendMessage(text="Эта функция доступна только преподавателю.",
                                      chat_id=update.message.chat_id)
        keyboard = [
            [
                InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return "what_to_do"
    context.user_data["chat_id"] = update.message.chat_id
    await context.bot.send_message(
        text="Выберите коллекцию, из которой хотите редактировать задачи. Для этого напишите ниже название коллекции:",
        chat_id=context.user_data["chat_id"], reply_markup=ForceReply()
    )
    return 'specify_group'


async def specify_group_et(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[str, int]:
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    user_id = update.message.from_user.id
    query_db.execute(f"""SELECT * FROM Groups WHERE GROUP_ID = "{update.message.text}";""")
    res = query_db.fetchone()
    conn.commit()
    conn.close()
    if res is None:
        await context.bot.send_message(
            text=f"Такой коллекции не существует, пожалуйста, введите команду еще раз.",
            chat_id=context.user_data["chat_id"])
        context.user_data.clear()
        return ConversationHandler.END
    if res[1] == user_id:
        context.user_data["group_id"] = update.message.text
        return await show_tasks_in_group(update, context)
    else:
        await context.bot.send_message(
            text=f"Вы не создавали эту коллекцию, поэтому удалить в ней ничего не можете :(",
            chat_id=context.user_data["chat_id"])
        context.user_data.clear()
        return ConversationHandler.END


async def check_keyboard_for_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "Изменить условие":
        return 'pre_edit_condition'
    elif query.data == "Изменить решение":
        return 'pre_edit_solution'
    elif query.data == "Изменить ответ":
        return 'pre_edit_ans'
    elif query.data == "Выйти из редактирования":
        await context.bot.send_message(text="Вы вышли из режима редактирования задачи!", chat_id=query.message.chat_id)
        return ConversationHandler.END


async def show_tasks_in_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[str, int]:
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    query_db.execute(
        f"""SELECT * FROM All_Tasks WHERE GROUP_ID = "{context.user_data["group_id"]}";""")
    res = query_db.fetchall()
    conn.commit()
    conn.close()
    if res is None or len(res) == 0:
        await context.bot.send_message(
            text=f"Эта коллекция пуста. Для добавления новых задач воспользуйтесь командой /add.",
            chat_id=context.user_data["chat_id"])
        context.user_data.clear()
        await bot_help(update, context)
        return ConversationHandler.END
    from_numbers_to_tasks = dict()
    for i in range(len(res)):
        answer = res[i][2]
        solution = res[i][3]
        task = res[i][1]
        if type(task) != str:
            await context.bot.send_photo(photo=task, chat_id=update.message.chat_id)
            task = 'Изображение выше'
        if type(answer) != str:
            await context.bot.send_photo(photo=answer, chat_id=update.message.chat_id)
            answer = 'Изображение выше'
        if type(solution) != str:
            await context.bot.send_photo(photo=solution, chat_id=update.message.chat_id)
            solution = 'Изображение выше'
        ans = str(i + 1) + '. ' + task + '\n Ответ: ' + answer + '\n Решение: ' + solution + '\n'
        from_numbers_to_tasks[str(i + 1)] = res[i][0]
        await context.bot.send_message(
            text=f"{ans}",
            chat_id=update.message.chat_id)
    context.user_data["tasks"] = from_numbers_to_tasks
    return 'pre_edit_condition'


async def pre_edit_condition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(text="Введите, пожалуйста, что вы хотите изменить и как в формате [Ответ/Решение/Условие] [текст]!", chat_id=update.message.chat_id)
    context.user_data["num"] = update.message.text
    keyboard = [
        [
            InlineKeyboardButton("Продолжить", callback_data="Продолжить"),
            InlineKeyboardButton("Выйти", callback_data="Выйти к списку команд")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    if context.user_data["num"] not in context.user_data["tasks"].keys():
        await context.bot.send_message(
            text="Вы ввели несуществующий номер задачи. Возможно задача была удалена ранее. Повторите попытку.",
            chat_id=context.user_data["chat_id"], reply_markup=reply_markup)
        return 'show_next_steps_et'
    return 'edit_condition'


async def edit_condition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_tasks = context.user_data["tasks"]
    text_task = update.message.text.split()
    keyboard = [
        [
            InlineKeyboardButton("Продолжить", callback_data="Продолжить"),
            InlineKeyboardButton("Выйти", callback_data="Выйти к списку команд")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if text_task[0] not in ['Ответ', 'Решение', 'Условие'] or len(text_task) <= 1:
        await context.bot.send_message(
            text="Вы ввели данные в неверном формате, попробуйте еще раз!",
            chat_id=context.user_data["chat_id"], reply_markup=reply_markup)
        return 'show_next_steps_et'
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    if text_task[0] == 'Ответ':
        field = 'ANSWER'
    elif text_task[0] == 'Решение':
        field = 'SOLVE'
    else:
        field = 'TASK'
    query_db.execute(f"""UPDATE All_Tasks SET "{field}" = "{text_task[1]}" WHERE ID = "{all_tasks[context.user_data['num']]}";""")
    conn.commit()
    conn.close()
    keyboard = [
        [
            #InlineKeyboardButton("Продолжить", callback_data="Продолжить"),
            InlineKeyboardButton("Выйти", callback_data="Выйти к списку команд")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(text=f"Задача {context.user_data['num']} была успешно отредактирована!",
                                       chat_id=context.user_data["chat_id"])
    await context.bot.send_message(text="Что дальше?",
                                       chat_id=context.user_data["chat_id"],
                                       reply_markup=reply_markup)
    return 'show_next_steps_et'


async def show_next_steps_et(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.data == 'Продолжить':
        return await show_tasks_in_group(update, context)
    elif update.callback_query.data == 'Выйти к списку команд':
        context.user_data.clear()
        await bot_help(update, context)
        return ConversationHandler.END


async def gen_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_id = update.message.from_user.id
    correct_person = check_student(user_id)
    if correct_person != "correct":
        await context.bot.sendMessage(text="Эта функция доступна только ученикам.",
                                      chat_id=update.message.chat_id)
        keyboard = [
            [
                InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return "what_to_do"
    keyboard = [
        [
            InlineKeyboardButton("Дефолтные", callback_data="Стандарт"),
            InlineKeyboardButton("От пользователей", callback_data="Пользователи"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Выбери, какие задачи хочешь решать", reply_markup=reply_markup)
    return 'choose_cluster'


async def choose_tasks_cluster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if update.callback_query.data == "Стандарт":
        keyboard = [
            [
                InlineKeyboardButton("Матанализ", callback_data="Матанализ"),
                InlineKeyboardButton("Дискретная математика", callback_data="Дискретная математика"),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text("Выбери предмет, по которому хочешь решать задачи:",
                                        reply_markup=reply_markup)
        return 'choose_subject'
    elif update.callback_query.data == "Пользователи":
        await update.callback_query.message.reply_text("Укажи коллекцию, из которой хочешь решать задачи:",
                                        reply_markup=ForceReply())
        return 'choose_collection'


async def choose_standard_task_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    query = update.callback_query
    if query.data == "Матанализ":
        context.user_data["group"] = "matan_default"
    elif query.data == "Дискретная математика":
        context.user_data["group"] = "discr_default"
    context.user_data["text_group"] = False
    context.user_data["query_group"] = True
    return await send_task_message(update, context)


async def choose_task_collection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[int, str, None]:
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    query_db.execute(
        f"""SELECT * FROM All_Tasks WHERE GROUP_ID = "{update.message.text}" ORDER BY RANDOM() LIMIT 1;""")
    res = query_db.fetchone()
    conn.commit()
    conn.close()
    if res is None:
        await context.bot.sendMessage(
            text="Упс! Такой коллекции не существует. Создайте ее, если хотите!", chat_id=update.message.chat_id)
        context.user_data.clear()
        await context.bot.sendMessage(
            text="Заканчиваем подбор задач.", chat_id=update.message.chat_id)
        keyboard = [
            [
                InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return "what_to_do"
    else:
        context.user_data["group"] = update.message.text
        context.user_data["text_group"] = True
        context.user_data["query_group"] = False
        return await send_task_message(update, context)


async def send_task_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    query_db.execute(f"""SELECT * FROM ALL_TASKS WHERE GROUP_ID = "{context.user_data["group"]}" ORDER BY RANDOM() LIMIT 1;""")
    res = query_db.fetchone()
    conn.commit()
    conn.close()
    if not context.user_data["text_group"] and context.user_data["query_group"]:
        await context.bot.send_message(text="Задача:", chat_id=update.callback_query.message.chat_id)
        context.user_data["task_number"] = res[0]
        if type(res[1]) == str:  # проверка на то, что перед нами, - фото или текст
            await context.bot.send_message(
                text=f"{res[1]}",
                chat_id=update.callback_query.message.chat_id)
        elif type(res[1]) == bytes:
            await context.bot.send_photo(
                photo=res[1],
                chat_id=update.callback_query.message.chat_id)
        await context.bot.send_message(text="Введите ваш ответ:",
                                       chat_id=update.callback_query.message.chat_id,
                                       reply_markup=ForceReply())
        return 'check_ans'
    elif context.user_data["text_group"] and not context.user_data["query_group"]:
        await context.bot.send_message(text="Задача:", chat_id=update.message.chat_id)
        context.user_data["task_number"] = res[0]
        if type(res[1]) == str:  # проверка на то, что перед нами, - фото или текст
            await context.bot.send_message(
                text=f"{res[1]}",
                chat_id=update.message.chat_id)
        elif type(res[1]) == bytes:
            await context.bot.send_photo(
                photo=res[1],
                chat_id=update.message.chat_id)
        await context.bot.send_message(text="Введите ваш ответ:",
                                       chat_id=update.message.chat_id,
                                       reply_markup=ForceReply())
        return 'check_ans'



async def all_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    correct_person = check_teacher(user_id)
    if correct_person != "correct":
        await context.bot.sendMessage(text="Эта функция доступна только преподавателю.",
                                      chat_id=update.message.chat_id)
        keyboard = [
            [
                InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return "what_to_do"
    await context.bot.sendMessage(text="Введите название коллекции, задания которой вы хотите посмотреть:",
                                  chat_id=update.message.chat_id, reply_markup=ForceReply())
    context.user_data["chat_id"] = update.message.chat_id
    return "input_group"


async def get_all_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    user_id = update.message.from_user.id
    message = update.message.text
    query_db.execute(f"""SELECT * FROM Groups WHERE GROUP_ID = "{message}";""")
    group = query_db.fetchone()
    query_db.execute(
        f"""SELECT * FROM All_Tasks WHERE GROUP_ID = "{message}";""")
    res = query_db.fetchall()
    conn.commit()
    conn.close()
    if group is None:
        await context.bot.send_message(
            text=f"Такой коллекции не существует.",
            chat_id=context.user_data["chat_id"])
        context.user_data.clear()
        keyboard = [
            [
                InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return 'what_to_do'
    if group[1] != user_id:
        await context.bot.send_message(
            text=f"Вы не создавали эту коллекцию, поэтому посмотреть ее задания не можете :(",
            chat_id=context.user_data["chat_id"])
        context.user_data.clear()
        keyboard = [
            [
                InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return 'what_to_do'
    for i in range(len(res)):
        answer = res[i][2]
        solution = res[i][3]
        task = res[i][1]
        if type(task) != str:
            await context.bot.send_photo(photo=task, chat_id=update.message.chat_id)
            task = 'Изображение выше'
        if type(answer) != str:
            await context.bot.send_photo(photo=answer, chat_id=update.message.chat_id)
            answer = 'Изображение выше'
        if type(solution) != str:
            await context.bot.send_photo(photo=solution, chat_id=update.message.chat_id)
            solution = 'Изображение выше'
        ans = str(i + 1) + '. ' + task + '\n Ответ: ' + answer + '\n Решение: ' + solution + '\n'
        await context.bot.send_message(
            text=f"{ans}",
            chat_id=update.message.chat_id)
    keyboard = [
        [
            InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
    return 'what_to_do'


async def what_to_do(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[int, str]:
    query = update.callback_query
    if query.data == "Выйти к списку команд":
        await bot_help(update, context)
        return ConversationHandler.END

async def bot_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Проверяем, есть ли пользователь в Teachers
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    if update.callback_query is not None:
        query_db.execute("""SELECT * from Teachers WHERE ID = {}""".format(update.callback_query.from_user.id))
    else:
        query_db.execute("""SELECT * from Teachers WHERE ID = {}""".format(update.message.from_user.id))
    response = query_db.fetchall()
    conn.commit()
    conn.close()
    if len(response) > 0:  # Значит, пользователь в Teachers
        text = """Вы - преподаватель. Ваши команды:\n
1) /add - добавить в коллекцию карточку или создать новую коллекцию.\n
2) /edit_task - редактировать карточку из моей коллекции.\n
3) /delete_task - удалить карточку из моей коллекции.\n
4) /delete_group - удалить мою коллекцию.\n
5) /all_tasks - посмотреть все задачи в коллекции.\n
6) /results - посмотреть результаты учеников в коллекции.\n
7) /top - посмотреть топ-10 людей, решивших больше всех задач.\n
8) /help - посмотреть доступные команды.\n """

        if update.callback_query is not None:
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=text)
        else:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=text)
    else:
        text = """Вы - студент. Ваши команды:\n
1) /gen_task - решать задачи.\n
2) /top - посмотреть топ-10 людей, решивших больше всех задач.\n
3) /my_stat - посмотреть, сколько задач я решил. \n
4) /help - посмотреть доступные команды.\n
"""

        if update.callback_query is not None:
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=text)
        else:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=text)


async def my_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    correct_person = check_student(user_id)
    if correct_person != "correct":
        await context.bot.sendMessage(text="Эта функция доступна только ученикам.",
                                      chat_id=update.message.chat_id)
        keyboard = [
            [
                InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return "what_to_do"
    conn = sql.connect('study_bot.db')
    user_id = update.message.from_user.id
    query_db = conn.cursor()
    query_db.execute(
        f"""SELECT * FROM Students WHERE ID = "{user_id}" ORDER BY RANDOM() LIMIT 1;""")
    res = query_db.fetchone()
    success_solve = res[3]
    attempts = res[4]
    await context.bot.send_message(
        text=f"Вы решили правильно: {success_solve} задач \n"
             f"Вы пробовали решить: {attempts} задач",
        chat_id=update.message.chat_id)
    keyboard = [
        [
            InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
    return 'what_to_do'


async def results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    correct_person = check_teacher(user_id)
    if correct_person == "correct":
        await context.bot.sendMessage(text="Введите название группы, результаты которой вы хотите посмотреть.",
                                      chat_id=update.message.chat_id)
        return "input_group"
    else:
        await context.bot.sendMessage(text="Эта функция доступна только преподавателю.",
                                      chat_id=update.message.chat_id)
        keyboard = [
            [
                InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return "what_to_do"


async def get_resuts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = update.message.text
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    query_db.execute(
        f"""SELECT * FROM Groups WHERE GROUP_ID = "{group_id}";""")
    res = query_db.fetchone()
    if res is None or len(res) == 0:
        await context.bot.sendMessage(
            text="Такой группы не существует, создайте ее, если хотите!", chat_id=update.message.chat_id)
    elif res[2] is None:
        await context.bot.sendMessage(
            text="Задачи из вашей группы пока никто не решал!", chat_id=update.message.chat_id)
    else:
        res_students = res[2].split()
        res_dict = dict()
        for i in range(len(res_students)):
            res_one = res_students[i].split('_')
            task = res_one[1]
            id_student = res_one[0]
            if id_student in res_dict:
                res_dict[id_student].add(task)
            else:
                res_dict[id_student] = set()
                res_dict[id_student].add(task)
        j = 0
        text = ""
        for student in res_dict.keys():
            res_student = list(res_dict[student])
            text += "@" + str(student) + ": "
            text += str(len(res_student)) + " уникальных задач\n"
        await context.bot.send_message(
            text=f"{text}",
            chat_id=update.message.chat_id)

    keyboard = [
        [
            InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
    return 'what_to_do'


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text="Привет, @{}! Это учебный бот для подготовки к коллоквиумам и контрольным работам! "
             "Здесь ты сможешь решать задачи, как из уже готовых коллекций, так и создавать свои коллекции и добавлять в них задачи. "
             "Подробнее - в /help. "
             "Удачи! Но перед тем, как приступить:".format(update.message.from_user.username)
        )

    keyboard = [
        [
            InlineKeyboardButton("Студент", callback_data="Студент"),
            InlineKeyboardButton("Преподаватель", callback_data="Преподаватель"),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Выбери, кто ты - студент или преподаватель.", reply_markup=reply_markup)
    return 'choose_role'


async def choose_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    if query.data == "Студент":
        query_db.execute(f"""SELECT * FROM Students WHERE ID = {query.from_user.id};""")
        res_stud = query_db.fetchone()
        query_db.execute(f"""SELECT * FROM Teachers WHERE ID = {query.from_user.id};""")
        res_teach = query_db.fetchone()
        if res_teach is not None:
            await context.bot.send_message(text="Вы уже зарегистрированы как преподаватель.",
                                           chat_id=query.message.chat_id)
        elif res_stud is not None:
            await context.bot.send_message(text="Вы уже зарегистрированы как студент.",
                                           chat_id=query.message.chat_id)
        else:
            query_db.execute("""INSERT INTO Students VALUES(?, ?, ?, ?, ?, ?);""",
                             (query.from_user.id, query.from_user.first_name, query.from_user.last_name, 0, 0, None))
            conn.commit()
            conn.close()
            await context.bot.send_message(text="Теперь вы можете решать задачи и готовиться к работам!",
                                           chat_id=query.message.chat_id)
    elif query.data == "Преподаватель":
        query_db.execute(f"""SELECT * FROM Students WHERE ID = {query.from_user.id};""")
        res_stud = query_db.fetchone()
        query_db.execute(f"""SELECT * FROM Teachers WHERE ID = {query.from_user.id};""")
        res_teach = query_db.fetchone()
        if res_stud is not None:
            await context.bot.send_message(text="Вы уже зарегистрированы как студент.",
                                           chat_id=query.message.chat_id)
        elif res_teach is not None:
            await context.bot.send_message(text="Вы уже зарегистрированы как преподаватель.",
                                           chat_id=query.message.chat_id)
        else:
            query_db.execute("""INSERT INTO Teachers VALUES(?, ?, ?);""",
                             (query.from_user.id, query.from_user.first_name, query.from_user.last_name))
            conn.commit()
            conn.close()
            await context.bot.send_message(
                text="Теперь вы можете добавлять сюда задачи, генерировать работы для студентов, а также смотреть их оценки.",
                chat_id=query.message.chat_id)
    await bot_help(update, context)
    return ConversationHandler.END



async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    query_db.execute("""SELECT * FROM Students ORDER BY SUCCESS_SOLVE DESC LIMIT 10""")
    res = query_db.fetchall()
    text_top = ''
    iter = min(10, len(res))
    for i in range(iter):
        text_top += str(i + 1) + ". "
        if res[i][1] is not None:
            text_top += res[i][1]
        if res[i][2] is not None:
            text_top += " " + res[i][2]
        text_top += f", решено задач: {res[i][3]}\n"
    await context.bot.send_message(text=text_top, chat_id=update.message.chat_id)

    keyboard = [
        [
            InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
    return 'what_to_do'


async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_id = update.message.from_user.id
    correct_person = check_teacher(user_id)
    if correct_person != "correct":
        await context.bot.sendMessage(text="Эта функция доступна только преподавателю.",
                                      chat_id=update.message.chat_id)
        keyboard = [
            [
                InlineKeyboardButton("Выйти к списку команд", callback_data="Выйти к списку команд")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return "what_to_do"
    context.user_data["chat_id"] = update.message.chat_id
    await context.bot.send_message(text="Напишите в сообщения или пришлите фотографией условие вашей задачи:",
                                   chat_id=update.message.chat_id, reply_markup=ForceReply())
    return 'prep_task'


async def prep_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if len(update.message.photo) > 0:
        photo_id = update.message.photo[-1].file_id
        photo_file = await context.bot.get_file(photo_id)
        photo_bytes = await photo_file.download_as_bytearray()
        context.user_data["photo_task"] = photo_bytes
    else:
        context.user_data["text_task"] = update.message.text

    await context.bot.send_message(text="Напишите ответ к заданию:",
                                   chat_id=update.message.chat_id, reply_markup=ForceReply())
    return 'prep_ans'


async def prep_ans(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    context.user_data["ans"] = update.message.text

    await context.bot.send_message(text="Напишите в сообщения или пришлите фотографией решение:",
                                   chat_id=update.message.chat_id, reply_markup=ForceReply())
    return 'prep_solution'


async def prep_solution(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if len(update.message.photo) > 0:
        photo_id = update.message.photo[-1].file_id
        photo_file = await context.bot.get_file(photo_id)
        photo_bytes = await photo_file.download_as_bytearray()
        context.user_data["photo_solution"] = photo_bytes
    else:
        context.user_data["text_solution"] = update.message.text
    await context.bot.send_message(text="Выберите или создайте коллекцию, в которую хотите что-то добавить. Для этого напишите ниже название коллекции:",
                                   chat_id=update.message.chat_id, reply_markup=ForceReply())
    return 'prep_collection'


async def prep_collection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[str, int]:
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    query_db.execute("""SELECT GROUP_ID FROM GROUPS""")
    response = set([group[0] for group in query_db.fetchall()])
    conn.commit()
    conn.close()
    if update.message.text not in response:
        keyboard = [
            [
                InlineKeyboardButton("Да", callback_data="Да"),
                InlineKeyboardButton("Нет", callback_data="Нет"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.user_data["collection"] = update.message.text
        context.user_data["new_collection"] = True
        context.user_data["user_id"] = update.message.from_user.id
        await context.bot.send_message(
            text="Такой коллекции пока нет. Мне её создать?",
            chat_id=update.message.chat_id, reply_markup=reply_markup)
        return 'create_collection'
    else:
        context.user_data["collection"] = update.message.text
        await add_query(update, context)
        await bot_help(update, context)
        return ConversationHandler.END


async def create_collection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query.data == "Да":
        conn = sql.connect('study_bot.db')
        query_db = conn.cursor()
        query_db.execute("""INSERT INTO GROUPS VALUES(?, ?, ?);""",
                         (context.user_data["collection"], context.user_data["user_id"], None))
        conn.commit()
        conn.close()
        await add_query(update, context)
        context.user_data.clear()
        await bot_help(update, context)
        return ConversationHandler.END
    elif update.callback_query.data == "Нет":
        await context.bot.send_message(
            text="Создание коллекции и задачи отменено",
            chat_id=context.user_data["chat_id"])
        context.user_data.clear()
        await bot_help(update, context)
        return ConversationHandler.END


async def add_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = sql.connect('study_bot.db')
    query_db = conn.cursor()
    query_db.execute("""SELECT max(ID) FROM ALL_TASKS;""")
    item_id = query_db.fetchone()[0] + 1
    if "text_task" in context.user_data:
        if "text_solution" in context.user_data:
            query_db.execute("""INSERT INTO ALL_TASKS VALUES(?, ?, ?, ?, ?);""",
                             (item_id, context.user_data["text_task"], context.user_data["ans"],
                              context.user_data["text_solution"], context.user_data["collection"]))
        else:
            query_db.execute("""INSERT INTO ALL_TASKS VALUES(?, ?, ?, ?, ?);""",
                             (item_id, context.user_data["text_task"], context.user_data["ans"],
                              context.user_data["photo_solution"], context.user_data["collection"]))
    else:
        if "text_solution" in context.user_data:
            query_db.execute("""INSERT INTO ALL_TASKS VALUES(?, ?, ?, ?, ?);""",
                             (item_id, context.user_data["photo_task"], context.user_data["ans"],
                              context.user_data["text_solution"], context.user_data["collection"]))
        else:
            query_db.execute("""INSERT INTO ALL_TASKS VALUES(?, ?, ?, ?, ?);""",
                             (item_id, context.user_data["photo_task"], context.user_data["ans"],
                              context.user_data["photo_solution"], context.user_data["collection"]))
    conn.commit()
    conn.close()

    if "new_collection" in context.user_data:
        await context.bot.send_message(text="Новая коллекция {} была добавлена.".format(context.user_data["collection"]), chat_id=context.user_data["chat_id"])
    await context.bot.send_message(text="Новая задача была добавлена в коллекцию.", chat_id=context.user_data["chat_id"])



# Logging setup
logging.basicConfig(
    format="[%(asctime)s]{%(levelname)s} %(name)s: %(message)s",
    level=logging.DEBUG,
)

def run_bot(config_file_path: str):
    # get bot configuration

    # build the bot application using bot token
    application = ApplicationBuilder().token("5964932384:AAFwuhEZB4S5uq4yGGTAj8hTq4b8g-jF5hg").build()

    # add handlers
    start_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={'choose_role': [CallbackQueryHandler(choose_role)]},
        fallbacks=[]
    )

    help_handler = CommandHandler('help', bot_help)
g
    add_task_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_task)],
        states={'prep_task': [MessageHandler(filters=(filters.TEXT | filters.PHOTO), callback=prep_task)],
                'prep_ans': [MessageHandler(filters=filters.TEXT, callback=prep_ans)],
                'prep_solution': [MessageHandler(filters=(filters.TEXT | filters.PHOTO), callback=prep_solution)],
                'prep_collection': [MessageHandler(filters=filters.TEXT, callback=prep_collection)],
                'create_collection': [CallbackQueryHandler(create_collection)],
                'what_to_do': [CallbackQueryHandler(what_to_do)]
                },
        fallbacks=[]
    )

    solve_handler = ConversationHandler(
        entry_points=[CommandHandler('gen_task', gen_task)],
        states={
            'choose_cluster': [CallbackQueryHandler(choose_tasks_cluster)],
            'choose_subject': [CallbackQueryHandler(choose_standard_task_group)],
            'choose_collection': [MessageHandler(filters.TEXT, choose_task_collection)],
            'check_ans': [MessageHandler(filters.TEXT, check_ans)],
            'choose_next_when_correct': [CallbackQueryHandler(choose_next_step_correct)],
            'choose_next_when_incorrect': [CallbackQueryHandler(choose_next_step_incorrect)],
            'what_to_do': [CallbackQueryHandler(what_to_do)]
        },
        fallbacks=[]
    )

    all_tasks_handler = ConversationHandler(
        entry_points=[CommandHandler('all_tasks', all_tasks)],
        states={
            'input_group': [MessageHandler(filters.TEXT, get_all_tasks)],
            'what_to_do': [CallbackQueryHandler(what_to_do)]
        },
        fallbacks=[]
    )

    results_handler = ConversationHandler(
        entry_points=[CommandHandler('results', results)],
        states={
            'input_group': [MessageHandler(filters.TEXT, get_resuts)],
            'what_to_do': [CallbackQueryHandler(what_to_do)]
        },
        fallbacks=[]
    )

    top_handler = ConversationHandler(
        entry_points=[CommandHandler('top', top)],
        states={
            'what_to_do': [CallbackQueryHandler(what_to_do)]
        },
        fallbacks=[]
    )

    my_stat_handler = ConversationHandler(
        entry_points=[CommandHandler('my_stat', my_stat)],
        states={
            'what_to_do': [CallbackQueryHandler(what_to_do)]
        },
        fallbacks=[]
    )

    delete_task_handler = ConversationHandler(
        entry_points=[CommandHandler('delete_task', delete_task)],
        states={
            'specify_group': [MessageHandler(filters.TEXT, specify_group_dt)],
            'delete_task_from_db': [MessageHandler(filters.TEXT, delete_task_by_number)],
            'show_next_steps': [CallbackQueryHandler(show_next_steps_dt)],
            'what_to_do': [CallbackQueryHandler(what_to_do)]
        },
        fallbacks=[]
    )

    delete_group_handler = ConversationHandler(
        entry_points=[CommandHandler('delete_group', delete_group)],
        states={
            'specify_group': [MessageHandler(filters.TEXT, specify_group_dg)],
            'confirm_deletion': [CallbackQueryHandler(confirm_deletion)],
            'show_next_steps': [CallbackQueryHandler(show_next_steps_dg)],
            'what_to_do': [CallbackQueryHandler(what_to_do)]
        },
        fallbacks=[]
    )

    edit_task_handler = ConversationHandler(
        entry_points=[CommandHandler('edit_task', edit_task)],
        states={
            'specify_group': [MessageHandler(filters.TEXT, specify_group_et)],
            'pre_edit_condition': [MessageHandler(filters.TEXT, pre_edit_condition)],
            'edit_condition': [MessageHandler(filters.TEXT, edit_condition)],
            'show_next_steps_et': [CallbackQueryHandler(show_next_steps_et)],
            'what_to_do': [CallbackQueryHandler(what_to_do)]
        },
        fallbacks=[]
    )

    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(add_task_handler)
    application.add_handler(solve_handler)
    application.add_handler(my_stat_handler)
    application.add_handler(all_tasks_handler)
    application.add_handler(top_handler)
    application.add_handler(delete_task_handler)
    application.add_handler(delete_group_handler)
    application.add_handler(edit_task_handler)
    application.add_handler(results_handler)
    # initialize and start the bot application
    application.run_polling()



def run_asb():
    """
    Build and run asb application.
    """
    # build and run the bot
    run_bot(Path(__file__).with_name("bot_config.toml"))  # current path + config file

    # Program runs asynchronously inside `run_bot`


if __name__ == "__main__":
    run_asb()
