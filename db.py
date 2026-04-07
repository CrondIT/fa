from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy import (
    Integer,
    String,
    BigInteger,
    DateTime,
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)

# Загрузить переменные из файла .env
load_dotenv()


# ============================================================
# Модель базы данных
# ============================================================

class Base(DeclarativeBase):
    pass


DATABASE_URL = "sqlite+aiosqlite:///.maxbot.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, index=True
    )
    name: Mapped[str] = mapped_column(
        String(50), default="user"
    )
    startdate: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    coindate: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    coins: Mapped[int] = mapped_column(
        Integer, default=0
    )
    giftcoins: Mapped[int] = mapped_column(
        Integer, default=0
    )
    note: Mapped[str] = mapped_column(
        String(150), default=""
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}', coins={self.coins})>"


# ============================================================
# Базовый репозиторий
# ============================================================

class BaseRepository:
    """Базовый репозиторий — обёртка над AsyncSession."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def commit(self) -> None:
        """Сохраняет изменения в базе."""
        await self.session.commit()

    async def refresh(self, instance) -> None:
        """Обновляет атрибуты экземпляра из базы."""
        await self.session.refresh(instance)


# ============================================================
# Репозиторий пользователей
# ============================================================

class UserRepository(BaseRepository):
    """Репозиторий для работы с моделью User."""

    # ---------- чтение ----------

    async def get_by_id(self, userid: int) -> Optional[User]:
        """Возвращает пользователя по id или None."""
        result = await self.session.execute(
            select(User).where(User.id == userid)
        )
        return result.scalar_one_or_none()

    async def exists(self, userid: int) -> bool:
        """Проверяет, существует ли пользователь с данным userid."""
        user = await self.get_by_id(userid)
        return user is not None

    async def get_or_create(
        self,
        userid: int,
        nickname: str = "User",
        coins: int = 0,
        giftcoins: int = 0,
        note: str = "",
    ) -> User:
        """
        Возвращает существующего пользователя или создаёт нового.
        Всегда возвращает объект User.
        """
        user = await self.get_by_id(userid)
        if user:
            return user

        user = User(
            id=userid,
            name=nickname,
            startdate=datetime.now(),
            coindate=datetime.now(),
            coins=coins,
            giftcoins=giftcoins,
            note=note,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    # ---------- создание ----------

    async def create(
        self,
        userid: int,
        nickname: str,
        coins: int = 0,
        giftcoins: int = 0,
        note: str = "",
    ) -> bool:
        """
        Создаёт нового пользователя.
        Возвращает True при успехе, False — если пользователь уже есть.
        """
        if await self.exists(userid):
            print(f"Ошибка: пользователь с userid={userid} уже есть.")
            return False

        now = datetime.now()
        user = User(
            id=userid,
            name=nickname,
            startdate=now,
            coindate=now,
            coins=coins,
            giftcoins=giftcoins,
            note=note,
        )
        self.session.add(user)
        await self.session.commit()
        return True

    # ---------- обновление ----------

    async def add_coins(
        self,
        userid: int,
        coins_delta: int = 0,
        giftcoins_delta: int = 0,
    ) -> bool:
        """
        Добавляет coins / giftcoins к текущему значению
        и обновляет coindate.
        Возвращает True при успехе, False — если пользователь не найден.
        """
        user = await self.get_by_id(userid)
        if not user:
            return False

        user.coins += coins_delta
        user.giftcoins += giftcoins_delta
        user.coindate = datetime.now()

        await self.session.commit()
        return True

    async def set_coins(
        self,
        userid: int,
        coins: int,
        giftcoins: int,
    ) -> bool:
        """
        Устанавливает точные значения coins и giftcoins.
        Возвращает True при успехе, False — если пользователь не найден.
        """
        user = await self.get_by_id(userid)
        if not user:
            return False

        user.coins = coins
        user.giftcoins = giftcoins
        user.coindate = datetime.now()

        await self.session.commit()
        return True

    # ---------- утилиты ----------

    def to_dict(self, user: User) -> dict:
        """Преобразует объект User в словарь."""
        return {
            "id": user.id,
            "userid": user.id,
            "nickname": user.name,
            "startdate": user.startdate,
            "coindate": user.coindate,
            "coins": user.coins,
            "giftcoins": user.giftcoins,
            "note": user.note,
        }


# ============================================================
# Фасад для обратной совместимости (функции-обёртки)
# ============================================================

async def create_database():
    """Создаёт таблицы и системного пользователя."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            user = await repo.get_by_id(0)
            if not user:
                await repo.create(userid=0, nickname="System")

    except Exception as e:
        print(f"Ошибка при создании базы или системного пользователя: {e}")


async def check_user(userid: int) -> bool:
    """Проверяет существование пользователя."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        return await repo.exists(userid)


async def create_user(
    userid: int,
    nickname: str,
    coins: int = 0,
    giftcoins: int = 0,
    note: str = None,
) -> bool:
    """Создаёт пользователя."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        return await repo.create(
            userid=userid,
            nickname=nickname,
            coins=coins,
            giftcoins=giftcoins,
            note=note or "",
        )


async def get_user(userid: int) -> Optional[dict]:
    """Возвращает данные пользователя в виде словаря."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(userid)
        if user:
            return repo.to_dict(user)
        return None


async def change_all_coins(
    userid: int, coins: int, giftcoins: int
) -> bool:
    """Добавляет coins и giftcoins к текущему значению."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        return await repo.add_coins(
            userid=userid,
            coins_delta=coins,
            giftcoins_delta=giftcoins,
        )
