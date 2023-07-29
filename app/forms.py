from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, RadioField, SelectField,  SubmitField, SelectMultipleField, TextAreaField, widgets, IntegerField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, InputRequired, Length, NumberRange, NoneOf
from app.models import User
from werkzeug.security import generate_password_hash
from flask_babel import lazy_gettext

class LoginForm(FlaskForm):
    username = StringField(lazy_gettext('Username'), validators = [DataRequired()])
    password = PasswordField(lazy_gettext('Password'), validators = [DataRequired()])
    remember_me = BooleanField(lazy_gettext('Stay logged on'))
    submit = SubmitField(lazy_gettext('Login'))

class RegistrationForm(FlaskForm):
    username = StringField(lazy_gettext('Username'), validators = [DataRequired()])
    email = StringField(lazy_gettext('Email'), validators = [DataRequired(), Email()])
    password = PasswordField(lazy_gettext('Password'), validators = [DataRequired()])
    password2 = PasswordField(lazy_gettext('Repeat password'), validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(lazy_gettext('Register'))

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError(lazy_gettext('This username is already in use. Please choose a different one.'))

    def validate_email(self, email):
        user = User.query.filter_by(email_contact=email.data).first()
        if user is not None:
            raise ValidationError(lazy_gettext('This email address is already in use. You probably already have registered.'))

class MultiCheckboxField(SelectMultipleField):
    option_widget = widgets.CheckboxInput()
    widget = widgets.ListWidget(prefix_label = False)

class ChecklisteForm(FlaskForm):
    list_of_files = ['Binnenland', 'Buitenland', 'Economie', 'Milieu', 'Wetenschap en technologie', 'Immigratie en integratie', 'Justitie en Criminaliteit', 'Sport', 'Kunst, cultuur en entertainment', 'Anders/Diversen']
    files = [(x, x) for x in list_of_files]
    example = MultiCheckboxField('Label', choices=files)
    submit = SubmitField('Wijzigen')

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False
        if len(self.example.data) > 2:
            self.example.errors.append('Let op! U kunt maximaal drie opties kiezen.')
            return False
        return True

class FinalQuestionnaireForm(FlaskForm):
    eval_game = SelectField(label=lazy_gettext(
        "To what extend did this site make you feel like you were part of a game?"), validators=[DataRequired(), NoneOf(["-999"])],
        choices = [
        (-999, lazy_gettext("--please make a choice--")),
        (-3, lazy_gettext("-3 (not at all)")), 
        (-2, -2), 
        (-1, -1),
        (0, 0),
        (1, 1),
        (2, 2),
        (3, lazy_gettext("+3 (very much)"))])

    eval_nudge = SelectField(label=lazy_gettext(
        "Did you notice the yellow text box that sometimes appeared on top of the page asking you to share specific news content"), validators=[DataRequired(), NoneOf(["-999"])],
        choices = [
        (-999, lazy_gettext("--please make a choice--")),
        (0, lazy_gettext("No")),
        (1, lazy_gettext("Yes"))])

    eval_diversity = SelectField(label=lazy_gettext(
        "How diverse were the items that this site showed to you?"), validators=[DataRequired(), NoneOf(["-999"])],
        choices = [
        (-999, lazy_gettext("--please make a choice--")),
        (-3, lazy_gettext("-3 (not at all)")), 
        (-2, -2), 
        (-1, -1),
        (0, 0),
        (1, 1),
        (2, 2),
        (3, lazy_gettext("+3 (very much)"))])

    eval_personalization = SelectField(label=lazy_gettext(
        "How aligned with your interests and preferences were the items that this site showed to you?"), validators=[DataRequired(), NoneOf(["-999"])],
        choices = [
        (-999, lazy_gettext("--please make a choice--")),
        (-3, lazy_gettext("-3 (not at all)")), 
        (-2, -2), 
        (-1, -1),
        (0, 0),
        (1, 1),
        (2, 2),
        (3, lazy_gettext("+3 (very much)"))])
    eval_future = SelectField(label=lazy_gettext(
        "If it were possible, would you like to continue using this news app?"), validators=[DataRequired(), NoneOf(["-999"])],
        choices = [
        (-999, lazy_gettext("--please make a choice--")),
        (-3, lazy_gettext("-3 (not at all)")), 
        (-2, -2), 
        (-1, -1),
        (0, 0),
        (1, 1),
        (2, 2),
        (3, lazy_gettext("+3 (very much)"))])

    eval_comments1 = TextAreaField(label=lazy_gettext("Did you experience any error during the usage?"))
    eval_comments2 = TextAreaField(label=lazy_gettext("What do you like most about the app?"))
    eval_comments3 = TextAreaField(label=lazy_gettext("What do you like least about the app?"))
    eval_comments4 = TextAreaField(label=lazy_gettext("Do you prefer accessing the site via laptop/desktop or mobile/ipad? Why?"))
    eval_comments5 = TextAreaField(label=lazy_gettext("What do you think we should improve in this app?"))
    submit = SubmitField(lazy_gettext("Done!"))

    
class IntakeForm(FlaskForm):
    # remember to change the user class in models.py if you change sth here.
    # remember to check the /activate function in routes.py whether all fields are stored
    age = IntegerField(label=lazy_gettext("How old are you?"), validators=[DataRequired(), NumberRange(min=18, max=120)])
    gender = RadioField(label=lazy_gettext("What is your gender?"), validators=[DataRequired()], choices=[
        lazy_gettext("female"), 
        lazy_gettext("male"), 
        lazy_gettext("non-binary"),
        lazy_gettext("prefer not to say")])
    education = SelectField(label=lazy_gettext("What is your the highest degree you have completed or are enrolled in?"), validators=[DataRequired(),NoneOf(["-999"])], choices=[
        (-999, lazy_gettext("--please make a choice--")),
        (0, lazy_gettext("no higher education")), 
        (1, lazy_gettext("bachelor")), 
        (2, lazy_gettext("master")),
        (3, lazy_gettext("PhD"))])
    newsinterest = SelectField(label=lazy_gettext(
        "How interested are you in news and current affairs?"), validators=[DataRequired(), NoneOf(["-999"])],
        choices = [
        (-999, lazy_gettext("--please make a choice--")),
        (-3, lazy_gettext("-3 (not at all)")), 
        (-2, -2), 
        (-1, -1),
        (0, 0),
        (1, 1),
        (2, 2),
        (3, lazy_gettext("+3 (very much)"))])
    polorient = SelectField(label=lazy_gettext(
        "In politics, we often talk about left or right. On a scale from -5 (left) to +5 (right), where would you place yourself?'"),
        validators=[DataRequired(), NoneOf(["-999"])],
        choices = [(-999, lazy_gettext("--please make a choice--")),
        (-5, lazy_gettext("-5 (left)")), 
        (-4, -4), 
        (-3, -3), 
        (-2, -2), 
        (-1, -1),
        (0, lazy_gettext ("0 (center)")),
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, lazy_gettext("+5 (right)"))])
    submit = SubmitField(lazy_gettext("Done!"))

class ResetPasswordRequestForm(FlaskForm):
    email = StringField(lazy_gettext('Email'), validators=[DataRequired(), Email()])
    submit = SubmitField(lazy_gettext('Reset my password!'))

class ResetPasswordForm(FlaskForm):
    password = PasswordField(lazy_gettext('Password'), validators= [DataRequired()])
    password2 = PasswordField(lazy_gettext('Repeat password'), validators = [DataRequired(), EqualTo('password')])
    submit = SubmitField(lazy_gettext('Reset my password!'))


class RatingForm(FlaskForm):
    rating = TextAreaField()
    rating2 = TextAreaField()

class ContactForm(FlaskForm):
    email = TextAreaField(lazy_gettext('Your email: '))
    lead = TextAreaField(lazy_gettext('Subject: '), validators = [DataRequired()])
    message = TextAreaField(lazy_gettext('Your message:'), validators = [DataRequired()])
    submit = SubmitField(lazy_gettext('Submit'))

class ReportForm(FlaskForm):
    lead = TextAreaField('subject::', validators = [DataRequired()])
    message = TextAreaField(lazy_gettext('What problem does this article have?'), validators = [DataRequired()])
    submit = SubmitField(lazy_gettext('Submit'))
