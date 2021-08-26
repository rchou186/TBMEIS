###############################################################################
# This Program tests EIS for one module                                       #
# Select the test frequencies from desired frequency file                     #
# Output to MySQL Server for data storage                                     #
# Module to install in pip:                                                   #
# pandas, pyserial, matplotlib, mysql_connector, pyinstaller                  #
###############################################################################

from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import pandas as pd
import os
import base64
import powereign_icon
import usb_rs
import threading
import datetime
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
import mysql.connector
import math

Version = "1.30"
VersionDate = "2021/08/20"

### Debug switches ###
DebugWithoutCom = False

textbox_font = ("Monaco", 10, "bold")

current_path = os.path.abspath(os.getcwd())
configuration_filename = "TBMEIS.cfg"

def CreateIcon():
    if not os.path.isfile('icon.ico'):
        icondata = base64.b64decode(powereign_icon.icon)                    #convert icon base64 date to HEX
        iconfile = open('icon.ico', 'wb')                                   #create icon.ico as temp file
        iconfile.write(icondata)                                            #write icondata to temp file
        iconfile.close()

def Init_BT4560(Comm):
    Comm.sendMsg('*RST')
    Comm.sendMsg('SYSTEM:BEEPER OFF')            
    Comm.sendMsg('FUNCTION RV')          
    Comm.sendMsg('RANGE '+ReadDefault("Range"))           
    Comm.sendMsg('SAMPLE:RATE V,MED')            
    Comm.sendMsg('SAMPLE:RATE Z,MED')            
    Comm.sendMsg('SAMPLE:DELAY:MODE WAVE')            
    Comm.sendMsg('SAMP:DELAY:WAVE 0.5')            
    Comm.sendMsg('LIMITER OFF')            
    Comm.sendMsg('ZERO:CROSS ON')            
    Comm.sendMsg('CALCULATE:AVERAGE 1')            
    Comm.sendMsg('ADJUST:SLOPE ON')
    Comm.sendMsg('TRIGGER:SOURCE EXT')
    Comm.sendMsg('INITIATE:CONTINUOUS ON')

def ReadDefault(Item):
    #get default setting values from .cfg file
    #the return values are string
    try:
        with open(current_path+"/"+configuration_filename) as configuration_file:
            lines = configuration_file.readlines()
        configuration_file.close()
        if Item == "FrequencyFile":
            return(lines[0].split('= ')[1].split('\n')[0])
        if Item == "OutputPath":
            return(lines[1].split('= ')[1].split('\n')[0])
        if Item == "ComPort":  
            return(lines[2].split('= ')[1].split('\n')[0])
        if Item == "BaudRate":
            return(lines[3].split('= ')[1].split('\n')[0])
        if Item == "SaveCSV":
            if lines[4].split('= ')[1].split('\n')[0] == "True":
                return(True)
            else:
                return(False)
        if Item == "MySQLDB":
            return(lines[5].split('= ')[1].split('\n')[0])
        if Item == "MySQLTable":
            return(lines[6].split('= ')[1].split('\n')[0])
        if Item == "SlopeFreq1":
            return(lines[7].split('= ')[1].split('\n')[0])
        if Item == "SlopeFreq2":
            return(lines[8].split('= ')[1].split('\n')[0])
        if Item == "X-AxisLowLimit":
            return(lines[9].split('= ')[1].split('\n')[0])
        if Item == "X-AxisHighLimit":
            return(lines[10].split('= ')[1].split('\n')[0])
        if Item == "Y-AxisLowLimit":
            return(lines[11].split('= ')[1].split('\n')[0])
        if Item == "Y-AxisHighLimit":
            return(lines[12].split('= ')[1].split('\n')[0])
        if Item == "Range":
            return(lines[13].split('= ')[1].split('\n')[0])
    except:
        messagebox.showerror("Open File Error", "Can't Open Configuration File!\nMake sure TBMEIS.cfg in in the current folder.")
        exit()

