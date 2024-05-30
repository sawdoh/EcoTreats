from flask import *
import mysql.connector
from cart import CartItem
from Forms import CreateProductForm, SearchForm, deliveryOptionForm
from Product import  Product
import os
from werkzeug.utils import secure_filename
import stripe
from flask import redirect
from dotenv import load_dotenv
load_dotenv()




app = Flask(__name__)
app.secret_key = 'my_super_secret_key_123'
ALLOWED_EXTENSIONS = set(['jpg', 'jpeg', 'png', 'gif'])
UPLOAD_FOLDER = 'static/img/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mydb = mysql.connector.connect(
    host='localhost',
    user='root',
    password='1234',
    port='3306',
    database='ecotreats')

mycursor = mydb.cursor()

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/store')
def store():
    mycursor.execute('SELECT * FROM products')
    products = mycursor.fetchall()
    return render_template('store.html',products=products)



@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    if not product_id:
        flash('Product ID is missing')
        return redirect(request.referrer or url_for('home'))

    select_query = "SELECT idproducts, name, price, image FROM products WHERE idproducts = %s"
    mycursor.execute(select_query, (product_id,))
    product_details = mycursor.fetchone()

    if product_details:
        product_name = product_details[1]
        product_price = product_details[2]
        product_image = product_details[3]

        quantity = int(request.form.get(f'quantity_{product_id}', 1))

        # Check if the product is already in the cart
        select_cart_query = "SELECT * FROM cart WHERE product_name = %s"
        mycursor.execute(select_cart_query, (product_name,))
        cart_item = mycursor.fetchone()

        if cart_item:
            # Update quantity if the product is already in the cart
            new_quantity = cart_item[4] + quantity  # existing quantity in the cart + new quantity
            update_cart_query = "UPDATE cart SET quantity = %s WHERE product_name = %s"
            mycursor.execute(update_cart_query, (new_quantity, product_name))
        else:
            # Add the product to the cart
            insert_cart_query = "INSERT INTO cart (product_name, product_price, quantity, product_image) VALUES (%s, %s, %s, %s)"
            mycursor.execute(insert_cart_query, (product_name, product_price, quantity, product_image))

        mydb.commit()
    else:
        flash('Product not found')

    total_quantity_query = "SELECT SUM(quantity) FROM cart"
    mycursor.execute(total_quantity_query)
    total_quantity = mycursor.fetchone()[0] or 0  # handle None result

    referring_page = request.referrer or url_for('home')

    session['cart_quantity'] = total_quantity

    return redirect(referring_page)



@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if request.method == 'POST':
        product_name = request.form.get('product_id')

        user_id = session['user_id']

        # Remove the product from the cart
        delete_cart_query = "DELETE FROM cart WHERE product_name = %s"
        mycursor.execute(delete_cart_query, (product_name,))
        mydb.commit()
        flash('Product removed from cart')
        total_quantity_query = "SELECT SUM(quantity) FROM cart"
        mycursor.execute(total_quantity_query)
        total_quantity = mycursor.fetchone()[0] or 0  # handle None result
        session['cart_quantity'] = total_quantity

    return redirect(url_for('view_cart'))


@app.route('/update_cart', methods=['POST'])
def update_cart():
    if request.method == 'POST':
        product_name = request.form.get('product_id')


        # Fetch product details from the database
        select_query = "SELECT name, price FROM products WHERE name = %s"
        mycursor.execute(select_query, (product_name,))
        product_details = mycursor.fetchone()

        if product_details:
            new_quantity = int(request.form.get('quantity', 1))

            # Update the quantity in the cart
            update_cart_query = "UPDATE cart SET quantity = %s WHERE product_name = %s"
            mycursor.execute(update_cart_query, (new_quantity, product_name))
            mydb.commit()
            flash('Cart updated')
            total_quantity_query = "SELECT SUM(quantity) FROM cart"
            mycursor.execute(total_quantity_query)
            total_quantity = mycursor.fetchone()[0] or 0  # handle None result
            session['cart_quantity'] = total_quantity

        else:
            flash('Product not found')

    return redirect(url_for('view_cart'))

def get_cart_items():

    mycursor = mydb.cursor()
    select_cart_query = "SELECT product_name, product_price, quantity, product_image FROM cart WHERE product_name IS NOT NULL AND product_price IS NOT NULL AND product_image IS NOT NULL"
    mycursor.execute(select_cart_query)
    cart_items_data = mycursor.fetchall()
    # Create CartItem instances from the fetched data
    cart_items = [CartItem(item[0], item[1], item[3], quantity=item[2]) for item in cart_items_data]

    return cart_items

