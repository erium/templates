from .board_manager import BoardManager
from datetime import datetime
from enum import Enum
import json
from json.decoder import JSONDecodeError
import logging
from pathlib import Path
import sqlite3
from typing import Any
import uuid


class DatabaseConfig(Enum):
    """
    Enum for database and table names.
    """

    db_path = Path(__file__).resolve().parent / "../db"
    db_file = db_path / "sessions.db"
    global_ = "global"
    sessions = "sessions"
    board = "boards"
    chat_history = "chat_history"
    chatbot_configs = "chatbot_configs"


class Connection:
    """
    Context manager for database connections.
    """

    logger = logging.getLogger(__name__)

    def __init__(self, db_file: str):
        self.db_file = db_file

    def __enter__(self):
        try:
            self.connection = sqlite3.connect(self.db_file)
        except sqlite3.DatabaseError as e:
            Connection.logger.error(f"Error connecting to database {self.db_file}: {e}")
            raise
        else:
            return self.connection

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.connection:
            self.connection.close()


class DBOperations:
    # ------------------------------------------------------------------------------------------
    # DB OPERATIONS
    # ------------------------------------------------------------------------------------------

    logger = logging.getLogger(__name__)

    @staticmethod
    def execute_query(
        query: str,
        params: tuple = None,
        fetchone: bool = False,
        db_file: str = DatabaseConfig.db_file.value,
    ) -> list[Any] | int:
        """
        Execute a query on the database. If the query is a SELECT query, the results are returned.

        Args:
            query (str): The query to execute.
            params (tuple): The parameters to pass to the query.
            fetchone (bool): Whether to fetch only the first row of the query. Defaults to False (fetchall).
            db_file (str): Path to the database file. Defaults to the db/sessions.db file.

        Returns:
            List[Any] | int: The results of the query: either a list of row data or the number of rows affected by the query
        """
        if params and not isinstance(params, tuple):
            params = (params,)

        try:
            with Connection(db_file) as c:
                cursor = c.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                c.commit()

                if query.strip().lower().startswith("select"):
                    if fetchone:
                        data = cursor.fetchone()
                    else:
                        data = cursor.fetchall()
                    if data:
                        return data
                    else:
                        return None
                else:
                    return cursor.rowcount

        except sqlite3.Error as e:
            DBOperations.logger.error(
                f"Database error occurred in db {db_file} with query {query} and params {params}: {e}"
            )
            raise

    @staticmethod
    def create_table(table_name: str, table_schema: str):
        """
        Create a table in the database.

        Args:
            table_name (str): Name of the table.
            table_schema (str): Schema of the table.
        """
        DBOperations.execute_query(
            query=f"CREATE TABLE IF NOT EXISTS {table_name} ({table_schema})"
        )

    @staticmethod
    def setup_database():
        """
        Setup an sqlite3 database with tables for global configurations, sessions, chatbot instances, and chat history/boards.
        """
        # ensure path exists
        Path.mkdir(DatabaseConfig.db_path.value, parents=True, exist_ok=True)

        # tables and schemas
        tables = {
            DatabaseConfig.global_.value: """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                port INTEGER DEFAULT 8501,
                skip_intro INTEGER DEFAULT 0,
                intro_wide TEXT DEFAULT "Welcome to Hal-E! Your personal chatbot assistant.",
                intro_narrow TEXT DEFAULT "Welcome to Hal-E! Your personal chatbot assistant.",
                bot_name TEXT DEFAULT "Hal-E",
                board_path TEXT DEFAULT "../polybot.board",
                debug_mode INTEGER DEFAULT 0
            """,
            DatabaseConfig.sessions.value: """
                session_id TEXT PRIMARY KEY, 
                username_ TEXT, 
                email TEXT, 
                ip TEXT, 
                active_session INTEGER DEFAULT 1
            """,
            DatabaseConfig.chat_history.value: """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, 
                date TEXT, 
                time TEXT, 
                role TEXT, 
                content TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            """,
            DatabaseConfig.board.value: """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, 
                current_card_id TEXT,
                board TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            """,
            DatabaseConfig.chatbot_configs.value: """
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, 
                model TEXT,
                name TEXT,
                personality TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            """,
        }

        for table_name, table_schema in tables.items():
            DBOperations.create_table(table_name, table_schema)

        # delete previous configuration and set default values
        DBOperations.execute_query(f"DELETE FROM {DatabaseConfig.global_.value}")
        DBOperations.execute_query(
            f"INSERT INTO {DatabaseConfig.global_.value} DEFAULT VALUES"
        )

    @staticmethod
    def delete_user_data(session_id: str):
        """
        Remove all user data from the database.

        Args:
            session_id (str): The ID of the current session.
        """
        try:
            DBSessions.delete_session(session_id)
            DBHistory.delete_history(session_id)
            DBBoard.delete_board(session_id)
            DBChatbotConfig.delete_config(session_id)
        except Exception as e:
            DBOperations.logger.error(f"error deleting session {session_id}: {e}")
        else:
            DBOperations.logger.info(f"deleted session {session_id}")

    @staticmethod
    def delete_database():
        """
        Delete the sqlite3 database.
        """
        Path.unlink(DatabaseConfig.db_file.value, missing_ok=True)


