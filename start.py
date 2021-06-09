import mysql.connector
from flask import Flask, render_template,request, redirect, url_for, session
import bcrypt
import smtplib
import jwt
from PIL import Image
import base64
from io import BytesIO
import PIL.Image
import matplotlib.pyplot as plt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
SECRET_KEY = 'your_secret_key_for_jwt'
algorithm = 'HS256'

class Database():
    def __init__(self):
        self.db=mysql.connector.connect(host="0.0.0.0", user="jp", passwd="1234", database="seon",use_unicode=True, charset='utf8mb4')
        self.cursor =self.db.cursor()
        
    
            
    def imageShow(self):
        sql='select*from image'
        self.cursor.execute(sql)
        result= self.cursor.fetchall()
        
        imgFile=result[-1][1].decode("UTF-8")
        return(imgFile)
    def imageInsert(self,img):
        data=Database()
        sql ='INSERT INTO image (`img`) VALUES (%s)'
        self.cursor.execute(sql,(img,))
        self.db.commit()
        data.sendEmail()
 
    def waveInsert(self,date,value):
        sql = """insert into wave values (%s,%s)"""
        self.cursor.execute(sql,(date,value))
        self.db.commit()
    def waveShow(self):
        sql='SELECT * FROM wave'
        self.cursor.execute(sql)
        result = self.cursor.fetchall()
       
        return(result)    
        
    def login(self):
        msg=''
        if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
            data=Database()
            username = request.form['username']
            password = request.form['password']
            sql="SELECT COUNT(username) as cnt FROM accounts"
            self.cursor.execute(sql)
            row = self.cursor.fetchone()
            count='SELECT * FROM accounts WHERE username = %s'
            self.cursor.execute(count,(username,))
            usercheck=self.cursor.fetchone()
            print("userCheck",usercheck)
           
            if usercheck is not None:
                account,check_password = data.login_check(username, password)
                if account and check_password:
                      
                    session['loggedin'] = True
                    session['id'] = account[0]
                    session['username'] = account[1]
                    print(session)
                    fromip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
                    data = Database()
                    data.updateIp(fromip, account[0])
                
                    return redirect(url_for('index'))
            
                else:
                    msg="Login Fail"
            else:
                msg="Login Fail"
                
        if 'loggedin' in session:
            
            return redirect(url_for('index'))
        
        return render_template('login.html',list=msg)
    
    
    def pfl(self):
        
        if 'loggedin' in session:
            sql='SELECT * FROM accounts WHERE id = %s'
            self.cursor.execute(sql, [session['id']])
            account = self.cursor.fetchone()
            return render_template('profile.html', account=account)
    
        return redirect(url_for('login'))
    
    
    def updateIp(self,fromip,userid):
        sql="""UPDATE accounts SET fromip ="%s" WHERE id = %s"""
        self.cursor.execute(sql, (str(fromip), userid))
        self.db.commit()
        
    def login_check(self,input_username, input_password):
        input_password = input_password.encode('utf-8')
        sql ='SELECT * FROM accounts WHERE username = %s'
        self.cursor.execute(sql, [input_username])
        account = self.cursor.fetchone()
        check_password = bcrypt.checkpw(input_password, account[2].encode('utf-8'))
        return account, check_password
    
    def useradd(self,username, password, email):
        password = (bcrypt.hashpw(password.encode('UTF-8'), bcrypt.gensalt())).decode('utf-8')
        sql="INSERT INTO accounts (`username`, `password`, `email`) VALUES (%s, %s, %s)"
        self.cursor.execute(sql, (username, password, email))
        self.db.commit()
        
    def check_username_exist(self,username):
        sql = 'SELECT * FROM accounts where username=%s'
        self.cursor.execute(sql,(username,))
        account = self.cursor.fetchall()
        print(account)
        return account
    
    def check_email_exist(self,email):
        sql = 'SELECT * FROM accounts where email=%s'
        self.cursor.execute(sql,(email,))
        account = self.cursor.fetchall()
        print(account)
        return account
    
    def signup(self):
        msg=''
       
        if 'loggedin' in session:
            return redirect(url_for('index'))
        if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
            db=Database()
            username = request.form['username']
            password = request.form['password']
            email = request.form['email']
            aleadyUser=db.check_username_exist(username)
            aleadyEmail=db.check_email_exist(email)
            if aleadyUser:
                msg = '이미 사용중인 아이디입니다'
            elif aleadyEmail:
                msg = '이미 사용중인 이메일입니다'
            
            else:
                db.useradd(username, password, email)
                print('success')
                return redirect(url_for('loginP'))
        return render_template('signup.html', msg=msg)
    
        
if (__name__ == '__main__'):
    db=Database()
    db.show()