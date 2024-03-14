import configparser
import os
import platform
import time
import io
import csv
import traceback
import uuid
import paho.mqtt.client as paho
import tkinter

from   tkinter import ttk
from   tkinter import messagebox
from   tkinter import filedialog
from   os.path import normpath
from   paho    import mqtt
from   tksheet import Sheet

#---------------------- Fix local.DE -------------------
class locale:
    
    @staticmethod
    def atof(s):
        return float(s.strip().replace(',','.'))

    @staticmethod
    def format_string(fmt, *args):
        return  (fmt % args).replace('.',',')
    
#-------------------------------------------------------------------
# Define the GUI
#-------------------------------------------------------------------
class sheetapp_tk(tkinter.Tk):
    
    def __init__(self,parent):
        tkinter.Tk.__init__(self,parent)
        self.parent = parent
        self.initialize()
        self.run  =  0
        self.xRow = -1
        self.xCol = -1
        self.xVal = ''

    def showError(self, *args):
        err = traceback.format_exception(*args)
        messagebox.showerror('Exception',err)
        
        # but this works too
        tkinter.Tk.report_callback_exception = self.showError

    def initialize(self):
        noteStyle = ttk.Style()
        noteStyle.theme_use('default')
        noteStyle.configure("TNotebook", background='lightgray')
        noteStyle.configure("TNotebook.Tab", background='#eeeeee')
        noteStyle.map("TNotebook.Tab", background=[("selected", '#005fd7')],foreground=[("selected", 'white')])
        
        self.geometry("600x400")
        
        self.menuBar = tkinter.Menu(self)
        self.config(menu = self.menuBar)
        
        self.menuFile = tkinter.Menu(self.menuBar, tearoff=False)
        self.menuFile.add_command(command = self.saveSheet, label="Blatt speichern")
        self.menuFile.add_command(command = self.loadSheet, label="Blatt laden")
        self.menuFile.add_command(command = self.clearSheet, label="Blatt löschen")
        
        self.menuBar.add_cascade(label="Datei",menu=self.menuFile)
        
        self.pageHeader = tkinter.Label(self,text="Startnummer Eingabe",
                                        font=("Arial", 18),
                                        bg='#D3E3FD')
        self.pageHeader.pack(expand = 0, fill ="x") 
        
        self.tabControl = ttk.Notebook(self) 
        self.tabControl
          
        self.startTab   = ttk.Frame(self.tabControl) 
        self.tabControl.add(self.startTab, text ='Start') 
        
        self.finishTab   = ttk.Frame(self.tabControl) 
        self.tabControl.add(self.finishTab, text ='Ziel')
        
        self.tabControl.pack(expand = 1, fill ="both") 
         
        #----- Start Page -------
                 
        self.startTab.grid_columnconfigure(0, weight = 1)
        self.startTab.grid_rowconfigure(0, weight = 1)
        self.startSheet = Sheet(self.startTab,
                               name = 'startSheet',
                               #data = [['00:00:00','0,00','',''] for r in range(2)],
                               header = ['Uhrzeit','Zeitstempel','Startnummer','Bemerkung'],
                               header_bg = "azure",
                               header_fg = "black",
                               index_bg  = "azure",
                               index_fg  = "gray",
                               font = ("Calibri", 12, "bold")
                            )
        self.startSheet.enable_bindings()
        self.startSheet.grid(column = 0, row = 0)
        self.startSheet.grid(row = 0, column = 0, sticky = "nswe")
        self.startSheet.span('A:').align('right')
        self.startSheet.span('A').readonly()
        self.startSheet.span('B').readonly()
        
        self.startSheet.disable_bindings("All")
        self.startSheet.enable_bindings("edit_cell","single_select","right_click_popup_menu",
                                        "drag_select","row_select","copy")
        self.startSheet.extra_bindings("end_edit_cell", func=self.startEndEditCell)
        
        #----- Start Page -------
                 
        self.finishTab.grid_columnconfigure(0, weight = 1)
        self.finishTab.grid_rowconfigure(0, weight = 1)
        self.finishSheet = Sheet(self.finishTab,
                               name = 'finishSheet',
                               #data = [['00:00:00','0,00','',''] for r in range(2)],
                               header = ['Uhrzeit','Zeitstempel','Startnummer','Bemerkung'],
                               header_bg = "azure",
                               header_fg = "black",
                               index_bg  = "azure",
                               index_fg  = "gray",
                               font = ("Calibri", 12, "bold")
                            )
        self.finishSheet.enable_bindings()
        self.finishSheet.grid(column = 0, row = 0)
        self.finishSheet.grid(row = 0, column = 0, sticky = "nswe")
        self.finishSheet.span('A:').align('right')
        self.finishSheet.span('A').readonly()
        self.finishSheet.span('B').readonly()
        
        self.finishSheet.disable_bindings("All")
        self.finishSheet.enable_bindings("edit_cell","single_select","right_click_popup_menu",
                                         "drag_select","row_select","copy")
        self.finishSheet.extra_bindings("end_edit_cell", func=self.finishEndEditCell)
        
    def startEndEditCell(self, event):
        print("Start EndEditCell: ")
        
        for cell, value in event.cells.table.items():
            row = cell[0]
            col = cell[1]
            print(row,col,value)
            time   = self.startSheet[row,0].data
            stamp  = self.startSheet[row,1].data
            remark = str(self.startSheet[row,3].data).replace(' ','_')
            if col == 2:
                self.startSheet.after_idle(self.sendStartMsg,"{:} {:} {:} {:}".format(time,stamp,value,remark))
    
    def finishEndEditCell(self, event):
        print("Start EndEditCell: ")
        
        for cell, value in event.cells.table.items():
            row = cell[0]
            col = cell[1]
            print(row,col,value)
            time   = self.finishSheet[row,0].data
            stamp  = self.finishSheet[row,1].data
            remark = str(self.finishSheet[row,3].data).replace(' ','_')
            if col == 2:
                self.finishSheet.after_idle(self.sendFinishMsg,"{:} {:} {:} {:}".format(time,stamp,value,remark))
                     
    def sendStartMsg(self,*args):
        if messagebox.askyesno("MODBUS", "Sende Startnummer zur Basis ?"):
            if len(args) == 1:
                print("Send: ",args[0])
                mqtt_client.publish("elzwelle/stopwatch/start/number", payload=args[0], qos=1)
                
    def sendFinishMsg(self,*args):
        if messagebox.askyesno("MODBUS", "Sende Startnummer zur Basis ?"):
            if len(args) == 1:
                print("Send: ",args[0])
                mqtt_client.publish("elzwelle/stopwatch/finish/number", payload=args[0], qos=1)

    def getSelectedSheet(self):
        tab = self.tabControl.tab(self.tabControl.select(),"text")
        if tab == "Start":
            return self.startSheet
        elif tab == "Ziel":
            return self.finishSheet

    def saveSheet(self):
        saveSheet = self.getSelectedSheet()
        print("Save: "+saveSheet.name)
        # create a span which encompasses the table, header and index
        # all data values, no displayed values
        sheet_span = saveSheet.span(
            header=True,
            index=True,
            hdisp=False,
            idisp=False,
        )
        
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Save sheet as",
            filetypes=[("CSV File", ".csv"), ("TSV File", ".tsv")],
            defaultextension=".csv",
            confirmoverwrite=True,
        )
        if not filepath or not filepath.lower().endswith((".csv", ".tsv")):
            return
        try:
            with open(normpath(filepath), "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(
                    fh,
                    dialect=csv.excel if filepath.lower().endswith(".csv") else csv.excel_tab,
                    lineterminator="\n",
                )
                writer.writerows(sheet_span.data)
        except Exception as error:
            print(error)
            return

    def loadSheet(self):
        loadSheet = self.getSelectedSheet()
        print("Load: "+loadSheet.name)
        
        sheet_span = loadSheet.span(
            header=True,
            index=True,
            hdisp=False,
            idisp=False,
        )
        
        filepath = filedialog.askopenfilename(parent=self, title="Select a csv file")
        if not filepath or not filepath.lower().endswith((".csv", ".tsv")):
            return
        try:
            with open(normpath(filepath), "r") as filehandle:
                filedata = filehandle.read()
            loadSheet.reset()
            sheet_span.data = [
                r
                for r in csv.reader(
                    io.StringIO(filedata),
                    dialect=csv.Sniffer().sniff(filedata),
                    skipinitialspace=False,
                )
            ]
        except Exception as error:
            print(error)
            return
        
    def clearSheet(self):
        tab = self.tabControl.index(self.tabControl.select())  
        if messagebox.askyesno("Start/Ziel", "Alle Daten löschen ?"):
            print("Clear sheet:",tab)
            if tab == 0:
                self.startSheet.deselect()
                self.startSheet.data = []
            elif tab == 1:
                self.finishSheet.deselect()
                self.finishSheet.data = []
                