def calculate_total_price(cart_items):
    return sum(
        item.get_price() * item.get_quantity() if item.get_price() is not None and item.get_quantity() is not None else 0
        for item in cart_items)

@app.route('/cart', methods=['GET'])
def view_cart():
    cart_items = get_cart_items()
    total_price = calculate_total_price(cart_items)
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/create_product', methods=['GET', 'POST'])
def create_product():
    create_product_form = CreateProductForm(request.form)

    if request.method == 'POST' and create_product_form.validate():
        try:
            # Handle image upload
            if 'image' in request.files:
                image = request.files['image']
                if image.filename == '':
                    flash('No image selected for uploading')
                    return redirect(request.url)

                if image and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    # image.save(image_path)
                else:
                    flash('Allowed image types are - jpg, png, jpeg')
                    return redirect(request.url)

            # Check if a product with the same name already exists
            existing_product_query = "SELECT * FROM products WHERE name = %s"
            mycursor.execute(existing_product_query, (create_product_form.name.data,))
            existing_product = mycursor.fetchone()

            if existing_product:
                flash('Product with the same name already exists. Please choose a different name.')
                return render_template('create_product.html', form=create_product_form)

            # Create an instance of the Product class
            product = Product(
                name=create_product_form.name.data,
                price=create_product_form.price.data,
                category=create_product_form.category.data,
                image=filename,
                description=create_product_form.description.data,
                ingredients_info=create_product_form.ingredients_info.data,
                is_recommended=create_product_form.is_recommended.data
            )

            insert_query = "INSERT INTO products (name, price, category, image, description, ingredients_info, is_recommended) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            product_data = (product.get_name(), product.get_price(), product.get_category(), product.get_image(),
                            product.get_description(), product.get_ingredients_info(), product.get_is_recommended())
            mycursor.execute(insert_query, product_data)

            mydb.commit()

            return redirect(url_for('retrieve_product'))

        except Exception as e:
            print('Error:', e)
            mydb.rollback()
            return "Error Occurred. Check logs for details"


    return render_template('create_product.html', form=create_product_form)


@app.route('/retrieve_product', methods=['GET'])
def retrieve_product():

    search_form = SearchForm(request.args)

    if request.method == 'GET' and search_form.validate():
        search_query = search_form.search_query.data
        # Check if a search query is provided
        if search_query:
            select_query = f"SELECT idproducts, name, price, category, image, description, ingredients_info, is_recommended FROM products WHERE name LIKE '%{search_query}%'"
        else:
            # If no search query, retrieve all products
            select_query = "SELECT idproducts, name, price, category, image, description, ingredients_info, is_recommended FROM products"
    else:
        # If no search query, retrieve all products
        select_query = "SELECT idproducts, name, price, category, image, description, ingredients_info, is_recommended FROM products"


    mycursor.execute(select_query)
    rows = mycursor.fetchall()

    # Create instances of the Product class
    products = [Product(idproducts=row[0], name=row[1], price=row[2], category=row[3], image=row[4], description=row[5],
                        ingredients_info=row[6], is_recommended=row[7]) for row in rows]

    # Calculate the count of products
    count = len(products)

    return render_template('retrieve_product.html', products=products, count=count, search_form=search_form)



@app.route('/update_product/<int:id>/', methods=['GET', 'POST'])
def update_product(id):
    update_product_form = CreateProductForm(request.form)

    if request.method == 'POST' and update_product_form.validate():
        try:
            # Fetch existing product details from the database
            select_query = "SELECT idproducts, name, price, category, image, description, ingredients_info, is_recommended FROM products WHERE idproducts = %s"
            mycursor.execute(select_query, (id,))
            product_details = mycursor.fetchone()

            if product_details:
                # Update product details
                name = update_product_form.name.data
                price = update_product_form.price.data
                category = update_product_form.category.data
                image = update_product_form.image.data
                description = update_product_form.description.data
                ingredients_info = update_product_form.ingredients_info.data
                is_recommended = update_product_form.is_recommended.data

                # Handle image upload
                if 'image' in request.files:
                    image = request.files['image']
                    if image.filename != '':
                        filename = secure_filename(image.filename)
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        image.save(image_path)
                        # Save the new image filename to the database
                        update_query = "UPDATE products SET name = %s, price = %s, category = %s, image = %s, description = %s, ingredients_info = %s, is_recommended = %s WHERE idproducts = %s"
                        data = (name, price, category, filename, description, ingredients_info, is_recommended, id)
                        mycursor.execute(update_query, data)
                        mydb.commit()
                    else:
                        # If no new image provided, update without changing the image
                        update_query = "UPDATE products SET name = %s, price = %s, category = %s, description = %s, ingredients_info = %s, is_recommended = %s WHERE idproducts = %s"
                        data = (name, price, category, description, ingredients_info, is_recommended, id)
                        mycursor.execute(update_query, data)
                        mydb.commit()

                return redirect(url_for('retrieve_product'))

            else:
                return "Product not found"

        except Exception as e:
            print("Error: ", e)
            mydb.rollback()
            return "Error occurred while updating product"

    else:
        try:
            # Fetch existing product details to prepopulate the form
            select_query = "SELECT idproducts, name, price, category, image, description, ingredients_info, is_recommended FROM products WHERE idproducts = %s"
            mycursor.execute(select_query, (id,))
            product_details = mycursor.fetchone()

            if product_details:
                update_product_form.idproducts.data = product_details[0]  # Set the product ID in the form
                update_product_form.name.data = product_details[1]
                update_product_form.price.data = product_details[2]
                update_product_form.image.data = product_details[4]
                update_product_form.category.data = product_details[3]
                update_product_form.description.data = product_details[5]
                update_product_form.ingredients_info.data = product_details[6]
                update_product_form.is_recommended.data = product_details[7]

                return render_template('update_product.html', form=update_product_form, product_id_error=None,
                                       product_details=product_details)
            else:
                return render_template('update_product.html', form=update_product_form,
                                       product_id_error="Product not found", product_details=None)

        except Exception as e:
            print('Error:', e)
            return "Error occurred while fetching product details"


