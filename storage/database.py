import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Session

logger = logging.getLogger(__name__)

engine = create_engine("sqlite:///world_cup.db", echo=False)


class Base(DeclarativeBase):
    pass


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    post_type = Column(String(20), nullable=False)  # morning / evening / drama
    content = Column(Text, nullable=False)
    facebook_post_id = Column(String(50))
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime)


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False)
    source = Column(String(100))
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    used = Column(Boolean, default=False)


def init_db():
    Base.metadata.create_all(engine)
    logger.info("Database initialized")


def get_session() -> Session:
    return Session(engine)


def is_news_seen(url: str) -> bool:
    with get_session() as session:
        return session.query(NewsItem).filter_by(url=url).first() is not None


def save_news_items(items: list[dict]):
    from sqlalchemy.exc import IntegrityError
    with get_session() as session:
        for item in items:
            try:
                session.add(NewsItem(
                    title=item["title"],
                    url=item["url"],
                    source=item.get("source", ""),
                ))
                session.flush()
            except IntegrityError:
                session.rollback()
        session.commit()


def get_unused_news(limit: int = 10) -> list[NewsItem]:
    with get_session() as session:
        return session.query(NewsItem).filter_by(used=False).order_by(
            NewsItem.fetched_at.desc()
        ).limit(limit).all()


def mark_news_used(news_ids: list[int]):
    with get_session() as session:
        session.query(NewsItem).filter(NewsItem.id.in_(news_ids)).update(
            {"used": True}, synchronize_session=False
        )
        session.commit()


def save_post(post_type: str, content: str) -> int:
    with get_session() as session:
        post = Post(post_type=post_type, content=content)
        session.add(post)
        session.commit()
        session.refresh(post)
        return post.id


def mark_post_published(post_id: int, facebook_post_id: str):
    with get_session() as session:
        post = session.get(Post, post_id)
        if post:
            post.published = True
            post.facebook_post_id = facebook_post_id
            post.published_at = datetime.now(timezone.utc)
            session.commit()