def SavetoMySQL(dfin, MSN):
    mydb = mysql.connector.connect(
        host = "192.168.1.84",
        user = "richard",
        password = "richardtbts",
        database = ReadDefault("MySQLDB")   #TBR_Battery_Test(official) or Richard(test)
    )
    mycursor = mydb.cursor()
    #create fieldlist and datalist in MySQL
    fieldlist = ['M_SN', 'Date', 'Time', 'Voltage', 'BIN']                                              #V1.20 add BIN to save to MySQL
    datalist = [MSN, dfin.loc[0,'Date'], dfin.loc[0,'Time'], dfin.loc[0,'V(V)'], win.frame_file.BIN]    #get the date, time and voltage from first point
    for i in range(0, len(dfin)):
        fieldlist.append('F{0:02d}_F'.format(i+1))
        datalist.append(dfin.loc[i,'FREQUENCY'])
        fieldlist.append('F{0:02d}_R'.format(i+1))
        datalist.append(dfin.loc[i,'R(ohm)'])
        fieldlist.append('F{0:02d}_X'.format(i+1))
        datalist.append(dfin.loc[i,'X(ohm)'])
    #sql is "INSERT INTO EIS (M_SN, Date, Time, Voltage, F01_F, F01_R, F01_X, ...) VALUES (MSN, Date, Time, Voltage, 1000, 0.000xxx, 0.000xxx, ...)"
    sql = "INSERT INTO "+ReadDefault("MySQLTable")+" ("
    #repeat generate the field name from indexlist into sql
    for i in range(0, len(fieldlist)):
        sql = sql+fieldlist[i]+','
    sql = sql[0:-1]+") VALUES ("
    #repeat generate the values from datalist into sql
    for i in range(0, len(datalist)):
        sql = sql+"'"+str(datalist[i])+"',"
    sql = sql[0:-1]+")"
    mycursor.execute(sql)   #write to MySQL and commit
    mydb.commit()

def ReadBinfromMySQL(MSN):
    mydb = mysql.connector.connect(
        host = "192.168.1.84",
        user = "richard",
        password = "richardtbts",
        database = "TBR_Battery_Test"
    )
    mycursor = mydb.cursor()
    sql = "SELECT BIN FROM Total WHERE M_SN = '{a}' ORDER BY Date DESC".format(a=MSN)
    mycursor.execute(sql)
    myresult = mycursor.fetchone()
    if myresult == None:
        return("X")
    else:    
        return(myresult[0].decode())


def ClearResult(selection):     #selection: All, MSNEntry or OutputResult
    #Clear Result in text, graph and slope+theta
    #clear MSN entry
    if selection == "All" or selection == "MSNEntry":
        win.frame_file.Entry2.configure(state=NORMAL)
        win.frame_file.Entry2.bind("<Return>", win.frame_file.Entry_Start)
        win.frame_file.Entry2.delete(0, END)
        win.frame_file.Entry2.update()
        win.frame_grade.Lable2.configure(text="")
        win.frame_file.Entry2.focus()    #set the cursor at output file entry
    if selection == "All" or selection == "OutputResult":
        #clear ResultText
        win.frame_text.TextBox1.configure(state=NORMAL)
        win.frame_text.TextBox1.delete(1.0, END)
        win.frame_text.TextBox1.configure(state=DISABLED)
        #clear ResultGraph
        chart.clear()
        chart.set_title("Nyquist Chart", fontsize=12)
        chart.invert_yaxis()
        chart.set_ylabel("X(Ohm)", fontsize=11)
        chart.set_xlabel("R(Ohm)", fontsize=11)
        chart.set_xlim([float(ReadDefault("X-AxisLowLimit")), float(ReadDefault("X-AxisHighLimit"))])
        chart.set_ylim([float(ReadDefault("Y-AxisLowLimit")), float(ReadDefault("Y-AxisHighLimit"))])
        chart.canvas.draw()
        #clear ProgBar
        win.frame_prog.ProgBar['value'] = 0
        win.frame_prog.Label1['text'] = "0%"
        #clear slope and theta
        win.frame_text.Label4.configure(text="")
        win.frame_text.Label5.configure(text="")

