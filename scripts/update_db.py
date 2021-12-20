from todo.models import *

def read_data():
    file = open(r"C:\Users\sivashankar.palraj\PycharmProjects\daily\scripts\Quotes.txt", "r", encoding="utf8")
    lines = file.readlines()
    return lines

def run():
    lines = read_data()
    for line in lines:
        line = line.strip()
        quot = line.split('-')[0]
        auth = line.split('-')[1]
        try:
            aut_obj = Auth_names.objects.get(name = auth)
            m = Quotes(quote = quot, auth = aut_obj)
            m.save()
        except:
            continue
