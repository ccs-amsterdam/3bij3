

```
pybabel extract -F babel.cfg -o messages.pot .   # don't forget the final dot!

pybabel init -i messages.pot -d app/translations -l en   # of nl of whatever
```

Dan .po bestanden in `app/translations` vertalen.

Vervolgens

```
pybabel compile -d app/translations
```