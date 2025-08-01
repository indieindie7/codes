import tkinter as tk
from tkinter import ttk
import CallInterface as CI
from unittest import case

#print(server)
janela = tk.Tk()
janela.title("Q/A")
janela.geometry("1000x500")
frame = ttk.Frame(janela)
frame.pack(expand=True, anchor="center")
connectedUsername=''
def mainMenu():


    login_option = ttk.Button(frame, text="Log in", command=lambda: [login(), hide()])
    login_option.grid(row=0,column=0,padx=20, pady=10)
    signup_option = ttk.Button(frame, text="Sign up", command=lambda: [signup(),hide()])
    signup_option.grid(row=1,column=0)

    def hide():
        login_option.grid_forget()
        signup_option.grid_forget()
mainMenu()
def signup():
    signup_frame = ttk.LabelFrame(frame, text='Register')
    signup_frame.grid(row=0, column=0, padx=20, pady=20)

    user_name = ttk.Label(signup_frame, text='User')
    user_name.grid(row=0, column=0, padx=20)

    user_name_entry = ttk.Entry(signup_frame)
    user_name_entry.grid(row=1,column=0, padx=20)

    user_pass = ttk.Label(signup_frame, text='Password')
    user_pass.grid(row=2, column=0)

    user_pass_entry = ttk.Entry(signup_frame,show="*")
    user_pass_entry.grid(row=3,column=0, padx=20)

    signup_button = ttk.Button(signup_frame, text="Sign up",
                                   command=lambda: [CI.RegisterUser(user_name_entry,user_pass_entry,signup_frame)])
    signup_button.grid(row=4, column=0,padx=20, pady=10)
    signup_button = ttk.Button(signup_frame, text="Return",
                                   command=lambda: [mainMenu(),signup_frame.grid_forget()])
    signup_button.grid(row=5, column=0, padx=20, pady=10)



def login():
    login_frame = ttk.LabelFrame(frame, text='Login')
    login_frame.grid(row=0, column=0, padx=20, pady=20)

    user_name = ttk.Label(login_frame, text='User')
    user_name.grid(row=0, column=0, padx=20)

    user_name_entry = ttk.Entry(login_frame)
    user_name_entry.grid(row=1,column=0, padx=20)

    user_pass = ttk.Label(login_frame, text='Password')
    user_pass.grid(row=2, column=0)

    user_pass_entry = ttk.Entry(login_frame,show="*")
    user_pass_entry.grid(row=3,column=0, padx=20)

    login_button = ttk.Button(login_frame, text="Log in",
                                  command=lambda: [CI.TryLogin(user_name_entry,user_pass_entry,login_frame)])
    login_button.grid(row=4, column=0,padx=20, pady=10)
    login_button = ttk.Button(login_frame, text="Return",
                                  command=lambda: [mainMenu(),login_frame.grid_forget()])
    login_button.grid(row=5, column=0, padx=20, pady=10)

def hideFrame(frame):
    frame.grid_forget()

def solicitacoes():
    request_frame = ttk.LabelFrame(frame, text="Requests")
    request_frame.grid(row=0, column=0, padx=20, pady=20)

    questions_button = ttk.Button(request_frame, text="Questions", command=lambda: [perguntas(), hideFrame()])
    questions_button.grid(row=1, column=0, padx=20, pady=20)

    answers_button = ttk.Button(request_frame, text="Answers", command=lambda: [respostas(0), hideFrame()])
    answers_button.grid(row=2, column=0, padx=20, pady=20)

    leaderboard_button = ttk.Button(request_frame, text="Leaderboard", command=lambda: [leaderboard(), hideFrame()])
    leaderboard_button.grid(row=3, column=0, padx=20, pady=20)

    def hideFrame():
        request_frame.grid_forget()


def leaderboard():
    leaderboard_frame = ttk.LabelFrame(frame, text="Leaderboard")
    leaderboard_frame.grid(row=0, column=0)

    def sort_treeview(tree, col, reverse):
        data = [(tree.set(item, col), item) for item in tree.get_children("")]
        #print(col)
        print(data)
        match col:
            case "name":
                #print(int(float(data[0][0][0])))
                data.sort(key=lambda x: x[0].lower(), reverse=reverse)
                pass
            case "questions":
                data.sort(key=lambda x: int(x[0]), reverse=reverse)

                print("questions")
                pass
            case "answers":
                data.sort(key=lambda x: int(x[0]), reverse=reverse)

                pass
        for index, (val, item) in enumerate(data):
            tree.move(item, '', index)  # Re-insert items in sorted order

        # Toggle the sorting direction for the next click
        tree.heading(col, command=lambda: sort_treeview(tree, col, not reverse))

    names = CI.get_user_names()
    print(names)
    questions = CI.getQuestonsCountArray(names)
    answers = CI.getAnswerCountArray(names)

    tree = ttk.Treeview(leaderboard_frame, columns=("name", "questions", "answers"), show="headings")
    tree.heading("name", text="User name", command=lambda: sort_treeview(tree, "name", False))
    tree.heading("questions", text="Number of questions", command=lambda: sort_treeview(tree, "questions", False))
    tree.heading("answers", text="Number of answers", command=lambda: sort_treeview(tree, "answers", False))

    for n in range(len(names)):
        tree.insert("", "end", values=(names[n], questions[n], answers[n]))
    tree.grid(row=0, column=0)

    returnButton = ttk.Button(leaderboard_frame, text="return", command=lambda:[solicitacoes(),leaderboard_frame.grid_forget()])
    returnButton.grid(row=1, column=1, padx=20, pady=20)

