from datetime import datetime, date

from sqlalchemy import String, Integer, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String, unique=True, index=True)  # whatsapp:+22XXXXXXXXX
    name: Mapped[str] = mapped_column(String)
    station: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")
    responses: Mapped[list["Response"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    check_date: Mapped[date] = mapped_column(Date, default=date.today)
    current_question: Mapped[int] = mapped_column(Integer, default=0)
    awaiting_answer: Mapped[bool] = mapped_column(Boolean, default=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    user: Mapped["User"] = relationship(back_populates="sessions")


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    check_date: Mapped[date] = mapped_column(Date, default=date.today)
    station: Mapped[str] = mapped_column(String)

    pompes_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    etat_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    monnaie_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    besoin_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    incident_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    confirmation: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    status: Mapped[str | None] = mapped_column(String, nullable=True)  # OK / PROBLEME
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    user: Mapped["User"] = relationship(back_populates="responses")
