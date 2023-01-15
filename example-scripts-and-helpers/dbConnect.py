import mysql.connector
from config import Config
import logging

logger = logging.getLogger('app.dbconnect')

def _getDbConnection(dbConfig):
    logger.warn('Use of the direct mysql connector is deprecated - use SQLalchemy instead')
    connection = mysql.connector.connect(host = dbConfig.MYSQL_HOST,
                                     port=dbConfig.MYSQL_PORT,
                                     database = dbConfig.MYSQL_DB,
                                     user = dbConfig.MYSQL_USER, 
                                     password = dbConfig.MYSQL_PASSWORD)

    cursor = connection.cursor()
    return cursor, connection

dbconnection = _getDbConnection(Config)