class CommFilter:
    def __init__(self, gui):
        if DebugWithoutCom:
            pass
        else:
            self.DownComm = usb_rs.Usb_rs(gui=gui)
        self.opend = False

    def open(self, port, speed):
        if DebugWithoutCom:
            self.opend = True
            return True
        else:
            if self.DownComm.open(port, speed):
                self.opend = True
                return True
            else:
                return False    
    
    def close(self):
        if DebugWithoutCom:
            self.opend = False
            return True
        else:    
            if self.DownComm.close():
                self.opend = False
                return True
            else:
                return False
    
    def sendMsg(self, Msgs):
        if DebugWithoutCom:
            self.PrevMsg = Msgs
            return True
        else:    
            if self.DownComm.sendMsg(Msgs):
                return True
            else:
                return False

    def receiveMsg(self, tout):
        if DebugWithoutCom:
            return("0.006,-0.006 7.588")
        else:
            msgBuf = self.DownComm.receiveMsg(tout)
            return msgBuf

    def SendQueryMsg(self, Msgstr, tout):
        debug_data = [[1000,"0.0065671,0.00282787,7.37814"],
                     [580,"0.00628132,0.00169447,7.37816"],
                     [340,"0.00614037,0.00093712,7.37814"],
                     [200,"0.00611339,0.000408554,7.37815"],
                     [110,"0.00618469,-7.45E-06,7.37815"],
                     [67,"0.0063031,-0.000265443,7.37815"],
                     [39,"0.00647533,-0.000481753,7.37815"],
                     [23,"0.00669506,-0.000666083,7.37815"],
                     [13,"0.00697566,-0.000836176,7.37814"],
                     [7.6,"0.00731187,-0.000998995,7.37815"],
                     [4.4,"0.00770709,-0.00112642,7.37814"],
                     [2.6,"0.00810023,-0.00122147,7.37813"],
                     [1.5,"0.00849225,-0.00133395,7.37814"],
                     [1,"0.00877006,-0.00146869,7.37812"],
                     [0.87,"0.00886432,-0.00153233,7.3781"],
                     [0.51,"0.00925799,-0.00186667,7.37808"],
                     [0.3,"0.00969718,-0.00238691,7.37807"],
                     [0.17,"0.010213,-0.00326531,7.37801"],
                     [0.1,"0.0107295,-0.00461955,7.37794"]]
        debug_df = pd.DataFrame(debug_data, columns=['FREQUENCY', 'Data'])
        if DebugWithoutCom:
            freq = float(self.PrevMsg.split(' ')[1])
            ret = debug_df.loc[(debug_df.FREQUENCY == freq)]['Data'].values[0]
            return(ret)
        else:
            msgbuf = self.DownComm.SendQueryMsg(Msgstr, tout)
            return msgbuf
    
class ComFrame(Frame):
    def __init__(self, window):
        super().__init__()
        self.config(bd=2)#, bg='blue')
        self.CreateWidget()
        self.Button1.configure(state=NORMAL)
        self.Button2.configure(state=DISABLED)

    def CreateWidget(self):
        #self.Communication = usb_rs.Usb_rs(gui=True)      #Create a Usb_rs object
        self.Communication = CommFilter(gui=True)
        self.Label1=Label(self, text="COM Port")
        self.Label2=Label(self, text="Buad Rate")
        self.Entry1 = Entry(self, width=8)
        self.Entry2 = Entry(self, width=8)
        self.Button1 = Button(self, text="Connect", command=self.Button1_Click, width=15)
        self.Button2 = Button(self, text="Disconnect", command=self.Button2_Click, width=15)
        self.Label1.grid(row=0, column=0, padx=10, pady=10, sticky=E)
        self.Label2.grid(row=1, column=0, padx=10, pady=10, sticky=E)
        self.Entry1.grid(row=0, column=1, padx=10, pady=10, sticky=W)
        self.Entry2.grid(row=1, column=1, padx=10, pady=10, sticky=W)
        self.Button1.grid(row=0, column=2, padx=10)
        self.Button2.grid(row=1, column=2, padx=10)

    def Button1_Click(self):    #Connect
        #win.frame_file.Entry2.configure(state=NORMAL)
        win.frame_prog.Button1.configure(state=DISABLED)
        port = self.Entry1.get()
        speed = int(self.Entry2.get())
        if not self.Communication.open(port, speed):  #Connect
            return
        Init_BT4560(self.Communication)
        self.Button1.configure(state=DISABLED)
        self.Button2.configure(state=NORMAL)
        self.Entry1.configure(state=DISABLED)
        self.Entry2.configure(state=DISABLED)

    def Button2_Click(self):    #Disconnect
        if DebugWithoutCom is False:
            self.Communication.close()                    #Disconnect
        self.Button1.configure(state=NORMAL)
        self.Button2.configure(state=DISABLED)
        self.Entry1.configure(state=NORMAL)
        self.Entry2.configure(state=NORMAL)
        #win.frame_file.Entry2.configure(state=DISABLED)
        win.frame_prog.Button1.configure(state=DISABLED)

