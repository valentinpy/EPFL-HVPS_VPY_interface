from PyQt5 import QtGui, QtWidgets, QtSerialPort, QtCore
import numpy as np
import pyqtgraph as pg
import serial
import sys

nbChannels = 8


class ComSelect(QtWidgets.QDialog):
    """
    This class is a dialog window asking the user for COM port
    """
    def __init__(self, parent=None) :
        super(ComSelect, self).__init__(parent)

        # list all available com port in the combobox
        self.portname_comboBox = QtWidgets.QComboBox()
        for info in QtSerialPort.QSerialPortInfo.availablePorts():
            self.portname_comboBox.addItem(info.portName() + " " +info.description())

        buttonBox = QtWidgets.QDialogButtonBox()
        buttonBox.setOrientation(QtCore.Qt.Horizontal)
        buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        buttonBox.accepted.connect(self.accept)
        # buttonBox.rejected.connect(self.reject)

        lay = QtWidgets.QFormLayout(self)
        lay.addWidget(QtWidgets.QLabel("Please select COM port"))
        lay.addRow("Port Name:", self.portname_comboBox)
        lay.addRow(buttonBox)
        lay.addWidget(QtWidgets.QLabel("If using USB: select COM port with description: Silicon Labs CP210x...\n"))
        lay.addWidget(QtWidgets.QLabel("If using Bluetooth:"))
        lay.addWidget(QtWidgets.QLabel("The board has to be paired using Windows bluetooth settings\nbefore using this application"))
        lay.addWidget(QtWidgets.QLabel("LED DS2 must be blinking before connection"))
        lay.addWidget(QtWidgets.QLabel("LED DS3 will be ON after connection"))
        lay.addWidget(QtWidgets.QLabel("\nTry to connect to another COM port if unable to connect"))
        lay.addWidget(QtWidgets.QLabel("Try to disconnect and reconnect board power supply if unable to connect"))

        self.setGeometry(100, 100, 500, 120)


    def get_results(self):
        return self.portname_comboBox.currentText().split(" ")[0]



