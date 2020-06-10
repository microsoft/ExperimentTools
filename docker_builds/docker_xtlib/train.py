# test basic run
print("hello from train.py running in docker!")

# test xtlib presence
import xtlib
print("xtlib: ", xtlib.__version__)

# test connectivity to mongo db
from xtlib.helpers.xt_config import XTConfig
config = XTConfig()
mongo_cs = config.get_vault_key("xt-sandbox-cosmos")

import pymongo
from pymongo import MongoClient
client = MongoClient(mongo_cs) 

mongo_db = client["xtdb"]
qt_coll = mongo_db["quick-test"]

count = qt_coll.count()
print("quick-test count from mongodb: ", count)

