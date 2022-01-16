import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():

    stocks = db.execute("SELECT * FROM stocks WHERE user_id = :user_id ORDER BY symbol ASC", user_id=session["user_id"])
    user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
    grand_total = 0.0

        
    for i in range(len(stocks)):
        stock = lookup(stocks[i]["symbol"])
        stocks[i]["comp_name"] = stock["name"]
        stocks[i]["cur_price"] = "%.2f"%(stock["price"])


        stocks[i]["cur_total"] = "%.2f"%(float(stock["price"]) * float(stocks[i]["quantity"]))
        stocks[i]["profit"] = "%.2f"%(float(stocks[i]["cur_total"]) - float(stocks[i]["total"]))
        grand_total += stocks[i]["total"]
        stocks[i]["total"] = "%.2f"%(stocks[i]["total"])

    grand_total += float(user[0]["cash"])

    return render_template("index.html", stocks=stocks, cash=usd(user[0]["cash"]), grand_total=usd(grand_total))



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure a symbol and shares were submited
        if not request.form.get("symbol") or not request.form.get("shares") or int(request.form.get("shares")) < 1:
            return render_template("buy.html")

        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        user_id = session["user_id"]

        # lookup the stock
        stock = lookup(symbol)

        # ensure symbol exists
        if not stock:
            return apology("symbol not found")

        # calculate total price
        total_price = float(stock["price"]) * float(shares)

        user = db.execute("SELECT * FROM users WHERE id = :id", id=user_id)
        funds = float(user[0]["cash"])

        # check if user has enough funds
        if funds < total_price:
            return apology("not enough funds","available: " + str("%.2f"%funds))

        funds_left = funds - total_price

        # check if symbol is already owned
        stock_db = db.execute("SELECT * FROM stocks WHERE user_id = :user_id AND symbol = :symbol",
                            user_id=user_id, symbol=symbol)

        # update with new price if already owned
        if len(stock_db) == 1:

            new_shares = int(stock_db[0]["quantity"]) + int(shares)



            db.execute("UPDATE users SET shares = :shares WHERE id = :user_id AND symbol = :symbol",
                        shares=new_shares, user_id=user_id, symbol=symbol)
            db.execute("UPDATE stocks SET quantity = :quantity,total=:total WHERE user_id = :user_id AND symbol = :symbol",
                        quantity=new_shares, total=total_price,user_id=user_id, symbol=symbol)
        # else create a new entry in db
        else:

            db.execute("UPDATE users SET symbol=:symbol, shares=:shares where id =:id",symbol=symbol,shares=shares,id=user_id)
            db.execute("insert into stocks values(:user_id,:price, :quantity,:total,:symbol)",user_id=user_id,price =stock['price'],quantity=shares,total=total_price,symbol=symbol)  #insert into the stoks table a new stock
        # modify available funds
        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=funds_left, id=user_id)

        # commit to history
        #db.execute("INSERT INTO history (user_id, action, symbol, shares, pps) VALUES (:user_id, :action, :symbol, :shares, :pps)",
         #           user_id=user_id, action=1, symbol=symbol, shares=shares, pps=stock["price"])

        # send a success message
        return redirect("/")
        #return render_template("index.html", action="bought", shares=shares,
         #                       name=stock["name"], total=usd(total_price), funds=usd(funds_left))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")





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
            return apology("must provide 678 password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        print(session["user_id"])
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
    """Get stock quote."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # ensure stock was submited
        if not request.form.get("quote"):
            return apology("must provide symbol")
        else:
            if not lookup(request.form.get("quote")):
                return apology("must provide valid symbol")


        stock=lookup(request.form.get("quote"))
        #symbol=stock["symbol"]
        #name=stock["name"]
        price=stock["price"]
        return render_template("quoted.html", symbol=stock["symbol"], name=stock["name"], price=stock["price"])

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submited
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submited
        elif not request.form.get("password") and not request.form.get("retype_password"):
            return apology("must provide password and confirmation")

        # ensure passwords match
        elif request.form.get("password") != request.form.get("retype_password"):
            return apology("passwords do not match")

        # ensure username is unique
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        if len(rows) >= 1:
            return apology("username already exists")


        # add user to database
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                    username=request.form.get("username"),
                    hash=generate_password_hash(request.form.get("password")))

        # login user automatically and remember session
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        session["user_id"] = rows[0]["id"]
        print(session["user_id"])
        # redirect to home page
        return redirect("/")

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    stocks = db.execute("SELECT * FROM users WHERE username = :username", username=session["user_id"])

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure quantity was submited
        if not request.form.get("quantity") or int(request.form.get("quantity")) < 1:
            return render_template("sell.html", stocks=stocks)

        user_id = session["user_id"]
        symbol = request.form.get("symbol").upper()
        quantity = request.form.get("quantity")

        # retrieve stock from db
        stock_db = db.execute("SELECT * FROM stocks WHERE user_id = :user_id AND symbol = :symbol",user_id=user_id, symbol=symbol)
        if stock_db:
            stock_db = stock_db[0]
        else:
            return render_template("sell.html", stocks=stocks)

        # retrieve user data from db
        user = db.execute("SELECT * FROM users WHERE id = :id", id=user_id)

        # ensure quantity to be sold is available
        if int(quantity) > stock_db["quantity"]:
            return apology(top="not enough shares", bottom="available: " + str(stock_db["quantity"]))

        # lookup the stock to get current price
        stock = lookup(symbol)

        # calculate total price
        total_price = float(stock["price"]) * float(quantity)

        # modify number of shares owned or delete if < 1
        if int(quantity) == stock_db["quantity"]:
            db.execute("DELETE FROM stocks WHERE user_id = :user_id AND symbol = :symbol", userid=user_id, symbol=symbol)
        else:
            new_quantity = int(stock_db["quantity"]) - int(quantity)
            new_total = float(new_quantity) * float(stock["price"])
            db.execute("UPDATE stocks SET quantity = :quantity, total = :total WHERE user_id = :user_id AND symbol = :symbol",
                        quantity=new_quantity, total=new_total, user_id=user_id, symbol=symbol)

        # modify available funds
        funds_available = float(user[0]["cash"]) + total_price
        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=funds_available, id=user_id)

        # commit to history
        #db.execute("INSERT INTO history (user_id, action, symbol, quantity, pps) VALUES (:user_id, :action, :symbol, :quantity, :pps)",
                    #user_id=user_id, action=0, symbol=symbol, quantity=quantity, pps=stock["price"])

        # send a success message
        return render_template("success.html", action="sold", quantity=quantity,
                                name=stock["name"], total=usd(total_price), funds=usd(funds_available))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("sell.html", stocks=stocks)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

#rows = db.execute("SELECT * FROM users WHERE username = ?",'eleena')
#session["user_id"] = rows[0]["id"]
#print(session["user_id"])
