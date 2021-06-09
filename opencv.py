import sys
import cv2
import serial
import time
import math
import numpy as np
import RPi.GPIO as gpio
import threading
from start import Database
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

ser = serial.Serial('/dev/ttyAMA0',9600) # UART ‘ser’ 객체 생성
cap = cv2.VideoCapture(0) #카메라 설정
maxv2_flag = 0 #표지판 인지 플래그 (플래그 작동 시 표지판 검출안함)
maxv2_count = 0 #표지판 인지 프레임 수(50프레임동안 -10 속도) 
pic_num = 0 #사진이름 넘버링
distance = 0 #초음파거리
ex_Dir=[0] #이전 방향값을 저장

def Email():
    global pic_num
    imgRows="/home/pi/final/cap{0}.jpg".format(pic_num)  #사진경로
        
    if imgRows is not None: # 사진경로에 사진있다면 
        fromEmail='pjp9157@gmail.com'
        toEmail='tkdrlf765@naver.com'
        smtp=smtplib.SMTP('smtp.gmail.com',587) #SMTP 서버명, 포트
        smtp.starttls() #보안
        smtp.login('pjp9157@gmail.com','pepuqfdpookxmnhc')
        msg=MIMEMultipart() #여러 MIME을 넣기위한 MIMEMultipart 객체 생성
        message=MIMEText('라즈베리파이에서 사진파일을 발송하였습니다.',_charset='utf-8')#메일 내용
        msg['Subject']= '라즈베리파이에서 보낸 메일'#제목
        msg['from']= fromEmail
        msg['To']=toEmail
        msg.attach(message)#msg에 message 담기
            
        with open(imgRows,'rb') as test: # 이미지 파일열기
            etcPart= MIMEApplication(test.read())#바이너리 파일 읽기
            etcPart.add_header('Content-Disposition','attachment', filename=imgRows)#첨부파일의 정보를 헤더로 추가
            msg.attach(etcPart)
            smtp.sendmail(fromEmail,toEmail,msg.as_string())
            smtp.quit()
            pic_num += 1
                  
def ultra_dis():					# 초음파 센서
    global distance
    gpio.setmode(gpio.BCM)				# BCM모드 : pin 번호를 GPIO 모듈 번호 사용
    trig = 13						# 송신부 GIOP 13 pin 사용
    echo = 19						# 수신부 GIOP 19 pin 사용
    print ("start")
    gpio.setup(trig, gpio.OUT)			# pin OUTPUT 설정
    gpio.setup(echo, gpio.IN)			# pin  INPUT 설정
    db=Database()					# ‘db’ 객체 생성
    
    try :
        while True :
            now = time.localtime()			# 표준 시간대의 현지 시간을 반환
            nowtime =("%04d/%02d/%02d %02d:%02d:%02d" % (now.tm_year,now.tm_mon,now.tm_mday,now.tm_hour,now.tm_min,now.tm_sec))		# “년/월/일 시간:분:초”를 nowtime에 저장
            gpio.output(trig, False)		# 송신부 OFF
            time.sleep(0.5)
            gpio.output(trig, True)		# 송신부 신호(HIGH)
            time.sleep(0.00001)
            gpio.output(trig, False)		# 송신부 신호(LOW)
            
            while gpio.input(echo) == 0 :			# 수신부 비활성화 시,
                pulse_start = time.time()			# 신호 송신 초기 시간 저장
            while gpio.input(echo) == 1 :			# 수신부 활성화 시
                pulse_end = time.time()			# 수시부 초음파 감지 시간 저장
            pulse_duration = pulse_end - pulse_start	# 소요시간 계산
            distance = pulse_duration * 17000		# 거리 계산
            distance = round(distance, 2)			# 데이터 소수점 2번째 자리까지 저장
            if distance <10:
                cv2.imwrite('cap'+str(pic_num)+'.jpg', frame)	# 사진(cap(숫자).jpg) 저장
                Email()						# 이메일 발송
            print("Distance : ", distance, "cm")			# 거리(단위:cm) 화면 출력
            db.waveInsert(nowtime,distance)			# db에 촬영시간, 거리 저장
            
            
    except :					# 예외 처리
        gpio.cleanup()			# GPIO 라이브러리/모듈이 점유한 리소스를 해제