def perguntas():
    question_frame = ttk.LabelFrame(frame, text="")
    question_frame.grid(row=0, column=0, padx=20, pady=20)

    question = ttk.Label(question_frame, text='Question')
    question.grid(row=0, column=0, padx=20)

    question_entry = tk.Text(question_frame, width=50, height=2)
    question_entry.grid(row=0,column=1, padx=20)
    priority = ttk.Label(question_frame, text='Priority')
    priority.grid(row=1, column=0, padx=20)
    main_combobox = ttk.Combobox(question_frame,  values=["High", "Medium","Low"])
    main_combobox.set('Low')
    main_combobox.grid(row=1, column=1, padx=20, pady=20)

    submit_button = ttk.Button(question_frame, text="submit",
                               command=lambda: [CI.RegisterQuestion(question_entry.get("1.0",'end-1c'),main_combobox.get())])
    submit_button.grid(row=2, column=2, padx=20, pady=20)

    returnButton = ttk.Button(question_frame, text="return", command=lambda: [solicitacoes(), hideFrame()])
    returnButton.grid(row=3, column=2, padx=20, pady=20)
    def hideFrame():
        question_frame.grid_forget()

def respostas(sortIndex):
    answers_frame = ttk.LabelFrame(frame, text="Response")
    answers_frame.grid(row=0, column=0)
    filters_text = ttk.Label(answers_frame, text="Filters", width=40)
    filters_text.grid(row=1, column=0)
    main_combobox = ttk.Combobox(answers_frame, values=["High", "Medium","Low",'Any'])#,key=lambda :[print("") ,])
    def updatePriorityFilter():
        print(main_combobox.get())
        pass
    main_combobox.bind("<<ComboboxSelected>>", updatePriorityFilter)
    main_combobox.set('Any')

    main_combobox.bind(updatePriorityFilter)
    main_combobox.grid(row=1, column=1, padx=20, pady=20)
    result = CI.getColumns("questions")
    stringResults=[]
    print(result)
    for n in range(len(result)):
        stringResults.append(('Sort by ',result[n][0]))
    stringResults.append(('Sort by Answers'))
    sorts_text = ttk.Label(answers_frame, text="Sort", width=40)
    sorts_text.grid(row=2, column=0)
    main_combobox2 = ttk.Combobox(answers_frame, values=stringResults)
    main_combobox2.set(stringResults[0])
    main_combobox2.grid(row=2, column=1, padx=20, pady=20)

    def renderQuestionsLoop(sortIndex,Filter):
        inner_frame = ttk.LabelFrame(answers_frame, text="Inner Frame", padding=(10, 10))
        inner_frame.grid(row=3, column=1)
        results = CI.getQuestionArray()
        print(sortIndex)
        print(Filter)
        for n in range(len(results)):
            question_text = ttk.Label(inner_frame, text=results[n][2], justify="left", width=40)
            question_text.grid(row=n + 3, column=0)
            question_text = ttk.Label(inner_frame, text=(('Solved') if results[n][4]==1 else 'not solved' ))
            question_text.grid(row=n + 3, column=1)
            view_button = ttk.Button(inner_frame, text="view",
                                     command=lambda n1=n: [subresposta(results[n1][0]), answers_frame.grid_forget()])
            view_button.grid(row=n + 3, column=2)
            question_text = ttk.Label(inner_frame, text=('priority: ', results[n][3]))
            question_text.grid(row=n + 3, column=3)
            question_text = ttk.Label(inner_frame, text=('answer count: ', CI.getAnswerCount(results[n][0])))
            question_text.grid(row=n + 3, column=4)
        pass

    return_button = ttk.Button(answers_frame, text="return",
                               command=lambda: [solicitacoes(), answers_frame.grid_forget()])
    return_button.grid(row=4, column=2, padx=20, pady=20)
    renderQuestionsLoop(0,'Any')

def subresposta(index):
    subanswer_frame = ttk.LabelFrame(frame, text="Question")
    subanswer_frame.grid(row=0, column=0)
    print(index)
    results = CI.getAnswerArray(index)
    question =CI.LookupQuestion(index)
    question_text = ttk.Label(subanswer_frame, text=question[2], wraplength=300)
    question_text.grid(row=0, column=0)
    submit_entry = tk.Text(subanswer_frame, width=50, height=2)
    submit_entry.grid(row=1,column=0, padx=5)

    submit_button = ttk.Button(subanswer_frame, text="submit", command=lambda: [submit()])
    submit_button.grid(row=2, column=0, padx=20, pady=5)
    def submit():
        print("submit")
        CI.RegisterAnswer(connectedUsername,index,submit_entry.get("1.0",'end-1c'))
        submit_entry.delete("1.0",'end-1c')
        #submit_entry.insert(0, '')
        subanswer_frame.grid_forget()
        subresposta(index)


    returnButton = ttk.Button(subanswer_frame, text="return", command=lambda:[respostas(0),subanswer_frame.grid_forget()])
    returnButton.grid(row=2, column=1, padx=20, pady=20)
    answer = ttk.Label(subanswer_frame, text='Answers')
    answer.grid(row=3, column=0, padx=20)
    for n in range(len(results)):
        answer_text = ttk.Label(subanswer_frame, text=(results[n][3],'- by user '+results[n][1]), wraplength=300)
        answer_text.grid(row=n+4,column=0)



janela.mainloop()