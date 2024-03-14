import re
from symtable import SymbolTable
import instfile


class Entry:
    def __init__(self, string, token, attribute):
        self.string = string
        self.token = token
        self.att = attribute
    #add,'add',0x18
    #programname, 'id', 0x1000

symtable = []
inst = 0
objectCode = True
startLoadingAddress = 0
programSize = 0


#symatable related
def lookup(s):
    for i in range(0,len(symtable)):
        if s == symtable[i].string:
            return i
    return -1

def insert(string, token, attribute):
    symtable.append(Entry(string,token,attribute))
    return len(symtable) - 1

def init():
    for i in range(0,instfile.inst.__len__()):
        insert(instfile.inst[i], instfile.token[i], instfile.opcode[i])
    for i in range(0,instfile.directives.__len__()):
        insert(instfile.directives[i], instfile.dirtoken[i], instfile.dircode[i])

file = open('input.sic', 'r')
fileContent = []
bufferindex = 0
tokenval = 0
lineno = 1
pass1or2 = 1
locctr = 0
lookahead = ''
startLine = True

#Setting flags
Xbit4set = 0x800000
Bbit4set = 0x400000
Pbit4set = 0x200000
Ebit4set = 0x100000

Nbitset = 2
Ibitset = 1

Xbit3set = 0x8000
Bbit3set = 0x4000
Pbit3set = 0x2000
Ebit3set = 0x1000


def is_hex(s):
    if s[0:2].upper() == '0X':
        try:
            int(s[2:], 16)
            return True
        except ValueError:
            return False
    else:
        return False

#lexical analyzer
def lexan():
    global fileContent, tokenval, lineno, bufferindex, locctr, startLine

    while True:
        
        if len(fileContent) == bufferindex:
            return 'EOF'
        elif fileContent[bufferindex] == '#':
            startLine = True
            while fileContent[bufferindex] != '\n':
                bufferindex = bufferindex + 1
            lineno += 1
            bufferindex = bufferindex + 1
        elif fileContent[bufferindex] == '\n':
            startLine = True
           
            bufferindex = bufferindex + 1
            lineno += 1
        else:
            break
    if fileContent[bufferindex].isdigit():
        tokenval = int(fileContent[bufferindex])  
        
        bufferindex = bufferindex + 1
        return ('NUM')
    elif is_hex(fileContent[bufferindex]):
        tokenval = int(fileContent[bufferindex][2:], 16)  
        
        bufferindex = bufferindex + 1
        return ('NUM')
    elif fileContent[bufferindex] in ['+', '#', ',']:
        c = fileContent[bufferindex]
        
        bufferindex = bufferindex + 1
        return (c)
    else:
        
        if (fileContent[bufferindex].upper() == 'C') and (fileContent[bufferindex+1] == '\''):
            bytestring = ''
            bufferindex += 2
            while fileContent[bufferindex] != '\'':  
                bytestring += fileContent[bufferindex]
                bufferindex += 1
                if fileContent[bufferindex] != '\'':
                    bytestring += ' '
            bufferindex += 1
            bytestringvalue = "".join("%02X" % ord(c) for c in bytestring)
            bytestring = '_' + bytestring
            p = lookup(bytestring)
            if p == -1:
                p = insert(bytestring, 'STRING', bytestringvalue)  
            tokenval = p
        elif (fileContent[bufferindex] == '\''): 
            bytestring = ''
            bufferindex += 1
            while fileContent[bufferindex] != '\'':  
                bytestring += fileContent[bufferindex]
                bufferindex += 1
                if fileContent[bufferindex] != '\'':
                    bytestring += ' '
            bufferindex += 1
            bytestringvalue = "".join("%02X" % ord(c) for c in bytestring)
            bytestring = '_' + bytestring
            p = lookup(bytestring)
            if p == -1:
                p = insert(bytestring, 'STRING', bytestringvalue)  
            tokenval = p
        elif (fileContent[bufferindex].upper() == 'X') and (fileContent[bufferindex+1] == '\''):
            bufferindex += 2
            bytestring = fileContent[bufferindex]
            bufferindex += 2
            

            bytestringvalue = bytestring
            if len(bytestringvalue)%2 == 1:
                bytestringvalue = '0'+ bytestringvalue
            bytestring = '_' + bytestring
            p = lookup(bytestring)
            if p == -1:
                p = insert(bytestring, 'HEX', bytestringvalue)  
            tokenval = p
        else:
            p=lookup(fileContent[bufferindex].upper())
            if p == -1:
                if startLine == True:
                    p=insert(fileContent[bufferindex].upper(),'ID',locctr) 
                else:
                    p=insert(fileContent[bufferindex].upper(),'ID',-1) 
            else:
                if (symtable[p].att == -1) and (startLine == True):
                    symtable[p].att = locctr
            tokenval = p
            
            bufferindex = bufferindex + 1
        return (symtable[p].token)


