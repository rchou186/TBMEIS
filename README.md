TBMEIS is the program for test each battery module in production line. This
program works with Hioki BT4560 Battery Impedance Meter to measure the Nyquist
chart. The output result save to CSV file and MySQL database directly for
further data analysis.

The files contained in this program:

TBMEIS.py           Main program
powereign_icon.py   Powereign (R) logo icon
usb_rs.py           BT4560 serial communication program
TBMEIS.cfg          Configuration file
frequency.csv       List of test frequencies
README.md           This file

Versions:

1.00
Date: 2021/07/20
 1. Initial Release

1.10
Date: 2021/07/23
 1. Auto connect to COM port with entering the program
 2. Disable the Frequency List entry and Open button to prevent operator miss
    operation
 3. The Nyquest chart shows schatter with lines
 4. R and X axes are fixed, the limits can by set in configuration file
 5. Output CSV file name saved with date and time
 6. The previous Module SN is logged, if operator run test of the same module
    in a row, the program will show repeat test warning
    After test is finished, no need to press Clear, operator can scan new 
    Module SN to start a new test
 7. Add error message when module polarity is reversed

1.20
Date: 2021/08/03
 1. Add reading bin grade from MySQL Total table and display on screen for
    user to double confirm
 2. Add MySQLDB in the cfg file to choose from official DB (TBR_Battery_Test)
    or test DB (Richard)

1.21
Date 2021/08/09
 1. The bin grading looked up from MySQL Total table will be stored in the EIS
    table.
    
1.30
Date 2021/08/20
 1. The measurement range of 30mOhm, 300mOhm and 3Ohm can be set in the .cfg
    file.
 2. The .cfg file add the Range at the last line 13.

1.31
Date 2021/08/27
 1. Change the location "Bad Connection!" and "Battery Reversed!" message on
    top of chart instead of pop-up window.
 2. Without the pop-up window, the user don't need to use the mouse or
    keyboard to close the pop-up window and clear the module SN entry.

1.32
Date 2021/10/14
 1. Add to check the length of the Module SN. If the MSN is not 12 digits,
    show "Length Error!" and wait for next test.
 2. If the Module SN is not in MySQL Total, show "Not Found!" and wait for 
    next test.