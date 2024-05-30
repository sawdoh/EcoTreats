from wtforms import Form, StringField, PasswordField, RadioField, SelectField, TextAreaField, validators, EmailField, \
    ValidationError, FileField, IntegerField, BooleanField
from flask_wtf.file import FileField, FileAllowed
from wtforms.fields import EmailField, DateField, SubmitField, TelField


class CreateProductForm(Form):
    idproducts = IntegerField('Product ID', render_kw={'readonly': True})
    name = StringField(' Name', [validators.Length(min=1, max=150), validators.DataRequired()])
    price = StringField('Price', [validators.Length(min=1, max=150), validators.DataRequired()])
    category = StringField('Category', [validators.Length(min=1, max=150), validators.DataRequired()])
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    description = TextAreaField('Description', [validators.Length(min=1, max=400), validators.DataRequired()])
    ingredients_info = TextAreaField('Ingredients Info', [validators.Length(min=1, max=600), validators.DataRequired()])

    is_recommended = BooleanField('Display in Recommended?')

    # function to validate price entered to make sure that the price entered is either integers or float
    def validate_price(form, field):
        try:
            # Attempt to convert the input from the above field, price, to a float
            float_value = float(field.data)
        except ValueError:
            raise validators.ValidationError('Price must be a valid number.')

    def validate_category(form, field):
        # Check if the field being validated is 'category'
        if field.name == 'category':
            # Convert the input to lowercase
            field.data = field.data.lower()


class SearchForm(Form):
    search_query = StringField(render_kw={'placeholder':'Search for a product'})
    submit = SubmitField('Search')


class deliveryOptionForm(Form):
    option = RadioField('Delivery Options', choices=[('Delivery', 'Delivery'), ('Dine-In', 'Dine-In'), ('Pick-Up', 'Pick-Up')],)