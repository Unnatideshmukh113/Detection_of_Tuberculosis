from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import tensorflow as tf
import numpy as np
import cv2
import os
import datetime

app = Flask(__name__)
mysql = MySQL(app)

app.secret_key = 'tube'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'tube'
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_FOLDER'] = 'static/uploads'

@app.route('/')
def index():
    msg = request.args.get('msg')
    if msg:
        return render_template('index.html', msg=msg)
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST' and 'name' in request.form and 'email' in request.form and 'password' in request.form and 'mobile' in request.form:
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        mobile = request.form['mobile']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        #cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        data = cursor.fetchone()
        if data:
            msg = 'User Already Exists, Please Try to Use Another Email Id.'
            return redirect(url_for('index', msg=msg))
        else:
            cursor.execute('INSERT INTO users VALUES (NULL,%s, %s, %s, %s)', (name, email, password, mobile))
            mysql.connection.commit()
            msg = 'You have been registered successfully!'
            return redirect(url_for('index', msg=msg))

    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        data = cursor.fetchone()
        if data:
            session['email'] = email
            session['id'] = data['id']
            session['loggedin'] = True
            return redirect(url_for('dashboard'))
        else:
            msg = 'Invalid login details. Please type valid input details.'
            return redirect(url_for('index',msg=msg))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('id',None)
    session.pop('email',  None)
    session.pop('loggedin',None)
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    return render_template('dashboard.html')

@app.route('/prevention')
def prevention():
    return render_template('prevention.html')

@app.route('/report')
def report():
    return render_template('report.html')

def predict_class(path):
    img = cv2.imread(path)
    RGBImg = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
    RGBImg= cv2.resize(RGBImg,(224,224))
    image = np.array(RGBImg) / 255.0
    new_model = tf.keras.models.load_model("64x3-CNN.model")
    predict=new_model.predict(np.array([image]))
    per=np.argmax(predict,axis=1)
    if per==1:
        return 'The result from uploaded X-Ray image is "Tuberculosis found'
    else:
        return 'The result from uploaded X-Ray image is "No Tuberculosis found'

@app.route('/upload', methods=['GET','POST'])
def upload():
    if request.method == 'POST':
        f = request.files['file']
        if f and f.filename.endswith('.png'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
            f.save(file_path)
            predict = predict_class(file_path)
            current_datetime = datetime.datetime.now()
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO user_history VALUES (NULL,%s, %s, %s, %s)', (session['id'], file_path, predict, current_datetime))
            mysql.connection.commit()
            return render_template('upload-file.html', file_path=file_path, file_result=predict)
    return render_template('upload-file.html')

@app.route('/history', methods=['GET','POST'])
def history():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM user_history WHERE user_id = %s", (session['id'],))
    all_data = cursor.fetchall()
    return render_template('view-history.html',all_data=all_data)

def get_image_address(image_path):
    image_path = image_path.replace("\\", "/")
    return image_path
app.jinja_env.globals.update(get_image_address=get_image_address)