import smbus
import time
import json
import random

import board
import busio
import adafruit_sgp30
import pandas as pd
import sqlite3
import subprocess
from time import sleep
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    flash,
    url_for,
    session
)

from datetime import timedelta
from sqlalchemy.exc import (
    IntegrityError,
    DataError,
    DatabaseError,
    InterfaceError,
    InvalidRequestError,
)
from werkzeug.routing import BuildError


from flask_bcrypt import Bcrypt,generate_password_hash, check_password_hash

from flask_login import (
    UserMixin,
    login_user,
    LoginManager,
    current_user,
    logout_user,
    login_required,
)

from app import create_app,db,login_manager,bcrypt
from models import User
from forms import login_form,register_form
import sqlite3
from flask_socketio import SocketIO
from random import random
from threading import Lock
from datetime import datetime


def sgp():
	

	print("sgp30 serial #",[hex(i) for i in sgp30.serial])
	sgp30.set_iaq_baseline(0x8973,0x8AAE)
	reading=sgp30.eCO2*0.001
	return reading
	

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app = create_app()

@app.before_request
def session_handler():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=1)

def get_db_connection():
	conn=sqlite3.connect('carbon.db')
	conn.row_factory=sqlite3.Row
	return conn

@app.route("/", methods=("GET", "POST"), strict_slashes=False)
def index():
    return render_template("index.html",title="Home")


@app.route("/login/", methods=("GET", "POST"), strict_slashes=False)
def login():
    form = login_form()

    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=form.email.data).first()
            if check_password_hash(user.pwd, form.pwd.data):
                login_user(user)
                return redirect(url_for('success'))
            else:
                flash("Invalid Username or password!", "danger")
        except Exception as e:
            flash(e, "danger")

    return render_template("auth.html",
        form=form,
        text="Login",
        title="Login",
        btn_action="Login"
        )
#---------------------------------------------------------------------------------------------------#
"""
Background Thread
"""
thread = None
thread_lock = Lock()

app.config['SECRET_KEY'] = 'donsky!'
socketio = SocketIO(app, cors_allowed_origins='*')
i2c=busio.I2C(board.SCL,board.SDA,frequency=100000)
sgp30=adafruit_sgp30.Adafruit_SGP30(i2c)

"""
Get current date time
"""

def get_current_datetime(x):

    now = datetime.now()+timedelta(days=x)
    return now.strftime("%Y-%m-%d %H:%M:%S")

def points(sgp_read):
    pts=0
    total=[]
    if(sgp_read!=0.4):
            diff=1.5-sgp_read
            if(diff>=0):
                if(diff<=1):
                    pts=pts+5
                else:
                    pts=pts+10
            else:
                diff=abs(diff)
                if(diff<=1):
                    pts=pts-5
                else:
                    pts=pts-10
    total.append(pts)
    return(total)
"""
Generate random sequence of dummy sensor values and send it to our clients
"""

def background_thread():
    connection=sqlite3.connect("live_data.db")
    cursor=connection.cursor()
    cursor.execute("DROP TABLE IF EXISTS sensor")
    cursor.execute("CREATE TABLE sensor (key text, value text, date text)")
    print("Generating random sensor values")
    data1={}
    key1=0
    data1[key1]=0
    data1={'data':[]}
    x=0
    sum=0
    while True:
        x+=1
        dummy_sensor_value = sgp()
        #dummy_sensor_value=round(random.uniform((1,57),3))
        score=points(dummy_sensor_value)
        for i in score:
            sum=sum+i
        socketio.emit('updateSensorData', {'value': dummy_sensor_value, "date": get_current_datetime(x), 'rewards': sum})
        
        
        data1[key1]=round(dummy_sensor_value,2)
        data2={'key':key1,'value':data1[key1],'date':get_current_datetime(x)}
        ans1=json.dumps(data2)
        json_Dict = json.loads(ans1)
        key= json_Dict['key']
        value= json_Dict['value']
        date= json_Dict['date']
        cursor.execute("INSERT INTO sensor (key,value,date) values (?,?,?)",[key,value,date])
        connection.commit()
        key1=key1+1
        data1['data'].append(data2)

        clients=pd.read_sql(('SELECT * FROM sensor ORDER BY date DESC LIMIT 1'),connection)
        clients.to_csv('datasheet.csv',index=False,mode='a',header=False)
        socketio.sleep(1)
        
        
		

"""
Serve root index file
"""
@app.route('/live_graph')
def live():
    return render_template('app.html')

"""
Decorator for connect
"""
@socketio.on('connect')
def connect():
    global thread
    print('Client connected')

    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)

"""
Decorator for disconnect
"""
@socketio.on('disconnect')
def disconnect():
    print('Client disconnected',  request.sid)

#------------------------------------------------------------------------------------------------------#

@app.route('/success', methods=["POST","GET"])
def success():
	conn=get_db_connection()
	cursor=conn.execute('SELECT * FROM records ORDER BY id DESC LIMIT 1')
	#conn.close()
	#user=request.form.get('username')
	return render_template('dash.html', items=cursor.fetchall())

@app.route('/vouchers', methods=['GET', 'POST'])
def index_func():
    if request.method == 'POST':
        
        return redirect(url_for('success'))
    # show the form, it wasn't submitted
    return render_template('vouchers.html')

# Register route
@app.route("/register/", methods=("GET", "POST"), strict_slashes=False)
def register():
    form = register_form()
    if form.validate_on_submit():
        try:
            email = form.email.data
            pwd = form.pwd.data
            username = form.username.data
            
            newuser = User(
                username=username,
                email=email,
                pwd=bcrypt.generate_password_hash(pwd),
            )
    
            db.session.add(newuser)
            db.session.commit()
            flash(f"Account Succesfully created", "success")
            return redirect(url_for("login"))

        except InvalidRequestError:
            db.session.rollback()
            flash(f"Something went wrong!", "danger")
        except IntegrityError:
            db.session.rollback()
            flash(f"User already exists!.", "warning")
        except DataError:
            db.session.rollback()
            flash(f"Invalid Entry", "warning")
        except InterfaceError:
            db.session.rollback()
            flash(f"Error connecting to the database", "danger")
        except DatabaseError:
            db.session.rollback()
            flash(f"Error connecting to the database", "danger")
        except BuildError:
            db.session.rollback()
            flash(f"An error occured !", "danger")
    return render_template("auth.html",
        form=form,
        text="Create account",
        title="Register",
        btn_action="Register account"
        )

@app.route("/user_profile")
def profile():
    return render_template('user_profile.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == "__main__":
    #app.run(debug=True)
    global x
    socketio.run(app, host='localhost', port=5000)
