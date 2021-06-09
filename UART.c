#define F_CPU        16,000,000UL
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
 
#define STX        0x5F		//	 ‘_’
#define ETX        0x2F		// 	‘/’
#define r        0x72		// 	‘r’
#define l        0x6C		//	 ‘l’

void UART_Init(void);		// UART 초기화
void UART_TX_CH(char c);		// 문자 보내기
void UART_TX_STR(char *s); 	// 문자열 보내기 
 
char rx_buf[20], rx_cnt = 0;	// 버퍼(rx), 카운터(rx)
char tx_buf[20], tx_cnt = 0;	// 버퍼(tx), 카운터(tx)

volatile char rx_flag = 0;		// 플래그(rx)
int du_R=0, du_L = 0;		// 오른쪽(R), 왼쪽(L) PWM 저장 변수.

// UART Initiallize
 void PWM_init() {					// PWM 초기화
    DDRD |= (1 << PD5);					// PD5 pin output활성화
    DDRD |= (1 << PD6);					// PD6 pin 활성화
    TCCR0A |= (1 << WGM01) | (1 << WGM00);		// 파형 설정
    TCCR0A |= (1 << COM0A1);				// 비반전 모드
    TCCR0A |= (1 << COM0B1);				// 비반전 모드
    TCCR0B |= (1 << CS02);				// 64 분주비 설정
 }
 void PWM_PD5(int duty) {				// PD5 듀티비 설정.
    OCR0B = duty;					// OCR0B: 듀티비 저장 레지스터
 }
 void PWM_PD6(int duty) {				// PD6 듀티비 설정.
    OCR0A = duty;					// OCR0A: 듀티비 저장 레지스터
 }
void UART_Init(void) {					// UART 초기화
    UCSR0A = 2;						// 2배속 모드 설정.
    UCSR0B = (1<<RXCIE0) | (1<<RXEN0) | (1<<TXEN0);	// RX INT enable, RX & TX Enable
    UCSR0C = (1<<UCSZ01) | (1<<UCSZ00);		// 8bit (no parity)
    UBRR0H = 0;	 	UBRR0L = 207;			// 9600 보드레이트 설정
}

 void Init_74595       (void) {				// shift 레지스터 초기화
    DDRB |= 0b00111000;				// pin OUTPUT 설정.
 }

 void ShiftClock(void) {	// atmega328과 시프트 레지스터가 박자에 맞춰 데이터를 전송할 수 있도록 클럭 신호를 전송.
    PORTB  |= 0b00100000;		// 비트마스크를 이용한 한 펄스 입력(HiGH)
    PORTB &= 0b11011111;		// 비트마스크를 이용한 한 펄스 입력(LOW)
 }
 void LatchClock(void) {		// 시프트 레지스터가 수신한 데이터를 래치 레지스터(핀 제어값 저장공간)에 저장
    PORTB  |= 0b00010000;		// 비트마스크를 이용한 한 펄스 입력(HiGH)
    PORTB &= 0b11101111;		// 비트마스크를 이용한 한 펄스 입력(LOW)
 }
 void ByteDataWrite(uint8_t data) {		// 데이터 쓰기
    for(uint8_t i =0; i<8; i++) {
       if(data & 0b10000000)	// 최상위 비트와 일치
       PORTB |= 0b00001000;	// data pin (HIGH)
       else
       PORTB &= 0b11110111;	// data pin (LOW) 
       ShiftClock();		// 데이터 전송 클럭 신호 전송.
       data = data << 1;		// data shift
    }
    LatchClock();			// 수신한 데이터를 래치 레지스터에 저장.
 }
 //  UART 문자 출력
void UART_TX_CH(char c) {
    while(!(UCSR0A & (1<<UDRE0)));	// 정보를 받을 수 있는 상태면 while문 탈출
    UDR0 = c;			     	// 버퍼(데이터를 전송할 정보를 담는 버퍼)에 문자 송신.
}

 // UART 문자열 출력
void UART_TX_STR(char *s) {
   for(int i=0; i<strlen(s); i++ ) {		// 문자열 길이 만큼 반복
      UART_TX_CH(*(s+i));		// 주소 값 이동하며, 문자 입력. 
   }
   memset(s, 0, sizeof(*s) * strlen(s));	// 문자열 NULL 초기화
}

 // UART Receive Interrupt
