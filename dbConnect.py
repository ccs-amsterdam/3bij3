import mysql.connector

def getDbConnection(dbConfig):
    connection = mysql.connector.connect(host = dbConfig.MYSQL_HOST,
                                     port=dbConfig.MYSQL_PORT,
                                     database = dbConfig.MYSQL_DB,
                                     user = dbConfig.MYSQL_USER, 
                                     password = dbConfig.MYSQL_PASSWORD)

    cursor = connection.cursor()
    return cursor, connection