class FileFrame(Frame):
    def __init__(self, window):
        super().__init__()
        self.config(bd=2)#, bg='green')
        #self.grid_propagate(0)      #將self的size固定
        self.abortflag = False
        self.timeoutflag = False
        self.connectionerrorflag = False
        self.reverseerrorflag = False
        self.CreateWidget()
        self.Entry1.configure(state=NORMAL)
        self.Entry2.configure(state=NORMAL)
        self.PreviousMSN = "Default"

    def CreateWidget(self):    
        self.Label1 = Label(self, text="Frequency List")
        self.Label2 = Label(self, text="Module SN")
        self.Entry1 = Entry(self, width=35)
        self.Entry2 = Entry(self, width=20, font="Arial 16 bold", bg="pink")
        self.Button1 = Button(self, text="Open", command=self.Button1_Click, width=10)
        self.Button2 = Button(self, text="Clear", command=self.Button2_Click, width=10)
        self.Label1.grid(row=0, column=0, padx=10, pady=10, sticky=E)
        self.Label2.grid(row=1, column=0, padx=10, pady=10, sticky=E)
        self.Entry1.grid(row=0, column=1, padx=10, pady=10, sticky=W)
        self.Entry2.grid(row=1, column=1, padx=10, pady=0, sticky=W)
        self.Button1.grid(row=0, column=2, padx=10)
        self.Button2.grid(row=1, column=2, padx=10)
        self.Entry2.bind("<Return>", self.Entry_Start)        #NOTE: This bind the entry key(<Return>) with Entry_Start
    
    def Button1_Click(self):    #Open frequency list
        freq_filename = filedialog.askopenfilename(title="Select File", filetypes=(("CSV files", ".csv"), ("All files", "*.*"),))
        if freq_filename is not None:   #insert the frequency list in FreqListFrame
            self.Entry1.delete(0, END)
            self.Entry1.insert(END, freq_filename)
            self.Entry1.update()
            freq_pd = pd.read_csv(freq_filename)
            freq_list = freq_pd['Frequency'].tolist()
            win.frame_list.TextBox1.configure(state=NORMAL)
            win.frame_list.TextBox1.delete(1.0, END)
            for i in range(0, len(freq_list)):
                win.frame_list.TextBox1.insert(END, str(freq_list[i])+'\n')
            win.frame_list.TextBox1.update()
    
    def Button2_Click(self):
        ClearResult("All")

    def Entry_Start(self, event):       #NOTE: This triggered by press the enter key in Entry2
        if win.frame_com.Communication.opend == True:               #check if COM Port is opend
            MSN = self.Entry2.get()
            if MSN == "":      #if Battery Test Number entry is empty
                messagebox.showerror("Error", "No Module SN,\nEnter Module Serial Number to Start!")
            elif MSN == self.PreviousMSN:
                messagebox.showwarning("Warning", "Module has been tested!")
                ClearResult("MSNEntry")
            else:
                self.BIN = ReadBinfromMySQL(MSN)
                win.frame_grade.Lable2.configure(text=self.BIN)
                threading.Thread(target=self.Threading_Start).start()
        else:
            messagebox.showerror("Error", "COM Port is not opend!")                
            win.frame_file.Entry2.delete(0,END)         #clear M_SN to begin
            win.frame_file.Entry2.update()

    def Threading_Start(self):
        global NQChart, NQChartplot
        NQChart = chart.scatter([], [])
        NQChartplot = chart.plot([], [])
        self.Button2.configure(state=DISABLED)                  #disable CLear
        win.frame_prog.Button1.configure(state=NORMAL)          #Enable Abort
        self.Entry2.configure(state=DISABLED)                   #disable M_SN Entry
        self.Entry2.bind("<Return>", lambda a: "break")
        ModuleSN = win.frame_file.Entry2.get()
        freq_list = win.frame_list.TextBox1.get(1.0, END).split('\n')
        df = pd.DataFrame(columns=['Date', 'Time', 'FREQUENCY', 'R(ohm)', 'X(ohm)', 'V(V)'])
        ClearResult("OutputResult")
        x = []
        y = []
        n = []
        deltapb = float(100/len(freq_list))     #each step equals 100th of number of frequency points
        #self.ProgBar.start(1200)
        win.frame_com.Communication.sendMsg('RANGE '+ReadDefault("Range"))   #set the range before measurement
        for i in range(0, len(freq_list)):
            win.frame_prog.ProgBar['value'] = (i+1)*deltapb
            win.frame_prog.Label1['text'] = "{0:.0f}%".format((i+1)*deltapb)
            if self.abortflag:
                break
            if freq_list[i] != '':
                cmd = 'FREQ '+freq_list[i]
                win.frame_com.Communication.sendMsg(cmd)
                msgBuf = win.frame_com.Communication.SendQueryMsg('*TRG;*WAI;FETCH?', 50)
                currenttime = datetime.datetime.now()
                if msgBuf == "Timeout Error":
                    self.timeoutflag = True
                    break
                R = msgBuf.split(',')[0]
                X = msgBuf.split(',')[1]
                V = msgBuf.split(',')[2]
                D = str(currenttime.strftime("%Y-%m-%d"))
                T = str(currenttime.strftime("%H:%M:%S"))
                if float(V) > 1E+8:        #value get from BT4560 > 1E+8 means H, or L connect error
                    self.connectionerrorflag = True
                    break
                if float(V) < 0:           #value get from BT4560 = 0 means reverse polarity error
                    self.reverseerrorflag = True
                    break
                if i == 0:      #print header of MSN, date, time and voltage
                    printstr = "Module SN = "+ModuleSN+'\n'+D+', '+T+', '+V+'\n'
                else:
                    printstr = ""
                msgBuf = msgBuf.replace(',', ', ', msgBuf.count(','))        #add space after comma
                printstr = printstr+freq_list[i]+', '+R+', '+X
                win.frame_text.TextBox1.configure(state=NORMAL)
                win.frame_text.TextBox1.insert(END, printstr+'\n')
                win.frame_text.TextBox1.see('end')
                win.frame_text.TextBox1.update()
                win.frame_text.TextBox1.configure(state=DISABLED)
                A_series = pd.Series([D, T, float(freq_list[i]), float(R), float(X), float(V)], index=df.columns)
                df = df.append(A_series, ignore_index=True)
                #draw chart
                n.append(float(freq_list[i]))       #Frequency
                x.append(float(R))       #R
                y.append(float(X))       #X
                if NQChart.axes is not None:
                    chart.clear()
                    chart.set_title("Nyquist Chart", fontsize=12)
                    chart.invert_yaxis()
                    chart.set_ylabel("X(Ohm)", fontsize=11)
                    chart.set_xlabel("R(Ohm)", fontsize=11)
                    chart.set_xlim([float(ReadDefault("X-AxisLowLimit")), float(ReadDefault("X-AxisHighLimit"))])
                    chart.set_ylim([float(ReadDefault("Y-AxisLowLimit")), float(ReadDefault("Y-AxisHighLimit"))])
