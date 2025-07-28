from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, FloatField, SubmitField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

class LotForm(FlaskForm):
    name = StringField('Lot Name', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    pin = StringField('Pin Code', validators=[DataRequired()])
    price = FloatField('Price per hour', validators=[DataRequired()])
    max_spots = IntegerField('Total Spots', validators=[DataRequired()])
    submit = SubmitField('Create Lot')