@app.route('/delete_product/<int:id>', methods=['GET', 'POST'])
def delete_product(id):
    try:
        select_query = "SELECT * FROM products WHERE idproducts = %s"
        mycursor.execute(select_query, (id,))
        product = mycursor.fetchone()

        if product:
            delete_query = "DELETE FROM products WHERE idproducts = %s"
            mycursor.execute(delete_query, (id,))
            mydb.commit()

            return redirect(url_for('retrieve_product'))
        else:
            return "Product not found"

    except Exception as e:
        print('Error: ', e)
        mydb.rollback()
        return "Error occurred while deleting product"


purchasedTableCheck = ['purchased']
for a in purchasedTableCheck:
    mycursor.execute(f"SHOW TABLES LIKE 'purchased'")
    tableExist = mycursor.fetchone()

    if not tableExist:
        mycursor.execute(
            "CREATE TABLE `purchased` (`id` int NOT NULL AUTO_INCREMENT,`total_amt` decimal(10,2) DEFAULT NULL,`cart_data` json DEFAULT NULL,`user_id` int DEFAULT NULL,`datetime` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,`deliveryOption` varchar(45) DEFAULT NULL,PRIMARY KEY (`id`)) ENGINE=InnoDB AUTO_INCREMENT=42 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;")



@app.route('/create-checkout-session', methods=['GET', 'POST'])
def create_checkout_session():
    try:
        cart_items = get_cart_items()

        # Create line items for the checkout session
        line_items = []
        for item in cart_items:
            # Convert the price to an integer in cents
            unit_amount_cents = int(item.get_price() * 100)

            line_items.append({
                'price_data': {
                    'currency': 'sgd',
                    'product_data': {
                        'name': item.get_name(),
                        'images': [item.get_image()],
                    },
                    'unit_amount': unit_amount_cents,
                },
                'quantity': item.get_quantity(),
            })

        #checkout session with line items
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url='http://localhost:5000/checkout-success',
            cancel_url='http://localhost:5000/cart',
        )


        return redirect(session.url)
        # return jsonify({'sessionId': session.id})
    except Exception as e:
        return str(e)




stripe.api_key = os.getenv("STRIPE_API_KEY")


@app.route('/checkout-success', methods=['GET', 'POST'])
def checkout_success():
    deliveryOption = deliveryOptionForm(request.form)
    if request.method == 'POST' and deliveryOption.validate():
        try:
            mycursor = mydb.cursor()

            user_id = session['user_id']
            cart = get_cart_items()
            total_amt = calculate_total_price(cart)
            option = deliveryOption.option.data
            print(option)

            cart_data = json.dumps([{'product_name': item.get_name(),
                                     'product_price': float(item.get_price()),
                                     'quantity': item.get_quantity()
                                     } for item in cart])

            print(cart_data)

            query = 'INSERT INTO purchased (total_amt, cart_data, user_id, deliveryOption ) VALUES (%s, %s, %s, %s)'
            value = (total_amt, cart_data, user_id, option)
            mycursor.execute(query, value)
            mydb.commit()
            return redirect(url_for('home'))
        except Exception as e:
            print("Error:", e)
            mydb.rollback()
            return "Error occurred. Check logs for details." +  str(e)

    return render_template('checkout-success.html', form=deliveryOption)



if __name__ == '__main__':
    app.run(debug=True)