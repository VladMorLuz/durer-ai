"""
core/session.py
Gerencia o estado persistente do Dürer AI usando SQLite.
Guarda histórico de conversas, tentativas de desenho e feedback.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class Session:
    """
    Interface com o banco de dados local.
    Cada instância mantém uma conexão aberta durante a sessão.
    """

    def __init__(self, db_path: str = "state.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
        self._initialize_schema()
        logger.info("Sessão iniciada. Banco: %s", db_path)

    def _initialize_schema(self) -> None:
        """Cria as tabelas se não existirem (safe — não apaga dados existentes)."""
        cursor = self.conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                role        TEXT NOT NULL,      -- 'user' ou 'assistant'
                content     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS drawing_attempts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT NOT NULL,
                prompt          TEXT NOT NULL,   -- O que foi pedido
                output_path     TEXT,            -- Caminho do arquivo salvo
                critic_score    REAL,            -- Nota automática (0.0 a 1.0)
                user_feedback   TEXT,            -- Feedback manual seu
                metadata        TEXT             -- JSON com detalhes extras
            );

            CREATE TABLE IF NOT EXISTS knowledge_entries (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                source      TEXT NOT NULL,       -- Nome do arquivo original
                content     TEXT NOT NULL,       -- Texto extraído
                summary     TEXT                 -- Resumo gerado pela IA
            );

            CREATE TABLE IF NOT EXISTS reports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                report_type TEXT NOT NULL,       -- 'study' ou 'drawing'
                source_ref  TEXT,                -- ID da entrada ou tentativa relacionada
                content     TEXT NOT NULL
            );
        """)

        self.conn.commit()
        logger.debug("Schema do banco verificado/criado.")

    # ── Chat ──────────────────────────────────────────────────────────────────

    def save_message(self, role: str, content: str) -> int:
        """Salva uma mensagem do chat. Retorna o ID inserido."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO chat_messages (timestamp, role, content) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), role, content),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_chat_history(self, limit: int = 50) -> list[dict]:
        """Retorna as últimas `limit` mensagens do chat."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT role, content FROM chat_messages ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    # ── Tentativas de desenho ─────────────────────────────────────────────────

    def save_attempt(self, prompt: str, output_path: str = None, metadata: dict = None) -> int:
        """Registra uma nova tentativa de desenho. Retorna o ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO drawing_attempts
               (timestamp, prompt, output_path, metadata)
               VALUES (?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                prompt,
                output_path,
                json.dumps(metadata or {}),
            ),
        )
        self.conn.commit()
        attempt_id = cursor.lastrowid
        logger.debug("Tentativa #%d registrada: %s", attempt_id, prompt[:60])
        return attempt_id

    def update_attempt_score(self, attempt_id: int, score: float, feedback: str = None) -> None:
        """Atualiza a nota e feedback de uma tentativa existente."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE drawing_attempts SET critic_score = ?, user_feedback = ? WHERE id = ?",
            (score, feedback, attempt_id),
        )
        self.conn.commit()

    def get_recent_attempts(self, limit: int = 10) -> list[dict]:
        """Retorna as tentativas mais recentes."""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id, timestamp, prompt, output_path, critic_score, user_feedback
               FROM drawing_attempts ORDER BY id DESC LIMIT ?""",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    # ── Relatórios ────────────────────────────────────────────────────────────

    def save_report(self, report_type: str, content: str, source_ref: str = None) -> int:
        """Salva um relatório escrito pela IA."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO reports (timestamp, report_type, source_ref, content) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), report_type, source_ref, content),
        )
        self.conn.commit()
        return cursor.lastrowid

    # ── Utilitários ───────────────────────────────────────────────────────────

    def close(self) -> None:
        """Fecha a conexão com o banco."""
        self.conn.close()
        logger.info("Sessão encerrada.")

    def stats(self) -> dict:
        """Retorna um resumo rápido do estado atual."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chat_messages")
        msgs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drawing_attempts")
        attempts = cursor.fetchone()[0]
        cursor.execute("SELECT AVG(critic_score) FROM drawing_attempts WHERE critic_score IS NOT NULL")
        avg_score = cursor.fetchone()[0]
        return {
            "total_messages": msgs,
            "total_attempts": attempts,
            "average_score": round(avg_score, 3) if avg_score else None,
        }