#                    NQChart.remove()        #need to remove the old scatter chart or it will not be turn off by set_visible(False)
#                    NQChartplot.clear()
                NQChartplot = chart.plot(x, y, linestyle="solid", c="blue", zorder=2)
                NQChart = chart.scatter(x, y, c="red", s=10, zorder=1)    #make the scatter chart and put in NQChart
                #for j, txt in enumerate(n):            #put frequency as annotation
                #    chart.annotate(txt, (x[j], y[j]), xytext=(2, -2), textcoords="offset points")
                chart.canvas.draw()
        if self.abortflag:
            messagebox.showinfo("Abort", "Test Abort!")
            self.abortflag = False
        elif self.timeoutflag:
            messagebox.showerror("Timeout", "BT4560 Communication Timeout!")
            self.timeoutflag = False
        elif self.connectionerrorflag:
            #messagebox.showerror("Error", "Battery Connection Error!")
            win.frame_message.message.set("Bad Connection!")
            self.connectionerrorflag = False
        elif self.reverseerrorflag:
            #messagebox.showerror("Error", "Battery Reverse Connection!")
            win.frame_message.message.set("Battery Reversed!")
            self.reverseerrorflag = False
        else: 
            #messagebox.showinfo("Done", "Test Completed!")
            #calculate slope and theta
            X1 = df.loc[df.FREQUENCY == float(ReadDefault("SlopeFreq1"))]['R(ohm)'].values[0]
            X2 = df.loc[df.FREQUENCY == float(ReadDefault("SlopeFreq2"))]['R(ohm)'].values[0]
            Y1 = df.loc[df.FREQUENCY == float(ReadDefault("SlopeFreq1"))]['X(ohm)'].values[0]
            Y2 = df.loc[df.FREQUENCY == float(ReadDefault("SlopeFreq2"))]['X(ohm)'].values[0]   
            slope = -(X1-X2)/(Y1-Y2)
            theta = math.degrees(math.atan(1/slope))
            win.frame_text.Label4.configure(text='%.6f' % slope)
            win.frame_text.Label5.configure(text='%.6f' % theta)
            if ReadDefault("SaveCSV") == True:
                #df.to_excel(ReadDefault("OutputPath")+'/'+ModuleSN+'.xlsx', index=False)
                DT = currenttime.strftime("%y%m%d_%H%M")
                df.to_csv(ReadDefault("OutputPath")+'/'+ModuleSN+"_"+DT+".csv", index=False)
            #save data to excel and MySQL
            SavetoMySQL(df, ModuleSN)
            #save to previousMSN, enable and clear Entry2 for next test
            self.PreviousMSN = ModuleSN
            ClearResult("MSNEntry")

        #self.Entry2.configure(state=NORMAL)                 #enable M_SN Entry
        #self.Entry2.bind("<Return>", self.Entry_Start)
        self.Button2.configure(state=NORMAL)                #enable Clear
        win.frame_prog.Button1.configure(state=DISABLED)     #disable Abort

