import sys
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
#from himlarcli import utils
from himlarcli.client import Client

class Resource():

    """ Resource object """
    def update(self, attributes):
        for k, v in attributes.items():
            setattr(self, k, v)

    @classmethod
    def create(cls, data):
        new_data = {}
        for k, v in data.items():
            if k == 'id':
                continue
            if k in cls.__dict__:
                new_data[k] = v
        return cls(**new_data)

Base = declarative_base(cls=Resource)

class State(Client):

    """ State client to manage state data in sqllite """

    def __init__(self, config_path, debug, log=False):
        super().__init__(config_path, debug, log)
        self.connect()

    def get_client(self):
        """ We return the db session since we do not have a client """
        return self.session

    def connect(self):
        """ Connect to the sqlite database """
        db = self.get_config('state', 'db')
        self.engine = create_engine(f'sqlite:///{db}', poolclass=NullPool)
        Base.metadata.bind = self.engine
        DBSession = sessionmaker()
        self.session = DBSession()
        Base.metadata.create_all(self.engine)
        self.logger.debug("=> sqlite driver %s", self.engine.driver)
        self.logger.debug("=> connected to %s", db)

    def close(self):
        self.logger.debug('=> close db session')
        self.session.close()

    def add(self, resource):
        """ Add a new resource to database """
        pf = self.log_prefix()
        self.logger.debug('%s add new resource of type %s', pf, resource.to_str())
        if not self.dry_run:
            self.session.add(resource)
        self.session.commit()

    def update(self, resource, data):
        """ Update an resource with new data """
        pf = self.log_prefix()
        if not self.dry_run:
            resource.update(data)
        self.logger.debug('%s update resource %s', pf, resource.to_str())

    def get_all(self, class_name, **kwargs):
        return self.session.query(class_name).filter_by(**kwargs).all()

    def get_first(self, class_name, **kwargs):
        return self.session.query(class_name).filter_by(**kwargs).first()

    def purge(self, table):
        """ Drop a table for database """
        self.logger.debug('=> drop table %s', table.title())
        found_table = getattr(sys.modules[__name__], table.title())
        if not self.dry_run:
            found_table.__table__.drop()

#
# Data models
#

class Keypair(Base):

    """ Keypair data model """

    __tablename__ = 'keypair'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(63), nullable=False, index=True)
    created = Column(DateTime, default=datetime.now)
    name = Column(String(255))
    type = Column(String(15))
    region = Column(String(15), index=True)
    public_key = Column(String(1024))

    def to_str(self):
        return f'keys for user id {self.user_id}'

    def compare(self, attributes):
        pass

class Instance(Base):

    """ Instance data model """

    __tablename__ = 'instance'
    id = Column(Integer, primary_key=True)
    instance_id = Column(String(63), nullable=False, index=True)
    created = Column(DateTime, default=datetime.now)
    name = Column(String(255))
    aggregate = Column(String(255))
    host = Column(String(255))
    status = Column(String(15))
    region = Column(String(15), index=True)

    def to_str(self):
        return f'instance with id {self.instance_id}'

    def compare(self, attributes):
        pass

class Quota(Base):

    """ Quota data model """

    __tablename__ = 'quota'
    id = Column(Integer, primary_key=True)
    project_id = Column(String(63), nullable=False, index=True)
    region = Column(String(15), index=True)
    created = Column(DateTime, default=datetime.now)
    # Compute
    cores = Column(Integer)
    ram = Column(Integer)
    instances = Column(Integer)
    # Volume
    snapshots = Column(Integer)
    volumes = Column(Integer)
    gigabytes = Column(Integer)
    # Network
    security_group_rules = Column(Integer)
    security_groups = Column(Integer)

    def to_str(self):
        return f'quota for project id {self.project_id}'

    def compare(self, attributes):
        miss_match = {}
        for k, v in attributes.iteritems():
            if k == 'id':
                continue
            if k not in Quota.__dict__:
                continue
            if getattr(self, k) != v:
                miss_match[k] = f'{getattr(self, k)} =! {v}'
        return miss_match
