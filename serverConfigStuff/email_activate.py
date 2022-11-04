#!/usr/bin/env python3

from email.mime.text import MIMEText
from subprocess import Popen, PIPE
import mysql.connector



connection = mysql.connector.connect(
    host = 'localhost',
    user = 'root',
    passwd= 'meinpasswortfuerroot95.',
    database = '3bij3'
    )
cursor = connection.cursor(prepared = True)
cursor.execute('select email_contact from user where activated = 0')
respondents = ','.join([item[0].decode('utf-8') for item in cursor])

body ="""                                                                                                                                                                                                                                 \

Beste gebruiker van 3bij3,                                                                                                                                                                                                                \

Je hebt onlangs een account aangemaakt op de nieuwswebsite 3bij3 om deel te nemen aan een onderzoek. Ons systeem laat echter zien dat je dit e-mailadres nog niet hebt geactiveerd. Alleen als je dat wel doet, kun je deelnemen aan het o\
nderzoek.

Tip: het kan zijn dat de e-mail in jouw spamfolder terecht is gekomen.

Als je niet wilt deelnemen hoef je verder niets te doen en ontvang je geen verdere e-mails van ons.

Heb je nog andere vragen over het onderzoek of heb je geen activatie e-mail ontvangen? Aarzel dan niet om contact met ons op te nemen via 3bij3.service@gmail.com.                                                                        \

Met vriendelijke groeten,                                                                                                                                                                                                                 \

Felicia Löcherbach                                                                                                                                                                                                                        \

"""
msg = MIMEText(body)
msg["From"] = "3bij3.service@gmail.com"
msg["To"] = "3bij3.service@gmail.com"
msg["BCC"] = respondents
msg["Subject"] = "Activeer je account op 3bij3"
p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE)
p.communicate(msg.as_bytes())
