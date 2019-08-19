#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlalchemy
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.orm import mapper, sessionmaker, relationship, scoped_session
import json
import engine
import threading
from bot_utils import bot_methods

# Создание объекта соединения с нашей базой данных
engn = sqlalchemy.create_engine('sqlite:///chat_data.db', echo=False)

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
                    Column('buildings', String),
                    Column('current_war_data', String),
                    Column('daily_dungeon_sponsored', Integer))

users_table = Table('users', metadata,
                    Column('id', Integer, primary_key=True),
                    Column('user_id', Integer, unique=True),
                    Column('attacked', Integer, default=0),
                    Column('experience', String),
                    Column('unit_dict', String))

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
                 buildings='{}',
                 current_war_data='{"attacked_by_chats": [], "chats_besieged": []}',
                 daily_dungeon_sponsored=0):
        self.chat_id = chat_id
        self.name = name
        self.data = data
        self.receipts = receipts
        self.armory = armory
        self.used_armory = used_armory
        self.resources = resources
        self.buildings = buildings
        self.current_war_data = current_war_data
        self.daily_dungeon_sponsored = daily_dungeon_sponsored
    # Пользователи

    def add_user(self, user_id):
        session.add(self.pyosession.user_class(user_id, self.chat_id))
        try:
            session.commit()
        except Exception as e:
            import traceback
            bot_methods.err(traceback.format_exc())
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
        if isinstance(receipt, engine.ChatContainer) or isinstance(receipt, engine.Container):
            container += receipt
        else:
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

    def get_current_war_data(self):
        return json.loads(self.current_war_data)

    def set_current_war_data(self, war_data_dict):
        self.current_war_data = json.dumps(war_data_dict)
        session.commit()

    def get_buildings(self):
        return json.loads(self.buildings)

    def set_buildings(self, building_dict):
        self.buildings = json.dumps(building_dict)
        session.commit()


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

    def get_income(self):
        return 10

    # Ресурсы

    def add_resources(self, value):
        self.resources += value
        session.commit()

    def __repr__(self):
        return "<Chat('%s', '%s', '%s', '%s', '%s')>" % (self.chat_id, self.name, self.data,
                                                               self.receipts, self.armory)


class SqlUser(object):
    pyosession = None

    def __init__(self, user_id, attacked=0, experience=0, unit_dict='{"unit":"human"}'):
        self.user_id = user_id
        self.attacked = attacked
        self.experience = experience
        self.unit_dict = unit_dict

    def __repr__(self):
        return "<User('%s')>" % (self.user_id)

    def refresh(self):
        self.attacked = 0
        session.commit()

    def add_experience(self, experience):
        self.experience += experience
        session.commit()

    def get_unit_dict(self):
        return json.loads(self.unit_dict)

    def set_unit_dict(self, unit_dict):
        self.unit_dict = json.dumps(unit_dict)
        session.commit()

    def get_abilities(self):
        return json.loads(self.unit_dict)['abilities']

    def set_abilities(self, abilities):
        unit_dict = self.get_unit_dict()
        unit_dict['abilities'] = abilities
        self.set_unit_dict(unit_dict)
        session.commit()

    def reset_abilities(self):
        self.set_unit_dict({"unit": "human", "abilities": []})



class Pyossession:
    def __init__(self, chat_class, user_class, non_primary=False):
        self.chat_class = chat_class
        self.user_class = user_class
        self.non_primary = non_primary
        chat_class.pyossession = self
        user_class.pyossession = self

    def start_session(self):
        mapper(self.chat_class, chats_table, non_primary=self.non_primary)
        mapper(self.user_class, users_table, non_primary=self.non_primary)

    def create_chat(self, chat_id, name):
        session.add(self.chat_class(chat_id, name, '{}', '{}', '{}', '{}'))
        try:
            session.commit()
        except Exception as e:
            print(e)
            session.rollback()
            pass

    def create_user(self, chat_id):
        session.add(self.user_class(chat_id))
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

    def get_users(self):
        users = session.query(self.user_class).all()
        return users


