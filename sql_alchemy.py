#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlalchemy
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.orm import mapper, sessionmaker, relationship, scoped_session
import json
import engine
import threading

# Создание объекта соединения с нашей базой данных
engn = sqlalchemy.create_engine('sqlite:///chat_data.db', echo=True)

session_factory = sessionmaker(bind=engn)
Session = scoped_session(session_factory)
session = Session()

# Создание таблицы чатов
metadata = MetaData()
chats_table = Table('chats', metadata,
                    Column('id', Integer, primary_key=True),
                    Column('chat_id', String, unique=True),
                    Column('name', String),
                    Column('data', String),
                    Column('receipts', String),
                    Column('resources', Integer),
                    Column('armory', String),
                    Column('used_armory', String),
                    Column('daily_income', Integer),
                    Column('construction_lvl', Integer),
                    Column('conquerors_list', String),
                    Column('conquered_list', String))

users_table = Table('users', metadata,
                    Column('id', Integer, primary_key=True),
                    Column('user_id', Integer, unique=True),
                    Column('chat_id', String, ForeignKey('chats.chat_id')))

# Занесение таблицы в базу данных с помощью metadata через engine
metadata.create_all(engn)


# Создаение объекта чата
class SqlChat(object):
    pyosession = None

    def __init__(self,
                 chat_id,
                 name=None,
                 data=None,
                 receipts='{"knife": "inf", "spear": "inf", "hatchet": "inf"}',
                 armory=None,
                 used_armory=None,
                 resources=100,
                 daily_income=10,
                 construction_lvl=1,
                 conquerors_list='[]',
                 conquered_list='[]'):
        self.chat_id = chat_id
        self.name = name
        self.data = data
        self.receipts = receipts
        self.armory = armory
        self.used_armory = used_armory
        self.resources = resources
        self.daily_income = daily_income
        self.construction_lvl = construction_lvl
        self.conquerors_list = conquerors_list
        self.conquered_list = conquered_list

    # Пользователи

    def add_user(self, user_id):
        session.add(self.pyosession.user_class(user_id, self.chat_id))
        try:
            session.commit()
        except Exception as e:
            print(e)
            session.rollback()
            pass

    def user_is_member(self, user_id):
        user = session.query(self.pyosession.user_class).filter_by(user_id=user_id).one()
        if user.chat_id == self.chat_id:
            return True
        return False

    # Рецепты

    def add_receipt(self, receipt):
        container = engine.ChatContainer()
        container.from_json(self.receipts)
        container.put(receipt)
        self.receipts = container.to_json()
        session.commit()

    def delete_receipt(self, receipt):
        container = engine.ChatContainer()
        container.from_json(self.receipts)
        container.remove(receipt)
        self.receipts = container.to_json()
        session.commit()

    def get_receipts(self):
        return json.loads(self.receipts)

    # Предметы
    # Обработка предметов
    def add_item(self, item, value=1):
        container = engine.ChatContainer()
        container.from_json(self.armory)
        container.put(item, value=value)
        self.armory = container.to_json()
        session.commit()

    # Получить список вооружения в чате в виде словаря для Container()
    def get_armory(self):
        return json.loads(self.armory)

    # Получить список не потраченного вооружения в чате в виде словаря для Container()
    def get_free_armory(self):
        armory = dict(self.get_armory())
        used_armory = json.loads(self.used_armory)
        for key in used_armory:
            armory[key] -= used_armory[key]
            if armory[key] < 1:
                del armory[key]
        return armory

    def use_item(self, item):
        container = engine.ChatContainer()
        container.from_json(self.used_armory)
        print(item)
        container.put(item)
        print(self.used_armory)
        self.used_armory = container.to_json()
        session.commit()

    def delete_item(self, item, value=1):
        container = engine.ChatContainer()
        container.from_json(self.armory)
        container.remove(item, value=value)
        self.armory = container.to_json()
        session.commit()

    def delete_used_item(self, item, value=1):
        container = engine.ChatContainer()
        container.from_json(self.used_armory)
        container.remove(item, value=value)
        self.used_armory = container.to_json()
        session.commit()

    def clear_used_items(self):
        self.used_armory = '{}'
        session.commit()

    def add_conqueror(self, chat_id):
        conquerors = json.loads(self.conquerors_list)
        conquerors.append(str(chat_id))
        self.conquerors_list = json.dumps(conquerors)
        session.commit()

    def get_income(self):
        imcome_receivers = []

    # Ресурсы

    def add_resources(self, value):
        self.resources += value
        session.commit()

    def __repr__(self):
        return "<Chat('%s', '%s', '%s', '%s', '%s', '%s')>" % (self.chat_id, self.name, self.users, self.data,
                                                               self.receipts, self.armory)


class SqlUser(object):
    pyosession = None

    def __init__(self, user_id, chat_id):
        self.user_id = user_id
        self.chat_id = chat_id

    def __repr__(self):
        return "<User('%s', '%s')>" % (self.chat_id, self.user_id)

    def get_armory(self):
        return self.chat.armory


class Pyossession:
    def __init__(self, chat_class, user_class):
        self.chat_class = chat_class
        self.user_class = user_class
        chat_class.pyossession = self
        user_class.pyossession = self

    def start_session(self):
        mapper(self.chat_class, chats_table, properties={'users': relationship(self.user_class)})
        mapper(self.user_class, users_table, properties={'chat': relationship(self.chat_class)})

    def create_chat(self, chat_id, name):
        session.add(self.chat_class(chat_id, name, '{}', '{}', '{}', '{}'))
        try:
            session.commit()
        except Exception as e:
            print(e)
            session.rollback()
            pass

    def get_chat(self, chat_id):
        print('Get_chat from thread number {}'.format(threading.current_thread()))
        chat = session.query(self.chat_class).filter_by(chat_id=chat_id).one()
        chat.pyosession = self
        if chat:
            return chat
        else:
            return None

    def get_chats(self):
        chats = session.query(self.chat_class).all()
        return chats

    def get_user(self, user_id):
        user = session.query(self.user_class).filter_by(user_id=user_id).one()
        user.pyosession = self
        if user:
            return user
        else:
            return None