class DBGlobal:
    # ------------------------------------------------------------------------------------------
    # GLOBAL TABLE
    # ------------------------------------------------------------------------------------------
    logger = logging.getLogger(__name__)

    @staticmethod
    def get_config():
        """
        Get config from db.
        """
        data = DBOperations.execute_query(
            f"SELECT port, skip_intro, intro_wide, intro_narrow, bot_name, board_path, debug_mode FROM {DatabaseConfig.global_.value}",
            fetchone=True,
        )

        if data:
            keys = [
                "port",
                "skip_intro",
                "intro_wide",
                "intro_narrow",
                "bot_name",
                "board_path",
                "debug_mode",
            ]
            return dict(zip(keys, data))
        return None

    @staticmethod
    def set_config(**kwargs):
        """
        Set config in db. Can include the keys:
        - port: int
        - intro_wide: str
        - intro_narrow: str
        - bot_name: str
        - board_path: str
        - debug_mode: int
        """
        if not kwargs:
            return

        set_clause = ", ".join([f"{key} = ?" for key in kwargs])
        DBOperations.execute_query(
            query=f"UPDATE {DatabaseConfig.global_.value} SET {set_clause}",
            params=tuple(kwargs.values()),
        )


class DBSessions:
    # ------------------------------------------------------------------------------------------
    # SESSIONS TABLE
    # ------------------------------------------------------------------------------------------
    logger = logging.getLogger(__name__)

    @staticmethod
    def add_session(username: str, useremail: str, userip: str) -> str:
        """
        Add a session to the databaseConfig.

        Args:
            username (str): The username of the user.
            email (str): The email of the user.
            ip (str): The IP address of the user.

        Returns:
            str: The ID of the current session.
        """
        session_id = str(uuid.uuid4())
        DBOperations.execute_query(
            query=f"""
            INSERT INTO {DatabaseConfig.sessions.value} (session_id, username_, email, ip) VALUES (?,?,?,?)
            """,
            params=(session_id, username, useremail, userip),
        )

        return session_id

    @staticmethod
    def is_active_session(session_id: str) -> bool:
        """
        Check if a session is active. The column active_session is set to 1 if the session is active, 0 otherwise.
        This function returns the boolean value of the column.

        Args:
            session_id (str): The ID of the current session.

        Returns:
            bool: True if the session is active, False otherwise.
        """
        data = DBOperations.execute_query(
            query=f"SELECT active_session FROM {DatabaseConfig.sessions.value} WHERE session_id =?",
            params=session_id,
            fetchone=True,
        )

        if data:
            return bool(data[0])
        return False

    @staticmethod
    def get_session_data(session_id: str) -> dict | None:
        """
        Get session data from db.

        Args:
            session_id (str): The ID of the current session.

        Returns:
            dict | None: The session data if found. None otherwise.
        """
        data = DBOperations.execute_query(
            query=f"SELECT session_id, username_, email, ip, active_session FROM {DatabaseConfig.sessions.value} WHERE session_id =?",
            params=session_id,
            fetchone=True,
        )

        if data:
            keys = [
                "session_id",
                "username",
                "email",
                "ip",
                "active_session",
            ]
            return dict(zip(keys, data))
        return None

    @staticmethod
    def get_active_session_ids() -> list:
        """
        Retrieves all active session IDs from the database.

        Returns:
            list: A list of all active session IDs.
        """
        data = DBOperations.execute_query(
            query=f"SELECT session_id FROM {DatabaseConfig.sessions.value} WHERE active_session=1",
            fetchall=True,
        )

        if data:
            return [item[0] for item in data]
        else:
            return []

    @staticmethod
    def deactivate_session(session_id: str):
        """
        Deactivate a session in the database: set the active_session column to 0.

        Args:
            session_id (str): The ID of the current session.
        """
        DBOperations.execute_query(
            query=f"UPDATE {DatabaseConfig.sessions.value} SET active_session = 0 WHERE session_id =?",
            params=session_id,
        )

    @staticmethod
    def delete_session(session_id: str):
        """
        Delete a session from the database.

        Args:
            session_id (str): The ID of the current session.
        """
        DBOperations.execute_query(
            query=f"DELETE FROM {DatabaseConfig.sessions.value} WHERE session_id =?",
            params=session_id,
        )