class HVPS_interface(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # init user interface + callback for buttons...
        self.init_ui()
        self.qt_connections()

        # init plot,...
        self.plotcurve0 = pg.PlotCurveItem()
        self.plotwidget0.addItem(self.plotcurve0)
        self.plotcurve1 = pg.PlotCurveItem()
        self.plotwidget1.addItem(self.plotcurve1)
        self.plotcurve2 = pg.PlotCurveItem()
        self.plotwidget2.addItem(self.plotcurve2)

        # init data arrays + time basis,...
        self.t = 0
        self.t = np.arange(300)
        self.Vtarget = np.zeros(shape=300)
        self.Vin = np.zeros(shape=300)
        self.Vout = np.zeros(shape=300)

        # open a dialog to ask port
        dialog = ComSelect()
        if dialog.exec_():
            portname = dialog.get_results()
            print("User selected com port: {}".format(portname))

            # open serial port
            try:
                self.ser = serial.Serial(portname, 115200, timeout=0.5)
                print("Connected to {}".format(self.ser.name))
            except:
                print("Please make sur than you use the right COM port")
                sys.exit(-1)

            # remove old data in input buffer
            self.ser.flushInput()
            line = self.ser.readline().decode("utf-8")
            print(line)
            if line == "":
                # if no data received, activate autosend by sending "d\n"
                self.ser.write(b'd')
                self.ser.write(b'\n')
                line = self.ser.readline().decode("utf-8")
                # print(line)
                if line == "":
                    print("no data received... ensure that the board has not been disconnected")
                    sys.exit(-1)

            # set a timer with the callback function which reads data from serial port and plot
            # period is 30ms => 33Hz, if enough data sent by the board
            self.timer = pg.QtCore.QTimer()
            self.timer.timeout.connect(self.updateplot)
            self.timer.start(20)
        else:
            print("canceled")
            sys.exit(0)

    def init_ui(self):
        #TODO: this is a little unclear, should be done better

        # ----------------------
        #main layout + window
        # ----------------------
        self.setWindowTitle('HVPS interface')
        layoutMain = QtWidgets.QHBoxLayout()
        self.setLayout(layoutMain)
        layoutMain.setSpacing(20)

        #----------------------
        # 3 plots with 3 titles
        # ----------------------
        layoutPlot = QtWidgets.QVBoxLayout()

        #plot 0
        self.plot0Title = QtWidgets.QLabel("DCDC output target voltage")
        layoutPlot.addWidget(self.plot0Title)
        self.plotwidget0 = pg.PlotWidget()
        layoutPlot.addWidget(self.plotwidget0)

        #plot 1
        self.plot1Title = QtWidgets.QLabel("DCDC input measured voltage")
        layoutPlot.addWidget(self.plot1Title)
        self.plotwidget1 = pg.PlotWidget()
        layoutPlot.addWidget(self.plotwidget1)

        #plot 2
        self.plot2Title = QtWidgets.QLabel("DCDC output measured voltage")
        layoutPlot.addWidget(self.plot2Title)
        self.plotwidget2 = pg.PlotWidget()
        layoutPlot.addWidget(self.plotwidget2)

        # ----------------------
        # Voltage selection: step and absolute
        # ----------------------
        self.btnVoltIncrease = QtGui.QPushButton("Increase voltage")
        self.btnVoltDecrease = QtGui.QPushButton("Decrease voltage")

        layoutBtnVoltageStep = QtWidgets.QVBoxLayout()
        layoutBtnVoltageStep.setSpacing(10)
        layoutBtnVoltageStep.addWidget(self.btnVoltIncrease)
        layoutBtnVoltageStep.addWidget(self.btnVoltDecrease)
        layoutBtnVoltageStep.addStretch(1)

        self.voltageTarget = QtGui.QLineEdit()
        self.voltageTargetConfirm = QtGui.QPushButton("Set voltage")
        layoutVoltageSet = QtWidgets.QHBoxLayout()
        layoutVoltageSet.setSpacing(10)
        layoutVoltageSet.addWidget(self.voltageTarget)
        layoutVoltageSet.addWidget(self.voltageTargetConfirm)
        layoutVoltageSet.addStretch(1)

        layoutVoltage = QtWidgets.QVBoxLayout()
        layoutVoltage.addLayout(layoutBtnVoltageStep)
        layoutVoltage.addLayout(layoutVoltageSet)
        layoutVoltage.addStretch(1)

        # ----------------------
        # Frequency selection
        # ----------------------
        self.FreqMeas = QtGui.QLabel("Current Frequncy")
        self.FreqTarget = QtGui.QLineEdit()
        self.FreqTargetConfirm = QtGui.QPushButton("Set frequency")
        layoutFreqSet = QtWidgets.QVBoxLayout()
        layoutFreqSet.setSpacing(10)
        layoutFreqSet.addWidget(self.FreqMeas)
        layoutFreqSet.addWidget(self.FreqTarget)
        layoutFreqSet.addWidget(self.FreqTargetConfirm)
        layoutFreqSet.addStretch(1)

        layoutFreq = QtWidgets.QVBoxLayout()
        layoutFreq.addLayout(layoutFreqSet)
        layoutFreq.addStretch(1)

        # ----------------------
        # Channel status + actuation
        # ----------------------
        self.channelNameText = []
        self.channelValueText = []
        self.channelChangeBtn = []

        layoutChannelStatus = QtWidgets.QFormLayout()

        self.allChannelsActivate = QtWidgets.QLabel("All channels switching")
        self.allChannelsActivateBtn =  QtWidgets.QPushButton("Activate")
        layoutChannelStatus.addRow(self.allChannelsActivate, self.allChannelsActivateBtn)

        self.allChannelsDeActivate = QtWidgets.QLabel("All channels switching")
        self.allChannelsDeActivateBtn =  QtWidgets.QPushButton("Deactivate")
        layoutChannelStatus.addRow(self.allChannelsDeActivate, self.allChannelsDeActivateBtn)


        for i in range(nbChannels):
            self.channelNameText.append(QtWidgets.QLabel("Channel {}".format(i)))
            self.channelValueText.append(QtWidgets.QLabel("status unknown".format(i)))
            self.channelValueText[i].setStyleSheet("background-color: rgb(255, 0, 0);")
            self.channelChangeBtn.append(QtWidgets.QPushButton("Test"))
            layoutChannelStatus.addRow(self.channelNameText[i], self.channelChangeBtn[i])


        # add all sub layouts to main
        layoutMain.addLayout(layoutPlot)
        layoutMain.addLayout(layoutVoltage)
        layoutMain.addLayout(layoutFreq)
        layoutMain.addLayout(layoutChannelStatus)

        self.setGeometry(100, 100, 1000, 600)
        self.show()

    def qt_connections(self):
        #buttons callbacks
        self.btnVoltIncrease.clicked.connect(self.on_btnVoltageIncrease_clicked)
        self.btnVoltDecrease.clicked.connect(self.on_btnVoltageDecrease_clicked)
        self.voltageTargetConfirm.clicked.connect(self.on_voltageChangeBtn_clicked)
        self.FreqTargetConfirm.clicked.connect(self.on_freqChangeBtn_clicked)

        #textbox callback when key "enter" pressed
        self.voltageTarget.returnPressed.connect(self.voltageTargetConfirm.click)
        self.FreqTarget.returnPressed.connect(self.FreqTargetConfirm.click)

        # this is absolutely awful! Should find a way to pass a parameter to the callback function
        # Should be dynamic in range: 0..nbChannels(-1)
        self.channelChangeBtn[0].clicked.connect(self.on_btn_channel_clicked_0)
        self.channelChangeBtn[1].clicked.connect(self.on_btn_channel_clicked_1)
        self.channelChangeBtn[2].clicked.connect(self.on_btn_channel_clicked_2)
        self.channelChangeBtn[3].clicked.connect(self.on_btn_channel_clicked_3)
        self.channelChangeBtn[4].clicked.connect(self.on_btn_channel_clicked_4)
        self.channelChangeBtn[5].clicked.connect(self.on_btn_channel_clicked_5)
        self.channelChangeBtn[6].clicked.connect(self.on_btn_channel_clicked_6)
        self.channelChangeBtn[7].clicked.connect(self.on_btn_channel_clicked_7)

        self.allChannelsActivateBtn.clicked.connect(self.on_btn_channel_activate_all)
        self.allChannelsDeActivateBtn.clicked.connect(self.on_btn_channel_deactivate_all)


    def updateplot(self):
        #shift time base
        self.t[:-1] = self.t[1:]
        self.t[-1] = self.t[-2]+1

        # shift data in the array one sample left
        self.Vtarget[:-1] = self.Vtarget[1:]
        self.Vin[:-1] = self.Vin[1:]
        self.Vout[:-1] = self.Vout[1:]

        # read from serial
        line = self.ser.readline().decode("utf-8")

        # if not data available: return and try later
        if "raw" not in line: # lines start with "raw", comma separated
            return

        # handle data
        data = line.split(";")
        self.Vtarget[-1] = float(data[1])
        self.Vin[-1] = float(data[2])
        self.Vout[-1] = float(data[3])
        self.currentFrequency = float(data[4])
        self.ChannelsStates = data[5]

        # plot
        self.plotcurve0.setData(self.t, self.Vtarget)
        self.plotcurve1.setData(self.t, self.Vin)
        self.plotcurve2.setData(self.t, self.Vout)

        #update plots title
        self.plot0Title.setText("DCDC output target voltage: {}V".format(data[1]))
        self.plot1Title.setText("DCDC input measured voltage: {}V".format(data[2]))
        self.plot2Title.setText("DCDC output measured voltage: {}V".format(data[3]))

        # update frequency label
        self.FreqMeas.setText("Current frequency: {} Hz".format(self.currentFrequency))

        #update channel status button: text + background color
        for i in range(nbChannels):
            if self.ChannelsStates[i] == "0":
                self.channelChangeBtn[i].setStyleSheet("background-color: rgb(255, 255, 0);")
                self.channelChangeBtn[i].setText("0V shorted")
            elif self.ChannelsStates[i] == "1":
                self.channelChangeBtn[i].setStyleSheet("background-color: rgb(0, 255, 0);")
                self.channelChangeBtn[i].setText("Switching")
            elif self.ChannelsStates[i] == "3":
                self.channelChangeBtn[i].setStyleSheet("background-color: rgb(255, 0, 255);")
                self.channelChangeBtn[i].setText("High Z")
            else:
                self.channelChangeBtn[i].setStyleSheet("background-color: rgb(127, 127, 127);")
                self.channelChangeBtn[i].setText("Unknown state: {}".format(self.ChannelsStates[i]))

        # flush input if too much data not handled: avoid keeping very old values
        if self.ser.in_waiting > 200:
            print(self.ser.in_waiting)
            self.ser.flushInput()

    def on_btnVoltageIncrease_clicked(self):
        print ("Increase voltage")
        self.ser.write(b'V+\n')

    def on_btnVoltageDecrease_clicked(self):
        print ("Decrease voltage")
        self.ser.write(b'V-\n')

    def on_voltageChangeBtn_clicked(self):
        try:
            newVoltage = int(self.voltageTarget.text())

            # check value in range ?
            if (newVoltage < 0) or (newVoltage > 400):
                print("please respect range [0;400]V")
                return

            #prepare bytes to send
            toSend = "V{:d}\n".format(newVoltage)
            print(toSend)
            toSend = bytearray(toSend, encoding="utf-8")
            self.ser.write(toSend)

        except:
            print("must write a NUMBER (int) instead of : {}".format(self.voltageTarget.text()))

    def on_freqChangeBtn_clicked(self):
        try:
            newFrequency = int(self.FreqTarget.text())

            # check value in range ?
            if (newFrequency < 1) or (newFrequency > 1000):
                print("please respect range [1;1000]Hz")
                return

            # prepare bytes to send
            toSend = "F{:d}\n".format(newFrequency)
            print(toSend)
            toSend = bytearray(toSend, encoding="utf-8")
            self.ser.write(toSend)
            print("setting new frequency: {}".format(newFrequency))

        except:
            print("must write a NUMBER (int) instead of : {}".format(self.voltageTarget.text()))

    # this is absolutely awful! Should find a way to pass a parameter to the callback function
    def on_btn_channel_clicked_0(self):
        self.on_btn_channel_clicked(0)

    def on_btn_channel_clicked_1(self):
        self.on_btn_channel_clicked(1)

    def on_btn_channel_clicked_2(self):
        self.on_btn_channel_clicked(2)

    def on_btn_channel_clicked_3(self):
        self.on_btn_channel_clicked(3)

    def on_btn_channel_clicked_4(self):
        self.on_btn_channel_clicked(4)

    def on_btn_channel_clicked_5(self):
        self.on_btn_channel_clicked(5)

    def on_btn_channel_clicked_6(self):
        self.on_btn_channel_clicked(6)

    def on_btn_channel_clicked_7(self):
        self.on_btn_channel_clicked(7)

    def on_btn_channel_activate_all(self):
        toSend = "C991\n"
        print(toSend)
        toSend = bytearray(toSend, encoding="utf-8")
        self.ser.write(toSend)
        # for channel in range(nbChannels):
        #     toSend = "C{:02d}{}\n".format(channel, 1)
        #     print(toSend)
        #     toSend = bytearray(toSend, encoding="utf-8")
        #     self.ser.write(toSend)

    def on_btn_channel_deactivate_all(self):
        toSend = "C990\n"
        print(toSend)
        toSend = bytearray(toSend, encoding="utf-8")
        self.ser.write(toSend)

        # for channel in range(nbChannels):
        #     toSend = "C{:02d}{}\n".format(channel, 0)
        #     print(toSend)
        #     toSend = bytearray(toSend, encoding="utf-8")
        #     self.ser.write(toSend)

    def on_btn_channel_clicked(self, channel):
        print("Clicked on channel: {}".format(channel))
        state = self.ChannelsStates[channel]

        if state == "0":
            newState = 1
        elif (state == "1") or (state == "2"):
            newState = 3
        else:
            newState = 0

        toSend = "C{:02d}{}\n".format(channel, newState)
        print(toSend)
        toSend = bytearray(toSend, encoding="utf-8")
        self.ser.write(toSend)
def main():
    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('HVPS interface')
    ex = HVPS_interface()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()