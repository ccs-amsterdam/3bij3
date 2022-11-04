import mysql.connector

def getDbConnection(dbConfig):

    connnection = mysql.connector.connect \
        (host=dbConfig["host"], user=dbConfig["user"],\
         password=dbConfig["password"], db=dbConfig["db"], port=dbConfig["port"])
    cursor = connnection.cursor()
    return cursor, connnection
