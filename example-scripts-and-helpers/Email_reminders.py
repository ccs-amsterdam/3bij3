#!/usr/bin/env python3

from email.mime.text import MIMEText
from subprocess import Popen, PIPE
import mysql.connector
from datetime import datetime, timedelta

cutoff = datetime.utcnow().date() - timedelta(days=3)

connection = mysql.connector.connect(
    host = 'localhost',
    user = 'root',
    passwd= 'meinpasswortfuerroot95.',
    database = '3bij3'
    )
cursor = connection.cursor(prepared = True)
cursor.execute('select email_contact from user where date(last_visit) < ? and activated = 1 and reminder_sent = 0 and phase_completed != 3', (str(cutoff),))
respondents = ','.join([item[0].decode('utf-8') for item in cursor])

body ="""
Beste gebruiker van 3bij3,

Dit is een vriendelijke herinnering van ons systeem dat je de afgelopen drie dagen niet bent ingelogd op onze website.
Je kunt daar terecht via deze link: http://www.3bij3.nl en ook jouw wachtwoord resetten voor het geval je het bent vergeten.
Mocht je vragen hebben of wil je stoppen met het onderzoek, stuur dan een e-mail via het contactformulier en we nemen contact met je op.

Met vriendelijke groeten,
Felicia Löcherbach
"""
msg = MIMEText(body)
msg["From"] = "3bij3.service@gmail.com"
msg["To"] = "3bij3.service@gmail.com"
msg["BCC"] = respondents
msg["Subject"] = "Herinnering: Blijf 3bij3 gebruiken om de studie af te sluiten"
p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE)
p.communicate(msg.as_bytes())

reminder_sent = respondents.split(',')
query = "update user set reminder_sent = 1 where email_contact in ('%s')" % "','".join(reminder_sent)
cursor.execute(query)
connection.commit()