def camera_init(): # 카메라를 열고 기본적인 정보들을 출력합니다.
    if not cap.isOpened(): 
        print("Camera open failed!")
        sys.exit()  # 카메라 못찾을 시 프로그램 종료
    print('Frame width:', int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))) #프레임 너비
    print('Frame height:', int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))) #프레임 높이
    fps = round(cap.get(cv2.CAP_PROP_FPS)) # 분 당 프레임 수
    delay = round(1000/fps) #프레임 간격 시간
    print('delay:',delay)


def find_Dir_and_rec_load(frame):
    total = 0 # 도로인자(픽셀)의 번호의 합
    count = 1 # 도로인자(픽셀) 갯수
    center_x = [] # 도로 중심의 X좌표의 리스트 
    center_y = [] # 도로 중심의 y좌표의 리스트
    #global Dir
    HSV_frame = cv2.cvtColor(frame,cv2.COLOR_BGR2HSV) # RGB -> HSV 이미지 변환
    lower_hsv_1 = cv2.inRange(HSV_frame, (0, 100, 100), (5, 255, 255)) # 최소 색검출
    upper_hsv_2 = cv2.inRange(HSV_frame, (169, 100, 100), (180, 255, 255)) # 최대 색검출
    dst = cv2.addWeighted(lower_hsv_1, 1.0, upper_hsv_2, 1.0, 0.0) #lower_hsv_1 + upper_hsv_2 
    
    for i in range(640):		# 카메라 이미지 넓이(640) x 높이(480)
        if dst.item(479,i) != 0:	# 이진 이미지 픽셀(y좌표, x좌표)이 0(black)이 아니면
            total += i		# i의 총합.
            count += 1		# 나누는 값.
    x_value1 = round(total/count)	# 평균값
    Dir = x_value1 - 320 # 조향할 방향 설정 (차선 중앙의 평균값이 카메라의 정중앙과 가까울수록 Dir=0)
    cv2.circle(frame,(x_value1,479),10,(255,0,255),2,None,0)	# 차선의 중심(평균값)에 원을 그림
    total = 0			# 초기화
    count = 1			# 초기화

    
    for w in range(10): # 선형회귀에서 사용할 도로의 10개의 중점을 찾는다.
        for i in range(640):
            if dst.item(w*45,i) != 0		# 각 높이(45씩 증가)에서 차선의 평균값을 구함
                total += i				# i의 총합.
                count += 1				# 나누는 값.
        center_x.append(round(total/count))	# center_x [list]에 x축 평균값을 추가
        center_y.append(w*45)			# center_y [list]에 y축 위치를 추가
        total = 0		# 초기화
        count = 1		# 초기화

    fit = np.polyfit(center_y,center_x, 2) # 2차 함수로 선형회귀를 구함
    ploty = np.linspace(0, dst.shape[0] - 1, dst.shape[0])
    fitx = fit[0] * ploty ** 2 + fit[1] * ploty + fit[2]
    tx = np.trunc(fitx) 
    pts = np.array([np.transpose(np.vstack([tx, ploty]))])

    for i in range(20):       #인지한 도로를 나타내는 20개의 점 찍기
        po_x,po_y = pts[0,479-i*10,0],pts[0,479-i*10,1]
        po_xx = int(po_x)
        po_yy = int(po_y)   
        cv2.line(frame,(po_xx,po_yy),(po_xx,po_yy),(100,25,150),10,None,0)

    
    cv2.imshow('frame', dst)
    center_x = []
    center_y =[]
    
    return Dir
    
