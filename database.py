from pymongo import MongoClient
from conf import db_user, db_pwd, db_host

db = MongoClient(db_host, 27017,
                 username=db_user, password=db_pwd, authSource='maintenant', authMechanism='SCRAM-SHA-1')
