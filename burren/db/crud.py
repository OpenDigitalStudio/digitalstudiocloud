# Copyright (c) 2020 Erno Kuvaja OpenDigitalStudio.net
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from datetime import datetime
from datetime import timedelta
import uuid

from sqlalchemy.orm import Session

from burren.db import models
from burren.db import schemas
from burren.utils import pwdtools


def get_user_by_id(db: Session, user_id: str):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_name(db: Session, name: str):
    return db.query(models.User).filter(models.User.name == name).first()


def get_user(db: Session, hint: str):
    for f in [get_user_by_id, get_user_by_email, get_user_by_name]:
        db_user = f(db, hint)
        if db_user:
            return db_user
    return None


def list_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwdtools.salted_hash(user.password)
    db_user = models.User(id=str(uuid.uuid4()),
                          name=user.name,
                          fullname=user.fullname,
                          email=user.email,
                          hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_from_token(db: Session, token: str):
    db_token = db.query(models.Token).filter(models.Token.id == token).first()
    if not db_token:
        return None
    if db_token.expires_at < datetime.now():
        return False
    db_token.expires_at = datetime.now() + timedelta(minutes=30)
    db.commit()
    return get_user_by_id(db, db_token.user_id)


def create_token(db: Session, user_id: str):
    token_id = str(uuid.uuid4())
    created_at = datetime.now()
    expires_at = created_at + timedelta(minutes=30)
    db_token = models.Token(id=token_id,
                            created_at=created_at,
                            expires_at=expires_at,
                            user_id=user_id)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def list_user_tokens(db: Session, user_id: str,
                     skip: int = 0, limit: int = 100):
    return db.query(models.Token).filter(
            models.Token.user_id == user_id).offset(skip).limit(limit).all()


def delete_user_token(db: Session, token_id: str, user_id: str):
    db_token = db.query(models.Token).filter(
            models.Token.id == token_id).first()
    if db_token and getattr(db_token, 'user_id', "") == user_id:
        db.delete(db_token)
        db.commit()
        return True
    return False


def get_session(db: Session, session_id: str):
    return db.query(models.Session).filter(
            models.Session.id == session_id).first()


def list_sessions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Session).offset(skip).limit(limit).all()


def create_session(db: Session, session: schemas.SessionCreate):
    session_id = str(uuid.uuid4())
    new_session = session.dict()
    members = [new_session.owner]
    tags = []
    if getattr(new_session, 'members', None):
        members += new_session.pop("members")
    if getattr(new_session, 'tags', None):
        tags = new_session.pop("tags")
    db_session = models.Session(id=session_id,
                                **new_session)
    for member in members:
        db_member = get_user(db, member)
        if db_member:
            db_session.members.append(db_member)
    for tag in tags:
        db_tag = get_tag(db, tag)
        if db_tag:
            db_session.tags.append(db_tag)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_image(db: Session, image_id: str):
    return db.query(models.Image).filter(models.Image.id == image_id).first()


def list_images(db: Session, skip: int = 0,
                limit: int = 100, qfilter: str = '*'):
    return db.query(models.Image).filter(
            models.Image.owner_id == qfilter).offset(skip).limit(limit).all()


def create_image(db: Session, image: schemas.ImageCreate, owner: str):
    image_id = str(uuid.uuid4())
    new_image = image.dict()
    new_image['owner_id'] = owner
    tags = []
    image_models = []
    if 'image_data' in new_image.keys():
        new_image['image'] = new_image.pop("image_data")
    if 'tags' in new_image.keys():
        tags = new_image.pop("tags")
    if 'model_ids' in new_image.keys():
        image_models = new_image.pop("model_ids")
    db_image = models.Image(id=image_id,
                            **new_image)
    for tag in tags:
        db_tag = get_tag(db, tag)
        if db_tag:
            db_image.tags.append(db_tag)
    for model in image_models:
        db_model = get_user(db, model)
        if db_model:
            db_image.models.append(db_model)
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image


def get_tag(db: Session, tag_name: str):
    return db.query(models.Tag).filter(models.Tag.name == tag_name).first()


def list_tags(db: Session, skip: int = 0, limit: int = 0):
    return db.query(models.Tag).offset(skip).limit(limit).all()


def create_tag(db: Session, tag: schemas.TagCreate):
    db_tag = models.Tag(**tag.dict())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


def get_objectdata(db: Session, object_id: str):
    return db.query(models.ObjectData).filter(
            models.ObjectData.id == object_id).first()


def list_objectdata(db: Session, skip: int = 0, limit: int = 0):
    db.query(models.ObjectData).offset(skip).limit(limit).all()


def create_objectdata(db: Session,
                      objectdata: schemas.ObjectData):
    object_id = str(uuid.uuid4())
    db_object = models.Session(id=object_id,
                               **objectdata.dict())
    db.add(db_object)
    db.commit()
    db.refresh(db_object)
    return db_object
