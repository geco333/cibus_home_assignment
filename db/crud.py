from typing import List

from sqlalchemy.orm import Session

from db import models
from schemas import user, message
from schemas.message import Vote


async def create_user(db: Session, request_user: user.RequestUser) -> models.User:
    db_user = models.User(username=request_user.username,
                          hashed_password=request_user.password)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


async def get_user_by_name(db: Session, username: str) -> models.User | None:
    return db.query(models.User).filter(models.User.username == username).first()


async def login_user(db: Session, db_user: models.User):
    db_user.logged_in = True

    db.commit()
    db.refresh(db_user)
    db.close()


async def logout_user(db: Session, db_user: models.User):
    db_user.logged_in = False

    db.commit()
    db.refresh(db_user)
    db.close()


async def get_all_messages(db: Session) -> List[models.Message]:
    return db.query(models.Message).all()


async def post_message(db: Session,
                 new_message: message.MessageBase,
                 db_user: models.User):
    new_message = models.Message(
        author_id=db_user.id,
        message=new_message.message,
    )

    db.add(new_message)

    db.commit()
    db.close()


async def get_message(db: Session, message_id: int) -> models.Message:
    return db.query(models.Message).filter(models.Message.id == message_id).first()


async def vote_for_message(db: Session,
                     db_message: models.Message,
                     vote: Vote):
    if vote is Vote.UP:
        db_message.vote_count += 1
    elif vote is Vote.DOWN:
        db_message.vote_count -= 1

    db.commit()
    db.refresh(db_message)
    db.close()


async def delete_message(db: Session,
                   message_id: int):
    db.query(models.Message) \
        .filter(models.Message.id == message_id) \
        .delete()

    db.commit()
    db.close()


async def get_user_messages(db: Session,
                      db_user: models.User) -> List[models.Message]:
    return db.query(models.Message).filter(models.Message.author_id == db_user.id).all()
