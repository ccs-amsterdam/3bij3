import mysql.connector
from mysql.connector import Error
from mysql.connector import errorcode

connection = mysql.connector.connect(host = '172.17.0.1', database = '3bij3', user = 'newsflow', password = 'Bob416!', port=3307)

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
