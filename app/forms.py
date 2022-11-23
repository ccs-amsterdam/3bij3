from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, RadioField, SelectField,  SubmitField, SelectMultipleField, TextAreaField, widgets, IntegerField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, InputRequired, Length, NumberRange
from app.models import User
from werkzeug.security import generate_password_hash
from flask_babel import gettext

class LoginForm(FlaskForm):
    username = StringField(gettext('Username'), validators = [DataRequired()])
    password = PasswordField(gettext('Password'), validators = [DataRequired()])
    remember_me = BooleanField(gettext('Stay logged on'))
    submit = SubmitField(gettext('Login'))

class RegistrationForm(FlaskForm):
    username = StringField(gettext('Username'), validators = [DataRequired()])
    email = StringField(gettext('Email'), validators = [DataRequired(), Email()])
    password = PasswordField(gettext('Password'), validators = [DataRequired()])
    password2 = PasswordField(gettext('Repeat password'), validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(gettext('Register'))

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError(gettext('This username is already in use. Please choose a different one.'))

    def validate_email(self, email):
        user = User.query.filter_by(email_contact=email.data).first()
        if user is not None:
            raise ValidationError(gettext('This email address is already in use. You probably already have registered.'))

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

class ResetPasswordRequestForm(FlaskForm):
    email = StringField(gettext('Email'), validators=[DataRequired(), Email()])
    submit = SubmitField(gettext('Reset my password!'))

class ResetPasswordForm(FlaskForm):
    password = PasswordField(gettext('Password'), validators= [DataRequired()])
    password2 = PasswordField(gettext('Repeat password'), validators = [DataRequired(), EqualTo('password')])
    submit = SubmitField(gettext('Reset my password!'))


class rating(FlaskForm):
    rating = TextAreaField()
    rating2 = TextAreaField()

class ContactForm(FlaskForm):
    email = TextAreaField(gettext('Your email: '))
    lead = TextAreaField(gettext('Subject: '), validators = [DataRequired()])
    message = TextAreaField(gettext('Your message:'), validators = [DataRequired()])
    submit = SubmitField(gettext('Submit'))

class ReportForm(FlaskForm):
    lead = TextAreaField('subject::', validators = [DataRequired()])
    message = TextAreaField(gettext('What problem does this article have?'), validators = [DataRequired()])
    submit = SubmitField(gettext('Submit'))