class ProgFrame(Frame):     #Progress Frame

    def __init__(self, window):
        super().__init__()
        self.config(bd=2)#, bg='purple')
        self.CreateWidget()
        self.Button1.configure(state=DISABLED)

    def CreateWidget(self):
        self.ProgBar = ttk.Progressbar(self, orient=HORIZONTAL, mode="determinate", length=177)
        self.Label1 = Label(self, text="0%", width=5)
        self.Button1 = Button(self, text="Abort", command=self.Button1_Click, width=12, height=1)
        self.ProgBar.grid(row=0, column=0, padx=5, pady=10, sticky=E)
        self.Label1.grid(row=0, column=1, padx=5, pady=10, sticky=W)
        self.Button1.grid(row=1, column=0, padx=5, pady=7, columnspan=2)

    def Button1_Click(self):    #Abort
        win.frame_file.abortflag = True
#        win.frame_file.Button2.configure(state=NORMAL)
#        self.Button1.configure(state=DISABLED)

class FreqListFrame(Frame):
    def __init__(self, window):
        super().__init__()
        self.config(bd=2, width=104, height=680)#, bg='pink')
        self.CreateWidget()

    def CreateWidget(self):
        self.Label1 = Label(self, text="Frequencies:")
        self.TextBox1 = Text(self, wrap=NONE, width=10, height=47)
        self.TextBox1.configure(font=textbox_font)
        self.Label1.place(x=10, y=10)
        self.TextBox1.place(x=10, y=40, width=80, height=630)

class ResultGraphFrame(Frame):
    def __init__(self, window):
        super().__init__()
        self.config(bd=12)#, width=500, height=680)#, bg='brown')        
        self.CreateWidget()

    def CreateWidget(self):
        global chart, NQChart, NQchartplot
        #NQChart = []            #Make empty list for nyquist traces of each module
        self.fig = Figure(figsize=(6,6), dpi=102, tight_layout=True)
        chart = self.fig.add_subplot(111)
        chart.set_title("Nyquist Chart", fontsize=12)
        chart.invert_yaxis()
        chart.set_ylabel("X(Ohm)", fontsize=11)
        chart.set_xlabel("R(Ohm)", fontsize=11)
        chart.set_xlim([float(ReadDefault("X-AxisLowLimit")), float(ReadDefault("X-AxisHighLimit"))])
        chart.set_ylim([float(ReadDefault("Y-AxisLowLimit")), float(ReadDefault("Y-AxisHighLimit"))])
        chart.canvas = FigureCanvasTkAgg(self.fig, self)
        chart.canvas.get_tk_widget().pack(side=BOTTOM, expand=1)
        toolbar = NavigationToolbar2Tk(chart.canvas, self)
        chart.canvas.draw()
        NQChart = chart.scatter([], [])
        NQChartplot = chart.plot([], [])

class ResultTextFrame(Frame):
    def __init__(self, win):
        super().__init__()
        self.config(bd=2, width=284, height=680)#, bg='orange')  
        self.CreateWidget()
        self.TextBox1.configure(state=DISABLED)

    def CreateWidget(self):
        self.Label1 = Label(self, text="Result:")
        self.TextBox1 = Text(self, wrap=NONE)
        self.Scrollbar1 = Scrollbar(self, orient=VERTICAL ,command=self.TextBox1.yview)
        self.Label2 = Label(self, text="Slope(m) = ")
        self.Label3 = Label(self, text="Theta("u"\N{GREEK SMALL LETTER THETA}) = ")
        self.Label4 = Label(self, text="", fg='red')
        self.Label5 = Label(self, text="", fg='red')
        self.TextBox1.config(yscrollcommand=self.Scrollbar1.set)
        self.TextBox1.configure(font=textbox_font)        
        self.Label1.place(x=10, y=10)
        self.TextBox1.place(x=10, y=40, width=242, height= 550)
        self.Scrollbar1.place(x=252, y=40, width=16, height=550)
        self.Label2.place(x=10, y=600)
        self.Label3.place(x=10, y=630)
        self.Label4.place(x=80, y=600)
        self.Label5.place(x=80, y=630)

class GradeFrame(Frame):
    def __init__(self, window):
        super().__init__()
        self.config(bd=2, width=100, height=100)#, bg='white')
        self.CreateWidget()

    def CreateWidget(self):
        self.Lable2 = Label(self, text="K", font=("Arial", 20, "bold"), fg="Blue")
        self.Lable2.pack()

class MessageFrame(Frame):
    def __init__(self, window):
        super().__init__()
        self.createWidget()
    
    def createWidget(self):
        self.message = StringVar()
        self.message.set("")
        self.Label1 = Label(self, textvariable=self.message, font=("Arial", 14), fg = "red")
        self.Label1.pack()

