# coding: UTF-8

import serial
import time
import tkinter.messagebox

class Usb_rs:

    def __init__(self, gui=False):
        self.ser = serial
        self.gui = gui
    
    #Open port
    def open(self, port, speed):
        ret = False

        try:
            self.ser = serial.Serial(port, speed,timeout=0)
            ret = True
        except Exception as e:
            if self.gui == True:
                tkinter.messagebox.showerror("Open Error", e)
            else:
                print("Open error")
                print(e)
        
        return ret

    #Close port
    def close(self):
        ret = False

        try:   
            self.ser.close()
            ret = True
        except Exception as e:
            if self.gui == True:
                tkinter.messagebox.showerror("Close Error", e)
            else:
                print("Close error")
                print(e)
        
        return ret
    #Send command
    def sendMsg(self, strMsg):
        ret = False

        try:
            strMsg = strMsg + '\r\n'                #Add a terminator, CR+LF, to transmitted command
            self.ser.write(bytes(strMsg, 'utf-8'))  #Convert to byte type and send
            ret = True
        except Exception as e:
            if self.gui == True:
                tkinter.messagebox.showerror("Send Error", e)
            else:
                print("Send Error")
                print(e)

        return ret
    
    #Receive
    def receiveMsg(self, timeout):

        msgBuf = bytes(range(0))                    #Received Data

        try:
            start = time.time()                     #Record time for timeout
            while True:
                if self.ser.inWaiting() > 0:        #Is exist the data in the receive buffer?
                    rcv = self.ser.read(1)          #Receive 1 byte
                    if rcv == b"\n":                #End the loop when LF is received
                        msgBuf = msgBuf.decode('utf-8')
                        break
                    elif rcv == b"\r":              #Ignore the terminator CR
                        pass
                    else:
                        msgBuf = msgBuf + rcv
                
                #Timeout processing
                if  time.time() - start > timeout:
                    msgBuf = "Timeout Error"
                    break
        except Exception as e:
            if self.gui == True:
                tkinter.messagebox.showerror("Receive Error", e)
            else:
                print("Receive Error")
                print(e)
            msgBuf = "Error"

        return msgBuf
    
    #Transmit and receive commands
    def SendQueryMsg(self, strMsg, timeout):
        ret = Usb_rs.sendMsg(self, strMsg)
        if ret:
            msgBuf_str = Usb_rs.receiveMsg(self, timeout)   #Receive response when command transmission is succeeded
        else:
            msgBuf_str = "Error"

        return msgBuf_str