class DBHistory:
    # ------------------------------------------------------------------------------------------
    # CHAT HISTORY TABLE
    # ------------------------------------------------------------------------------------------
    @staticmethod
    def add_history_item(session_id: str, role: str, message: str):
        """
        Add an item to the chat history in the databaseConfig.

        Args:
            session_id (str): The ID of the current session.
            role (str): The role of the sender ('user' or 'bot').
            message (str): The message content.
        """
        date = datetime.now().strftime("%Y-%m-%d")
        time = datetime.now().strftime("%H:%M:%S")

        DBOperations.execute_query(
            query=f"INSERT INTO {DatabaseConfig.chat_history.value} (session_id, date, time, role, content) VALUES (?,?,?,?,?)",
            params=(session_id, date, time, role, message),
        )

    @staticmethod
    def get_history(session_id: str) -> list | None:
        """
        Get chat history from db.

        Args:
            session_id (str): The ID of the current session.

        Returns:
            list | None: The chat history if found. None otherwise.
        """
        data = DBOperations.execute_query(
            query=f"SELECT date, time, role, content FROM {DatabaseConfig.chat_history.value} WHERE session_id =?",
            params=session_id,
        )

        if data:
            keys = ["date", "time", "role", "content"]
            return [dict(zip(keys, item)) for item in data]
        return None

    @staticmethod
    def delete_history(session_id: str):
        """
        Delete chat history from db.

        Args:
            session_id (str): The ID of the current session.
        """
        DBOperations.execute_query(
            query=f"DELETE FROM {DatabaseConfig.chat_history.value} WHERE session_id =?",
            params=session_id,
        )