class MyMenu(Menu):
    def __init__(self, window):
        super().__init__()
        self.CreateWidget()
    
    def CreateWidget(self):
        self.Menu1 = Menu(self, tearoff=False)#, background='lightblue', foreground='black', activebackground='#004c99', activeforeground='white')
        self.Menu2 = Menu(self, tearoff=False)
        self.add_cascade(label="Settings", menu=self.Menu1)
        self.add_cascade(label="Help", menu=self.Menu2)
        self.Menu1.add_command(label="Default Values", command=self.Default_Values, font=("Arial", 9))
        self.Menu2.add_command(label="About", command=self.About, font=("Arial", 9))
        #self.Menubar.add_command(label="COM Port", command=self.COM_Port)

    def Default_Values(self):
        self.window_default = DefaultWindow(self)
        self.window_default.iconbitmap('icon.ico')
        self.window_default.title("Default Values Setting")
        #self.window_default.geometry("450x360")
    
    def About(self):
        messagebox.showinfo("TBMEIS", "Toyota Battery Module EIS Test\nVersion: {0:s}\nDate: {1:s}".format(Version, VersionDate))

class DefaultWindow(Toplevel):  
    def __init__(self, window):
        super().__init__()
        self.config(bd=2)
        self.CreateWidget()
        self.Button1_Click()    #read from cfg when open the window_default

    def CreateWidget(self):
        self.Label0 = Label(self, text="Configuration File: TBMEIS.cfg")
        self.Label1 = Label(self, text="Frequency List File:")
        self.Label2 = Label(self, text="Path of Output File:")
        self.Label3 = Label(self, text="COM Port:")
        self.Label4 = Label(self, text="Baud Rate:")
        self.Label5 = Label(self, text="Save CSV File:")
        self.Label6 = Label(self, text="Measurement Range:")
        self.Entry1 = Entry(self, width=35)
        self.Entry2 = Entry(self, width=35)
        self.Entry3 = Entry(self, width=35)
        self.Entry4 = Entry(self, width=35)
        self.savecsv = BooleanVar()
        self.RB5a = Radiobutton(self, text="Yes", variable=self.savecsv, value=True)
        self.RB5b = Radiobutton(self, text="No", variable=self.savecsv, value=False)
        self.range = IntVar()
        self.RB6a = Radiobutton(self, text="30m\u03A9", variable=self.range, value=1)
        self.RB6b = Radiobutton(self, text="300m\u03A9", variable=self.range, value=2)
        self.RB6c = Radiobutton(self, text="3\u03A9", variable=self.range, value=3)
        self.Label0.grid(row=0, column=0, padx=10, pady=10, columnspan=7)
        self.Label1.grid(row=1, column=0, padx=10, pady=10, sticky=E)
        self.Label2.grid(row=2, column=0, padx=10, pady=10, sticky=E)
        self.Label3.grid(row=3, column=0, padx=10, pady=10, sticky=E)
        self.Label4.grid(row=4, column=0, padx=10, pady=10, sticky=E)
        self.Label5.grid(row=5, column=0, padx=10, pady=10, sticky=E)
        self.Label6.grid(row=6, column=0, padx=10, pady=10, sticky=E)
        self.Entry1.grid(row=1, column=1, padx=10, pady=10, sticky=W, columnspan=6)
        self.Entry2.grid(row=2, column=1, padx=10, pady=10, sticky=W, columnspan=6)
        self.Entry3.grid(row=3, column=1, padx=10, pady=10, sticky=W, columnspan=6)
        self.Entry4.grid(row=4, column=1, padx=10, pady=10, sticky=W, columnspan=6)
        self.RB5a.grid(row=5, column=1, padx=10, pady=10, columnspan=3)
        self.RB5b.grid(row=5, column=4, padx=10, pady=10, columnspan=3)
        self.RB6a.grid(row=6, column=1, padx=10, pady=10, columnspan=2)
        self.RB6b.grid(row=6, column=3, padx=10, pady=10, columnspan=2)
        self.RB6c.grid(row=6, column=5, padx=10, pady=10, columnspan=2)

        self.Button1 = Button(self, text="Read", command=self.Button1_Click, width=10)
        self.Button2 = Button(self, text="Save", command=self.Button2_Click, width=10)
        self.Button3 = Button(self, text="Cancel", command=self.Button3_Click, width=10)
        self.Button1.grid(row=8, column=1, padx=10, pady=10, columnspan=2)
        self.Button2.grid(row=8, column=3, padx=10, pady=10, columnspan=2)
        self.Button3.grid(row=8, column=5, padx=10, pady=10, columnspan=2)

    def Button1_Click(self):    #Read
        self.Entry1.delete(0, END)
        self.Entry1.insert(END, ReadDefault("FrequencyFile"))
        self.Entry2.delete(0, END)
        self.Entry2.insert(END, ReadDefault("OutputPath"))
        self.Entry3.delete(0, END)
        self.Entry3.insert(END, ReadDefault("ComPort"))
        self.Entry4.delete(0, END)
        self.Entry4.insert(END, ReadDefault("BaudRate"))
        self.savecsv.set(ReadDefault("SaveCSV"))
        s = ReadDefault("Range")
        if s == "3.0E+0":  
            self.range.set(3)
        elif s == "300.0E-3":
            self.range.set(2)
        else: #"30.0E-3"
            self.range.set(1)

    def Button2_Click(self):    #Save
        with open(current_path+"/"+configuration_filename, 'r') as configuration_file:
            lines = configuration_file.readlines()
        configuration_file.close()

        lines[0] = "FrequencyFile = "+self.Entry1.get()+'\n'
        lines[1] = "OutputPath = "+self.Entry2.get()+'\n'
        lines[2] = "COMPort = "+self.Entry3.get()+'\n'
        lines[3] = "BaudRate = "+self.Entry4.get()+'\n'
        lines[4] = "SaveCSV = "+str(self.savecsv.get())+'\n'
        if self.range.get() == 1:
            s = "30.0E-3"
        elif self.range.get() == 2:
            s = "300.0E-3"
        elif self.range.get() == 3:
            s = "3.0E+0"
        lines[13] = "Range = "+s+'\n'
        

        with open(current_path+"/"+configuration_filename, 'w') as configuration_file:
            configuration_file.writelines(lines)
        configuration_file.close()

    def Button3_Click(self):    #Cancel
        self.destroy()
        win.Insert_Defaults()


