from datetime import datetime, date

from sqlalchemy import String, Integer, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    station: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    sessions: Mapped[list["CheckSession"]] = relationship(back_populates="user")


class Question(Base):
    """Question posee aux gerants via le chatbot."""
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    problem_type: Mapped[str | None] = mapped_column(String, nullable=True)  # maintenance, exploitation, etc.
    problem_label: Mapped[str | None] = mapped_column(String, nullable=True)
    schedule_type: Mapped[str] = mapped_column(String, default="quotidien")  # quotidien / occasionnel
    position: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    answers: Mapped[list["Answer"]] = relationship(back_populates="question")


class CheckSession(Base):
    """Session de conversation chatbot avec un gerant."""
    __tablename__ = "check_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    check_date: Mapped[date] = mapped_column(Date, default=date.today)
    check_type: Mapped[str] = mapped_column(String, default="quotidien")  # quotidien / occasionnel
    question_ids: Mapped[str] = mapped_column(String)  # "1,3,5,7" - IDs des questions a poser
    current_index: Mapped[int] = mapped_column(Integer, default=0)  # index dans question_ids
    awaiting_answer: Mapped[bool] = mapped_column(Boolean, default=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str | None] = mapped_column(String, nullable=True)  # OK / PROBLEME
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    user: Mapped["User"] = relationship(back_populates="sessions")
    answers: Mapped[list["Answer"]] = relationship(back_populates="session", cascade="all, delete-orphan")

    def get_question_id_list(self) -> list[int]:
        """Retourne la liste des IDs de questions."""
        if not self.question_ids:
            return []
        return [int(x) for x in self.question_ids.split(",")]

    def get_current_question_id(self) -> int | None:
        """Retourne l'ID de la question courante."""
        ids = self.get_question_id_list()
        if self.current_index < len(ids):
            return ids[self.current_index]
        return None

    def total_questions(self) -> int:
        return len(self.get_question_id_list())


class Answer(Base):
    """Reponse OUI/NON a une question specifique."""
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("check_sessions.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    answer: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    session: Mapped["CheckSession"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="answers")