#-------------------------------------------------------------------

# setting callbacks for different events to see if it works, print the message etc.
def on_connect(client, userdata, flags, rc, properties=None):
    """
        Prints the result of the connection with a reasoncode to stdout ( used as callback for connect )

        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param flags: these are response flags sent by the broker
        :param rc: stands for reasonCode, which is a code for the connection result
        :param properties: can be used in MQTTv5, but is optional
    """
    print("CONNACK received with code %s." % rc)
    
    # subscribe to all topics of encyclopedia by using the wildcard "#"
    client.subscribe("elzwelle/stopwatch/#", qos=1)
        
    # a single publish, this can also be done in loops, etc.
    client.publish("elzwelle/monitor", payload="running", qos=1)
    

FIRST_RECONNECT_DELAY   = 1
RECONNECT_RATE          = 2
MAX_RECONNECT_COUNT     = 12
MAX_RECONNECT_DELAY     = 60

def on_disconnect(client, userdata, rc):
    print("Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        print("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            print("Reconnected successfully!")
            return
        except Exception as err:
            print("%s. Reconnect failed. Retrying...", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1
    print("Reconnect failed after %s attempts. Exiting...", reconnect_count)

# with this callback you can see if your publish was successful
def on_publish(client, userdata, mid, properties=None):
    """
        Prints mid to stdout to reassure a successful publish ( used as callback for publish )

        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param mid: variable returned from the corresponding publish() call, to allow outgoing messages to be tracked
        :param properties: can be used in MQTTv5, but is optional
    """
    print("Publish mid: " + str(mid))


# print which topic was subscribed to
def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    """
        Prints a reassurance for successfully subscribing

        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param mid: variable returned from the corresponding publish() call, to allow outgoing messages to be tracked
        :param granted_qos: this is the qos that you declare when subscribing, use the same one for publishing
        :param properties: can be used in MQTTv5, but is optional
    """
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


# print message, useful for checking if it was successful
def on_message(client, userdata, msg):
    """
        Prints a mqtt message to stdout ( used as callback for subscribe )

        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param msg: the message with topic and payload
    """
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
        
    payload = msg.payload.decode('ISO8859-1')        # ('utf-8')
                
    if msg.topic == 'elzwelle/stopwatch/start':
        if config.getboolean('view','start_enabled'):
            try:
                data = payload.split(' ')
                app.startSheet.insert_row([ data[0].strip(),
                                            data[1].strip(),
                                            data[2].strip(),
                                                ''])     
                row = app.startSheet.get_currently_selected().row    
                app.startSheet.see(row)
            except Exception as e:
                print("MQTT Decode exception: ",e,msg.payload)
            
    if msg.topic == "elzwelle/stopwatch/start/number/akn":
        if config.getboolean('view','start_enabled'):
            try:
                data  = payload.split(' ')
                stamp = data[1].strip()
                num   = data[2].strip() 
                row   = int(app.startSheet.span("B").data.index(str(stamp)))
                app.startSheet.set_cell_data(row,2,num)
                app.startSheet[row].highlight(bg = "aquamarine")   
                print("AKN: ",row,stamp,num)
                 
            except Exception as e:
                print("MQTT Decode exception: ",e,msg.payload)
            
    if msg.topic == 'elzwelle/stopwatch/finish':
        if config.getboolean('view','finish_enabled'):
            try:
                data = payload.split(' ')
                app.finishSheet.insert_row([ data[0].strip(),
                                             data[1].strip(),
                                             data[2].strip(),
                                                '']) 
                row = app.finishSheet.get_currently_selected().row 
                app.finishSheet.see(row)        
            except Exception as e:
                print("MQTT Decode exception: ",e,msg.payload)
            
    if msg.topic == "elzwelle/stopwatch/finish/number/akn":
        if config.getboolean('view','finish_enabled'):
            try:
                data  = payload.split(' ')
                stamp = data[1].strip()
                num   = data[2].strip()
                row = int(app.finishSheet.span("B").data.index(str(stamp)))
                app.finishSheet.set_cell_data(row,2,num)
                app.finishSheet[row].highlight(bg = "aquamarine")   
                print("AKN: ",row,stamp,num)
                 
            except Exception as e:
                print("MQTT Decode exception: ",e,msg.payload)
        
#-------------------------------------------------------------------
# Main program
#-------------------------------------------------------------------

if __name__ == '__main__':    
   
    myPlatform = platform.system()
    print("OS in my system : ", myPlatform)
    myArch = platform.machine()
    print("ARCH in my system : ", myArch)

    config = configparser.ConfigParser()
   
    config['mqtt']   = { 
        'url':'144db7091e4a45cbb0e14506aeed779a.s2.eu.hivemq.cloud',
        'port':8883,
        'tls_enabled':'yes',
        'auth_enabled':'no',
        'user':'welle',
        'password':'elzwelle', 
    }
      
    # Platform specific
    if myPlatform == 'Windows':
        # Platform defaults
        config.read('windows.ini') 
    if myPlatform == 'Linux':
        config.read('linux.ini')

    #--------------------------------- MQTT --------------------------

    # using MQTT version 5 here, for 3.1.1: MQTTv311, 3.1: MQTTv31
    # userdata is user defined data of any type, updated by user_data_set()
    # client_id is the given name of the client
    try:
        mqtt_client = paho.Client(client_id="elzwelle_"+str(uuid.uuid4()), userdata=None, protocol=paho.MQTTv311)
    
        # enable TLS for secure connection
        if config.getboolean('mqtt','tls_enabled'):
            #mqtt_client.tls_set(certfile="/etc/ssl/certs/isrgrootx1.pem",tls_version=mqtt.client.ssl.PROTOCOL_TLS)
            mqtt_client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
        # set username and password
        if config.getboolean('mqtt','auth_enabled'):
            mqtt_client.username_pw_set(config.get('mqtt','user'),
                                    config.get('mqtt','password'))
        # connect to HiveMQ Cloud on port 8883 (default for MQTT)
        mqtt_client.connect(config.get('mqtt','url'), config.getint('mqtt','port'))
    
        # setting callbacks, use separate functions like above for better visibility
        mqtt_client.on_connect      = on_connect
        mqtt_client.on_subscribe    = on_subscribe
        mqtt_client.on_message      = on_message
        mqtt_client.on_publish      = on_publish
        
        mqtt_client.loop_start()
    except Exception as e:
        messagebox.showerror(title="Fehler", message="Keine Verbindung zum MQTT Server!")
        print("Error: ",e)
        exit(1)   
        
    # ---------- setup and start GUI --------------
    app = sheetapp_tk(None)
    
    if not config.getboolean('view','start_enabled'):
        app.tabControl.tab(0, state="hidden")
        
    if not config.getboolean('view','finish_enabled'):
        app.tabControl.tab(1, state="hidden") 
    
    app.title("MQTT Start/Ziel Tabelle Elz-Zeit")
    
    app.startSheet.popup_menu_add_command(
        "Clear sheet data",
        app.clearSheet,
    )
    
    app.finishSheet.popup_menu_add_command(
        "Clear sheet data",
        app.clearSheet,
    )
    
    # run
    app.mainloop()
    print(time.asctime(), "GUI done")
          
    # Stop all dangling threads
    os.abort()