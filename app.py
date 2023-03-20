from flask import Flask, escape, request, render_template, jsonify, session, redirect, make_response, send_from_directory
import pickle
import numpy as np
from PIL import Image
from io import BytesIO
import tensorflow as tf
import pymongo
from passlib.hash import pbkdf2_sha256
import uuid
from functools import wraps
import pdfkit
import os

# Database

client = pymongo.MongoClient('mongodb+srv://codejay:codejay@jaydatabase.yczkjho.mongodb.net/?retryWrites=true&w=majority')
print(client)
db = client.vegetables

# Decorators
def login_required(f):
  @wraps(f)
  def wrap(*args, **kwargs):
    if 'logged_in' in session:
      return f(*args, **kwargs)
    else:
      return redirect('/login')
  
  return wrap

model_potato = tf.keras.models.load_model("./models/potato/1")
model_tomato = tf.keras.models.load_model("./models/tomato/1")
model_pepper = tf.keras.models.load_model("./models/pepper_bell/1")
class_name_potato = ["Early Blight", "Late Blight", "Healthy"]
class_name_pepper_bell = ["Bacterial spot", "Healthy"]
class_name_tomato = ['Tomato_Bacterial_spot',
 'Tomato_Early_blight',
 'Tomato_Late_blight',
 'Tomato_Leaf_Mold',
 'Tomato_Septoria_leaf_spot',
 'Tomato_Spider_mites_Two_spotted_spider_mite',
 'Tomato__Target_Spot',
 'Tomato__Tomato_YellowLeaf__Curl_Virus',
 'Tomato__Tomato_mosaic_virus',
 'Tomato_healthy']

def read_file_as_image(data):
    image = np.array(Image.open(BytesIO(data)))
    return image

def start_session(user):
    del user['password']
    session['logged_in'] = True
    session['user'] = user
    return jsonify(user), 200

app = Flask(__name__)
app.secret_key = b'\xcc^\x91\xea\x17-\xd0W\x03\xa7\xf8J0\xac8\xc5'

@app.route('/')
@login_required
def home():
    return render_template("index.html")

@app.route('/about')
@login_required
def about():
    return render_template("about.html")

@app.route('/contact')
@login_required
def contact():
    return render_template("contact.html")

@app.route('/output')
@login_required
def output():
    return render_template("output.html")

@app.route('/potato', methods=['POST'])
@login_required
def potato():
    if request.method == "POST":
        f = request.files['image']
        data = f.read()
        image = read_file_as_image(data)
        img_batch = np.expand_dims(image, 0)

        predictions = model_potato.predict(img_batch)
        predicted_class = class_name_potato[np.argmax(predictions[0])]
        confidence = np.max(predictions[0])
        print("potato")
        return render_template("output.html", veg = "Potato Plant", confidence=str(confidence), prediction=str(predicted_class))

@app.route('/pepperbell', methods=['POST'])
@login_required
def pepperbell():
    if request.method == "POST":
        f = request.files['image']
        data = f.read()
        image = read_file_as_image(data)
        img_batch = np.expand_dims(image, 0)

        predictions = model_pepper.predict(img_batch)
        predicted_class = class_name_pepper_bell[np.argmax(predictions[0])]
        confidence = np.max(predictions[0])
        return render_template("outputpepper.html", veg = "Pepper Bell Plant", confidence=str(confidence), prediction=str(predicted_class))

@app.route('/tomato', methods=['POST'])
@login_required
def tomato():
    if request.method == "POST":
        f = request.files['image']
        data = f.read()
        image = read_file_as_image(data)
        img_batch = np.expand_dims(image, 0)

        predictions = model_tomato.predict(img_batch)
        predicted_class = class_name_tomato[np.argmax(predictions[0])]
        confidence = np.max(predictions[0])
        return render_template("outputtomato.html", veg = "Tomato Plant", confidence=str(confidence), prediction=str(predicted_class))
    
@app.route('/outputtomato')
@login_required
def outputt():
    return render_template("outputtomato.html")
    
@app.route('/outputpepper')
@login_required
def outputp():
    return render_template("outputpepper.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    # print(client)
    if request.method == "POST":

        user = db.users.find_one({
          "email": request.form.get('email')
        })
        # print(user)
        # print(request.form.get('password'))
        # print(user['password'])
        if user and pbkdf2_sha256.verify(request.form.get('password'), user['password']):
            start_session(user)
            return render_template("index.html")
        else:
            status = "Invalid login credentials"
            print(status)
            return render_template("login.html", status=status)
    else:
        return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        user = {
            "_id": uuid.uuid4().hex,
            "name": request.form.get('fullname'),
            "username": request.form.get('username'),
            "email": request.form.get('email'),
            "password": request.form.get('password'),
            "confirmpassword": request.form.get('confirmpassword')
            }
        print("get data")

        # Encrypt the password
        user['password'] = pbkdf2_sha256.hash(user['password'])
        user['confirmpassword'] = pbkdf2_sha256.hash(user['confirmpassword'])

        print("database")

        # Check for existing email address
        if db.users.find_one({ "email": user['email'] }):
            status = "Email Address is already exit !"
            print(status)
            return render_template("register.html", status=status)

        else:
            if db.users.insert_one(user) :
                start_session(user)
            status = "Registration successfull !"
            print(status)
            return render_template("login.html")
    else:
        return render_template("register.html")
        


@app.route('/detection', methods=['GET', 'POST'])
@login_required
def detection():
    return render_template("detection.html")

@app.route('/tomatoreport/')
@login_required
def tomatoreport():
    try:
        confidence = request.args["confidence"]
        predicted_class = request.args["predicted_class"]

        rendered =  render_template("potatoreport.html", veg = "Tomato Plant", confidence=str(confidence), prediction=str(predicted_class))
        config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
        pdfkit.from_string(rendered, "report.pdf",  configuration=config)
        print("report generated")

    except:
        return render_template("Reportgenerated.html")
    
@app.route('/potatoreport/')
@login_required
def potatoreport():
    try:
        confidence = request.args["confidence"]
        predicted_class = request.args["predicted_class"]

        rendered =  render_template("potatoreport.html", veg = "Potato Plant", confidence=str(confidence), prediction=str(predicted_class))
        config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
        pdfkit.from_string(rendered, "report.pdf",  configuration=config)
        print("report generated")

    except:
        return render_template("Reportgenerated.html")
    
@app.route('/pepperbellreport/')
@login_required
def pepperbellreport():
    try:
        confidence = request.args["confidence"]
        predicted_class = request.args["predicted_class"]

        rendered =  render_template("potatoreport.html", veg = "Pepper Bell Plant", confidence=str(confidence), prediction=str(predicted_class))
        config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
        pdfkit.from_string(rendered, "report.pdf",  configuration=config)
        print("report generated")

    except:
        return render_template("Reportgenerated.html")

@app.route("/openpdf")
@login_required
def openpdf():
    workingdir = os.path.abspath(os.getcwd())
    return send_from_directory(workingdir, 'report.pdf')

if __name__ == '__main__':
    app.debug = True
    app.run()