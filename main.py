import logging
from datetime import datetime, timedelta
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import ValidationError
from sqlalchemy.orm import Session

from db import crud, models
from db.database import SessionLocal, Base, engine
from schemas import user, message

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s',
                    level=logging.DEBUG)

Base.metadata.create_all(bind=engine)

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_db():
    db = SessionLocal()

    try:
        yield db
    except ValidationError as err:
        logging.error(err)
    finally:
        db.close()


def create_access_token(data: dict,
                        expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def validate_password(password: str, hashed_password: bytes) -> bool:
    return pwd_context.verify(bytes(password, "utf-8"), hashed_password)


async def validate_token(token: Annotated[str, Depends(oauth2_scheme)],
                         db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db_user = crud.get_user_by_name(db, username=username)

    if db_user is None:
        raise credentials_exception

    return db_user


def authenticate_user(db, username: str, password: str) -> bool | models.User:
    db_user = crud.get_user_by_name(db, username)

    if not db_user:
        return False

    if not validate_password(password, db_user.hashed_password):
        return False

    return db_user


@app.post("/register", status_code=201)
def create_user(request_user: user.RequestUser,
                db: Session = Depends(get_db)):
    logging.info(f"Received new user registration.")
    logging.info(f"Checking to see if the username already exists in the database ...")

    db_user = crud.get_user_by_name(db, username=request_user.username)

    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    request_user.password = pwd_context.hash(request_user.password)

    logging.info("Adding new user to database ...")
    crud.create_user(db=db, user=request_user)

    logging.info("Successfully added new user to database.")

    return "Successfully added new user to database."


@app.post("/login")
def login_user(request_user: user.RequestUser,
               db: Session = Depends(get_db)):
    db_user = crud.get_user_by_name(db, request_user.username)

    if not db_user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if validate_password(request_user.password, db_user.hashed_password) is False:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if db_user.logged_in:
        return "User already logged in."

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": request_user.username},
                                       expires_delta=access_token_expires)

    crud.login_user(db, db_user)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/logout")
async def logout_user(token: str = Depends(oauth2_scheme),
                      db: Session = Depends(get_db)):
    db_user = await validate_token(token, db)

    crud.logout_user(db, db_user)

    return "User logout successful."


@app.get("/messages")
async def get_all_messages(token: str = Depends(oauth2_scheme),
                           db: Session = Depends(get_db)):
    await validate_token(token, db)

    all_messages = crud.get_all_messages(db)

    return all_messages


@app.post("/messages", status_code=201)
async def post_message(new_message: message.MessageBase,
                       token: str = Depends(oauth2_scheme),
                       db: Session = Depends(get_db)):
    db_user = await validate_token(token, db)

    all_messages = crud.post_message(db, new_message, db_user)

    return "Message posted successfully."


@app.post("/messages/{message_id}/vote", status_code=201)
async def vote_for_message(message_id: int,
                           vote: message.MessageVote,
                           token: str = Depends(oauth2_scheme),
                           db: Session = Depends(get_db)):
    await validate_token(token, db)

    crud.vote_for_message(db, message_id, vote.vote)

    return "Vote registered successfully."


@app.delete("/messages/{message_id}")
async def delete_message(message_id: int,
                         token: str = Depends(oauth2_scheme),
                         db: Session = Depends(get_db)):
    await validate_token(token, db)

    db_message = crud.get_message(db, message_id)

    if db_message is None:
        raise HTTPException(status_code=400, detail="Cannot find message ID.")

    crud.delete_message(db, message_id)

    return "Message deleted successfully."


@app.get("/user/messages")
async def delete_message(token: str = Depends(oauth2_scheme),
                         db: Session = Depends(get_db)):
    db_user = await validate_token(token, db)

    user_messages = crud.get_user_messages(db, db_user)

    if user_messages is None:
        raise HTTPException(status_code=200, detail="User has no messages.")

    return user_messages


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
