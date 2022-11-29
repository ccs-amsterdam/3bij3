from config import Config
import mysql.connector
from mysql.connector import Error
from mysql.connector import errorcode

connection = mysql.connector.connect(host = Config.MYSQL_HOST,
                                     port=Config.MYSQL_PORT,
                                     database = Config.MYSQL_DB,
                                     user = Config.MYSQL_USER, 
                                     password = Config.MYSQL_PASSWORD)
                                     
sql = "SELECT `group` FROM user WHERE ID = (SELECT MAX(id) FROM user)"
cursor = connection.cursor(buffered=True)
cursor.execute(sql)
group = cursor.fetchall()[0][0]

newGroup = 30

if(group == 1):
    newGroup=2
elif(group == 2):
    newGroup=3
elif(group == 3):
    newGroup=4
elif(group == 4):
    newGroup=1

print(group)
print(newGroup)