ISR(USART_RX_vect) {
    int i;
    char rxdata;				// 문자 받는 변수
    rxdata = UDR0;			// 문자 수신.
    if(!rx_flag) {				// ‘rx_flag’ 비활성화 시 수행
      	//_  // l 1 r 100
        if(rxdata == STX) { }		// 변수가 ‘_’ 일 때
        
      // ‘/’
        else if(rxdata == ETX) {			// 변수가 ‘/’ 일 때
            for(i=0; (i<rx_cnt) && (i<15); i++) {
                tx_buf[i] = rx_buf[i];		// 버퍼(rx)의 값을 버퍼(tx)에 저장
                rx_buf[i] = NULL;			// ‘버퍼(rx)를 ‘NULL’로 초기화
            }
            rx_cnt = 0;				// 카운트 변수(rx) 초기화
            rx_flag = 1;				// ‘rx_flag’ 활성화
        }
        else {
            rx_buf[rx_cnt] = rxdata;		// 버퍼(rx)에 ‘rxdata’ 입력: (l,□,□,□,r,□,□,□)
            rx_cnt++;				// 카운트(rx)
      }
   }
}

int main(void) {
   int cnt_r = 0;		//왼쪽(l) PWM의 길이를 구하는 변수.
   int cnt_e = 0;		//오른쪽(r) PWM의 길이를 구하는 변수.
   
    UART_Init();			// UART 초기화
    PWM_init();			// PWM 초기화
    Init_74595();			// Shift Resister 초기화
    ByteDataWrite(0b00000000);	// Shift Resister data(0x00) 초기화
    sei();			// 인터럽트 발생을 전역적으로 허용

   // l17r237	l123r125
   while (1) {
        if(rx_flag) {				// ‘rx_flag’ 활성화 시
         // l80r80
               // while(tx_buf)
               for(int i =0; i<20; i++) {
                  if(tx_buf[i] == r) {		// ‘tx_buf[i]’의 문자가 ‘r’이면
                     cnt_r = i;			// ‘r’ 문자의 인덱스 저장
                  }
                  if(tx_buf[i] == NULL) {		// ‘tx_buf[i]’의 문자가 ‘NULL’이면
                     cnt_e = i;			// ‘NULL’ 문자의 인덱스 저장
                     break;			// 구문 탈출.
                  }    
               }
               char* buf_L = malloc(sizeof(char) * (cnt_r-1));		//동적 메모리할당(사이즈: l_PWM)
               char* buf_R = malloc(sizeof(char) * (cnt_e-cnt_r-1));	//동적 메모리할당(사이즈: r_PWM)
		// l000r000
               for(int i = 0; i < cnt_r-1;i++) {	// ‘r’문자 전 index까지 반복
                  *(buf_L + i) = tx_buf[i+1];	// 왼쪽 PWM 저장.
               } 
               for(int i = 0; i <cnt_e-cnt_r-1;i++) {	// ‘NULL’문자 전 index까지 반복
                  *(buf_R + i) = tx_buf[cnt_r+1+i];	// 오른쪽 PWM 저장.
               }
                du_L = atoi(buf_L);	// 문자열(PWM)을 int 자료형으로 변환 및 저장
                du_R = atoi(buf_R);	// 문자열(PWM)을 int 자료형으로 변환 및 저장
                cnt_r=0;			// 카운터 변수 초기화
                cnt_e=0;			// 카운터 변수 초기화
                
                ByteDataWrite(0b00000101);	// 시프트 레지스터 이진 입력.
                PWM_PD5(du_L);			// 오른쪽 PWM 입력
                PWM_PD6(du_R);			// 왼쪽 PWM 입력

                UART_TX_CH('_');			// 문자 데이터 UART TX 송신
                UART_TX_CH('L');			// 문자 데이터 UART TX 송신
                UART_TX_STR(buf_L);		// 문자열(PWM) 데이터 UART TX 송신
                UART_TX_CH('R');			// 문자 데이터 UART TX 송신
                UART_TX_STR(buf_R);		// 문자열(PWM) 데이터 UART TX 송신
                UART_TX_CH('/');			// 문자 데이터 UART TX 송신
                rx_flag = 0;			// ‘rx_flag’ 비활성화
                free(buf_L);			// 동적 메모리 해제
                free(buf_R);			// 동적 메모리 해제
                   }	// rx_flag
              }		// while(1)
   return 0;
}
