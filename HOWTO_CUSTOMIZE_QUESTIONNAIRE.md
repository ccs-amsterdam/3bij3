# How to add custom questions:

1. Edit `app/forms.py`
2. Edit `app/blueprints/multilingual/routes.py`: make sure that the form fields are all also mentioned in `def final_questionnaire():`
3. Update `app/models.py` and add the new fields to `class User(UserMixin, db.Model):`
4. Do the translations (see HOWTO_TRANSLATE)
5. Update database

```bash
flask db migrate
flask db upgrade
```