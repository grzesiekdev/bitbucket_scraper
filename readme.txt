Wymagania:
Python >= 3.8

Instalacja:
1. python3 -m venv venv
2. source venv/bin/activate
3. pip install -r requirements.text

Uruchomienie:
python main.py

Kofiguracja:
W pliku config.py ustawić należy następujące parametry:
1. request:
user: nazwa użytkownika konta na bitbucket
password: hasło użytkownika konta na bitbucket

2. converter_email:
email: adres email konta na https://json-csv.com/

3. smtp:
sender: adres email konta z którego wysyłka będzie się odbywać
password: hasło do konta wysyłającego maile
receiver: adres email konta na który maile powinny dochodzić
host: serwer smtp konta z którego odbywa się wysyłka
port: port ww. serwera
app_pass: tylko dla gmail
