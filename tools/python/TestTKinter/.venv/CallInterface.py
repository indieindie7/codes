import mysql.connector
import tkinter
import tkinter.messagebox
from unicodedata import lookup
import tela_inicial as tela
def TryLogin(username,password,frame):
  if  _CheckUsername(username.get()):
    if  _CheckPassword(username.get(),password.get()):
      print("Login Successful")
      printMessageGUI('Login System',("Login Successful of ",username.get()))
      tela.connectedUsername=username.get()
      print(tela.connectedUsername)
      tela.solicitacoes()
      frame.grid_forget()
      return True
    print("Wrong password")
    printMessageGUI('Login System', "Wrong password")

    return False
  print("Wrong username")
  printMessageGUI('Login System', "Username not found")

  return False
def _CheckUsername(usernameStr):
    mydb = mysql.connector.connect(
        host="localhost",
        user="testUser",
        password="Uma1nova2Vila3",
        database="forum"
    )

    mycursor = mydb.cursor()
    mycursor.execute("SELECT 1 FROM accounts WHERE username = %s", (usernameStr,))
    record_exists = mycursor.fetchone() is not None
    print('Username is registered: ' if record_exists else 'Username not registered: ',usernameStr)
    mycursor.close()
    return record_exists
def _CheckPassword(usernameStr,passwordStr):
    mydb = mysql.connector.connect(
        host="localhost",
        user="testUser",
        password="Uma1nova2Vila3",
        database="forum"
    )

    mycursor = mydb.cursor()
    mycursor.execute("SELECT 1 FROM accounts WHERE username = %s and password = %s", (usernameStr,passwordStr))
    record_exists = mycursor.fetchone() is not None
    print('Account credentials approved: ' if record_exists else 'Account credentials not approved: ', usernameStr,' - ',passwordStr)
    mycursor.close()


    return record_exists
def printMessageGUI(title,message):
    tkinter.messagebox.showinfo(title, message)
def RegisterUser(username,password,frame):

    if len(username.get())==0:
        print("Username is empty")
        printMessageGUI("Register System","Username cannot be empty")
        return False
    usernameUsed = _CheckUsername(username.get())
    if not usernameUsed:
        if len(password.get()) ==0:
            print("Password is empty")
            printMessageGUI("Register System","Password cannot be empty")

            return False
        else:
            mydb = mysql.connector.connect(host="localhost",user="testUser",password="Uma1nova2Vila3",database="forum")
            mycursor = mydb.cursor()
            mycursor.execute("INSERT INTO accounts (username, password) VALUES (%s, %s);",
                             (username.get(), password.get()))
            mydb.commit()
            mycursor.close()
            printMessageGUI("Register System","Registered successfully")
            username.delete(0, tkinter.END)
            username.insert(0, "")
            password.delete(0, tkinter.END)
            password.insert(0, "")
            return True
    else:
        printMessageGUI("Register System","Username already registered")
    return False
def LookupQuestionText(description): #-1 return if question not on database
    mydb = mysql.connector.connect(host="localhost",
                                       user="testUser",
                                       password="Uma1nova2Vila3",
                                       database="forum")
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM questions WHERE description = %s", (description,))
    #result = mycursor.fetchall()
    result = mycursor.fetchall()
    mycursor.close()
    if len(result) !=0:
        print("Question exists made by ",result[0][1])
        for resulted in result:
            print(resulted)
        print(description,' - index of ',result[0][0])
        return result[0][0]
    print(" question: ",description," not found")
    return -1
def LookupQuestion(questionID):
    mydb = mysql.connector.connect(host="localhost",
                                       user="testUser",
                                       password="Uma1nova2Vila3",
                                       database="forum")
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM questions WHERE questionID = %s", (questionID,))
    #result = mycursor.fetchall()
    result = mycursor.fetchone()
    mycursor.close()
    if len(result) !=0:
        print("Question exists made by ",result[1])
        for resulted in result:
            print(resulted)
        #print(description,' - index of ',result[0])
        return result
    print(" question: ",description," not found")
    return result
def getQuestionArray(): #returns array of questions
    mydb = mysql.connector.connect(host="localhost",
                                       user="testUser",
                                       password="Uma1nova2Vila3",
                                       database="forum")
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM questions")
    #result = mycursor.fetchall()
    result = mycursor.fetchall()
    mycursor.close()
    return result
def getAnswerArray(index): #returns array of questions
    mydb = mysql.connector.connect(host="localhost",
                                       user="testUser",
                                       password="Uma1nova2Vila3",
                                       database="forum")
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM answers WHERE questionID = %s", (index,))
    #result = mycursor.fetchall()
    result = mycursor.fetchall()
    mycursor.close()
    return result