def error(s):
    global lineno
    print('line ' + str(lineno) + ': '+s)

#checks for match, and reads next word
def match(token):
    global lookahead
    if lookahead == token:
        lookahead = lexan()
    else:
        error('Syntax error')


############################## Syntax grammer function ###################################################
def index():
    global inst
    if lookahead == ',':
        match(',')

        if pass1or2 == 2: 
            inst += Xbit3set
        prevRegIndex = tokenval
        match('REG')
        if (symtable[prevRegIndex].string != 'X') and (pass1or2 == 2):
            error('Index register should be X')



def rest3(prevStmtIndex):
    global inst
    if startLine == False: 
        inst += symtable[tokenval].att
        match('ID')
        index()
    else:
        if symtable[prevStmtIndex].string  != 'RSUB': # only RSUB is allowed to not have an operand
            error('Statement without operand')

    

def stmt():
    global locctr, startLine, inst

    startLine = False
    prevStmtIndex = tokenval 

    if pass1or2 == 2:
        inst = symtable[tokenval].att << 16 

    match('f3')
    locctr += 3
    rest3(prevStmtIndex)
    startLine = True

    if pass1or2 == 2:
        if not objectCode:
            print('0x{:06x}'.format(inst))
        else:
            print('T {:06x} {:02x} {:06x}'.format(locctr-3,3,inst))

def rest2():
    global locctr, symtable
    if lookahead == 'STRING':
        size = int(len(symtable[tokenval].att) / 2)
        locctr += size
        if pass1or2 == 2:
            if objectCode:
                print('T {:06x} {:02x}'.format(locctr-size, size)+' '+symtable[tokenval].att)
            else:
                print(symtable[tokenval].att)
        match('STRING')

    elif lookahead == 'HEX':
        size = int(len(symtable[tokenval].att) / 2)
        locctr += size
        if pass1or2 == 2:
            if objectCode:
                print('T {:06x} {:02x}'.format(locctr-size, size)+' '+symtable[tokenval].att)
            else:
                print(symtable[tokenval].att)
        match('HEX')
    else:
        error("wrong byte initialization")

def data():
    global locctr
    if lookahead == 'WORD':
        match('WORD')
        locctr += 3
        match('NUM')
        if pass1or2 == 2:
            if objectCode:
                print('T {:06x} {:02x} {:06x}'.format(locctr-3, 3,tokenval))
            else:
                print('0x{:06x}'.format(tokenval))

    elif lookahead == 'RESW':
        match('RESW')
        locctr += tokenval * 3
        if (pass1or2 == 2) and not objectCode:
            for i in range(tokenval):
                print("000000") 
        match('NUM')
    elif lookahead == 'RESB':
        match('RESB')
        locctr += tokenval
        if (pass1or2 == 2) and not objectCode:
            for i in range(tokenval):
                print("00") 
        match('NUM')
    elif lookahead == 'BYTE':
        match('BYTE')
        rest2()
    else:
        error("wrong data declaration")


def header():
    global locctr, symtable, startLoadingAddress, programSize
    tok = tokenval
    match('ID')
    match('START')
    startLoadingAddress = locctr = tokenval
    symtable[tok].att = tokenval
    match('NUM')

    if pass1or2 == 2:
        if objectCode:
            print('H ' + symtable[tok].string + ' {:06x} {:06x}'.format(startLoadingAddress, programSize))
    

def rest1():
    global inst
    if lookahead in ['WORD','RESW','RESB','BYTE']:
        data()
        body()
    elif lookahead == 'f3':
        stmt()
        body()

def body():
    if lookahead == 'ID':
        match('ID')
        rest1()
    elif lookahead == 'f3':
        stmt()
        body() 
    
    

def tail():
    global programSize
    programSize = locctr - startLoadingAddress
    match('END')
    previousTokenIndex = tokenval
    match('ID')

    if (pass1or2 == 2) and objectCode:
        print('E {:06x}'.format(symtable[previousTokenIndex].att))

def parse():
    global lookahead
    lookahead = lexan()
    #code header of the file "ProgramName start 0x1000"
    header()
    #code body, sic instructions "Opcode 1-byte	x-bit Address 15-bit"
    body()

    #code tail, sic instructions "end ......"
    tail()
#################################################################################

def main():
    global file, fileContent, locctr, pass1or2, bufferindex, lineno
    init()
    w = file.read()
    fileContent=re.split("([\W])", w)
    i=0
    while True:
        while (fileContent[i] == ' ') or (fileContent[i] == '') or (fileContent[i] == '\t'):
            del fileContent[i]
            if len(fileContent) == i:
                break
        i += 1
        if len(fileContent) <= i:
            break
    if fileContent[len(fileContent)-1] != '\n': #to be sure that the content ends with new line
        fileContent.append('\n')
    for pass1or2 in range(1,3):
        parse()
        bufferindex = 0
        locctr = 0
        lineno = 1

    file.close()


main()