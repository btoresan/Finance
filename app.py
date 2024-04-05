import os

from cs50 import SQL
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():

    # Getting user stock data
    portifolio = db.execute("SELECT * FROM wallet WHERE user_id = ?", session["user_id"])
    result = [dict(item, price=lookup(item["stock"])["price"]) for item in portifolio]

    # Getting user cash data
    total = 0
    for row in result:
        total += row["price"] * row["shares"]

    user = {
        "cash": db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"],
        "total": db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"] + float(total)
    }

    return render_template("index.html", portifolio=result, user=user)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        # Check if stock exist
        if not lookup(request.form.get("symbol")):
            return apology("stock not found", 400)

        # Check if valid shares
        if not request.form.get("shares").isnumeric() or float(request.form.get("shares")) == 0:
            return apology("invalid shares", 400)

        # Check if not broke
        quote = lookup(request.form.get("symbol"))
        if float(db.execute("SELECT cash FROM users WHERE id = ?;", session["user_id"])[0]["cash"]) < quote["price"] * float(request.form.get("shares")):
            return apology("card declined", 400)

        # Takes cash
        db.execute("UPDATE users SET cash=cash - ? WHERE id = ?;",
                   (quote["price"] * float(request.form.get("shares"))), session["user_id"])
        # Register Transaction
        db.execute("INSERT INTO transactions(user_id, stock, shares, price, time) VALUES (?, ?, ?, ?, ?);",
                   session["user_id"], quote["symbol"], int(request.form.get("shares")), quote["price"], datetime.now())
        # Update Wallet
        if not db.execute("SELECT stock FROM wallet WHERE stock=? AND user_id=?;", quote["symbol"], session["user_id"]):
            db.execute("INSERT INTO wallet(user_id, stock, shares) VALUES (?, ?, ?);", session["user_id"], quote["symbol"], 0)
        # Add stock to wallet
        db.execute("UPDATE wallet SET shares= shares + ? WHERE user_id=? AND stock=?;",
                   int(request.form.get("shares")), session["user_id"], quote["symbol"])

        flash("Transaction successfull")
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    transactions = db.execute("SELECT * FROM transactions WHERE user_id=?", session["user_id"])
    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    if request.method == "POST":
        if not lookup(request.form.get("symbol")):
            return apology("stock not found", 400)

        name = lookup(request.form.get("symbol"))["name"]
        symbol = lookup(request.form.get("symbol"))["symbol"]
        price = usd(lookup(request.form.get("symbol"))["price"])
        return render_template("quoted.html", name=name, symbol=symbol, price=price)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Checks if password mach
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("password do not match", 400)

        # Adds user to the database if username is valid
        if db.execute("SELECT username FROM users WHERE username = ?;", request.form.get("username")):
            return apology("username taken", 400)

        hash = generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users(username, hash) VALUES (?, ?);", request.form.get("username"), hash)

        # Remember which user has logged in
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":
        # Check if stock exist
        if not lookup(request.form.get("symbol")):
            return apology("stock not found", 403)

        # Check if shares valid
        if int(request.form.get("shares")) > int(db.execute("SELECT shares FROM wallet WHERE user_id=? AND stock=?;", session["user_id"], request.form.get("symbol"))[0]["shares"]):
            return apology("invalid shares", 400)

        # Take Stocks
        db.execute("UPDATE wallet SET shares=shares-? WHERE user_id=? AND stock=?;",
                   request.form.get("shares"), session["user_id"], request.form.get("symbol"))
        # Give money
        db.execute("UPDATE users SET cash=cash + ? WHERE id=?", float(lookup(request.form.get("symbol"))
                                                                      ["price"]) * float(request.form.get("shares")), session["user_id"])
        # Register transaction
        db.execute("INSERT INTO transactions(user_id, stock, shares, price, time) VALUES (?, ?, -?, ?, ?);",
                   session["user_id"], request.form.get("symbol"), request.form.get("shares"), lookup(request.form.get("symbol"))["price"], datetime.now())

        flash("Stock sold")
        return redirect("/")

    else:
        stocks = db.execute("SELECT stock FROM wallet WHERE user_id=?;", session["user_id"])
        return render_template("sell.html", stocks=stocks)