def getAnswerCount(questionId):
    mydb = mysql.connector.connect(host="localhost",
                                       user="testUser",
                                       password="Uma1nova2Vila3",
                                       database="forum")
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM answers WHERE questionID = %s", (questionId,))
    #result = mycursor.fetchall()
    result = mycursor.fetchall()
    mycursor.close()
    return len(result)
def RegisterQuestion(description,priority): #returns the questionid bigger than -1 if success
    print(priority)
    if(len(priority)==0):
        printMessageGUI("Question system","Priority cannot be empty")
        return -1
    print('connected user: ',tela.connectedUsername)
    print(description)
    #usernameUsed = CheckUsername(username)
    if len(description)==0:
        printMessageGUI("Question entry System","Description cannot be empty")
        print("Question is empty")
        return -1
    #if not usernameUsed:
    #    print("username is not registered ", username)
    #    return -1
    mydb = mysql.connector.connect(host="localhost",
                                       user="testUser",
                                       password="Uma1nova2Vila3",
                                       database="forum")
    mycursor = mydb.cursor()
    #If question already in, stop and return id of previous one
    valCheck =    LookupQuestionText(description)
    if valCheck != -1:
        print("Question already registered")
        printMessageGUI("Question entrySystem","Question already registered")
        return valCheck
    mycursor.execute("INSERT INTO questions (username, description,priority) VALUES (%s, %s,%s);",
                     (tela.connectedUsername, description, priority))
    mydb.commit()
    #printMessageGUI("Question entrySystem","Question registered")
    print("Registering question")
    mycursor.close()
    valCheck =    LookupQuestionText(description)
    if valCheck == -1:
        printMessageGUI("Question entrySystem","Question already registered")
        print("Question not registered")
        return valCheck
    printMessageGUI("Question entrySystem","Question registered successfully")
    print("Registered successfully")
    return valCheck
def RegisterAnswer(username,questionID,description):
    if not _CheckUsername(username):
        return -1
    if len(description)==0:
        print("Answer is empty")
        return -1
    mydb = mysql.connector.connect(host="localhost",
                                       user="testUser",
                                       password="Uma1nova2Vila3",
                                       database="forum")
    mycursor = mydb.cursor()
    valCheck = LookupAnswer(questionID,description)
    if valCheck != -1:
        print("Answer already registered")
        return valCheck
    mycursor.execute("INSERT INTO answers (username,questionID, description) VALUES (%s, %s,%s);", (username, questionID, description))
    mydb.commit()
    mycursor.close()
    printMessageGUI("Answer entrySystem","Answer registered successfully")
    print("Registered successfully")
    return LookupAnswer(questionID,description)
def LookupAnswer(questionID,description): #return
    mydb = mysql.connector.connect(host="localhost",
                                   user="testUser",
                                   password="Uma1nova2Vila3",
                                   database="forum")
    mycursor = mydb.cursor()
    mycursor.execute("SELECT * FROM answers WHERE questionID = %s AND description = %s", (questionID,description,))
    # result = mycursor.fetchall()
    result = mycursor.fetchall()
    mycursor.close()
    if len(result) != 0:
        print("Answer exists made by ", result[0][1])
        for resulted in result:
            print(resulted)
        print(description, ' - index of ', result[0][0])
        return result[0][0]
    print(" question: ", description, " not found")
    #printMessageGUI("Question system","Question does not exist")
    return -1
def getColumns(tableName):
    mydb = mysql.connector.connect(host="localhost",
                                       user="testUser",
                                       password="Uma1nova2Vila3",
                                       database="forum")
    mycursor = mydb.cursor()
    mycursor.execute("Show columns FROM questions")
    result = mycursor.fetchall()
    mycursor.close()
    return result
def get_user_names():
    mydb = mysql.connector.connect(host="localhost",
                                       user="testUser",
                                       password="Uma1nova2Vila3",
                                       database="forum")
    mycursor = mydb.cursor()
    mycursor.execute("Select username FROM accounts")
    result = mycursor.fetchall()
    mycursor.close()
    return result
def getQuestonsCountArray(names):
    mydb = mysql.connector.connect(host="localhost",
                                       user="testUser",
                                       password="Uma1nova2Vila3",
                                       database="forum")
    countResult =[]
    for n in names:
        mycursor = mydb.cursor()
        mycursor.execute("Select * FROM questions where username = %s", (n[0],))
        result = mycursor.fetchall()
        mycursor.close()
        countResult.append(len(result))
        pass

    return countResult
def getAnswerCountArray(names):
    mydb = mysql.connector.connect(host="localhost",
                                       user="testUser",
                                       password="Uma1nova2Vila3",
                                       database="forum")
    countResult =[]
    for n in names:
        mycursor = mydb.cursor()
        mycursor.execute("Select * FROM answers where username = %s", (n[0],))
        result = mycursor.fetchall()
        mycursor.close()
        countResult.append(len(result))
        pass

    return countResult
    pass