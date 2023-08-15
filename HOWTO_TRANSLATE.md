

```
pybabel extract -F babel.cfg -k lazy_gettext -o messages.pot .   # don't forget the final dot!
```

Gevolgd door,  *alleen bij de eerste keer*:

```
pybabel init -i messages.pot -d app/translations -l en   # of nl of whatever
```

De volgende keer `pybabel update` ipv `init`:

```
pybabel update -i messages.pot -d app/translations -l en
```



Dan .po bestanden in `app/translations` vertalen.

Vervolgens

```
pybabel compile -d app/translations
```
