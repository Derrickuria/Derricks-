from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import pandas as pd
from datetime import datetime
import json
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'playpals_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///playpals.db'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "admin_login"
migrate = Migrate(app, db)

# MODELS 

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    price = db.Column(db.Integer)
    available = db.Column(db.Boolean, default=True)
    image = db.Column(db.String(200))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    location = db.Column(db.String(200))

    total_price = db.Column(db.Integer)
    deposit_paid = db.Column(db.Integer)
    balance_due = db.Column(db.Integer)

    status = db.Column(db.String(20), default="Pending")
    payment_status = db.Column(db.String(30), default="Deposit Paid")

    rental_start = db.Column(db.DateTime)
    return_date = db.Column(db.DateTime)

    items = db.Column(db.Text)

# LOGIN 

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# PUBLIC ROUTES

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/catalogue")
def catalogue():
    games = Game.query.filter_by(available=True).all()
    return render_template("catalogue.html", games=games)

@app.route("/cart")
def cart():
    return render_template("cart.html")

@app.route("/checkout")
def checkout():
    return render_template("checkout.html")

@app.route("/payment")
def payment():
    return render_template("payment.html")

@app.route("/orderConfirmation/<int:order_id>")
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    items = json.loads(order.items) if order.items else []
    return render_template("orderConfirmation.html", order=order, items=items)

# SAVE ORDER 

@app.route("/save_order", methods=["POST"])
def save_order():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data received"}), 400

        delivery = data
        items = data.get("items", [])

        total = int(data.get("total", 0))
        deposit = int(total * 0.5)
        balance = total - deposit

        new_order = Order(
            customer_name=delivery.get("name"),
            phone=delivery.get("phone"),
            location=delivery.get("address"),
            total_price=total,
            deposit_paid=deposit,
            balance_due=balance,
            items=json.dumps(items),
            status="Pending",
            payment_status="Deposit Paid"
        )

        db.session.add(new_order)
        db.session.commit()

        return jsonify({"order_id": new_order.id})

    except Exception as e:
        print("Error saving order:", e)
        return jsonify({"error": "Failed to save order"}), 500

# DELIVERY

@app.route("/admin/deliver_order/<int:id>")
@login_required
def deliver_order(id):
    order = Order.query.get_or_404(id)
    order.status = "Delivered"
    order.rental_start = datetime.utcnow()
    db.session.commit()
    return generate_delivery_receipt(order)

@app.route("/admin/return_order/<int:id>")
@login_required
def return_order(id):
    order = Order.query.get_or_404(id)
    order.status = "Completed"
    order.return_date = datetime.utcnow()
    order.payment_status = "Fully Paid"
    order.balance_due = 0
    db.session.commit()
    return generate_final_receipt(order)

#  RECEIPTS 

def generate_delivery_receipt(order):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 800, "PLAYPALS - DELIVERY RECEIPT")
    c.setFont("Helvetica", 12)
    c.drawString(50, 770, f"Order ID: {order.id}")
    c.drawString(50, 750, f"Customer: {order.customer_name}")
    c.drawString(50, 730, f"Deposit Paid: Ksh {order.deposit_paid}")
    c.drawString(50, 710, f"Balance Due On Return: Ksh {order.balance_due}")
    c.drawString(50, 690, f"Rental Start: {order.rental_start}")
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Delivery_Receipt_{order.id}.pdf", mimetype="application/pdf")

def generate_final_receipt(order):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 800, "PLAYPALS - FINAL RECEIPT")
    c.setFont("Helvetica", 12)
    c.drawString(50, 770, f"Order ID: {order.id}")
    c.drawString(50, 750, f"Customer: {order.customer_name}")
    c.drawString(50, 730, f"Total Paid: Ksh {order.total_price}")
    c.drawString(50, 710, f"Return Date: {order.return_date}")
    c.drawString(50, 690, "Status: Completed")
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Final_Receipt_{order.id}.pdf", mimetype="application/pdf")

# EXPORT ORDERS 

@app.route("/admin/export_orders")
@login_required
def export_orders():
    orders = Order.query.all()
    data = []
    for o in orders:
        data.append({
            "Order ID": o.id,
            "Customer": o.customer_name,
            "Phone": o.phone,
            "Location": o.location,
            "Total": o.total_price,
            "Deposit": o.deposit_paid,
            "Balance": o.balance_due,
            "Status": o.status
        })
    df = pd.DataFrame(data)
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="PlayPals_Orders.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ADMIN ROUTES

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        admin = Admin.query.filter_by(username=request.form["username"]).first()
        if admin and check_password_hash(admin.password, request.form["password"]):
            login_user(admin)
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials")
    return render_template("admin_login.html")

@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if Admin.query.filter_by(username=username).first():
            flash("Username already exists. Please choose another.")
        else:
            hashed_pw = generate_password_hash(password)
            new_admin = Admin(username=username, password=hashed_pw)
            db.session.add(new_admin)
            db.session.commit()
            flash("Admin account created successfully. Please log in.")
            return redirect(url_for("admin_login"))

    return render_template("admin_register.html")

@app.route("/admin/logout")
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for("home"))

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    games = Game.query.all()
    orders = Order.query.all()
    return render_template("admin_dashboard.html", games=games, orders=orders)

# ADD GAME 

@app.route("/admin/add_game", methods=["POST"])
@login_required
def add_game():
    try:
        name = request.form["name"]
        description = request.form["description"]
        price = int(request.form["price"])
        image = request.form["image"]
        available = "available" in request.form

        new_game = Game(
            name=name,
            description=description,
            price=price,
            image=image,
            available=available
        )
        db.session.add(new_game)
        db.session.commit()
        flash(f"Game '{name}' added successfully!")
    except Exception as e:
        flash(f"Error adding game: {e}")
    return redirect(url_for("admin_dashboard"))


# EDIT GAME 

@app.route("/admin/edit_game/<int:id>", methods=["GET", "POST"])
@login_required
def edit_game(id):
    game = Game.query.get_or_404(id)
    if request.method == "POST":
        try:
            game.name = request.form["name"]
            game.description = request.form["description"]
            game.price = int(request.form["price"])
            game.image = request.form["image"]
            game.available = "available" in request.form

            db.session.commit()
            flash(f"Game '{game.name}' updated successfully!")
            return redirect(url_for("admin_dashboard"))
        except Exception as e:
            flash(f"Error updating game: {e}")

    return render_template("edit_game.html", game=game)

# DELETE GAME 
@app.route("/admin/delete_game/<int:id>", methods=["POST"])
@login_required
def delete_game(id):
    game = Game.query.get_or_404(id)
    db.session.delete(game)
    db.session.commit()
    flash("Game deleted successfully")
    return redirect(url_for("admin_dashboard"))

# RUN 
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)