def move_wheel(frame,templ,Dir):
    global maxv2_flag 
    global maxv2_count 
    global ser
    global ex_Dir
    roi = frame[:240,100:540] # 표지판 관심 지역
    cv2.rectangle(roi, (0,0), (440-1,240-1), (0,255,0)) # 관심지역 표시
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    yellow_lower = np.array([20, 20, 100]) 
    yellow_upper = np.array([32, 255, 255]) 
    added_hsv = cv2.inRange(hsv, yellow_lower, yellow_upper)#노랜색 표지판 검출
    if maxv2_flag == 0: #플래그가 0일 때 표지판 검출
        res2 = cv2.matchTemplate(added_hsv, templ, cv2.TM_CCOEFF_NORMED)
        _, maxv2, _, maxloc2 = cv2.minMaxLoc(res2) # 최고 유사정도, 최고 유사이미지 좌표
    dst_t = cv2.cvtColor(added_hsv, cv2.COLOR_GRAY2BGR) # 사각형을 그리기 위해서 bgr로 변경
    if maxv2>0.20 :
        th, tw = templ2.shape[:2]
        cv2.rectangle(dst_t, maxloc2, (maxloc2[0] + tw, maxloc2[1] + th), (0, 255, 0), 2) # 닮은 게 나오면 사각형그리기
    print('maxv2:', maxv2)
    cv2.imshow('dst_t', dst_t)
    if Dir==-320: 
        if ex_Dir[0]>0:
            Dir =320
        elif ex_Dir[0]<0:
            Dir =-320
    print("aaaaaaaaaaaaaaaaaaaaa",ex_Dir)
    ex_Dir.append(Dir)
    ex_Dir.pop(0) #화면에서 완전히 길을 잃었을 경우
    if Dir >=-60 and Dir<=60:
        r_val = 55
        l_val = 55
    elif Dir > 60 and Dir<100:
        r_val = 55
        l_val = 25
    elif Dir <= -60 and Dir> -100:
        r_val = 25
        l_val = 55
    elif Dir <= 149 and Dir >= 100:
        r_val = 150
        l_val = 25
    elif Dir >= -149 and Dir <= -100:
        r_val = 25
        l_val = 150
    elif Dir <= 199 and Dir >= 150:
        r_val = 210
        l_val = 25
    elif Dir >= -199 and Dir <= -150:
        r_val = 25
        l_val = 190
    elif Dir >= 200:
        r_val = 255
        l_val = 20
    elif Dir <= -200:
        r_val = 20
        l_val = 255
        
    if maxv2>0.20: # 표지판 인지시 
        maxv2_count = 0
        maxv2_flag = 1
        maxv2 = 0.0
        
        cv2.imwrite('cap'+str(pic_num)+'.jpg', frame) 
        Email() # 사진찍고 이메일 전송
        
        
       
    if maxv2_flag == 1: 
    
        maxv2_count+=1
        r_val-=10
        l_val-=10
        if maxv2_count >50: # 50프레임동안 표지판 검출 안 함
            maxv2_flag =0
            maxv2_count = 0
    
    if distance < 10:
        r_val = 0
        l_val = 0
    print('Dir',Dir)
    
    cv2.imshow('frame2', frame)
    print(l_val,'    ',r_val)
    force= '_'+'l'+str(l_val)+'r'+str(r_val)+'/'
    ser.write(force.encode())

#요기서 부터 main
camera_init()
t = threading.Thread(target = ultra_dis)
t.start()
cv2.namedWin.imread('temp2.jpg', cv2.IMREAD_GRAYSCALE)
dow('frame',cv2.WINDOW_AUTOSIZE)
templ2 = cv2
while True:
    db=Database()
    ret, frame = cap.read(0)
    if not ret:
        break
    Direction = find_Dir_and_rec_load(frame)
    print('BBBBBB',Direction)
    if cv2.waitKey(33)== 27:
        break
    move_wheel(frame,templ2,Direction)
    '''# UART RX TEST
    a = ser.read()

    if (a==b'_'):

        a = ser.read()

        while a != b'/':

            print(a)

            a = ser.read()

 

        if (a==b'_'):

            while(1):

                temp = ser.read()

                if(temp == b'/'):

                    break

                print(temp) 

        print('=====')

    ''' 
cap.release()
cv2.destroyAllWindows()