class MainWindow(Frame):                #call by win = MainWindow(root)
    def __init__(self, window):         #self = MainWindow, window = root (this is pass from above)
        super().__init__()
        window.iconbitmap('icon.ico')
        window.title("TBMEIS")
        window.geometry("1024x778")
        self.menu_my = MyMenu(window)   
        self.frame_com = ComFrame(window)
        #self.line1 = Canvas(win, width=1, height=0).grid(row=0, column=1)
        self.frame_file = FileFrame(window)
        #self.line2 = Canvas(win, width=1, height=0).grid(row=0, column=11)
        self.frame_list = FreqListFrame(window)
        self.frame_text = ResultTextFrame(window)
        self.frame_graph = ResultGraphFrame(window)
        self.frame_prog = ProgFrame(window)
        self.frame_grade = GradeFrame(window)
        self.frame_message = MessageFrame(window)
        self.frame_com.place(y=0, x=0)
        self.frame_file.place(y=0, x=304)
        self.frame_prog.place(y=0, x=782)
        self.frame_list.place(y=88, x=0)
        self.frame_graph.place(y=92, x=104)
        self.frame_text.place(y=88, x=157+583)
        self.frame_grade.place(y=90, x=500)
        self.frame_message.place(y=90, x=450)
        self.Insert_Defaults()

    def Insert_Defaults(self):      #insert default values that reads from cfg file to desired entrys
        flname = ReadDefault("FrequencyFile")
        self.frame_com.Entry1.delete(0, END)
        self.frame_com.Entry1.insert(END, ReadDefault("ComPort"))
        self.frame_com.Entry1.update()
        self.frame_com.Entry2.delete(0, END)
        self.frame_com.Entry2.insert(END, ReadDefault("BaudRate"))
        self.frame_com.Entry2.update()
        self.frame_file.Entry1.delete(0, END)
        self.frame_file.Entry1.insert(END, flname)
        self.frame_file.Entry1.update()
        freq_pd = pd.read_csv(flname)
        freq_list = freq_pd['Frequency'].tolist()
        self.frame_list.TextBox1.configure(state=NORMAL)
        self.frame_list.TextBox1.delete(1.0, END)
        for i in range(0, len(freq_list)):
            self.frame_list.TextBox1.insert(END, str(freq_list[i])+'\n')
        self.frame_list.TextBox1.update()

if __name__=="__main__":
    CreateIcon()
    root = Tk()
    win = MainWindow(root)
    root.config(menu=win.menu_my)
    win.frame_com.Button1_Click()    #initial at COM pressed
    win.frame_file.Entry1.configure(state=DISABLED)
    win.frame_file.Button1.configure(state=DISABLED)
    win.frame_file.Entry2.focus()    #set the cursor at output file entry
    win.mainloop()