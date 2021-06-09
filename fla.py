from flask import Flask, render_template,request,redirect, url_for,session,Response
from start import Database
import cv2
import time
import cv2
app = Flask(__name__)
video = cv2.VideoCapture(2)
video.set(3,160)
video.set(4,120)

def gen(video):
    while True:
        success, image = video.read()
        ret, jpeg = cv2.imencode('.jpg', image)
        frame = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
@app.route('/video_feed')
def video_feed():
    global video
    return Response(gen(video),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route('/login', methods=['GET', 'POST'])
def loginP():
    
    db=Database()
        
    return db.login()
@app.route('/signup', methods=['GET', 'POST'])
def register():
    db =Database()
    return db.signup()
@app.route('/home',methods=['GET','POST'])
def index():
    
    if request.method =='GET':
        if 'loggedin' in session:
            db=Database()
            sql=db.waveShow()
            img=db.imageShow()
            return render_template('index.html',image=img,list=sql)
    return redirect(url_for('loginP'))
@app.route('/profile')
def profile():
    
    db=Database()
    data = db.pfl()
    return data
@app.route('/logout')
def logout():
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   
   return redirect(url_for('loginP'))

@app.route('/ip', methods=['GET'])
def client_ip():
    return request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    
if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.run(host='0.0.0.0', port=8888, threaded=True)
    