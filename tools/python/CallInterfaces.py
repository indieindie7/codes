import mysql.connector
import tkinter
from unicodedata import lookup
import tela_inicial as tela

def TryLogin(username,password):
  if  CheckUsername(username):
    if  CheckPassword(username,password):
      print("Login Successful")
      return True
    print("Wrong password")
    return False
  print("Wrong username")
  return False

def CheckUsername(usernameStr):
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

def CheckPassword(usernameStr,passwordStr):
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

    if record_exists:
        tela.hideframe()
    return record_exists

def RegisterUser(username,password):
    usernameUsed = CheckUsername(username)
    if len(username)==0:
        print("Username is empty")
        return False
    if not usernameUsed:
        if len(password) ==0:
            print("Password is empty")
            return False
        else:
            mydb = mysql.connector.connect(host="localhost",user="testUser",password="Uma1nova2Vila3",database="forum")
            mycursor = mydb.cursor()
            mycursor.execute("INSERT INTO accounts (username, password) VALUES (%s, %s);", (username, password))
            mydb.commit()
            mycursor.close()
            print("Registered successfully")
            return True
    else:
        print("Username already registered: ",username)
    return False

def LookupQuestion(description): #-1 return if question not on database
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

def getQuestionArray(): #returns array of questions
    pass

def getAnswerCount():
    pass

def RegisterQuestion(username,description): #returns the questionid bigger than -1 if success
    usernameUsed = CheckUsername(username)
    if len(description)==0:
        print("Question is empty")
        return -1
    if not usernameUsed:
        print("username is not registered ", username)
        return -1
    mydb = mysql.connector.connect(host="localhost",
                                       user="testUser",
                                       password="Uma1nova2Vila3",
                                       database="forum")
    mycursor = mydb.cursor()
    #If question already in, stop and return id of previous one
    valCheck =    LookupQuestion(description)
    if valCheck != -1:
        print("Question already registered")
        return valCheck
    mycursor.execute("INSERT INTO questions (username, description) VALUES (%s, %s);", (username, description))
    mydb.commit()
    print("Registering question")
    mycursor.close()
    valCheck =    LookupQuestion(description)
    if valCheck == -1:
        print("Question not registered")
        return valCheck

    print("Registered successfully")
    return valCheck

def RegisterAnswer(username,questionID,description):
    if not CheckUsername(username):
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
    return -1