class DBBoard:
    # ------------------------------------------------------------------------------------------
    # BOARD TABLE
    # ------------------------------------------------------------------------------------------
    logger = logging.getLogger(__name__)

    @staticmethod
    def add_board(session_id: str, board: dict, cid: str):
        """
        Add a board to the database.

        Args:
            session_id (str): The ID of the current session.
            board (dict): The board.
            cid (str): The ID of the current chat card.
        """
        board_str = json.dumps(board)

        DBOperations.execute_query(
            query=f"INSERT INTO {DatabaseConfig.board.value} (session_id, board, current_card_id) VALUES (?,?,?)",
            params=(session_id, board_str, cid),
        )

        DBBoard.logger.debug(f"Added board to database for session {session_id}")

    @staticmethod
    def get_board(session_id: str) -> dict | None:
        """
        Get board from db.

        Args:
            session_id (str): The ID of the current session.

        Returns:
            dict | None: The board if found. None otherwise.
        """
        data = DBOperations.execute_query(
            query=f"SELECT board FROM {DatabaseConfig.board.value} WHERE session_id =?",
            params=session_id,
            fetchone=True,
        )

        try:
            if data:
                DBBoard.logger.debug(
                    f"fetched board from database for session {session_id}"
                )
                return json.loads(data[0])
        except JSONDecodeError as e:
            DBBoard.logger.error(
                f"unable to decode board for session {session_id}: {e}"
            )
            return None

    @staticmethod
    def has_board(session_id) -> bool:
        """
        Debug method. Check if a board exists in the database for the session_id

        Args:
            session_id (str): The ID of the current session.

        Returns:
            bool: True if a board exists, False otherwise.
        """
        count = DBOperations.execute_query(
            query=f"SELECT COUNT(*) FROM {DatabaseConfig.board.value} WHERE session_id =?",
            params=session_id,
            fetchone=True,
        )

        return count[0] > 0

    @staticmethod
    def get_all_session_ids_with_boards() -> list | None:
        """
        Debug method. Returns all session_ids that have boards

        Returns:
            list | None: List of session_ids if found. None otherwise.
        """
        data = DBOperations.execute_query(
            query=f"SELECT session_id FROM {DatabaseConfig.board.value}",
        )

        if data:
            return [item[0] for item in data]
        return None

    @staticmethod
    def get_current_card_id(session_id: str) -> str | None:
        """
        Get current card id from db.

        Args:
            session_id (str): The ID of the current session.

        Returns:
            str | None: The current card id if found. None otherwise.
        """
        data = DBOperations.execute_query(
            query=f"SELECT current_card_id FROM {DatabaseConfig.board.value} WHERE session_id =?",
            params=session_id,
            fetchone=True,
        )

        if data:
            DBBoard.logger.debug(f"Current card id for session {session_id}: {data}")
            return data[0]

        DBBoard.logger.debug(f"No current card id found for session {session_id}")
        return None

    @staticmethod
    def update_board(session_id: str, role: str, message: str, attachment: str = ""):
        """
        Updates the board for session_id in the database.

        Args:
            session_id (str): The ID of the current session.
            role (str): The role of the sender as defined in ChatbotRoles class.
            message (str): The message content.
        """
        # get the board via session_id
        board = DBBoard.get_board(session_id)
        # get the latest card_id
        ccid = DBBoard.get_current_card_id(session_id)

        # update board and current_card_id
        update = {}
        if board and ccid:
            update = BoardManager.update_board(board, ccid, role, message, attachment)

        updated_board = json.dumps(update.get("board"))
        updated_ccid = update.get("new_card_id")

        # update database with updated board and current_card_id
        DBOperations.execute_query(
            query=f"UPDATE {DatabaseConfig.board.value} SET board =?, current_card_id =? WHERE session_id =?",
            params=(updated_board, updated_ccid, session_id),
        )

    @staticmethod
    def delete_board(session_id: str):
        """
        Delete a board from the database.

        Args:
            session_id (str): The ID of the current session.
        """
        DBOperations.execute_query(
            query=f"DELETE FROM {DatabaseConfig.board.value} WHERE session_id =?",
            params=session_id,
        )


class DBChatbotConfig:
    logger = logging.getLogger(__name__)

    @staticmethod
    def add(session_id: str, model: str, name: str, personality: str):
        """
        Add a chatbot configuration.

        Args:
            session_id (str): The ID of the current session.
            model (str): The model of the chatbot.
            name (str): The name of the chatbot.
            personality (str): The personality of the chatbot.
        """
        DBOperations.execute_query(
            query=f"INSERT INTO {DatabaseConfig.chatbot_configs.value} (session_id, model, name, personality) VALUES (?,?,?,?)",
            params=(session_id, model, name, personality),
        )
        DBChatbotConfig.logger.debug(
            f"Added chatbot configuration to database for session {session_id}"
        )

    @staticmethod
    def get(session_id: str) -> tuple | None:
        """
        Get a chatbot configuration via session_id

        Args:
            session_id (str): The ID of the current session.

        Returns:
            tuple | None: The chatbot configuration if found. None otherwise.
        """
        data = DBOperations.execute_query(
            query=f"SELECT model, name, personality FROM {DatabaseConfig.chatbot_configs.value} WHERE session_id =?",
            params=session_id,
            fetchone=True,
        )

        if data:
            return data
        return None

    @staticmethod
    def delete_config(session_id: str):
        """
        Delete a chatbot config from the database.

        Args:
            session_id (str): The ID of the current session.
        """
        DBOperations.execute_query(
            query=f"DELETE FROM {DatabaseConfig.chatbot_configs.value} WHERE session_id =?",
            params=session_id,
        )
